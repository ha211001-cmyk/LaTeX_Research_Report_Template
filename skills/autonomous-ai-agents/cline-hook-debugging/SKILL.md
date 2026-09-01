---
name: cline-hook-debugging
description: "ClineのTaskCompleteフックがスキップされる/失敗する問題を診断・修正する手順"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cline, hook, debugging, timeout, background-worker]
    related_skills: [hermes-agent]
---
# Cline フックのデバッグ

Cline のタスク完了フック(`.clinerules/hooks/TaskComplete`)が発火するのに処理されない、または `afterRun hook failed` になる問題の診断・修正手順。

## 発生する症状
- フックは実行されるのに「対象外イベント」でスキップされる
- タスク完了時にClineが「Hook failed」を表示する
- フック内のLLM分析が途中で切れる

## ステップ1: フック発火の確認
```bash
# skill-extractor 系スクリプトのログ(例)
tail -50 ~/.cline/data/logs/skill-extractor/runs.log
# Cline本体のフック実行記録
tail ~/.cline/data/hooks.jsonl   # 場所は環境により異なる
```
発火自体はしていて `[skip] 対象外のイベント: <hookName>` が出る場合 → ステップ2へ。

## ステップ2: hookNameの不一致をチェック
Clineはバージョンにより `hookName` として内部名 `agent_end` とフック名 `TaskComplete` のどちらかを送る。スクリプト側が片方しか受け付けないと常にスキップされる。

```python
# 両対応にする
if hook_name not in ("agent_end", "TaskComplete"):
    logger.log(f"[skip] 対象外のイベント: {hook_name}")
    return 0
```

## ステップ3: 30秒タイムアウトの特定
Cline拡張(v4.1.16など)はフック実行が**30秒でハードコード**されており、設定不可。LLM分析が30秒を超えると `ERROR [HooksAdapter] afterRun hook failed` になる。

バンドルされた拡張コードから確認:
```bash
grep -o 'WEu=[0-9a-z]*' ~/.vscode-server/extensions/<cline-extension>/next/dist/extension.js
# → WEu=3e4  (30秒)
grep -o '.{300}afterRun hook failed.{200}' .../extension.js
```
ログのタイムスタンプ差(起動〜failed)が約30秒ならタイムアウトが原因。

## ステップ4: バックグラウンド委譲で回避
フック経由(stdinペイロード)のときは重い処理をデタッチしたワーカー(`--bg`)に委譲し、フック自体は即座に `{}` を返して exit 0 する。

要点:
- ペイロードを一時ファイルに保存してワーカーに渡す
- `subprocess.Popen(..., start_new_session=True)` などでデタッチ
- 処理済みマーカー(`<session>.done.json`)に `n_messages` を記録し、メッセージ数が増えたときだけ再処理
- フックのフォアグラウンドはstdoutを `{}` のみにする(`quiet=True`)

## ステップ5: ログの分離設計
- **詳細ログ**: 従来どおり `~/.cline/data/logs/` 配下(`runs.log` + `bg-<session>.log`)。元の配置・形式は触らない
- **簡易サマリ**: `scripts/<name>.log` に「時刻 + スキル追加件数 + 一言メモ」だけを独自に書き出す。`.gitignore` で除外する

## 検証手順
```bash
python3 scripts/skill-extractor.py --self-test
# フック模擬(即時リターンすることを確認)
echo '{"hookName":"TaskComplete"}' | python3 scripts/skill-extractor.py --scope project
# → 即座に {} と exit 0
```
ワーカーの完了は簡易ログの `[done]` 行で確認する。
