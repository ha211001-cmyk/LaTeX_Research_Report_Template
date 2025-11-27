# 研究報告会用$\LaTeX$テンプレート

以下設定等のメモ書きです。

### Latex用Dockerイメージ

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

VS CodeとDocker Desktopインストール。拡張は
1. Remote Devlopment
2. Latex Workshop
3. Remote Explorer

### 操作手順

1. フォルダドラッグでワークスペースを開く
2. 左下からReopen in container
3. Latex Workshopのボタンかターミナルでコマンドたたく
    `.devcontainer`に`devcontainer.json`をいれておくと勝手にコンテナ起動

## Latex関連リンク

* [日本語LaTeXの新常識2021](https://qiita.com/wtsnjp/items/76557b1598445a1fc9da?utm_source=Qiita%E3%83%8B%E3%83%A5%E3%83%BC%E3%82%B9&utm_campaign=ab4bfefd0d-Qiita_newsletter_446_01_20_2021&utm_medium=email&utm_term=0_e44feaa081-ab4bfefd0d-33690169)
* [使ってはいけない LaTeX のコマンド・パッケージ・作法](https://ichiro-maruta.blogspot.com/2013/03/latex.html)
* [LaTeXでカウンタを自作し参照する](https://arakik10.hatenadiary.org/entry/20091227/p2)
* [日本語 LaTeX を使うときに注意するべきこと](http://www.math.tohoku.ac.jp/~kuroki/LaTeX/howtolatex.html#title)
* [amsmathの数式環境まとめ](https://qiita.com/t_kemmochi/items/a4c390b4967b13f3afb7)
* [TeXマクロプログラミング](https://refluster.blogspot.com/2010/08/blog-post.html)
* [BibTeX関連ツール](https://texwiki.texjp.org/?BibTeX%E9%96%A2%E9%80%A3%E3%83%84%E3%83%BC%E3%83%AB)
