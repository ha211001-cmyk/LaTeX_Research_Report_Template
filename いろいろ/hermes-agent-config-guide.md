# Hermes Agent 設定ファイルのパスと設定方法ガイド

調査日: 2026-08-31 / 対象: Hermes Agent v0.20.6 (`hermes-agent-install-notes.md` の続編)

> この資料は **「設定ファイルがどこにあり、どう編集するか」** に特化したガイド。
> インストール手順は [hermes-agent-install-notes.md](./hermes-agent-install-notes.md) を参照。

---

## 1. 全体像: 設定は2つのファイルに分かれる

Hermes の設定は「**設定 (config.yaml)**」と「**秘密情報 (.env)**」の2ファイルに分離されている。これが最も重要なルール。

| ファイル | 役割 | 例 |
|---|---|---|
| `config.yaml` | **設定値全般** (秘密以外) | モデル、ターミナル、圧縮、表示、承認モード… |
| `.env` | **APIキー・トークン・パスワード等の秘密情報** | `OPENROUTER_API_KEY`, `HERMES_CUSTOM_API_DEEPSEEK_COM_API_KEY` |

- **秘密情報を config.yaml に書かない**。`.env` に書く。
- `hermes config set KEY VAL` を使うと、**APIキーは `.env` に、それ以外は `config.yaml` に自動で振り分け**られる (手動編集より安全)。
- 両方に同じ非秘密設定がある場合、`config.yaml` が優先される。

---

## 2. 設定ファイルのパス

### 2.1 ホームディレクトリの決定

すべてのデータは **Hermes Home** と呼ばれる1つのディレクトリ以下に置かれる。

| 条件 | パス |
|---|---|
| デフォルト | `~/.hermes/` (例: `/home/latex/.hermes/`) |
| `HERMES_HOME` 環境変数を設定した場合 | `$HERMES_HOME/` |

- `HERMES_HOME` を設定すれば、設定・スキル・会話履歴ごと別の場所に移動できる (テスト用・複数環境の分離に便利)。
- **プロファイル利用時**は `~/.hermes/profiles/<name>/` に同じ構成が置かれる。パスを解決するときは `~/.hermes` をハードコードせず `$HERMES_HOME` を基準にするのが鉄則。
- パスを確認するコマンド:

  ```bash
  hermes config path       # → /home/latex/.hermes/config.yaml
  hermes config env-path   # → /home/latex/.hermes/.env
  ```

### 2.2 ディレクトリ構成 (`~/.hermes/`)

```
~/.hermes/
├── config.yaml       # 設定 (秘密以外) ← 本資料の主対象
├── .env              # APIキー・シークレット (chmod 600)
├── auth.json         # OAuthトークン / クレデンシャルプール (Nous Portal 等)
├── SOUL.md           # エージェントのアイデンティティ (system prompt のスロット#1)
├── memories/         # 永続メモリ (MEMORY.md / USER.md)
├── skills/           # インストール済みスキル (bundled + ユーザー作成)
├── cron/             # cron ジョブ定義
├── sessions/         # セッション転送・リクエストダンプ・*.jsonl 会話記録
├── logs/             # ログ (errors.log, gateway.log — 秘密は自動マスク)
├── skins/            # カスタムテーマ (display.skin で指定)
├── plugins/          # ユーザープラグイン
├── profiles/         # プロファイル (存在する場合のみ)
├── state.db          # セッションの正規ストア (SQLite + FTS5)
├── checkpoints/      # チェックポイント/スナップショット
└── hermes-agent/     # git インストール時のソースコード本体
```

### 2.3 この環境 (Dev Container) での実パス

| 項目 | パス |
|---|---|
| 設定ファイル | `/home/latex/.hermes/config.yaml` |
| 秘密情報ファイル | `/home/latex/.hermes/.env` |
| ソースコード | `/home/latex/.hermes/hermes-agent/` (git インストール) |
| 実行ファイル | `/home/latex/.local/bin/hermes` (symlink) |
| SOUL.md | `~/.hermes/SOUL.md` → symlink で `/workdir/scripts/instructions/Instructions.md` |
| スキル | `/workdir/skills` を git 管理し、`~/.hermes/skills` と同期 (詳細は install-notes 参照) |

