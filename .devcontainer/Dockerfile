# Hermes Agent (ACP 用) のビルド依存を追加した LaTeX イメージ
# base: being24/latex-docker
# - build-essential: hermes-agent の npm install (node-pty の node-gyp ビルド) に必要
# - xz-utils       : hermes 公式インストーラが Node.js (.tar.xz) を展開するのに必要
FROM ghcr.io/being24/latex-docker

# ベースイメージは既定ユーザーが latex (非root) のため、apt-get を使う前に root に切り替える
USER root

# Hermes Agent (ACP 用) のビルド依存を追加する
# - build-essential: hermes-agent の npm install (node-pty の node-gyp ビルド) に必要
# - xz-utils       : hermes 公式インストーラが Node.js (.tar.xz) を展開するのに必要
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        xz-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 元の既定ユーザー (latex) に戻す
USER latex

# Hermes Agent をインストールする
# - ファイルに保存してから実行する (curl 失敗時もビルドを失敗させるため)
# - --skip-setup        : 対話式セットアップ (APIキー設定) をスキップ。後で `hermes setup` で実行可能
# - --non-interactive   : プロンプトをデフォルト値で自動応答 (無人インストール)
# - --skip-browser      : Playwright Chromium を導入しない。本イメージには Chromium の
#                         システムライブラリが無く起動できないため。必要な場合は後で
#                         `cd ~/.hermes/hermes-agent && npx playwright install --with-deps chromium`
# - --skip-computer-use : cua-driver (Computer Use) のダウンロードをスキップ
RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/hermes-install.sh \
    && bash /tmp/hermes-install.sh --skip-setup --non-interactive --skip-browser --skip-computer-use \
    && rm -f /tmp/hermes-install.sh
