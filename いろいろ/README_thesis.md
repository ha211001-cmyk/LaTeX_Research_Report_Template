# 卒論/修論のLatexテンプレート

以下設定等のメモ書きです。

## 構成
LaTeX_Thesis：本旨テンプレ
LaTeX_Thesis_Abstract：要旨テンプレ

## 本旨テンプレ使用方法

詳細な使用方法については、[docker-latex-guide.pdf](docker-latex-guide.pdf)を参照してください。


## 中川 要旨更新ver

* 指定のテンプレートと相違があったため修正をおこなった

| 旧ver違反点 | 修正内容 |
|---|---|
| ページ番号が必要ない | 削除 |
| タイトルの左右余白が15mm | 25mm（指定通り）に修正 |
| タイトルが20pt | 14pt（指定通り）に修正 |
| 本文が10pt | 9pt（指定通り）に修正 |
| 本文を9ptに修正した影響で，1行26文字にならない | 1行26文字になるよう文字間を調整する処理を追加 |
| 2ページ以降，片段59行になってない | 59行（指定通り）に修正 |


## Latex用Dockerイメージ

* 重いの: https://github.com/being24/latex-docker
* 軽いの: https://hub.docker.com/r/paperist/alpine-texlive-ja/

コマンド
* イメージ一覧表示: docker images
* 動作中コンテナ: docker ps
* 停止コンテナ含む: docker ps -a
* ターミナルを起動: docker run -it paperist/alpine-texlive-ja
* フォルダをマウント: docker run -it -v ${PWD}:/workdir paperist/alpine-texlive-ja
* 名前付き, -rmで自動削除: docker run -it --name alpine-tex -v ${PWD}:/workdir paperist/alpine-texlive-ja
* docker run -it --name latexb24 -v ${PWD}:/workdir ghcr.io/being24/latex-docker

Latexコンパイル
latexmk -silent main.tex
	-pdfdviオプションでPDF作成

手動コンパイル
* platex main.tex
* pbibtex main
* dvipdfmx main.dvi

## VS Codeでdocker-latex

### 初期セットアップ

#### 1. 必要なソフトウェアのインストール

以下を順番にインストールしてください：

1. **Docker Desktop**
   - [公式サイト](https://www.docker.com/products/docker-desktop/)からダウンロード
   - macOS/Windows/Linuxに対応
   - インストール後、Docker Desktopを起動しておく

2. **Visual Studio Code (VS Code)**
   - [公式サイト](https://code.visualstudio.com/)からダウンロード
   - 無料のコードエディタ

#### 2. VS Code拡張機能のインストール

VS Codeを開いて、左のサイドバーから拡張機能アイコン（四角が4つ並んだアイコン）をクリックし、以下を検索してインストール：

1. **Dev Containers** (旧Remote Development)
   - Microsoft製
   - Dockerコンテナ内で開発するための拡張機能
   
2. **LaTeX Workshop**
   - James Yu製
   - LaTeXファイルの編集・コンパイル・プレビュー機能を提供
   
3. **Remote Explorer** (オプション)
   - Microsoft製
   - リモート環境の管理を視覚的に行える

### 使い方

#### 方法1: 自動起動（推奨）

1. **devcontainerの設定ファイルを配置**
   - プロジェクトのルートディレクトリに `.devcontainer` フォルダを作成
   - その中に `devcontainer.json` を配置
   - 例：
     ```json
     {
       "name": "LaTeX",
       "image": "paperist/alpine-texlive-ja",
       "customizations": {
         "vscode": {
           "extensions": ["james-yu.latex-workshop"]
         }
       }
     }
     ```

2. **VS Codeでフォルダを開く**
   - VS Codeを起動
   - `ファイル` → `フォルダーを開く` から、LaTeXプロジェクトのフォルダを選択
   - または、フォルダをドラッグ&ドロップ

3. **コンテナで開く**
   - 右下に「Reopen in Container」という通知が表示されるのでクリック
   - または、左下の緑色のアイコン（><のマーク）をクリック → 「Reopen in Container」を選択
   - 初回は数分かかります（Dockerイメージのダウンロード）

4. **LaTeXファイルをコンパイル**
   - `main.tex` を開く
   - 左のサイドバーに「TEX」アイコンが表示される
   - 「Build LaTeX project」ボタンをクリック
   - または、ターミナルで `latexmk -silent main.tex` を実行

#### 方法2: 手動起動

VS Codeのターミナル（`表示` → `ターミナル`）で以下のコマンドを実行：

```bash
# 軽量版LaTeXイメージを使用
docker run -it --name latex-container -v ${PWD}:/workdir paperist/alpine-texlive-ja

# フル機能版を使用する場合
docker run -it --name latex-container -v ${PWD}:/workdir ghcr.io/being24/latex-docker
```

### トラブルシューティング

- **Docker Desktopが起動していない**：Docker Desktopアプリを起動してください
- **コンテナが開かない**：古いコンテナが残っている場合、ターミナルで `docker rm latex-container` を実行
- **PDFが生成されない**：`.pdf` ファイルを閉じてから再度コンパイルしてください

## Latex関連リンク

* [日本語LaTeXの新常識2021](https://qiita.com/wtsnjp/items/76557b1598445a1fc9da?utm_source=Qiita%E3%83%8B%E3%83%A5%E3%83%BC%E3%82%B9&utm_campaign=ab4bfefd0d-Qiita_newsletter_446_01_20_2021&utm_medium=email&utm_term=0_e44feaa081-ab4bfefd0d-33690169)
* [使ってはいけない LaTeX のコマンド・パッケージ・作法](https://ichiro-maruta.blogspot.com/2013/03/latex.html)
* [LaTeXでカウンタを自作し参照する](https://arakik10.hatenadiary.org/entry/20091227/p2)
* [日本語 LaTeX を使うときに注意するべきこと](http://www.math.tohoku.ac.jp/~kuroki/LaTeX/howtolatex.html#title)
* [amsmathの数式環境まとめ](https://qiita.com/t_kemmochi/items/a4c390b4967b13f3afb7)
* [TeXマクロプログラミング](https://refluster.blogspot.com/2010/08/blog-post.html)
* [BibTeX関連ツール](https://texwiki.texjp.org/?BibTeX%E9%96%A2%E9%80%A3%E3%83%84%E3%83%BC%E3%83%AB)
