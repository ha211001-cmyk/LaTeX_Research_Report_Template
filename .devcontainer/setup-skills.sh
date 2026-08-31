#!/usr/bin/env bash
# Hermes Agent のスキルディレクトリをワークスペース (git管理) に移行する
#
# 背景: Hermes のスキルは ~/.hermes/skills に固定保存される (設定変更不可)。
#       ~/.hermes はコンテナ再構築で消えるため、スキルを git 管理するには
#       /workdir/skills (bind mount = リポジトリ) へ symlink する。
#
# 動作 (冪等):
#   1. ~/.hermes/skills が既に symlink → 何もしない
#   2. 実ディレクトリの場合 → 内容を /workdir/skills へコピーしてから symlink に置換
#      - --update=none (no-clobber): リポジトリ側に既にあるファイル (ユーザー変更分等) は上書きしない
#      - bundled スキルも含めて移行する (81件 / 約6.6MB、manifest ごと管理)
set -eu

SKILLS_SRC="$HOME/.hermes/skills"
SKILLS_GIT="/workdir/skills"

if [ -L "$SKILLS_SRC" ]; then
    echo "OK: $SKILLS_SRC is already a symlink (git managed)"
    exit 0
fi

mkdir -p "$SKILLS_GIT"

if [ -d "$SKILLS_SRC" ]; then
    cp -a --update=none "$SKILLS_SRC"/. "$SKILLS_GIT"/
    rm -rf "$SKILLS_SRC"
fi

ln -sfn "$SKILLS_GIT" "$SKILLS_SRC"
echo "Migrated: $SKILLS_SRC -> $SKILLS_GIT (git managed)"
