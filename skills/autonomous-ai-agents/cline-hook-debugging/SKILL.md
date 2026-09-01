---
name: cline-hook-debugging
description: "Cline hook (TaskComplete) が動かない/失敗するときの診断と回避手順（hookName不一致・30秒タイムアウト・バックグラウンド委譲）"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [cline, hooks, debugging, timeout, skill-extractor]
    related_skills: [hermes-agent]
---

# Cline Hook デバッグ (TaskComplete)

Cline のフック（`.clinerules/hooks/TaskComplete` 等）が「動かない」「Hook failed」になる際の診断・回避手順。

## 症状1: フックは発火するが常にスキップされる
- ログ: `[start] hook=TaskComplete` → `[skip] 対象外のイベント: TaskComplete`
- 原因: Cline は payload の `hookName` に内部イベント名 `agent_end` ではなく**フック名** `TaskComplete` を渡す（バージョン差異）。
- 修正: `if hook_name not in ("agent_end", "TaskComplete"):` で両対応。

## 症状2: `ERROR [HooksAdapter] afterRun hook failed`
- 原因: Cline のフック実行は **30 秒でハードコード・タイムアウト**（v4.1.16 では `extension.js` 内 `WEu=3e4`）。LLM 呼び出し等の重処理が 30 秒を超えると SIGTERM される。
- 診断: `grep -n 'WEu=3e4' ~/.vscode-server/extensions/saoudrizwan.claude-dev-*/next/dist/extension.js`。起動ログと `afterRun hook failed` の時刻差が約30秒なら確定。
- 補足: `Completed successfully but no JSON response found` の WARN は exit 0 なら無害。

## 回避策: バックグラウンド委譲
フック本体は即座に stdout へ `{}` を出力して exit 0。重処理はデタッチしたワーカー（`--bg`）に委譲する。
1. 処理済みマーカー `<session>.done.json` に `n_messages` を保存。
2. フックは `is_claimed()` で未処理のときだけワーカー起動（payload を `payload-<session>.json` に保存）。
3. ワーカーの `mark_done()` にも `n_messages` を書く（忘れると重複実行ガードが機能しない）。
4. 手動実行 `--payload` と `--bg` は委譲分岐に入れない。

## 注意
- `python3 script.py` で直接実行するファイルには `__pycache__` は生成されない（import されたモジュールのみ）。正常な挙動。
- runs.log は「時刻 + スキル件数 + 一言メモ」の簡易サマリに保ち、詳細は `bg-<session>.log` へ分離する。

## 検証コマンド
```bash
echo '{"hookName":"TaskComplete"}' | python3 scripts/skill-extractor.py --scope project  # {} 即時 + exit 0
python3 scripts/skill-extractor.py --self-test
tail -5 ~/.cline/data/logs/skill-extractor/runs.log
```
