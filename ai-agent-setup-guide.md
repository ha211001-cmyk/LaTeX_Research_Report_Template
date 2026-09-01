# Hermes Agent セットアップガイド

このリポジトリには、LaTeX 執筆を AI エージェント（Hermes Agent）で支援する仕組みが同梱されています。
使わなくても LaTeX 執筆自体には影響しません。

- **Hermes Agent** — VS Code の ACP Client 拡張から使えるエージェント。コンテナビルド時に自動インストール済み

> 以前は Cline との統合（スキル共有・タスク完了フックによるスキル自動生成）を同梱していましたが、**廃止しました**。
> 関連する `scripts/setup_cline_skills.py`・`scripts/skill-extractor.py`・`scripts/taskcomplete.sh` は削除済みです。

---

## 1. Hermes Agent（ACP 経由で VS Code 内利用）

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
- ルール（Instructions）は `scripts/instructions/Instructions.md` が**単一ソース**で、`~/.hermes/SOUL.md` はそこへの symlink です。ここを編集すれば Hermes の SOUL に反映されます

## 2. トラブルシューティング

| 症状 | 対処 |
|---|---|
| コンテナ再構築後に hermes の設定が消えた | `hermes setup` を再実行する。スキルは symlink + git 管理なので失われません |

## 3. 参考リンク

- [Hermes Agent](https://hermes-agent.nousresearch.com/) / [GitHub: NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- [ACP Client（VS Code 拡張）](https://marketplace.visualstudio.com/items?itemName=formulahendry.acp-client)

## 関連資料

- `いろいろ/hermes-agent-install-notes.md` — Hermes Agent 導入の調査メモ
- `hermes-agent-config-guide.md` — Hermes Agent の設定ガイド