> ⚠️ **Dev Container の注意**: `~/.hermes/` はコンテナ再構築で消える。
> 永続化したい場合は Docker volume で `~/.hermes` をマウントするか、
> devcontainer.json / Dockerfile に再セットアップ手順を組み込むこと。

---

## 3. 設定方法

### 3.1 コマンド一覧: `hermes config`

```bash
hermes config              # 現在の設定を表示
hermes config show         # 同上 (明示)
hermes config edit         # エディタで config.yaml を直接編集
hermes config get KEY      # 解決済みの設定値を1つ表示
hermes config get KEY --json   # JSON 形式で取得 (ネスト構造の確認に便利)
hermes config set KEY VAL  # 値を設定 (秘密は自動で .env へ)
hermes config set KEY VAL --force  # 未認識キーでも保存 (警告をスキップ)
hermes config unset KEY    # ユーザー設定値を削除 (デフォルトに戻る)
hermes config path         # config.yaml のパスを表示
hermes config env-path     # .env のパスを表示
hermes config check        # アップデート後に欠落した設定オプションを検査
hermes config migrate      # 欠落オプションを対話的に追加 (config check 後におすすめ)
```

**実例:**

```bash
# モデルを確認
hermes config get model.default
hermes config get model.provider

# モデルを変更
hermes config set model.default anthropic/claude-sonnet-4

# ターミナルバックエンドを docker に変更
hermes config set terminal.backend docker

# 変更を取り消してデフォルトに戻す
hermes config unset terminal.backend

# APIキーを設定 (自動で .env に保存される)
hermes config set OPENROUTER_API_KEY sk-or-xxxx
```

> ⚠️ **config.yaml を手で編集する場合の注意**
> `hermes config edit` か `hermes config set` を使うのが推奨。インデントが崩れると
> ファイルが壊れて稼働中の gateway を停止させかねない。特に手で書いた YAML は
> 編集後に `hermes doctor` または `hermes config check` で検証すること。

### 3.2 ウィザード系コマンド (対話式設定)

| コマンド | 用途 |
|---|---|
| `hermes setup` | セットアップウィザード (APIキー等を一括設定) |
| `hermes setup --portal` | Nous Portal で一括設定 (OAuthログイン + モデル + Tool Gateway) |
| `hermes model` | LLM プロバイダ / モデル選択 |
| `hermes tools` | ツールセットの有効/無効 (非対話: `hermes tools enable/disable NAME`) |
| `hermes skin` | テーマ (skin) の一覧・切替 |
| `hermes gateway` | Telegram/Discord 等のメッセージング gateway 設定 |
| `hermes doctor` | 設定・依存関係の健康診断 |
| `hermes update` | 本体の更新 |

### 3.3 CLI オプションによる一時上書き (設定ファイルを変えない)

```bash
hermes chat --model anthropic/claude-sonnet-4   # この起動だけモデルを変える
hermes -m MODEL -t TOOLSETS                     # モデル / ツールセット指定
hermes --continue                               # 前回セッションを再開
```

### 3.4 セッション内のスラッシュコマンド

`/new` 会話リセット、`/model` モデル変更、`/personality`、`/retry`、`/compress` など。
変更は次セッションから有効になるものもある (ツールセット等はプロンプトキャッシュ保護のため)。

---

## 4. 設定の優先順位

解決順 (上ほど優先):

```
1. CLI 引数                   例: hermes chat --model xxx
2. config.yaml                ~/.hermes/config.yaml (非秘密設定の正)
3. .env                       環境変数のフォールバック (秘密は必須)
4. 組み込みデフォルト         ハードコードされた安全な既定値
```

**ルール**: 秘密 (.env) 以外の設定は config.yaml に置く。
同じ設定が両方にある場合は config.yaml が優先される。

