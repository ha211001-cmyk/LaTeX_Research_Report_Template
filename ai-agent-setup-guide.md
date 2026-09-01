# Cline / Hermes Agent セットアップガイド

このリポジトリには、LaTeX 執筆を AI エージェントで支援する仕組みが同梱されています。
使わなくても LaTeX 執筆自体には影響しません。

- **Cline** — タスク完了フック経由で、作業内容からスキル（`SKILL.md`）を自動生成・更新する
- **Hermes Agent** — VS Code の ACP Client 拡張から使えるエージェント。コンテナビルド時に自動インストール済み

---

## 1. Cline のセットアップ

### 1.1 前提

- Dev Container を起動してください（Cline 拡張 `saoudrizwan.claude-dev` は `devcontainer.json` で自動インストール済み）
- 初回は VS Code の「ワークスペースを信頼」ダイアログで `.clinerules` の読み込みを許可してください

### 1.2 セットアップスクリプトの実行

```bash
python3 /workdir/scripts/setup_cline_skills.py --prune
```

このスクリプトを **一度実行すると、Cline の「タスク完了フック（TaskComplete）」経由のスキル更新機能が有効になります**。
以降、Cline でタスクを完了するたびに:

1. Cline が `.clinerules/hooks/TaskComplete` を実行
2. `scripts/taskcomplete.sh` → `scripts/skill-extractor.py` が起動
3. セッションのトランスクリプトを OpenAI 互換 API（デフォルト DeepSeek）で分析
4. 再利用可能な手順があれば `skills/<カテゴリ>/<スキル名>/SKILL.md` を自動生成・更新
5. 変更時は `setup_cline_skills.py --prune` を自動実行して Cline 用の symlink を再構築

### 1.3 作成されるもの

| 配置物 | 中身 |
|---|---|
| `.agents/skills/<skill>` | `skills/<category>/<skill>` への symlink（Cline 用フラット構造。Cline はカテゴリ階層を再帰しないため） |
| `.clinerules/hooks/TaskComplete` | `scripts/taskcomplete.sh` の**コピー**。ファイル名は Cline のフック名 `TaskComplete` と完全一致させる（Cline は `<hooks_dir>/<HookName>` を fs.stat + 実行ビットで検出） |
| `.clinerules/rules` | `scripts/instructions/` への symlink（Cline が `.clinerules` を再帰走査してルールとして読む） |
| `~/.hermes/SOUL.md` | `scripts/instructions/Instructions.md` への symlink（Hermes の SOUL を一元管理） |
| `scripts/.env` | Cline の OpenAI 互換 API 設定（`SKILL_EXTRACTOR_*`）の書き出し。git 追跡除外・パーミッション 600（API キーを含む） |

> `.agents/`・`.cline/`・`.clinerules/` は `.gitignore` 済み（生成物）。git 管理するのは `skills/`・`scripts/` 側です。

### 1.4 オプション

```bash
python3 scripts/setup_cline_skills.py             # 冪等にセットアップ
python3 scripts/setup_cline_skills.py --dry-run   # 実行せず予告のみ
python3 scripts/setup_cline_skills.py --prune     # 不要になった symlink / コピーも削除
python3 scripts/setup_cline_skills.py --no-hooks  # Hooks セクションのみスキップ
python3 scripts/setup_cline_skills.py --no-env    # .env 書き出しのみスキップ
```

### 1.5 API 設定の自動検出（`.env`）

`setup_cline_skills.py` は Cline の設定（`~/.cline/data/globalState.json` と `settings/providers.json`）から**現在使われている OpenAI 互換 API**（OpenAI / DeepSeek / OpenRouter / Groq など）を検出して `scripts/.env` に書き出します。`skill-extractor.py` は `.env` があれば読み込むので、Cline 側で DeepSeek 以外の API を設定していてもスキル自動生成が動きます。anthropic など OpenAI 互換でないプロバイダはスキップされます。

