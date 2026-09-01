# 修士中間報告書テンプレート

`main.tex` は、既存の報告書と同じ用紙サイズ、余白、タイトル配置、二段組、見出し間隔を維持した汎用テンプレートです。

## 使い方

1. `main.tex` 冒頭の「この部分だけ各自で編集」にある題目、英題、日付、発表者、指導教員を記入します。
2. 本文中の案内文を自分の研究内容に置き換えます。不要な節や例は削除して構いません。
3. 図を使う場合は、コメントアウトされている図の例を有効化し、画像ファイル名を指定します。
4. 参考文献は末尾の `\bibitem` を複製して追加します。

## コンパイル

TeX Live 環境で、次を実行します。

```powershell
latexmk main.tex
```

生成物は `main.pdf` です。

## Docker・VS Codeで使う

このリポジトリには、VS Code Dev Containers用の設定を含めています。Docker DesktopとVS Codeの
**Dev Containers** 拡張機能をインストールしたうえで、このフォルダをVS Codeで開き、
表示される **Reopen in Container** を選択してください。既定では軽量版が起動します。コンテナ内では
LaTeX Workshop拡張機能が自動的に有効になります。

`main.tex` を開き、LaTeX Workshopの **Build LaTeX project** を実行するか、
ターミナルで次を実行するとPDFを生成できます。

```sh
latexmk -silent main.tex
```

`main.tex` を保存すると、LaTeX Workshopが自動的にコンパイルして `main.pdf` を更新します。

軽量版とフル機能版のどちらも利用できます。

| 構成 | 設定ファイル | イメージ |
| --- | --- | --- |
| 軽量版（既定） | `.devcontainer/devcontainer.json` | `paperist/alpine-texlive-ja:latest` |
| フル機能版 | `.devcontainer/heavy/devcontainer.json` | `ghcr.io/being24/latex-docker:latest` |

フル機能版を使う場合は、コマンドパレット（`F1`）で
**Dev Containers: Open Folder in Container...** を実行し、
**Japanese LaTeX (Full)** を選択してください。
パッケージ追加が必要になった場合に利用します。

```text
ghcr.io/being24/latex-docker:latest
```

VS Codeを使わずにPowerShellからコンパイルする場合は、プロジェクトのフォルダで
次を実行します。

```powershell
docker run --rm -v "${PWD}:/workdir" -w /workdir paperist/alpine-texlive-ja:latest latexmk -silent main.tex
```
