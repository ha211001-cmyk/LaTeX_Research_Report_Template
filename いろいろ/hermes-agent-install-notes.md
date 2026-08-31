# Hermes Agent 導入メモ (環境調査結果)

```.env
TERMINAL_ENV=local
HERMES_CUSTOM_API_DEEPSEEK_COM_API_KEY=？？？？？？？？？
```

調査日: 2026-08-30
対象: [Nous Research / hermes-agent](https://github.com/NousResearch/hermes-agent) (MIT License, ~238k stars)
最新版: v0.20.6 (v2026.8.27) / PyPI `hermes-agent` 0.19.0
利用形態: **VS Code の ACP Client 拡張 (`formulahendry.acp-client`) で動作させる**

> Hermes Agent は「経験からスキルを作り、使いながら自己改善する」自己学習型 AI エージェント。
> CLI/TUI に加えて Telegram・Discord・Slack 等のゲートウェイ、cron 自動実行、MCP 統合などの機能を持つ。
> **ACP (Agent Client Protocol)** 経由で VS Code / Zed / JetBrains のエディタ内から利用できる。

---

## 1. 必要要件 (Linux 公式インストーラ利用時)

| 項目 | 要件 | 備考 |
|---|---|---|
| Python | **>= 3.11 かつ < 3.14** | インストーラが uv 経由で Python 3.11 を自動導入 (sudo 不要) |
| git | 必須 | インストーラがリポジトリを clone するため |
| curl | 必須 | Linux では必須 |
| xz-utils | 必須 | インストーラが Node.js を `.tar.xz` で取得するため |
| Node.js | 22.22+ / 24.11+ / 26+ | 既存があればそのまま使用。無ければインストーラが v26 を導入 |
| ripgrep | 自動導入 | 高速ファイル検索 |
| ffmpeg | 自動導入 | TTS の音声変換用 |
| build-essential | Desktop アプリ使用時のみ | ネイティブモジュールのコンパイル用 |

- 公式インストーラを使う限り、Python・Node.js・ripgrep・ffmpeg は**手動インストール不要** (不足分を自動検出して導入)。
- PyPI 経由の `pip install hermes-agent` や Homebrew は**非推奨** (README で公式にサポート対象外と明言、`setup.py` からも pip/brew 経路が削除済み)。

---

## 2. 現在環境の調査結果

### 2.1 基本情報

| 項目 | 値 |
|---|---|
| OS | Ubuntu 26.04 LTS (Dev Container 内) |
| アーキテクチャ | x86_64 |
| HOME | `/home/latex` |
| ディスク空き | 約 947 GB (十分) |

### 2.2 要件チェック一覧

| 項目 | 要件 | 現在の状態 | 判定 |
|---|---|---|---|
| Python (system) | 3.11–3.13 | 3.14.4 | ⚠️ システム Python は要件外 |
| uv | インストーラが自動導入 | 0.12.5 (導入済み) | ✅ |
| Node.js | 22.22+ / 24.11+ / 26+ | v24.19.0 | ✅ 要件充足 |
| git | 必須 | 2.53.0 | ✅ |
| curl | 必須 | 8.18.0 | ✅ |
| xz-utils | 必須 | **未インストール** | ❌ **要対応** (Dockerfile で解決済み) |
| C++ コンパイラ (build-essential) | **実質必須** | **未インストール** | ❌ **要対応** (Dockerfile で解決済み) |
| sudo | インストーラが自動 apt 実行に使用 | **存在しない** | ❌ コンテナに sudo なし |
| ripgrep | 自動導入 | 未インストール | ⏳ インストーラが導入 |
| ffmpeg | 自動導入 | 未インストール | ⏳ インストーラが導入 |
| `~/.hermes` | — | 未作成 (クリーン状態) | — |

### 2.3 重要な注意点

1. **システム Python 3.14.4 は要件外** (`< 3.14`)
   - 公式インストーラは uv で **Python 3.11 を専用 venv に導入**するため、システム Python のバージョンは実質問題にならない。
   - 手動インストールする場合は必ず uv 等で Python 3.11 を用意すること (3.14 では動かない可能性が高い)。

2. **C++ コンパイラ + xz-utils が必要 (インストール失敗の直接原因)**
   - hermes リポジトリの `npm install` は **node-pty を node-gyp でビルド**するため C++ コンパイラが必須。
   - インストーラは不足時に `sudo apt install build-essential` を自動実行しようとするが、**このコンテナには sudo 自体が存在しない**ため失敗 → インストールが exit 1 で中断。
   - 対処: `.devcontainer/Dockerfile` で base イメージに `build-essential` と `xz-utils` を追加済み (下記 3.1 参照)。

3. **Dev Container 環境での永続化**
   - Hermes のデータは `~/.hermes/` (= `/home/latex/.hermes`) に置かれるため、**コンテナを再構築すると設定・スキル・会話履歴が消える**。
   - 長期間使う場合は以下を検討:
     - Docker volume で `~/.hermes` をマウント
     - または devcontainer.json / Dockerfile にインストール手順を組み込む

### 2.4 スキルの git 管理 (2026-08-30 追記)

**スキルは git 管理する**ことにした。`~/.hermes/skills` は再構築で消えるため、
`/workdir/skills` (bind mount = リポジトリ) への **symlink** で解決している。

- 背景: Hermes のスキル保存先は `get_skills_dir()` = `HERMES_HOME/skills` に
  **ハードコード**されており、設定キーや環境変数での変更は不可
  (`HERMES_BUNDLED_SKILLS` は bundled の読み取り元指定のみ)。
  `~/.hermes/skills` には bundled スキル (81件 / 約6.6MB) とユーザー作成スキルが同居する。
- 方式:
  - `.devcontainer/setup-skills.sh` (冪等): 実ディレクトリの場合に `/workdir/skills` へ
    `cp -a --update=none` でコピー → `~/.hermes/skills` を symlink に置換。
    既存ファイルは上書きしないので、ユーザー変更分やリポジトリ側の編集は保持される。
  - `devcontainer.json` の `postCreateCommand` で毎回実行 (再構築時も自動適用)。
- 注意:
  - bundled スキル81件も git 管理される (テンプレート配布時は 6.6MB 分のファイルが増える)。
  - `.bundled_manifest` は Hermes 更新時にハッシュが変わるため、git に差分が出る想定。
  - ユーザー作成スキルもこのディレクトリに入るので、`git add skills/` でコミットする。

---

## 3. インストール手順 (推奨: 公式インストーラ)

### 3.1 事前対応 (済): devcontainer.json / Dockerfile の更新

この環境ではコンテナに sudo がないため、**コンテナ再構築時 (root) に依存パッケージを導入**する方針にした。

- `.devcontainer/Dockerfile` (新規作成): `ghcr.io/being24/latex-docker` を base に
  `build-essential` と `xz-utils` を apt 導入
- `.devcontainer/devcontainer.json` (変更):
  - `"image"` → `"build": { "dockerfile": "Dockerfile" }` に変更
  - 拡張一覧で `"formulahendry.acp-client"` (ACP Client) のコメントアウトを解除

**変更後に「Reopen in Container」→「Rebuild Container」で再構築すること。**

### 3.2 インストール実行

```bash
# 1. インストール (Linux / macOS / WSL2 / Termux)
#    ※ 前提 (xz-utils, build-essential) は Dockerfile 側で導入済みなので sudo 不要
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# 2. シェルの再読み込み
source ~/.bashrc

# 3. 動作確認 & ACP のセルフチェック
hermes doctor       # 環境診断
hermes acp --check  # ACP アダプタの依存確認
hermes              # 対話開始 (CLI)
```

- ブラウザ自動化 (Playwright) を省きたい場合: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --skip-browser`
- Computer Use を省きたい場合: `--skip-computer-use`
- 注意: `--skip-browser` を指定しても **node-pty のビルド (npm install) は実行される**ため、build-essential は必須。

### インストールレイアウト

| モード | ソース | 実行ファイル | データ |
|---|---|---|---|
| 通常ユーザ | `~/.hermes/hermes-agent/` | `~/.local/bin/hermes` (symlink) | `~/.hermes/` |
| root モード (`sudo bash`) | `/usr/local/lib/hermes-agent/` | `/usr/local/bin/hermes` | `/root/.hermes/` (or `$HERMES_HOME`) |

---

## 4. VS Code の ACP Client 拡張での利用 (本環境の利用形態)

ACP = **Agent Client Protocol** (JSON-RPC over stdio)。Hermes を ACP サーバとして起動し、
VS Code の ACP Client 拡張がそのプロセスに接続してチャットする。

### 4.1 前提

- Hermes 本体のインストール完了 (標準の `[all]` extras に ACP が含まれる)
- ACP 用の依存が入っていることの確認:

  ```bash
  hermes acp --check        # ACP アダプタと依存の検証
  hermes acp --version
  ```

  (もし入っていなければ `cd ~/.hermes/hermes-agent && uv pip install -e '.[acp]'`)

### 4.2 VS Code 拡張の設定 (済: devcontainer.json に追加済み)

- 拡張: **ACP Client** (`formulahendry.acp-client`) — 公式ドキュメントが推奨する拡張
- 使い方:
  1. アクティビティバーの ACP Client パネルを開く
  2. 組み込みエージェント一覧から **Hermes Agent** を選択
  3. Connect → チャット開始
- 手動で定義する場合 (VS Code settings.json):

  ```json
  {
    "acp.agents": {
      "Hermes Agent": {
        "command": "hermes",
        "args": ["acp"]
      }
    }
  }
  ```

### 4.3 ACP 起動コマンド

```bash
hermes acp          # ACP サーバとして起動 (stdout は JSON-RPC、ログは stderr)
hermes-acp          # 同上
python -m acp_adapter
hermes acp --setup  # 初回: 対話式のプロバイダ/モデル設定 (ACP 経由でも起動可)
```

### 4.4 ACP モードの仕様メモ

- ツールセットは `hermes-acp` 専用構成 (ファイル操作, ターミナル, Web/ブラウザ, メモリ, todo, スキル, execute_code, delegate_task, vision)。
  CLI 用と違い clarify / cronjob / 画像生成 / TTS / Computer Use 等は除外される。
- 設定・認証は CLI と共通 (`~/.hermes/.env`, `~/.hermes/config.yaml`)。
  **事前に `hermes model` でプロバイダ/モデル設定が必要**。
- 承認: エディタに承認プロンプトが転送される (allow once / allow for session / allow always / deny)。
- 作業ディレクトリ: エディタのワークスペース (cwd) がセッションにバインドされる。

---

## 5. 初期設定

```bash
hermes setup            # セットアップウィザード (APIキー等を一括設定)
hermes setup --portal   # Nous Portal で一括設定 (モデル+ツールゲートウェイ。OAuthログイン)
hermes model            # LLM プロバイダ / モデル選択
hermes tools            # ツールの有効/無効設定
hermes config set       # 個別設定値の変更
hermes gateway          # Telegram/Discord 等のメッセージングゲートウェイ起動
hermes update           # 更新
```

- プロバイダ: Nous Portal / OpenRouter / OpenAI / Anthropic / 独自エンドポイント など多数対応。
- よく使うスラッシュコマンド: `/new` (会話リセット)、`/model`、`/personality`、`/retry`、`/compress`。

---

## 6. この環境でやることまとめ (チェックリスト)

- [x] `.devcontainer/Dockerfile` 作成 (build-essential + xz-utils 追加)
- [x] `devcontainer.json` 更新 (Dockerfile 参照 + ACP Client 拡張を有効化)
- [ ] **コンテナを Rebuild** (Reopen in Container → Rebuild Container)
- [ ] `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
- [ ] `source ~/.bashrc`
- [ ] `hermes doctor` → `hermes acp --check` で診断
- [ ] `hermes model` でプロバイダ/モデル設定 (ACP 利用の前提)
- [ ] VS Code の ACP Client パネルから Hermes Agent に接続
- [ ] (任意) `~/.hermes` を Docker volume 等で永続化する対応を検討

---

## 7. 参考リンク

- 公式サイト: https://hermes-agent.nousresearch.com/
- GitHub: https://github.com/NousResearch/hermes-agent
- インストールドキュメント: https://hermes-agent.nousresearch.com/docs/getting-started/installation
- ACP 統合ドキュメント: https://hermes-agent.nousresearch.com/docs/user-guide/features/acp
- ACP Client (VS Code 拡張): https://marketplace.visualstudio.com/items?itemName=formulahendry.acp-client
- PyPI: https://pypi.org/project/hermes-agent/
- Nous Portal: https://portal.nousresearch.com/