## 2. skill-extractor の動作詳細

### 2.1 手動実行

```bash
python3 scripts/skill-extractor.py --self-test            # 環境診断
python3 scripts/skill-extractor.py --no-llm --force       # LLM なしで配管確認
python3 scripts/skill-extractor.py --force --dry-run --payload /path/to/payload.json  # 書き込みなしドライラン
```

### 2.2 API の指定方法

使用する API は `scripts/.env`（存在すれば自動読込）または環境変数 `SKILL_EXTRACTOR_API_BASE` / `SKILL_EXTRACTOR_MODEL` / `SKILL_EXTRACTOR_API_KEY` で指定できます（**既存の環境変数が優先**。`.env` は読み込み専用で、書き出しは `setup_cline_skills.py` の役割です）。

### 2.3 タイムアウト対策とログ

> **Cline のフックは 30 秒でタイムアウトする**（v4.1.16 ではハードコード）ため、フック経由（stdin ペイロード）のときは、LLM 分析をデタッチしたバックグラウンドワーカー（`--bg`）に委譲して即座に完了します（stdout には空 JSON `{}` を返す）。
>
> **ログは2系統です。**
> - 詳細ログ: `~/.cline/data/logs/skill-extractor/runs.log`（従来どおり。Cline の元のログ配置・形式は触らない）
> - 簡易サマリ: `scripts/skill-extractor.log`（時刻 + スキル追加件数 + 一言メモ。独自ログとして `scripts/` 配下に書き出し。git 追跡対象外）

動作の詳細・環境変数（`SKILL_EXTRACTOR_*`）は `scripts/skill-extractor.py` の docstring を参照してください。

## 3. Hermes Agent（ACP 経由で VS Code 内利用）

- Dev Container のビルド時に自動インストール済み。ターミナルで `hermes` コマンドが使えます
- VS Code の **ACP Client** 拡張から接続すると、エディタ内でタスクを依頼できます
- 初回のみプロバイダ / モデルの設定が必要です:

```bash
hermes setup    # セットアップウィザード（API キー等）
hermes model    # プロバイダ / モデル選択
hermes doctor   # 環境診断
hermes          # 対話開始
```

- 設定・履歴は `~/.hermes/` に保存されます。**コンテナ再構築で消える**ため、スキルは `/workdir/skills` への symlink で git 管理して失われないようにしています
- ルール（Instructions）は `scripts/instructions/Instructions.md` が**単一ソース**です。`.clinerules/rules` と `~/.hermes/SOUL.md` はそこへの symlinkなので、ここを編集すれば **Cline のルールと Hermes の SOUL の両方に反映**されます

## 4. トラブルシューティング

| 症状 | 対処 |
|---|---|
| コンテナ再構築後に hermes の設定が消えた | `hermes setup` を再実行する。スキルは symlink + git 管理なので失われません |
| タスク完了時に Cline が「Hook failed」を表示する | フック実行は Cline 側で **30 秒タイムアウト**（v4.1.16 ではハードコード）。`scripts/skill-extractor.py` はバックグラウンド委譲（`--bg`）で回避済み。`scripts/skill-extractor.log`（簡易サマリ）に「時刻 + スキル追加件数 + メモ」、`~/.cline/data/logs/skill-extractor/runs.log` に詳細が記録されていれば正常動作。`[llm]` の応答が遅い場合は DeepSeek 側の混雑 |

## 5. 参考リンク

- [Hermes Agent](https://hermes-agent.nousresearch.com/) / [GitHub: NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- [ACP Client（VS Code 拡張）](https://marketplace.visualstudio.com/items?itemName=formulahendry.acp-client)
- [Cline（VS Code 拡張）](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)

## 関連資料

- `いろいろ/hermes-agent-install-notes.md` — Hermes Agent 導入の調査メモ
- `いろいろ/hermes-agent-config-guide.md` — Hermes Agent の設定ガイド
