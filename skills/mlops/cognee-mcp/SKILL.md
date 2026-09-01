---
name: cognee-mcp
description: "cognee MCPサーバーのadd/searchツールの使い方と、ステージングvs cognifyの仕様・プローブによる既存KB抽出方法"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cognee, mcp, knowledge-base, rag, testing]
    related_skills: [llm-wiki]
---

# Cognee MCP

## Overview
cognee MCPは2つのツールを提供: `add_knowledge_mcp`（ナレッジ登録）と `search_knowledge_mcp`（意味検索）。

## 重要な仕様
- `add_knowledge_mcp` は**ステージング保存のみ**でcognify（索引化）しない。登録直後は検索にヒットしない（バグではない）。
- cognifyは**毎朝5時の夜間バッチ**で自動実行。登録内容は翌朝のバッチ後に検索可能になる。
- `search_knowledge_mcp` は**クエリ必須**で、一覧取得ツールは無い。レスポンスは上位1件のみで、未ヒット時は「context does not mention...」を返す。

## テスト手順 (add → verify)
1. テスト用ナレッジを登録: `add_knowledge_mcp(text="...", source="mcp_test", category="test")` → 登録IDを返す。
2. 直後に検索 → ヒットしない。仕様どおり。
3. 既存KBで検索（例: 既知のドメイン用語）→ 正常動作を確認。
4. バッチ後に一意キーワード（例: `PINEAPPLE_FACT_42`）で再検索し登録を確認。

## 既存ナレッジのプローブ方法
一覧APIが無いため、キーワード・プローブで内容を抽出する:
- ドメイン用語の推測を繰り返し検索（例: RTK GPS, LaTeX, AvNav, OLLAMA, docker, ardupilot, Signal K, BTS7960, udev 等）。
- 各クエリは上位1件のコンテキストを返すので、返却テキストを切り捨て前に保存する。
- ヒットした結果をカテゴリごとに整理してユーザーへ要約する。

## 備考
- 即時検索が必要な場合は、MCPには無いので外部でcognifyを手動実行する。
- 既にcognify済みのナレッジ（夜間バッチ由来）は問題なく検索できる。
