# 研究室用 LaTeX テンプレート集 on VS Code + Docker

このリポジトリは、**研究報告書・卒業論文（本旨）・卒業論文要旨の 3 種類の LaTeX テンプレート**と、環境構築が不要な **VS Code + Docker 開発環境**をまとめたものです。

> AI エージェント（Hermes Agent）の解説は [ai-agent-setup-guide.md](ai-agent-setup-guide.md) へ移行しました。

LaTeX や Docker に詳しくなくても、以下の「使い方」の手順どおりに進めれば PDF を出力するところまで到達できます。

## 目次

1. [使い方（クイックスタート）](#1-使い方クイックスタート)
2. [テンプレートの詳細](#2-テンプレートの詳細)
3. [開発環境について](#3-開発環境について)
4. [VS Code での操作](#4-vs-code-での操作)
5. [Git によるバージョン管理・差分管理](#5-git-によるバージョン管理差分管理)
6. [AI エージェント連携](#6-ai-エージェント連携)
7. [トラブルシューティング](#7-トラブルシューティング)
8. [参考リンク](#8-参考リンク)

---

## 1. 使い方（クイックスタート）

### 1.1 必要なもの

| ソフトウェア | 用途 | 入手先 |
|---|---|---|
| **VS Code** | エディタ本体 | <https://code.visualstudio.com/> |
| **Docker Desktop** | コンパイル環境をコンテナで実行 | <https://www.docker.com/products/docker-desktop/> |
| **Git**（任意・推奨） | バージョン管理 | <https://git-scm.com/> |

macOS / Windows / Linux すべて対応しています。**TeX Live などを自分の PC にインストールする必要はありません。** LaTeX 環境はすべて Docker コンテナの中に閉じています。

### 1.2 初回セットアップ

**Step 1.** VS Code と Docker Desktop をインストールし、Docker Desktop を起動しておきます。

**Step 2.** このリポジトリを手元に用意します（どちらでも可）。

- GitHub の **「Use this template」** から自分のリポジトリを作る（推奨）
- または `git clone` する

**Step 3.** VS Code でこのフォルダを開きます（メニュー「ファイル」→「フォルダーを開く」、またはフォルダのドラッグ & ドロップ）。

**Step 4.** 左下の緑色のアイコン `><` をクリックし、**「Reopen in Container」** を選択します。

- 初回は Docker イメージのダウンロードとビルドが走るため、**数分〜十数分**かかります。2 回目以降は高速です。
- 完了すると自動的にコンテナ内でフォルダが開き直されます。

**Step 5.** VS Code のメニュー「表示」→「ターミナル」でターミナルを開き、環境が入っていることを確認します。

```bash
which latexmk   # パスが表示されれば OK
```

### 1.3 どのテンプレートを使うか

用途に合わせてフォルダを選びます。

| 用途 | フォルダ | メインファイル |
|---|---|---|
| 研究報告書（ゼミ・進捗報告など） | `Latex_Report/` | `main.tex` |
| 卒業論文・修士論文（本旨） | `LaTeX_Thesis/` | `thesis_main.tex` |
| 卒業論文・修士論文（要旨） | `LaTeX_Thesis_Abstract/` | `abstract_main.tex` |

> **ヒント** このリポジトリは全テンプレート共通の環境（`.devcontainer/` や `scripts/`）をルートに持つ構成です。1 つの論文を書き始めるときは、使うテンプレートのフォルダを **`.devcontainer/`・`.vscode/`・`.gitignore` と一緒に**新しいリポジトリへコピーするのがおすすめです（`latexmkrc` は各テンプレートフォルダに入っているので、コンパイル設定はフォルダごとに動きます）。

### 1.4 はじめてのコンパイル

1. 使うテンプレートのメインファイル（例: `LaTeX_Thesis/thesis_main.tex`）を開く
2. ファイルを保存（`Ctrl+S`）。設定により **保存するたび自動でコンパイル** されます
3. 左サイドバーの **TeX アイコン** → **「Build LaTeX project」** でも同じビルドが走ります
4. ターミナルから実行する場合はこちら（`latexmk` が設定を自動で読むので `cd` するだけ）:
   ```bash
   cd LaTeX_Thesis && latexmk thesis_main.tex
   ```
5. ソースと同じフォルダに `thesis_main.pdf` が生成されます。**TeX アイコン →「View LaTeX PDF」** または虫眼鏡ボタンでプレビューを開けます

生成される `.aux`・`.log`・`.dvi` などは中間ファイルで、`.gitignore` 済みなのでコミット不要です。

### 1.5 最初に書き換える場所

| テンプレート | 書き換える箇所 |
|---|---|
| 報告書 `Latex_Report/main.tex` | `\title{...}`、`\author{...}`、`\date{...}` |
| 本旨 `LaTeX_Thesis/thesis_main.tex` | 冒頭の表紙設定 `\settitlepage{年度}{大学名}{研究科名}{文書種別}{日本語タイトル}{英語タイトル}{提出日}{氏名}{学籍番号}`、`\supervisor{指導教員名}{役職}`、`\thefaculty`・`\thecourse` |
| 要旨 `LaTeX_Thesis_Abstract/abstract_main.tex` | `\title{...}`、`\author{...}`、`\abstracttxt{...}`（アブストラクト本文）、`\supervisor{...}{...}` |

書き換えたら保存するだけで再コンパイルされます。

---

## 2. テンプレートの詳細

3 テンプレートすべて共通の技術スタックです。

- 組版エンジン: **uplatex + dvipdfmx**（日本語組版に最適）
- ビルド: **latexmk**（各フォルダの `latexmkrc` に `uplatex` / `upbibtex` / `dvipdfmx` / `mendex` の設定済み）
- ドキュメントクラス: `jsarticle`
- 参考文献: `bibfile.bib` + `ssice.bst`

### 2.1 `LaTeX_Thesis/` — 卒論・修論（本旨）

卒業論文・修士論文の本文用テンプレートです。表紙から謝辞まで一式そろっています。

主な機能:

- **表紙の自動生成**（`\settitlepage` + `\maketitlepage`）: 年度・大学名・研究科名・文書種別（学士論文/修士論文）・和英タイトル・提出日・学部/コース・氏名・学籍番号・指導教員
- **目次**: ローマ数字ページ番号 → 本文はアラビア数字に自動切替
- **見出し番号**: 「第1章」「1.1」形式、図表は「図 1.2」「表 2.1」、数式は「(1.2)」形式
- **ヘッダー/フッター**: ヘッダーに章・節名、フッター中央にページ番号（fancyhdr）
- **フォント**: 欧文 Times（newtxtext / newtxmath）
- **参考文献**: `\cite{}` で引用、末尾に自動リスト、引用は上付き `[n]`
- **謝辞**（`\makeacknowledgment`）
- **定理環境**: definition / assumption / theorem / lemma / corollary / remark
- **付録**（appendix 環境）

さらに本文には「LaTeX の概要」「表と図」「数式」「参考文献」「差分管理」「報告書の章立て」の**実用的なサンプルコードが一式**入っているので、コピペで自分の原稿を書き始められます。

ファイル構成:

```
LaTeX_Thesis/
├── thesis_main.tex    # 本文（ここに原稿を書く）
├── header.tex         # プリアンブル（スタイル・マクロ定義）
├── latexmkrc          # latexmk 設定
├── bibfile.bib        # 参考文献 DB
├── ssice.bst          # 参考文献スタイル
└── fig/               # 図の画像（pdf / png / jpg）
```

### 2.2 `LaTeX_Thesis_Abstract/` — 卒論・修論（要旨）

要旨（アブストラクト）は大学指定の書式に合わせて調整済みのテンプレートです。

- A4 **二段組 9pt**・左右余白 15mm・段間 10mm
- **1 段あたり全角 26 文字・1 ページ 59 行**に収まるよう字間・行送りを自動調整（`header.tex` の `\GraduateSetKanjiskipForTwentySix`）
- タイトル 14pt・発表者/指導教員の表・アブストラクト欄を上部に配置
- ページ番号はデフォルトで非表示（`\pagestyle{empty}`）。コメントアウトすると「― n ―」形式の番号が付きます
- 参考文献は `\bibliography{bibfile}` 方式（`ssice.bst`）
- 図表のキャプションは英語表記（Fig. / Table）が基本

> 書式は大学・年度によって変わることがあるため、**最新の指定と必ず照合**してください。修正履歴メモは `いろいろ/README_thesis.md` にあります。

### 2.3 `Latex_Report/` — 研究報告書

ゼミや進捗報告など、手軽に使う報告書向けテンプレートです。

- A4 **二段組 12pt**、余白は上 1.5cm / 下 1.0cm / 左右 1.4cm
- タイトルは自作スタイル（太字タイトル + 日付・著者 + 罫線）
- 定理環境と自作コマンド（`\bm` `\del` `\diag`）を定義済み
- 本文に**報告書の推奨章立て**（概要 → 研究計画 → 導入 → 本題 → 結論）のサンプルが入っています

### 2.4 全テンプレート共通のファイル

| ファイル | 役割 |
|---|---|
| `main.tex` など | 本文（原稿を書く場所） |
| `header.tex` | プリアンブル（パッケージ読み込み・スタイル・マクロ定義） |
| `latexmkrc` | latexmk のビルド設定 |
| `bibfile.bib` | 参考文献データベース |
| `ssice.bst` | 参考文献の並び・書式スタイル |
| `fig/` | 図の画像を置くフォルダ |

---

## 3. 開発環境について

### 3.1 使っている Docker イメージ

| イメージ | 説明 |
|---|---|
| `ghcr.io/being24/latex-docker` | フル機能版。このリポジトリの Dev Container のベース（`.devcontainer/Dockerfile`） |
| `paperist/alpine-texlive-ja` | 軽量版。コマンドで手軽に試す場合に |

Dev Container のビルド内容（`.devcontainer/`）:

- `Dockerfile`: `being24/latex-docker` をベースに `build-essential`・`xz-utils` を追加。AI エージェント（Hermes Agent）向けの環境も同梱（詳細は [ai-agent-setup-guide.md](ai-agent-setup-guide.md)）
- `devcontainer.json`: VS Code 拡張（LaTeX Workshop / Git Graph ほか）の自動インストール、`postCreateCommand` で `setup-skills.sh` を実行
- `setup-skills.sh`: エージェントのスキルを git 管理するための移行スクリプト（冪等）

### 3.2 docker コマンドでの手動起動（Dev Container を使わない場合）

```bash
docker images                                     # イメージ一覧
docker ps                                         # 動作中のコンテナ
docker ps -a                                      # 停止中を含む一覧
docker run -it paperist/alpine-texlive-ja         # ターミナルだけ起動
docker run -it -v ${PWD}:/workdir paperist/alpine-texlive-ja              # 現在のフォルダをマウント
docker run -it --rm --name alpine-tex -v ${PWD}:/workdir paperist/alpine-texlive-ja  # --rm で終了時自動削除
docker run -it --name latexb24 -v ${PWD}:/workdir ghcr.io/being24/latex-docker
```

コンテナ内でビルド:

```bash
latexmk -silent main.tex    # PDF まで一括生成
```

latexmk を使わない手動コンパイル:

```bash
platex main.tex             # 1 回目
pbibtex main                # 参考文献の .bbl 生成
platex main.tex             # 参照を解決するため 2 回目
dvipdfmx main.dvi           # PDF 化
```

### 3.3 Overleaf / Cloud LaTeX で使う

ローカル環境を用意しなくてもオンラインで使えます。

- **Overleaf**: 無料プランはコンパイル時間に制限あり。メニューのコンパイラを **「LaTeX」** に設定し、`latexmkrc` も一緒にアップロードしてください
- **Cloud LaTeX**: コンパイル時間の制限なし・VS Code 連携あり。新規プロジェクトから zip をアップロード

どちらも新規プロジェクトからの zip アップロードで使えます。ただし卒論のような長文では、Git 管理と `latexdiff-vc`（後述）のためローカル環境がおすすめです。

## 4. VS Code での操作

### 4.1 自動インストールされる拡張機能（`devcontainer.json` 内）

| 拡張機能 | 役割 |
|---|---|
| **LaTeX Workshop** | ビルド・プレビュー・SyncTeX |
| **Git Graph** | コミット履歴の可視化 |

### 4.2 ビルド・プレビュー

`.vscode/settings.json` の設定により:

- **自動ビルド**: `latex-workshop.latex.autoBuild.run: "onSave"` → ファイル保存のたびに latexmk が走ります
- **ビルド**: TeX アイコン →「Build LaTeX project」（Recipe: latexmk）
- **プレビュー**: TeX アイコン →「View LaTeX PDF」。ビューアはタブ表示
- **出力先**: `%DIR%` → ソースファイルと同じフォルダ

### 4.3 SyncTeX（ソース⇔PDF の相互ジャンプ）

- PDF 上で **Ctrl + クリック** → ソースの該当行へ移動
- ソースから PDF の該当位置へは、TeX タブ →「View LaTeX PDF」→ 該当箇所へジャンプ

### 4.4 設定ファイルの役割

| パス | 内容 |
|---|---|
| `.vscode/settings.json` | LaTeX Workshop のツール・レシピ・ビューア設定 |
| `.devcontainer/devcontainer.json` | コンテナの設定（ビルド元・拡張・起動フック） |
| `.devcontainer/Dockerfile` | ベースイメージへの依存追加（AI エージェント環境含む） |
| `.devcontainer/setup-skills.sh` | スキルの git 管理移行（冪等） |
| `.gitignore` | LaTeX 中間ファイル等の生成物を除外 |

---

## 5. Git によるバージョン管理・差分管理

### 5.1 基本操作

```bash
git init
git add .
git commit -m "Initial commit"
# 書き進めるたびに commit / push
```

- コミット粒度の目安: 章ごと・図表の追加修正ごと・大きな構成変更時・毎日の作業終了時
- メッセージは具体的に（例: 「第2章の初稿を完成」「図3.5のキャプションを修正」）

### 5.2 latexdiff-vc で差分 PDF を作る

修正前後の差分を**青（追加）・赤（削除）**でマークした PDF を生成できます。進捗報告で「どこを直したか」を伝えるのに便利です。

```bash
git add . && git commit -m "wip"      # まず現在の状態をコミット
latexdiff-vc --git -r HEAD main.tex   # 直前コミットとの差分 .tex を生成
latexmk main-diffHEAD.tex             # 差分ファイルをコンパイル
```

生成された `main-diffHEAD.pdf` で変更箇所を確認できます。

## 6. AI エージェント連携

Hermes Agent のセットアップ方法（プロバイダ / モデル設定、スキルの git 管理）は、以下のファイルに移行しました。

→ **`ai-agent-setup-guide.md`** を参照

---

## 7. トラブルシューティング

| 症状 | 対処 |
|---|---|
| 「Reopen in Container」が出ない | Docker Desktop が起動しているか確認。Dev Containers 拡張が入っているか確認 |
| 初回ビルドが数分以上かかる | 正常です。イメージのダウンロード + ビルドが走るため（2 回目以降は速い） |
| 古いコンテナが残って開けない | `docker rm <コンテナ名>` で削除してから開き直す |
| PDF が生成されない | プレビューで PDF を開いたままにしない（ファイルロック）。TeX アイコン →「View LaTeX Log」でログを確認 |
| ビルド時に `This file needs format 'pLaTeX2e'` と出る | メインファイル先頭の `% !TEX program = latexmk` を**削除**する。このマジックコメントがあると LaTeX Workshop が `latexmk ... -pdf -f` を実行して **pdflatex を強制**するため（本テンプレートは uplatex 前提。エンジンは各フォルダの `latexmkrc` が決める）。代わりに先頭に `% !TEX root = ./メインファイル名.tex` を置く |
| 開いているファイルと違うファイルがビルドされる（複数フォルダ構成） | 各メインファイルの先頭に `% !TEX root = ./<そのファイル名>.tex` を書く（このリポジトリの全テンプレートで設定済み）。フォルダをコピーして使うときはファイル名に合わせて付け直す |
| ビルド時にフォントの警告が出る | `header.tex` の「本文を細字に設定」ブロックをコメントアウトすると解消します |
| Overleaf でエラーになる | コンパイラを「LaTeX」に設定し、`latexmkrc` をアップロードする |
| 画像が表示されない | `fig/` にファイルを置き、`\includegraphics[width=...]{fig/ファイル名}` のパス・拡張子を確認 |
| 参考文献が出ない | `\cite{キー}` のキーと `bibfile.bib` のエントリが一致しているか確認 |

## 8. 参考リンク

### LaTeX 全般

- [日本語LaTeXの新常識2021](https://qiita.com/wtsnjp/items/76557b1598445a1fc9da)
- [使ってはいけない LaTeX のコマンド・パッケージ・作法](https://ichiro-maruta.blogspot.com/2013/03/latex.html)
- [LaTeXでカウンタを自作し参照する](https://arakik10.hatenadiary.org/entry/20091227/p2)
- [日本語 LaTeX を使うときに注意するべきこと](http://www.math.tohoku.ac.jp/~kuroki/LaTeX/howtolatex.html#title)
- [amsmathの数式環境まとめ](https://qiita.com/t_kemmochi/items/a4c390b4967b13f3afb7)
- [TeXマクロプログラミング](https://refluster.blogspot.com/2010/08/blog-post.html)
- [BibTeX関連ツール](https://texwiki.texjp.org/?BibTeX%E9%96%A2%E9%80%A3%E3%83%84%E3%83%BC%E3%83%AB)

### 環境構築

- [being24/latex-docker](https://github.com/being24/latex-docker)
- [paperist/alpine-texlive-ja](https://hub.docker.com/r/paperist/alpine-texlive-ja/)
- [LaTeX Workshop（VS Code 拡張）](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)
- [VS Code Dev Containers ドキュメント](https://code.visualstudio.com/docs/devcontainers/containers)

### リポジトリ内の資料

| ファイル | 内容 |
|---|---|
| `docker-latexガイド/docker-latex-guide.md` | VS Code + Docker + 卒論テンプレートの説明スライド（Marp） |
| `README_thesis.md` | 卒論テンプレート用の旧 README（要旨の書式修正履歴つき） |
| `ai-agent-setup-guide.md` | Hermes Agent のセットアップ解説（README 6 章からの移行先） |
| `hermes-agent-install-notes.md` | Hermes Agent 導入の調査メモ |
| `hermes-agent-config-guide.md` | Hermes Agent の設定ガイド |

## License

[MIT License](LICENSE)（Copyright (c) 2025 Kazuki UMEMOTO）
