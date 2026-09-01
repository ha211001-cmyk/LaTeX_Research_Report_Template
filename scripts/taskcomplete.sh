#!/usr/bin/env bash
# Cline TaskComplete hook (internal event: agent_end)
# =====================================================
# 実体: /workdir/scripts/skill-extractor.py
#
# このファイルは setup_cline_skills.py が各 Hooks フォルダへコピーする。
#   - ~/Documents/Cline/Hooks/taskcomplete.sh    (global)
#   - /workdir/.clinerules/hooks/TaskComplete     (project)
# ※ コピー先ファイル名は Cline のフック名 (TaskComplete) と完全一致させる必要がある
#   (Cline は <hooks_dir>/<HookName> を fs.stat + 実行ビットで探す)。
#
# scope は呼び出しパス ($0) から自動判定する。
case "$0" in
  */Documents/Cline/Hooks/*) SCOPE=global ;;
  */.clinerules/hooks/*|*/.cline/hooks/*) SCOPE=project ;;
  *) SCOPE=manual ;;
esac

exec python3 /workdir/scripts/skill-extractor.py --scope "$SCOPE" "$@"
