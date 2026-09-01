#!/usr/bin/env python3
"""skill-extractor — Cline タスク完了フック: 作業内容からスキルを自動生成/更新する。

概要
====
Cline の Hooks フォルダに置いた薄いラッパー (`taskcomplete.sh`) から呼ばれ、
完了した作業セッションのトランスクリプトを LLM に分析させ、
再利用可能な手順・知識があれば ./skills 配下の SKILL.md として作成/更新する。
変更があった場合、最後に setup_cline_skills.py --prune を実行して
Cline 用のフラット構造 (.agents/skills) の symlink を再構築する。

実体はこのファイル (git 管理)。Hooks フォルダにはラッパーのみを置く。

- トリガ: Cline タスク完了フック。stdin に JSON ペイロードが渡る。
  payload["hookName"] は "agent_end" (内部名) と "TaskComplete" (フック名) の両方を受け付ける。
- Cline のフック実行は 30 秒でタイムアウトする (v4.1.16 ではハードコード) ため、
  フック経由 (stdin ペイロード) のときは重い LLM 分析をデタッチしたバックグラウンド
  プロセス (--bg) に委譲し、フック自体は即座に完了する。stdout には空 JSON "{}" を返す。
- セッション情報: ~/.cline/data/db/sessions.db (SQLite)
- トランスクリプト: ~/.cline/data/sessions/<session_id>/<session_id>.messages.json
- LLM: DeepSeek Chat Completions (https://api.deepseek.com/v1/)。scripts/.env があれば
  読み込み、API ベース/モデル/キーを上書きできる (既存の環境変数が優先)。
  .env は setup_cline_skills.py が Cline の設定から書き出す (git 追跡対象外)。

使い方
------
    python3 skill-extractor.py --scope project            # フック経由 (stdin ペイロード)
    python3 skill-extractor.py --payload sample.json      # テスト (ファイルから)
    python3 skill-extractor.py --dry-run --payload ...    # 何も書き込まず確認
    python3 skill-extractor.py --no-llm --payload ...     # LLM を呼ばず配管のみ確認
    python3 skill-extractor.py --self-test                # 環境診断

環境変数 (すべて任意)
----------------------
    SKILL_EXTRACTOR_SKILLS_ROOT    スキルのルート   (デフォルト /workdir/skills)
    SKILL_EXTRACTOR_SETUP_SCRIPT   setup_cline_skills.py のパス
    SKILL_EXTRACTOR_API_BASE       LLM エンドポイント (デフォルト https://api.deepseek.com/v1)
    SKILL_EXTRACTOR_MODEL          LLM モデル        (デフォルト deepseek-v4-flash)
    SKILL_EXTRACTOR_API_KEY        API キー (未設定なら ~/.cline/data/secrets.json → providers.json)
    SKILL_EXTRACTOR_ENV_FILE       .env ファイルのパス (デフォルト scripts/.env。存在すれば読み込む)
    SKILL_EXTRACTOR_LOG_DIR        ログ・マーカーのディレクトリ
                                  (デフォルト ~/.cline/data/logs/skill-extractor)
    SKILL_EXTRACTOR_MIN_MESSAGES   分析対象とする最小メッセージ数 (デフォルト 4)
    SKILL_EXTRACTOR_MAX_TRANSCRIPT_CHARS  トランスクリプト上限 (デフォルト 100000)
    SKILL_EXTRACTOR_MAX_TOKENS     LLM 出力上限 (デフォルト 8000)
    SKILL_EXTRACTOR_TIMEOUT        LLM 呼び出しタイムアウト秒 (デフォルト 180)
    SKILL_EXTRACTOR_DISABLE=1      無効化 (即終了・ログのみ)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数・デフォルト
# ---------------------------------------------------------------------------
HOME = Path.home()
CLINE_DATA = Path(os.environ.get("CLINE_DATA_DIR", HOME / ".cline" / "data"))
SESSIONS_DIR = CLINE_DATA / "sessions"
SESSIONS_DB = CLINE_DATA / "db" / "sessions.db"
SECRETS_JSON = CLINE_DATA / "secrets.json"
PROVIDERS_JSON = CLINE_DATA / "settings" / "providers.json"

DEFAULT_SKILLS_ROOT = Path("/workdir/skills")
DEFAULT_SETUP_SCRIPT = Path("/workdir/scripts/setup_cline_skills.py")
DEFAULT_API_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_LOG_DIR = CLINE_DATA / "logs" / "skill-extractor"

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = Path(os.environ.get("SKILL_EXTRACTOR_ENV_FILE", str(SCRIPT_DIR / ".env")))

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.S | re.M)
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def env_or(name: str, default):
    """環境変数を読み、空文字ならデフォルト。bool 化もサポート。"""
    v = os.environ.get(name, "")
    if v == "":
        return default
    if isinstance(default, bool):
        return v.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(default, int):
        try:
            return int(v)
        except ValueError:
            return default
    return v


def load_env_file(path: Path) -> None:
    """scripts/.env があれば読み込み os.environ へ反映する (既存 env 優先・書き込みはしない)。

    KEY=VALUE 形式。コメント (#) と空行は無視し、値の前後の引用符は除去する。
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


load_env_file(ENV_FILE)  # モジュール読み込み時点で反映 (resolve_api_key / env_or / self_test が対象)


# ---------------------------------------------------------------------------
# ログ
# ---------------------------------------------------------------------------
class Logger:
    """フックは detached 実行で stdout が捨てられるため、常にファイルへ書く。

    - log():    runs.log へ追記。簡易サマリ用 (時刻 + 件数 + 一言メモ)。
    - detail(): stdout のみ (runs.log には書かない)。詳細はバックグラウンド
                ワーカーの bg-<session>.log 側へ流れる。
    quiet=True (フックのフォアグラウンド) では detail は抑制される。
    """

    def __init__(self, log_dir: Path, quiet: bool = False):
        self.log_dir = log_dir
        self.runs_log = log_dir / "runs.log"
        self.quiet = quiet
        log_dir.mkdir(parents=True, exist_ok=True)

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def log(self, message: str) -> None:
        line = f"[{self._ts()}] {message}\n"
        try:
            with open(self.runs_log, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass  # ログが書けなくてもフックは壊さない
        if not self.quiet:
            print(message)  # 手動実行時の可視化用 (フック時は捨てられる)

    def detail(self, message: str) -> None:
        """runs.log には書かず、詳細を stdout だけに出す (bg ログ向け)。"""
        if not self.quiet:
            print(message)


def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "..." + key[-4:]


# ---------------------------------------------------------------------------
# frontmatter / SKILL.md 検証
# ---------------------------------------------------------------------------
def parse_frontmatter(text: str) -> dict[str, str]:
    """SKILL.md の YAML frontmatter から name / description を簡易抽出。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)

    def _val(key: str) -> str | None:
        mm = re.search(rf"^{key}:\s*(.+?)\s*$", body, re.M)
        if not mm:
            return None
        v = mm.group(1)
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            return v[1:-1]
        return v

    return {"name": _val("name"), "description": _val("description")}


def strip_user_input_wrapper(text: str) -> str:
    """<user_input mode="..."> ラッパーを外す。"""
    text = re.sub(r"<user_input[^>]*>", "", text)
    text = text.replace("</user_input>", "")
    return text.strip()


# ---------------------------------------------------------------------------
# トランスクリプト抽出
# ---------------------------------------------------------------------------
def load_transcript(messages_path: Path, max_chars: int) -> str:
    """messages.json を読み、要約したトランスクリプト文字列を返す。

    - thinking は除外 (トークン節約)
    - tool_result はツール名 + 先頭 800 文字
    - 合計 max_chars で切り詰め
    """
    data = json.loads(messages_path.read_text(encoding="utf-8", errors="replace"))
    msgs = data.get("messages", []) if isinstance(data, dict) else data
    lines: list[str] = []

    for m in msgs:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content") or []
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if not isinstance(content, list):
            continue

        for item in content:
            if not isinstance(item, dict):
                continue
            itype = item.get("type")
            if itype == "thinking":
                continue
            if itype == "text":
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                if role == "user":
                    text = strip_user_input_wrapper(text)
                    if text:
                        lines.append(f"USER: {text}")
                else:
                    lines.append(f"ASSISTANT: {text[:1200]}")
            elif itype == "tool_result":
                name = item.get("name", "?")
                raw = item.get("content", "")
                if isinstance(raw, list):
                    parts = []
                    for x in raw:
                        if isinstance(x, dict):
                            parts.append(str(x.get("result", "")))
                        else:
                            parts.append(str(x))
                    raw = "\n".join(parts)
                raw = str(raw).strip()
                if raw:
                    lines.append(f"TOOL RESULT ({name}): {raw[:800]}")
            elif itype == "tool_use":
                name = item.get("name", "?")
                lines.append(f"TOOL USE: {name}")

    transcript = "\n\n".join(lines).strip()
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n...[transcript truncated]"
    return transcript


# ---------------------------------------------------------------------------
# セッション解決
# ---------------------------------------------------------------------------
def resolve_session(payload: dict, db_path: Path) -> dict | None:
    """ペイロードの agentId / conversationId からセッション行を引く。

    フォールバック: 最新セッション (フックはタスク完了直後に発火するため)。
    """
    agent_id = payload.get("agentId")
    conv_id = payload.get("conversationId")
    candidates: list[str] = []
    for v in (conv_id, agent_id):
        if isinstance(v, str) and v:
            candidates.append(v)

    row = None
    cols = []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        try:
            cols = [r[1] for r in con.execute("PRAGMA table_info(sessions)")]
            for key in ("session_id", "conversation_id", "agent_id"):
                if key not in cols:
                    continue
                for v in candidates:
                    row = con.execute(
                        f"SELECT * FROM sessions WHERE {key} = ? ORDER BY started_at DESC LIMIT 1",
                        (v,),
                    ).fetchone()
                    if row:
                        break
                if row:
                    break
            if not row:
                row = con.execute(
                    "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1"
                ).fetchone()
        finally:
            con.close()
    except (sqlite3.Error, OSError) as exc:
        print(f"[warn] sessions.db を読めません: {exc}")
        return None

    if not row:
        return None
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# 既存スキル一覧
# ---------------------------------------------------------------------------
def list_skills(skills_root: Path) -> tuple[list[str], list[str]]:
    """(カテゴリ一覧, 'category/name' 一覧) を返す。"""
    categories: list[str] = []
    skills: list[str] = []
    if not skills_root.is_dir():
        return categories, skills
    for cat in sorted(skills_root.iterdir()):
        if not cat.is_dir() or cat.name.startswith("."):
            continue
        categories.append(cat.name)
        for md in sorted(cat.glob("*/SKILL.md")):
            skills.append(f"{cat.name}/{md.parent.name}")
    return categories, skills


# ---------------------------------------------------------------------------
# LLM 呼び出し
# ---------------------------------------------------------------------------
def resolve_api_key() -> str | None:
    """API キーを env → secrets.json → providers.json の順で探す。"""
    for env_name in ("SKILL_EXTRACTOR_API_KEY", "DEEPSEEK_API_KEY"):
        v = os.environ.get(env_name, "")
        if v:
            return v
    try:
        data = json.loads(SECRETS_JSON.read_text(encoding="utf-8"))
        key = data.get("deepSeekApiKey") or data.get("apiKey")
        if key:
            return key
    except (OSError, json.JSONDecodeError):
        pass
    try:
        data = json.loads(PROVIDERS_JSON.read_text(encoding="utf-8"))
        key = (
            data.get("providers", {})
            .get("deepseek", {})
            .get("settings", {})
            .get("apiKey")
        )
        if key:
            return key
    except (OSError, json.JSONDecodeError):
        pass
    return None


def call_llm(
    api_base: str,
    model: str,
    api_key: str,
    system_prompt: str,
    user_content: str,
    max_tokens: int,
    timeout: int,
) -> str:
    """DeepSeek Chat Completions を呼び、応答テキストを返す。"""
    url = api_base.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# LLM プロンプト
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are "skill-extractor", an expert at distilling reusable knowledge from completed AI coding-assistant work sessions into skill files (SKILL.md) kept in a repository's ./skills directory.

Your job: read the transcript of ONE completed work session and decide whether it demonstrates a concrete, reusable, non-obvious procedure, workflow, or body of knowledge worth capturing as a skill.

Strict rules:
- Propose a skill ONLY when the session demonstrated something clearly reusable (e.g. a non-trivial setup procedure, a workflow, an API usage pattern, troubleshooting steps, project conventions). Do NOT propose skills for trivial one-off questions or short Q&A.
- Prefer updating an existing skill over creating a near-duplicate. If an existing skill already covers the topic and the session adds nothing meaningful, return skills: [].
- The skill name must be kebab-case and match the `name` field in the YAML frontmatter.
- The SKILL.md content MUST start with a YAML frontmatter block:
  ---
  name: <kebab-case name>
  description: "one-line description"
  version: 1.0.0
  author: Hermes Agent
  license: MIT
  platforms: [linux, macos, windows]
  metadata:
    hermes:
      tags: [comma, separated, lowercase]
      related_skills: [existing skill name if obviously related]
  ---
  followed by a markdown body. Keep the body actionable: Overview, concrete steps, commands, examples.
- `category` MUST be one of the existing category folder names provided to you when possible. If no category fits, use a short new kebab-case category.
- Keep the response compact: each SKILL.md body should be roughly 500-1500 characters (concise but actionable). Do not pad.
- Only output valid JSON, nothing else (no markdown fences). Schema:
  {"summary": "<one short line, Japanese or English, why/what>", "skills": [{"action": "create"|"update", "category": "...", "name": "...", "content": "<full SKILL.md text>"}]}
  If nothing is worth capturing: {"summary": "...", "skills": []}
"""


def build_user_content(
    session: dict, transcript: str, categories: list[str], skills: list[str]
) -> str:
    lines = [
        f"Session: {session.get('session_id')}",
        f"Model: {session.get('model')}",
        f"Prompt: {str(session.get('prompt'))[:200]}",
        f"Started: {session.get('started_at')}",
        "",
        "Existing category folders under ./skills:",
        json.dumps(categories, ensure_ascii=False),
        "",
        "Existing skills (category/name):",
        json.dumps(skills, ensure_ascii=False),
        "",
        "Analyze this completed work session and respond with JSON only.",
        "",
        "<transcript>",
        transcript,
        "</transcript>",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 提案の適用
# ---------------------------------------------------------------------------
def parse_proposal(raw: str) -> dict:
    """LLM 応答から JSON を抽出 (コードフェンスがあれば除去)。"""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def apply_changes(
    proposal: dict, skills_root: Path, dry_run: bool
) -> list[dict]:
    """提案を ./skills に適用し、変更サマリを返す。"""
    changed: list[dict] = []
    for s in proposal.get("skills", []):
        action = s.get("action", "create")
        category = str(s.get("category", "")).strip().strip("/")
        content = str(s.get("content", "")).strip()
        name = str(s.get("name", "")).strip()

        if not category or not content:
            print(f"[warn] 提案が不完全 (category/content 欠落): {s}")
            continue

        fm = parse_frontmatter(content)
        if not fm.get("name"):
            print(f"[warn] frontmatter に name がありません。スキップ: {name}")
            continue
        name = fm["name"]  # frontmatter を正とする
        if not NAME_RE.fullmatch(name):
            print(f"[warn] 不正なスキル名 '{name}'。スキップ")
            continue

        target = skills_root / category / name / "SKILL.md"
        existed = target.exists()

        if action == "update" and not existed:
            action = "create"  # 存在しない update は create として扱う
        if action == "create" and existed:
            action = "update"  # 既存への create は update として扱う

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content + "\n", encoding="utf-8")

        changed.append(
            {
                "action": action,
                "path": str(target),
                "was_existed": existed,
            }
        )
        print(f"[{action}] {target}")
    return changed


# ---------------------------------------------------------------------------
# setup_cline_skills.py 実行
# ---------------------------------------------------------------------------
def run_setup(skills_root: Path, dry_run: bool) -> str | None:
    """skills_root から .agents/skills への symlink を再構築する。"""
    candidates = [
        env_or("SKILL_EXTRACTOR_SETUP_SCRIPT", None),
        skills_root.parent / "setup_cline_skills.py",
        Path("/workdir/scripts/setup_cline_skills.py"),
        DEFAULT_SETUP_SCRIPT,
    ]
    script = None
    for c in candidates:
        if c and Path(c).is_file():
            script = Path(c)
            break
    if not script:
        print("[warn] setup_cline_skills.py が見つかりません。スキップ")
        return None

    target = skills_root.parent / ".agents" / "skills"
    cmd = [sys.executable, str(script), "--source", str(skills_root),
           "--target", str(target), "--prune"]
    if dry_run:
        cmd.append("--dry-run")
    print(f"[setup] {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(skills_root.parent),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[warn] setup 実行失敗: {exc}")
        return None
    out = (proc.stdout or "") + (proc.stderr or "")
    print(f"[setup] exit={proc.returncode}")
    for line in out.splitlines()[-15:]:
        print("  " + line)
    return out


# ---------------------------------------------------------------------------
# マーカー (重複実行ガード)
# ---------------------------------------------------------------------------
def is_claimed(session_id: str, log_dir: Path, n_messages: int) -> bool:
    """処理済みマーカーを読み取り専用で確認する (書き込みはしない)。

    バックグラウンド委譲の前段チェック用。実際のマーカー更新は
    ワーカー (claim_work) が行う。
    """
    marker = log_dir / f"{session_id}.done.json"
    try:
        if marker.exists():
            prev = json.loads(marker.read_text(encoding="utf-8"))
            return n_messages <= int(prev.get("n_messages", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return False


def claim_work(session_id: str, log_dir: Path, n_messages: int) -> bool:
    """既に処理済みかを判定。新規メッセージが増えていれば再処理する。

    戻り値: True = 今回処理すべき、False = スキップ。
    """
    marker = log_dir / f"{session_id}.done.json"
    try:
        if marker.exists():
            prev = json.loads(marker.read_text(encoding="utf-8"))
            if n_messages <= int(prev.get("n_messages", 0)):
                return False
        marker.write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "n_messages": n_messages,
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            ),
            encoding="utf-8",
        )
        return True
    except OSError as exc:
        print(f"[warn] マーカー書き込み失敗: {exc}")
        return True  # マーカーが使えなくても処理は継続


def mark_done(session_id: str, log_dir: Path, n_messages: int, result: dict) -> None:
    try:
        marker = log_dir / f"{session_id}.done.json"
        marker.write_text(
            json.dumps(
                {**result, "n_messages": n_messages,
                 "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[warn] マーカー書き込み失敗: {exc}")


def fmt_skills(changed: list[dict], skills_root: Path) -> str:
    """変更したスキルを 'category/name' 形式のカンマ区切りで返す。"""
    names: list[str] = []
    for c in changed:
        p = Path(c.get("path", ""))
        try:
            names.append(str(p.parent.relative_to(skills_root)))
        except ValueError:
            names.append(p.parent.name or p.name)
    return ", ".join(names)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="作業セッションから ./skills の SKILL.md を自動生成/更新する",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--scope", choices=["global", "project", "manual"], default="manual",
                   help="呼び出し元 (ログ用)")
    p.add_argument("--payload", type=Path, default=None,
                   help="stdin の代わりにこの JSON ファイルをペイロードとして使う")
    p.add_argument("--dry-run", action="store_true",
                   help="LLM は呼ぶがファイル書き込み・setup は実行しない")
    p.add_argument("--no-llm", action="store_true",
                   help="LLM を呼ばず、セッション解決とトランスクリプト抽出までで終了")
    p.add_argument("--force", action="store_true",
                   help="処理済みマーカーを無視して再実行")
    p.add_argument("--bg", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--self-test", action="store_true",
                   help="環境診断のみ実行して終了")
    p.add_argument("--skills-root", type=Path, default=None,
                   help="スキルルートの上書き (テスト用)")
    p.add_argument("--sessions-dir", type=Path, default=None,
                   help="セッションディレクトリの上書き (テスト用)")
    p.add_argument("--db", type=Path, default=None,
                   help="sessions.db の上書き (テスト用)")
    return p.parse_args()


def self_test() -> int:
    print("=== skill-extractor 環境診断 ===")
    checks = []

    def _check(label, fn):
        try:
            checks.append(f"  [OK]   {label}: {fn()}")
        except Exception as exc:  # noqa: BLE001
            checks.append(f"  [FAIL] {label}: {exc}")

    _check("Python", lambda: sys.version.split()[0])
    _check("sessions dir", lambda: str(SESSIONS_DIR) if SESSIONS_DIR.is_dir() else "NG")
    _check("sessions.db", lambda: str(SESSIONS_DB) if SESSIONS_DB.is_file() else "NG")
    _check("secrets.json", lambda: str(SECRETS_JSON) if SECRETS_JSON.is_file() else "NG")
    _check("skills root", lambda: str(DEFAULT_SKILLS_ROOT) if DEFAULT_SKILLS_ROOT.is_dir() else "NG")
    _check("setup script", lambda: str(DEFAULT_SETUP_SCRIPT) if DEFAULT_SETUP_SCRIPT.is_file() else "NG")
    _check("scripts/.env", lambda: f"{ENV_FILE} ({'読込あり' if ENV_FILE.is_file() else 'なし'})")
    _check("log dir", lambda: f"{DEFAULT_LOG_DIR} (書き込み可)" if DEFAULT_LOG_DIR.is_dir() else f"{DEFAULT_LOG_DIR} (未作成)" )

    key = resolve_api_key()
    checks.append(f"  [{'OK' if key else 'FAIL'}]   API key: {mask_key(key) if key else 'NG (未設定)'}")
    if key:
        checks.append(f"  [OK]   API base: {env_or('SKILL_EXTRACTOR_API_BASE', DEFAULT_API_BASE)}")
        checks.append(f"  [OK]   model: {env_or('SKILL_EXTRACTOR_MODEL', DEFAULT_MODEL)}")

    categories, skills = list_skills(DEFAULT_SKILLS_ROOT)
    checks.append(f"  [OK]   existing categories: {len(categories)}, skills: {len(skills)}")

    print("\n".join(checks))
    return 0


def main() -> int:
    args = parse_args()

    if args.self_test:
        return self_test()

    if env_or("SKILL_EXTRACTOR_DISABLE", False):
        print("[skip] SKILL_EXTRACTOR_DISABLE=1 のため無効")
        return 0

    log_dir = Path(env_or("SKILL_EXTRACTOR_LOG_DIR", str(DEFAULT_LOG_DIR)))
    # フック経由 (stdin ペイロード) のフォアグラウンドは stdout に "{}" だけを
    # 出して Cline に完了を伝えるため、Logger の print は抑制する。
    quiet = args.payload is None and not args.bg
    logger = Logger(log_dir, quiet=quiet)

    # ---- ペイロード取得 ----
    if args.payload:
        try:
            payload = json.loads(args.payload.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.log(f"[error] ペイロードファイル読込失敗: {exc}")
            return 0
    else:
        raw = sys.stdin.read()
        if not raw.strip():
            logger.log("[skip] stdin が空 (フック外で実行された可能性)")
            return 0
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.log(f"[skip] ペイロードが JSON ではない: {exc}")
            return 0

    scope = args.scope
    hook_name = payload.get("hookName", "?")
    agent_id = payload.get("agentId")
    conv_id = payload.get("conversationId")
    parent_id = payload.get("parentAgentId")
    logger.detail(
        f"[start] scope={scope} hook={hook_name} agentId={agent_id} "
        f"conversationId={conv_id} parentAgentId={parent_id}"
    )

    # Cline の hookName はバージョンによって "agent_end" (内部名) と
    # "TaskComplete" (フック名) のどちらかで渡る。両方受け付ける。
    if hook_name not in ("agent_end", "TaskComplete"):
        logger.log(f"[skip] 対象外のイベント: {hook_name}")
        return 0
    if parent_id:
        logger.log("[skip] サブエージェントのセッションのため対象外")
        return 0

    # ---- セッション解決 ----
    db_path = args.db or Path(env_or("SKILL_EXTRACTOR_DB", str(SESSIONS_DB)))
    session = resolve_session(payload, db_path)
    if not session:
        logger.log("[skip] セッションを解決できませんでした")
        return 0
    session_id = session.get("session_id")
    logger.detail(f"[session] {session_id} model={session.get('model')}")

    sessions_dir = args.sessions_dir or SESSIONS_DIR
    messages_path = Path(session.get("messages_path") or "")
    if not messages_path.is_file():
        messages_path = sessions_dir / session_id / f"{session_id}.messages.json"
    if not messages_path.is_file():
        logger.log(f"[skip] トランスクリプトがありません: {messages_path}")
        return 0

    # ---- メッセージ数で事前フィルタ ----
    try:
        raw_msgs = json.loads(messages_path.read_text(encoding="utf-8", errors="replace"))
        n_messages = (
            len(raw_msgs.get("messages", []))
            if isinstance(raw_msgs, dict)
            else len(raw_msgs)
        )
    except json.JSONDecodeError:
        n_messages = 0
    min_msgs = int(env_or("SKILL_EXTRACTOR_MIN_MESSAGES", 4))
    if n_messages < min_msgs:
        logger.log(f"[skip] メッセージ数 {n_messages} < {min_msgs} (短すぎる)")
        return 0

    # ---- バックグラウンド委譲 (フック経由のときのみ) ----
    # Cline のフック実行は 30 秒でタイムアウトするため (v4.1.16 ではハードコード)、
    # 重い LLM 分析はデタッチしたワーカー (--bg) に任せて、フック自体は即座に終了する。
    # 手動実行 (--payload 指定) やワーカー自身はこの分岐に入らない。
    if not args.bg and not args.payload:
        if is_claimed(session_id, log_dir, n_messages):
            logger.log("[skip] 既に処理済み (新規メッセージなし)")
            return 0
        try:
            payload_file = log_dir / f"payload-{session_id}.json"
            payload_file.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            logger.log(f"[error] ペイロード保存失敗: {exc}")
            return 0
        bg_log = log_dir / f"bg-{session_id}.log"
        cmd = [
            sys.executable, str(Path(__file__).resolve()),
            "--payload", str(payload_file),
            "--scope", scope,
            "--bg",
        ]
        try:
            with open(bg_log, "a", encoding="utf-8") as f:
                proc = subprocess.Popen(
                    cmd,
                    stdout=f, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except OSError as exc:
            logger.log(f"[error] バックグラウンド起動失敗: {exc}")
            return 0
        logger.log(f"[bg] バックグラウンド処理を開始 pid={proc.pid} (ログ: {bg_log})")
        print("{}")  # Cline が stdout を JSON として解釈するため空 JSON を返す
        return 0

    if args.bg:
        logger.detail(f"[bg] ワーカー開始 scope={scope} session={session_id}")

    # ---- 重複実行ガード ----
    if not args.force and not claim_work(session_id, log_dir, n_messages):
        logger.log("[skip] 既に処理済み (新規メッセージなし)")
        return 0

    # ---- トランスクリプト抽出 ----
    max_chars = int(env_or("SKILL_EXTRACTOR_MAX_TRANSCRIPT_CHARS", 100_000))
    try:
        transcript = load_transcript(messages_path, max_chars)
    except (OSError, json.JSONDecodeError) as exc:
        logger.log(f"[error] トランスクリプト抽出失敗: {exc}")
        return 0
    if not transcript:
        logger.log("[skip] 抽出できる内容がありません")
        return 0
    logger.detail(f"[transcript] {len(transcript)} chars, {n_messages} messages")

    if args.no_llm:
        logger.log("[dry] --no-llm のためここで終了 (配管は正常)")
        return 0

    # ---- スキルルート決定 ----
    skills_root = args.skills_root or Path(
        env_or("SKILL_EXTRACTOR_SKILLS_ROOT", str(DEFAULT_SKILLS_ROOT))
    )
    if not skills_root.is_dir():
        logger.log(f"[warn] スキルルートがありません: {skills_root} (作成します)")
    categories, skills = list_skills(skills_root)

    # ---- LLM 分析 ----
    api_base = env_or("SKILL_EXTRACTOR_API_BASE", DEFAULT_API_BASE)
    model = env_or("SKILL_EXTRACTOR_MODEL", DEFAULT_MODEL)
    max_tokens = int(env_or("SKILL_EXTRACTOR_MAX_TOKENS", 8000))
    timeout = int(env_or("SKILL_EXTRACTOR_TIMEOUT", 180))
    api_key = resolve_api_key()
    if not api_key:
        logger.log("[error] API キーを解決できません (env / secrets.json / providers.json)")
        return 0

    user_content = build_user_content(session, transcript, categories, skills)
    logger.detail(f"[llm] {api_base} model={model} (キー: {mask_key(api_key)})")

    RETRY_HINT = (
        "\n\nIMPORTANT: your previous response was truncated or invalid JSON. "
        "Reply again with the SAME JSON schema, but keep each SKILL.md body very "
        "concise (under ~1200 characters). Output only valid JSON."
    )
    proposal = None
    raw = ""
    last_err = None
    for attempt in (1, 2):
        content = user_content + (RETRY_HINT if attempt == 2 else "")
        try:
            raw = call_llm(api_base, model, api_key, SYSTEM_PROMPT, content,
                           max_tokens, timeout)
            proposal = parse_proposal(raw)
            break
        except json.JSONDecodeError as exc:
            last_err = f"JSON パース失敗: {exc}"
            logger.log(f"[warn] LLM 応答 {attempt} 回目が JSON として不正 ({exc})")
        except urllib.error.HTTPError as exc:
            last_err = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}"
            logger.log(f"[error] LLM HTTP {exc.code} ({attempt} 回目)")
            return 0
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = f"接続失敗: {exc}"
            logger.log(f"[error] LLM 呼び出し失敗 ({attempt} 回目): {exc}")
            return 0

    if proposal is None:
        logger.log(f"[error] LLM 応答を JSON として解釈できませんでした: {last_err}")
        logger.detail(f"[error] raw: {raw[:500]}")
        return 0
    logger.detail(f"[llm] 応答 {len(raw)} chars")

    summary = proposal.get("summary", "")
    proposed = proposal.get("skills", [])
    logger.detail(f"[llm] summary: {summary} | 提案スキル数: {len(proposed)}")

    if not proposed:
        logger.log("スキル追加: 0件")
        mark_done(session_id, log_dir, n_messages,
                  {"status": "no-change", "summary": summary})
        return 0

    # ---- 適用 ----
    changed = apply_changes(proposal, skills_root, args.dry_run)
    if not changed:
        logger.log("スキル追加: 0件")
        return 0

    # ---- setup 再実行 ----
    setup_out = run_setup(skills_root, dry_run=args.dry_run)
    if setup_out:
        logger.detail(f"[setup] output tail:\n{setup_out[-1200:]}")

    mark_done(session_id, log_dir, n_messages,
              {"status": "changed", "changed": changed, "summary": summary})
    logger.log(f"スキル追加: {len(changed)}件 ({fmt_skills(changed, skills_root)}) — {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
