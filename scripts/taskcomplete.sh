#!/usr/bin/env bash
# Cline TaskComplete hook (internal event: agent_end)
# =====================================================
# 実体: /workdir/scripts/skill-extractor.py
#
# このファイルは setup_cline_skills.py が各 Hooks フォルダへコピーする。
#   - ~/Documents/Cline/Hooks/taskcomplete.sh    (global)
#   - /workdir/.cline/hooks/taskcomplete.sh       (project)
# ※ symlink ではなくコピーにする理由: Cline のフック走査は fs.Dirent.isFile()
#   で判定するため、symlink ファイルは拾われない (Node で実証済み)。
#
# scope は呼び出しパス ($0) から自動判定する。
case "$0" in
  */Documents/Cline/Hooks/*) SCOPE=global ;;
  */.clinerules/hooks/*|*/.cline/hooks/*) SCOPE=project ;;
  *) SCOPE=manual ;;
esac

exec python3 /workdir/scripts/skill-extractor.py --scope "$SCOPE" "$@"
