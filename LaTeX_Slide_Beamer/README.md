# Beamer スライドテンプレート（卒論・修論発表用）

卒業論文・修士論文の発表スライド用の Beamer テンプレートです。
テーマはデフォルトです（`\usetheme` 指定なし）。

## ファイル構成

| ファイル | 説明 |
| --- | --- |
| `slide_main.tex` | メインファイル（スライド本体。ここを編集する） |
| `header.tex` | 共通設定（フォント・パッケージ・フッターなど） |
| `latexmkrc` | latexmk のビルド設定（uplatex + dvipdfmx） |
| `fig/` | 画像を置くフォルダ（サンプル: `fig_1.png`, `fig_2.png`） |
| `movie/` | 動画ファイル置き場（サンプル: `soft_material_recognition.mp4`。**使用不可・未使用**） |

## 使い方

1. `slide_main.tex` 冒頭の「タイトル情報」を自分のものに書き換える
   - タイトル・著者・所属・日付・指導教員（`\titlegraphic`）
2. 各セクションのサンプルスライドを参考に、自分の研究内容に置き換える
3. 不要なスライドは削除、足りないものはコピーして増やす

## コンパイル

このフォルダで次を実行します。

```sh
latexmk slide_main.tex
```

生成物は `slide_main.pdf` です。
VS Code + LaTeX Workshop なら保存時に自動コンパイルされます。

## 配布用PDF（handout出力）

発表用PDFは `\pause` によるアニメーション（クリックごとの追加表示）が入っています。
配布用には **`handout` オプション**で、全オーバーレイをまとめ **1フレーム = 1ページ** のPDFとして出力できます。

`slide_main.tex` の `\documentclass` を下のように切り替えてコンパイルします。

```latex
% 発表用（アニメーションあり）:
\documentclass[uplatex,dvipdfmx,aspectratio=169]{beamer}

% 配布用（\pause 無視・1フレーム=1ページ）:
% \documentclass[uplatex,dvipdfmx,aspectratio=169,handout]{beamer}
```

```sh
latexmk slide_main.tex
```

生成された `slide_main.pdf` が配布用PDFです。
`handout` を外せば通常の発表用PDFに戻ります。

## 主な機能・カスタマイズ

- **テーマ変更**: `slide_main.tex` で `\usetheme{Madrid}` などを指定
- **画面比率**: `\documentclass` の `aspectratio=169`（16:9）。`43` で 4:3 に変更可
- **フッター**: 右下に「ページ番号/総ページ数」を表示（`header.tex` で変更可）
- **セクションページ**: 各セクションの最初にタイトルスライドを自動挿入
- **目次**: 目次に載せたくないセクションは `\section*{...}` を使う
- **動画: 使用不可**
  - `movie/` の動画をPDFに埋め込む機能は無効化している
  - 理由: media9（Flashベース）はAdobe Acrobat以外で再生できない・PDFが約13MBに肥大化する
  - 動画スライドのコードは `slide_main.tex` にコメントアウトで残してある
