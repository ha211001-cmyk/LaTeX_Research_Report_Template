#!/usr/bin/env python3
"""Cline 連携ファイルのセットアップスクリプト

1. **Skills**: Hermes 形式 (/workdir/skills/<category>/<skill>/SKILL.md) を
   Cline が読み込めるフラット構造 <skill_root>/<skill_name>/SKILL.md に symlink する。
   Cline はスキルルート直下の 1 階層しか走査しない (再帰しない) ため、
   カテゴリ階層を外した「個別 symlink」を張る必要がある。

2. **Hooks**: /workdir/scripts/taskcomplete.sh を /workdir/.clinerules/hooks/TaskComplete へ**コピー**する。
   ※ 現在の Cline は <ws>/.clinerules/hooks からフックを探し、Unix では**フック名と完全一致するファイル名** (<HookName>。例: TaskComplete) を fs.stat + 実行ビットで検出する。symlink ファイルを拾わない実装 (fs.Dirent.isFile 判定) への耐性のためコピー方式を採用する。
   (実証済み: ディレクトリ symlink の中身は再帰走査で拾われるが、ファイル symlink は fs.Dirent.isFile() で拾われない)
   ※ フックはプロジェクトの .clinerules/hooks に集約 (グローバル側には置かない)。

3. **Instructions**: /workdir/scripts/instructions を /workdir/.clinerules/rules に symlink して公開する。
   (Cline は <ws>/.clinerules を再帰走査して .md/.txt をルールとして読む。ディレクトリ symlink は
   parentPath 経由で中身も拾われるため rules/ 配下のファイルがルールになる。なお
   .clinerules/hooks・workflows・skills はルール走査から除外される。グローバル側 ~/Documents/Cline には触らない)
   --prune 時は旧配置 (./.cline/rules, ./.agents/instructions 等) の残骸を掃除する。

4. **SOUL**: ~/.hermes/SOUL.md を scripts/instructions/Instructions.md への symlink にする
   (Hermes Agent の SOUL を git 管理された Instructions.md で一元管理する)。

5. **ENV**: Cline の設定 (~/.cline/data/globalState.json / settings/providers.json) から
   現在使用中の OpenAI 互換 API を検出し、scripts/.env に書き出す
   (skill-extractor.py が読み込む用。anthropic 等の非互換プロバイダはスキップ。
   .env は API キーを含むため git 追跡対象外)。

デフォルト出力先: /workdir/.agents/skills
  (Cline がプロジェクトでスキャンする 6 ルートのうちの 1 つ)

使い方:
    python3 setup_cline_skills.py                # 実行 (冪等)
    python3 setup_cline_skills.py --dry-run      # 実行せず予告のみ
    python3 setup_cline_skills.py --prune        # 不要になった symlink/コピーも削除
    python3 setup_cline_skills.py --no-hooks     # Hooks セクションのみスキップ
    python3 setup_cline_skills.py --no-env       # ENV セクションのみスキップ

依存ライブラリなし (標準ライブラリのみ)。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# スキル探索・検証
# ---------------------------------------------------------------------------
def find_skill_dirs(source: Path) -> dict[str, list[Path]]:
    """source 配下から SKILL.md を含むディレクトリを name -> [dir, ...] で返す。

    同じスキル名が複数カテゴリにある場合 (例: codebase-inspection) は
    リストに複数入る。rglob は symlink ディレクトリを再帰しない。
    """
    found: dict[str, list[Path]] = {}
    for skill_md in sorted(source.rglob("SKILL.md")):
        d = skill_md.parent
        found.setdefault(d.name, []).append(d)
    return found


def parse_frontmatter(text: str) -> dict[str, str]:
    """SKILL.md の YAML frontmatter から name / description を簡易抽出。

    YAML の全機能には対応しないが、この用途 (name/description の確認) には十分。
    """
    m = re.match(r"\A---\s*\n(.*?)\n---", text, re.S | re.M)
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


def validate_skill(skill_dir: Path) -> list[str]:
    """Cline が要求する SKILL.md の条件を検証し、問題点のリストを返す。"""
    problems: list[str] = []
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    if fm.get("name") is None:
        problems.append(f"frontmatter 'name' がありません: {skill_dir}")
    elif fm["name"] != skill_dir.name:
        problems.append(
            f"frontmatter name '{fm['name']}' がディレクトリ名 '{skill_dir.name}' と不一致"
        )
    if fm.get("description") is None:
        problems.append(f"frontmatter 'description' がありません: {skill_dir}")
    return problems


# ---------------------------------------------------------------------------
# 衝突解決
# ---------------------------------------------------------------------------
def resolve_candidates(
    name: str,
    candidates: list[Path],
    source: Path,
    hermes_root: Path,
    mode: str,
) -> Path | None:
    """同名スキルが複数ある場合の勝者を決める。

    mode:
      - "prefer-loaded": 候補のうち ~/.hermes/skills に実在する方を優先
                        (Hermes が実際に読み込んでいる = 使用中とみなす)。
                        どれも無ければ先頭を採用。
      - "first":        ソート順の先頭を採用。
      - "skip":         衝突はスキップ (symlink を作らない)。
    """
    if len(candidates) == 1:
        return candidates[0]
    if mode == "first":
        return candidates[0]
    if mode == "skip":
        return None
    # prefer-loaded
    for d in candidates:
        rel = d.relative_to(source)
        if (hermes_root / rel / "SKILL.md").exists():
            return d
    return candidates[0]


# ---------------------------------------------------------------------------
# symlink 作成
# ---------------------------------------------------------------------------
def create_link(link: Path, winner: Path, target_root: Path) -> None:
    """winner ディレクトリへの相対 symlink を張る。"""
    rel = os.path.relpath(winner, target_root)
    link.symlink_to(rel, target_is_directory=True)


def prune_stale_links(target_root: Path, source: Path, dry_run: bool) -> list[str]:
    """source 配下を指していない symlink (壊れたもの含む) を削除する。"""
    removed: list[str] = []
    if not target_root.is_dir():
        return removed
    source_resolved = source.resolve()
    for child in sorted(target_root.iterdir()):
        if not child.is_symlink():
            continue
        try:
            real = child.resolve(strict=False)
        except OSError:
            real = None
        keep = real is not None and real.is_dir() and real.is_relative_to(source_resolved)
        if not keep:
            removed.append(str(child))
            if not dry_run:
                child.unlink()
    return removed


# ---------------------------------------------------------------------------
# Hooks (コピー方式: Cline の走査は symlink を拾わない)
# ---------------------------------------------------------------------------
def sync_hook_file(
    hook_source: Path, dest_dir: Path, dry_run: bool, no_replace: bool, hook_name: str
) -> tuple[str, str]:
    """hook_source を dest_dir/<hook_name> にコピーする。戻り値: (status, message)。

    Cline は Unix で <hooks_dir>/<HookName> を完全一致で探す (例: TaskComplete) ため、
    コピー先ファイル名はフック名と一致させる。status: "copy" / "skip" / "error"
    """
    if not hook_source.is_file():
        return ("error", f"hook ソースがありません: {hook_source}")
    if not dest_dir.is_dir():
        if dry_run:
            return ("copy", f"{dest_dir / hook_name} (ディレクトリ作成 + コピー)")
        dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / hook_name
    if dest.is_symlink():
        # 以前の symlink 方式からの移行。置き換えてコピーにする。
        if no_replace:
            return ("skip", f"{dest} (symlink のため置換しない)")
        if dry_run:
            return ("copy", f"{dest} (symlink → コピーに置換)")
        dest.unlink()
    elif dest.exists():
        if dest.read_bytes() == hook_source.read_bytes():
            return ("skip", f"{dest} (既存OK)")
        if no_replace:
            return ("skip", f"{dest} (置換しない: 内容が異なる)")

    if dry_run:
        return ("copy", str(dest))
    dest.write_bytes(hook_source.read_bytes())
    dest.chmod(0o755)
    return ("copy", str(dest))


def prune_hook_files(
    hook_source: Path, dest_dirs: list[Path], dry_run: bool, hook_name: str
) -> list[str]:
    """配置済みのフックコピーを掃除する。

    - ソース消失時: 管理下 (dest_dirs) のコピーを削除。
    - 管理対象から外れた既知の Cline フック配置 (旧 .cline/hooks 等) に、
      当スクリプト由来のコピー (内容がソースと同一) が残っていれば削除。
      内容が異なるファイルはユーザー所有とみなし触らない。
    """
    removed: list[str] = []
    managed = {d / hook_name: d for d in dest_dirs}

    if not hook_source.is_file():
        for dest in managed:
            if dest.exists() and dest.is_file():
                removed.append(f"{dest} (ソース消失)")
                if not dry_run:
                    dest.unlink()
        return removed

    source_bytes = hook_source.read_bytes()
    # 注: ~/Documents/Cline (グローバル側) は Cline 本体が管理する場所のため対象外。
    known_dirs = [
        Path("/workdir/.cline/hooks"),  # 旧プロジェクト配置 (v1 の .cline 方式)
        Path.home() / ".cline" / "hooks",
        Path.home() / ".clinerules" / "hooks",
    ]
    for d in known_dirs:
        dest = d / hook_name
        if dest in managed:
            continue  # 現在の管理対象
        if dest.exists() and dest.is_file():
            if dest.read_bytes() == source_bytes:
                removed.append(f"{dest} (管理対象外へ移行)")
                if not dry_run:
                    dest.unlink()
    return removed


# ---------------------------------------------------------------------------
# Instructions (symlink 方式)
# ---------------------------------------------------------------------------
def _ensure_dir_symlink(link: Path, target: Path, dry_run: bool, no_replace: bool) -> str:
    """link が target への symlink になるよう調整する。戻り値: status。

    status: "create" / "skip" / "error"
    """
    if link.is_symlink():
        if link.resolve(strict=False) == target.resolve():
            return "skip"
        if no_replace:
            return "skip"
        if not dry_run:
            link.unlink()
    elif link.exists():
        return "error"  # 実体 (ファイル/ディレクトリ) が居座っている
    if dry_run:
        return "create"
    link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
    return "create"


def link_instructions(
    source: Path,
    link_dir: Path,
    dry_run: bool,
    no_replace: bool,
) -> list[tuple[str, str]]:
    """instructions を /workdir/.clinerules/rules に symlink で公開する。

    戻り値: [(status, message), ...]
    """
    if not source.is_dir():
        return [("error", f"instructions ソースがありません: {source}")]

    if not link_dir.parent.is_dir() and not dry_run:
        link_dir.parent.mkdir(parents=True, exist_ok=True)

    # link_dir が実ディレクトリで存在する場合: 空なら置換、中身があれば尊重
    if link_dir.exists() and not link_dir.is_symlink():
        try:
            entries = list(link_dir.iterdir())
        except OSError:
            entries = []
        if entries:
            return [("error", f"{link_dir} は空でない実ディレクトリのため置換不可 ({len(entries)} 件)")]
        if dry_run:
            return [("create", f"{link_dir} -> {os.path.relpath(source, link_dir.parent)}")]
        link_dir.rmdir()

    st = _ensure_dir_symlink(link_dir, source, dry_run, no_replace)
    return [(st, f"{link_dir} -> {os.path.relpath(source, link_dir.parent)}")]


def prune_instructions(
    source: Path, dry_run: bool, link_dir: Path
) -> list[str]:
    """instructions 関連の symlink を掃除する (新配置 + 旧配置の残骸)。"""
    removed: list[str] = []

    # 新配置: .clinerules/rules (ソース消失時のみ削除)
    if link_dir.is_symlink() and not source.is_dir():
        removed.append(f"{link_dir} (ソース消失)")
        if not dry_run:
            link_dir.unlink()

    # 旧配置の残骸: .cline/rules, .agents/instructions (~/Documents/Cline は触らない)
    source_resolved = source.resolve()
    for p in (
        Path("/workdir/.cline/rules"),
        Path("/workdir/.agents/instructions"),
    ):
        if p.is_symlink():
            try:
                target = p.resolve(strict=False)
            except OSError:
                target = None
            if target == source_resolved:
                removed.append(f"{p} (旧配置を掃除)")
                if not dry_run:
                    p.unlink()
    return removed


# ---------------------------------------------------------------------------
# SOUL (~/.hermes/SOUL.md → Instructions.md の symlink)
# ---------------------------------------------------------------------------
def _ensure_file_symlink(link: Path, target: Path, dry_run: bool, no_replace: bool) -> str:
    """link が target への symlink になるよう調整する。戻り値: status ("create"/"skip")。

    実体ファイルが居座っている場合は置き換える (管理対象のパスとして扱う)。
    """
    if link.is_symlink():
        if link.resolve(strict=False) == target.resolve():
            return "skip"
        if no_replace:
            return "skip"
        if not dry_run:
            link.unlink()
    elif link.exists():
        if no_replace:
            return "skip"
        if not dry_run:
            link.unlink()
    if dry_run:
        return "create"
    link.symlink_to(os.path.relpath(target, link.parent))
    return "create"


def link_soul(
    source: Path,
    link: Path,
    dry_run: bool,
    no_replace: bool,
) -> list[tuple[str, str]]:
    """~/.hermes/SOUL.md を Instructions.md への symlink にする。

    戻り値: [(status, message), ...]
    """
    if not source.is_file():
        return [("error", f"SOUL ソースがありません: {source}")]

    if not link.parent.is_dir() and not dry_run:
        link.parent.mkdir(parents=True, exist_ok=True)

    was_real_file = link.exists() and not link.is_symlink()
    st = _ensure_file_symlink(link, source, dry_run, no_replace)
    rel = os.path.relpath(source, link.parent)
    if st == "skip":
        return [(st, f"{link} -> {rel} (既存OK)")]
    if st == "error":
        return [(st, f"{link}: 置換できません")]
    note = " (実ファイルを置換)" if was_real_file else ""
    return [(st, f"{link} -> {rel}{note}")]


def prune_soul(source: Path, link: Path, dry_run: bool) -> list[str]:
    """ソース消失時に SOUL symlink を掃除する。"""
    removed: list[str] = []
    if link.is_symlink() and not source.is_file():
        removed.append(f"{link} (ソース消失)")
        if not dry_run:
            link.unlink()
    return removed


# ---------------------------------------------------------------------------
# Cline API (.env) — セクション5
# ---------------------------------------------------------------------------
# Cline のビルトイン API のうち OpenAI 互換 (/chat/completions) エンドポイントを持つもの。
# anthropic は OpenAI 互換でない (Messages API) ため含めない。カスタムプロバイダは
# providers.json の settings.baseUrl が優先される。
OPENAI_COMPAT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "xai": "https://api.x.ai/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}


def cline_data_dir() -> Path:
    """Cline のデータディレクトリ (~/.cline/data)。テスト用に CLINE_DATA_DIR で上書き可。"""
    env = os.environ.get("CLINE_DATA_DIR")
    return Path(env) if env else Path.home() / ".cline" / "data"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_active_provider(global_state: dict, providers: dict) -> str | None:
    """現在 Cline が使っているプロバイダ ID を返す。

    優先順: globalState の actMode/planMode の Provider → providers.json の
    lastUsedProvider → キーが入っているプロバイダ (後追いフォールバック)。
    """
    for key in ("actModeApiProvider", "planModeApiProvider"):
        v = global_state.get(key)
        if v:
            return v
    v = providers.get("lastUsedProvider")
    if v:
        return v
    for pid, cfg in (providers.get("providers") or {}).items():
        if (cfg.get("settings") or {}).get("apiKey"):
            return pid
    return None


def resolve_provider_api_key(provider_id: str, settings: dict, secrets: dict) -> str | None:
    """providers.json の settings.apiKey → secrets.json の <id>ApiKey の順で探す。

    secrets.json のキーは Cline が camelCase で保存する (例: deepSeekApiKey /
    openAiApiKey / anthropicApiKey) ため、大文字小文字を無視して照合する。
    """
    v = (settings or {}).get("apiKey")
    if v:
        return v
    for name, val in (secrets or {}).items():
        if name.endswith("ApiKey") and name[:-6].lower() == provider_id.lower():
            return val
    return None


def resolve_provider_base_url(provider_id: str, settings: dict) -> str | None:
    """カスタム baseUrl → ビルトイン対応表 の順に解決。None なら非対応プロバイダ。"""
    v = (settings or {}).get("baseUrl")
    if v:
        return v
    return OPENAI_COMPAT_BASE_URLS.get(provider_id)


def resolve_provider_model(global_state: dict, provider_id: str, settings: dict) -> str | None:
    """provider_id を使用中のモードの modelId → providers.json の settings.model の順。"""
    for mode in ("actMode", "planMode"):
        if global_state.get(f"{mode}ApiProvider") == provider_id:
            v = global_state.get(f"{mode}ApiModelId")
            if v:
                return v
    return (settings or {}).get("model") or None


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "..." + key[-4:]


def build_env_content(base_url: str, model: str | None, api_key: str) -> str:
    lines = [
        "# Generated by setup_cline_skills.py (Cline の OpenAI 互換 API 設定から書き出し)",
        "# このファイルは git 追跡対象外 (.gitignore)。API キーが含まれるため取り扱い注意。",
        "# skill-extractor.py が存在すれば読み込みます (再生成で上書きされます)。",
        f"SKILL_EXTRACTOR_API_BASE={base_url}",
    ]
    if model:
        lines.append(f"SKILL_EXTRACTOR_MODEL={model}")
    lines += ["SKILL_EXTRACTOR_API_KEY=" + api_key, ""]
    return "\n".join(lines)


def sync_env(env_file: Path, dry_run: bool, no_replace: bool) -> list[tuple[str, str]]:
    """Cline の設定から OpenAI 互換 API を検出し .env へ書き出す。

    戻り値: [(status, message), ...]  status: "create" / "skip" / "error"
    """
    data_dir = cline_data_dir()
    global_state = _load_json(data_dir / "globalState.json")
    providers = _load_json(data_dir / "settings" / "providers.json")
    secrets = _load_json(data_dir / "secrets.json")

    if not providers:
        return [("error", f"providers.json が読めません: {data_dir / 'settings' / 'providers.json'}")]

    provider_id = detect_active_provider(global_state, providers)
    if not provider_id:
        return [("error", "使用中プロバイダを特定できません (globalState.json / providers.json を確認)")]

    settings = ((providers.get("providers") or {}).get(provider_id, {})).get("settings") or {}
    api_key = resolve_provider_api_key(provider_id, settings, secrets)
    base_url = resolve_provider_base_url(provider_id, settings)
    model = resolve_provider_model(global_state, provider_id, settings)

    if base_url is None:
        return [("skip", f"provider={provider_id}: OpenAI 互換でないか未対応のため .env は生成しません")]
    if not api_key:
        return [("skip", f"provider={provider_id}: API キーが見つからないため .env は生成しません")]

    content = build_env_content(base_url, model, api_key)
    if env_file.exists() and env_file.read_text(encoding="utf-8") == content:
        return [("skip", f"{env_file} (既存OK)")]
    if no_replace:
        return [("skip", f"{env_file} (置換しない: --no-replace 指定)")]
    if dry_run:
        detail = f"provider={provider_id} base={base_url} model={model or '(未設定)'} key={_mask_key(api_key)}"
        return [("create", f"{env_file} ({detail})")]
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(content, encoding="utf-8")
    env_file.chmod(0o600)
    return [("create", f"{env_file} (provider={provider_id})")]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Hermes 形式のスキルを Cline が読めるフラット構造に symlink する",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--source", type=Path, default=Path("/workdir/skills"),
                   help="Hermes 形式スキルのルート (カテゴリ/スキル/SKILL.md)")
    p.add_argument("--target", type=Path, default=Path("/workdir/.agents/skills"),
                   help="Cline スキルルート (スキル/SKILL.md のフラット構造)")
    p.add_argument("--hermes-root", type=Path,
                   default=Path.home() / ".hermes" / "skills",
                   help="衝突解決 (prefer-loaded) で参照する Hermes のロード済みルート")
    p.add_argument("--on-conflict", choices=["prefer-loaded", "first", "skip"],
                   default="prefer-loaded",
                   help="同名スキルの衝突時の解決方法")
    p.add_argument("--prune", action="store_true",
                   help="source 配下を指していない既存 symlink を削除する")
    p.add_argument("--no-replace", action="store_true",
                   help="既存の symlink/ファイルを置き換えない")
    p.add_argument("--dry-run", action="store_true",
                   help="実際には変更せず、実行内容の予告のみ表示する")

    # ---- Hooks セクション ----
    p.add_argument("--no-hooks", action="store_true",
                   help="Hooks セクションをスキップ")
    p.add_argument("--hooks-source", type=Path,
                   default=Path("/workdir/scripts/taskcomplete.sh"),
                   help="Hooks ソースファイル (git 管理)")
    p.add_argument("--hooks-dest", type=Path, nargs="+",
                   default=[Path("/workdir/.clinerules/hooks")],
                   help="Hooks コピー先ディレクトリ (.clinerules/hooks に集約)")
    p.add_argument("--hooks-name", default="TaskComplete",
                   help="Cline のフック名 (コピー先ファイル名。Cline は <hooks_dir>/<HookName> を探す)")

    # ---- Instructions セクション ----
    p.add_argument("--no-instructions", action="store_true",
                   help="Instructions セクションをスキップ")
    p.add_argument("--instructions-source", type=Path,
                   default=Path("/workdir/scripts/instructions"),
                   help="instructions ディレクトリ (git 管理)")
    p.add_argument("--instructions-dir", type=Path,
                   default=Path("/workdir/.clinerules/rules"),
                   help="Cline がルールとして読む .clinerules 内の symlink 先")

    # ---- SOUL セクション ----
    p.add_argument("--no-soul", action="store_true",
                   help="SOUL セクションをスキップ")
    p.add_argument("--soul-source", type=Path, default=None,
                   help="SOUL ソース (デフォルト: --instructions-source/Instructions.md)")
    p.add_argument("--soul-link", type=Path,
                   default=Path.home() / ".hermes" / "SOUL.md",
                   help="SOUL symlink の場所 (デフォルト: ~/.hermes/SOUL.md)")

    # ---- ENV セクション ----
    p.add_argument("--no-env", action="store_true",
                   help="Cline API 検出 (.env 書き出し) セクションをスキップ")
    p.add_argument("--env-file", type=Path,
                   default=Path("/workdir/scripts/.env"),
                   help="書き出す .env ファイルのパス (デフォルト: scripts/.env)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    source: Path = args.source
    target: Path = args.target
    hermes_root: Path = args.hermes_root

    if not source.is_dir():
        print(f"エラー: source が存在しないかディレクトリではありません: {source}")
        return 1
    if target.resolve().is_relative_to(source.resolve()):
        print(f"エラー: target を source の内側に置くことはできません: {target}")
        return 1

    found = find_skill_dirs(source)
    total = sum(len(v) for v in found.values())
    print(f"[探索] source: {source}")
    print(f"       SKILL.md ディレクトリ: {total} 件 / ユニークなスキル名: {len(found)} 件")

    created: list[str] = []
    skipped: list[str] = []
    conflicts: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    for name in sorted(found):
        candidates = found[name]
        winner = resolve_candidates(name, candidates, source, hermes_root, args.on_conflict)

        # 検証 (警告)
        for d in candidates:
            for prob in validate_skill(d):
                warnings.append(f"{d.relative_to(source)}: {prob}")

        if winner is None:
            conflicts.append(name)
            continue

        link = target / name
        real_winner = winner.resolve()

        if link.is_symlink():
            if link.resolve(strict=False) == real_winner:
                skipped.append(f"{name} (既存OK)")
                continue
            if args.no_replace:
                skipped.append(f"{name} (置換しない: {link})")
                continue
            if not args.dry_run:
                link.unlink()
        elif link.exists() or link.is_dir():
            # 実ディレクトリや実ファイルが居座っている場合
            errors.append(f"{name}: 置換できません (実体が存在: {link})")
            continue

        if args.dry_run:
            rel = os.path.relpath(winner, target)
            created.append(f"{name} -> {rel}")
        else:
            create_link(link, winner, target)
            created.append(name)

    pruned: list[str] = []
    if args.prune:
        pruned = prune_stale_links(target, source, args.dry_run)

    # ---- セクション2: Hooks コピー ----
    if not args.no_hooks:
        print(f"\n[Hooks] source: {args.hooks_source}")
        for d in args.hooks_dest:
            status, msg = sync_hook_file(
                args.hooks_source, d, args.dry_run, args.no_replace, args.hooks_name
            )
            if status == "error":
                errors.append(msg)
            elif status == "copy":
                created.append(f"[hooks] {msg}")
            elif status == "skip":
                skipped.append(f"[hooks] {msg}")
        if args.prune:
            for pr in prune_hook_files(
                args.hooks_source, args.hooks_dest, args.dry_run, args.hooks_name
            ):
                pruned.append(f"[hooks] {pr}")

    # ---- セクション3: Instructions symlink (.clinerules/rules) ----
    if not args.no_instructions:
        print(f"\n[Instructions] source: {args.instructions_source}")
        if not args.instructions_source.is_dir():
            errors.append(f"instructions ソースがありません: {args.instructions_source}")
            if args.prune:
                for pr in prune_instructions(args.instructions_source, args.dry_run, args.instructions_dir):
                    pruned.append(f"[instructions] {pr}")
        else:
            for status, msg in link_instructions(
                args.instructions_source,
                args.instructions_dir,
                args.dry_run,
                args.no_replace,
            ):
                if status == "error":
                    errors.append(msg)
                elif status == "create":
                    created.append(f"[instructions] {msg}")
                elif status == "skip":
                    skipped.append(f"[instructions] {msg}")
            if args.prune:
                for pr in prune_instructions(args.instructions_source, args.dry_run, args.instructions_dir):
                    pruned.append(f"[instructions] {pr}")

    # ---- セクション4: SOUL symlink (~/.hermes/SOUL.md → Instructions.md) ----
    soul_source = args.soul_source or args.instructions_source / "Instructions.md"
    if not args.no_soul:
        print(f"\n[SOUL] source: {soul_source}")
        for status, msg in link_soul(
            soul_source, args.soul_link, args.dry_run, args.no_replace
        ):
            if status == "error":
                errors.append(msg)
            elif status == "create":
                created.append(f"[soul] {msg}")
            elif status == "skip":
                skipped.append(f"[soul] {msg}")
        if args.prune:
            for pr in prune_soul(soul_source, args.soul_link, args.dry_run):
                pruned.append(f"[soul] {pr}")

    # ---- セクション5: Cline API (.env) ----
    if not args.no_env:
        print(f"\n[ENV] Cline config ({cline_data_dir()}) -> {args.env_file}")
        for status, msg in sync_env(args.env_file, args.dry_run, args.no_replace):
            if status == "error":
                errors.append(f"[env] {msg}")
            elif status == "create":
                created.append(f"[env] {msg}")
            elif status == "skip":
                skipped.append(f"[env] {msg}")

    # ---- 結果表示 ----
    verb = "予定 (dry-run)" if args.dry_run else "実行"
    print(f"\n[{verb}結果]")
    if created:
        print(f"  作成/更新: {len(created)} 件")
        for c in created:
            print(f"    + {c}")
    if skipped:
        print(f"  スキップ: {len(skipped)} 件")
        for s in skipped:
            print(f"    = {s}")
    if conflicts:
        print(f"  衝突で未作成: {len(conflicts)} 件 ({args.on_conflict})")
        for c in conflicts:
            print(f"    ! {c}: " + ", ".join(str(d.relative_to(source)) for d in found[c]))
    if pruned:
        print(f"  stale symlink 削除: {len(pruned)} 件")
        for pr in pruned:
            print(f"    - {pr}")
    if warnings:
        print(f"  警告: {len(warnings)} 件")
        for w in warnings:
            print(f"    ? {w}")
    if errors:
        print(f"  エラー: {len(errors)} 件")
        for e in errors:
            print(f"    x {e}")

    if args.dry_run:
        print("\n(--dry-run のため変更は加えていません)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