---

## 5. config.yaml の主要セクション

完全なリファレンス: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

| セクション | 主なキー |
|---|---|
| `model` | `default`, `provider`, `base_url`, `api_key`, `api_mode`, `context_length`, `aliases` |
| `agent` | `max_turns` (90), `tool_use_enforcement`, `service_tier`, `verify_on_stop` |
| `terminal` | `backend` (local/docker/ssh/modal/daytona/singularity), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20) |
| `display` | `skin`, `interface` (cli/tui), `language`, `show_reasoning`, `show_cost`, `pet` |
| `approvals` | `mode` (smart/manual/off), `timeout`, `cron_mode` |
| `stt` / `tts` | 音声認識 / 音声合成の provider と各種キー |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider`, `write_approval` |
| `security` | `redact_secrets`, `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `max_concurrent_children`, `max_iterations` (50) |
| `checkpoints` | `enabled`, `max_snapshots` (50) |
| `skills` | スキル関連の設定 |
| `database` | `journal_mode` (wal/delete) 等の SQLite 設定 |
| `runtime` | `nofile_soft_limit` (4096) |
| `mcp_servers` | MCP サーバ定義 |
| `platforms.*` | Telegram/Discord 等の各プラットフォーム設定 |

- 設定名は `.` 区切りで `terminal.backend` のように指定する。
- `hermes config check` で、古い config.yaml に足りないセクションを教えてくれる。

---

## 6. .env での環境変数設定

`.env` は `KEY=VALUE` 形式 (コメント行は `#`)。**ファイルのパーミッションは 600** (他人に読めないように)。

```bash
# ~/.hermes/.env の例
OPENROUTER_API_KEY=sk-or-xxxx
HERMES_CUSTOM_API_DEEPSEEK_COM_API_KEY=sk-xxxx
TERMINAL_TIMEOUT=180
```

- config.yaml から環境変数を参照することもできる (シークレットを config.yaml に直書きしないため):

  ```yaml
  model:
    default: deepseek-v4-flash
    provider: custom
    base_url: https://api.deepseek.com/v1/
    api_key: ${HERMES_CUSTOM_API_DEEPSEEK_COM_API_KEY}   # ← .env を参照
    api_mode: chat_completions
  ```

- 環境変数の完全なリファレンス:
  https://hermes-agent.nousresearch.com/docs/reference/environment-variables

---

## 7. この環境での現在の設定 (2026-08-31 時点)

```bash
hermes config get model.default   # → deepseek-v4-flash
hermes config get model.provider  # → custom
```

- モデル: DeepSeek (`https://api.deepseek.com/v1/`, `api_mode: chat_completions`)
- APIキーは `.env` の `HERMES_CUSTOM_API_DEEPSEEK_COM_API_KEY` を参照
- `.env` には `TERMINAL_*` や `BROWSER_*` などの動作環境系の変数も設定済み
- `hermes doctor` の「Configuration Files」チェックで `Config version outdated (v0 → v39)` が出ている
  → **`hermes config migrate` を実行すると最新オプションが追記される**

---

## 8. 設定変更の流れ (まとめ)

```bash
# 1. 現状確認
hermes config get model

# 2. 変更 (秘密は自動で .env へ)
hermes config set terminal.backend local
hermes config set OPENROUTER_API_KEY sk-or-xxxx

# 3. 検証
hermes config check      # 欠落オプションの確認
hermes doctor            # 全体の健康診断

# 4. (必要なら) 新オプションを追記
hermes config migrate
```

---

## 9. 参考リンク

- 公式ドキュメント (Configuration): https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- 環境変数リファレンス: https://hermes-agent.nousresearch.com/docs/reference/environment-variables
- プロファイル: https://hermes-agent.nousresearch.com/docs/user-guide/profiles
- CLI コマンドリファレンス: https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- 導入メモ (前編): [hermes-agent-install-notes.md](./hermes-agent-install-notes.md)

