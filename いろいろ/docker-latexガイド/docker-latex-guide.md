---
marp: true
theme: default
paginate: true
header: 'VS CodeでDocker-LaTeXを使う（卒論・修論テンプレート）'
footer: '2026年1月20日'
---

# VS CodeでDocker-LaTeXを使う
## 卒論・修論本旨テンプレート編（Windows/Mac版）

---

Docker環境でLaTeXを快適に執筆する方法

---

## 目次

1. このテンプレートについて
2. 必要な環境
3. 使い方
4. トラブルシューティング

---

## 1. このテンプレートについて

---

### 特徴

- **uplatex + dvipdfmx** を使用
- **being24/latex-docker** イメージを使用
- **VS Code Dev Containers** で環境構築
- 卒論・修論の執筆に最適化

---

### ファイル構成

```
LaTeX_Thesis/
├── .devcontainer/
│   └── devcontainer.json    # コンテナ設定
├── .vscode/
│   └── settings.json        # VS Code設定
├── main.tex                 # メインファイル
├── header.tex               # プリアンブル
├── latexmkrc                # コンパイル設定
└── fig/                     # 図ファイル
```

---

## 2. 必要な環境

---

### インストールが必要なもの

1. **Docker Desktop**
   - [公式サイト](https://www.docker.com/products/docker-desktop)からダウンロード
 
2. **Visual Studio Code**
   - [公式サイト](https://code.visualstudio.com/)からダウンロード

3. **Git**
   - [公式サイト](https://git-scm.com/download/)からダウンロード
   - バージョン管理に使用
   - テンプレートのクローンに必要


---

## 3. 使用手順

---

### 1. Docker Desktopを起動

- バックグラウンドで実行されていることを確認

--- 

### 2. テンプレートから新しいリポジトリを作成

- GitHubでLaTeX_Thesis_templateを開き、テンプレートから新しいリポジトリを作成 

---

   ![テンプレートから新しいリポジトリを作成](fig/A.png)

---

- リポジトリ名をLaTeX_Thesisとし、プライベートリポジトリを作成

--- 

   ![リポジトリの作成設定](fig/B.png)
---

- 作成完了

--- 

   ![リポジトリの作成完了](fig/C.png)
   
--- 

### 3. VS Codeでリポジトリを開く

- VS Codeの新しいウィンドウを開く
- リポジトリを複製
   
--- 

   ![VS Codeでリポジトリを開く](fig/D.png)

---

- 先ほど作成したリポジトリを選択

---

   ![リポジトリの選択](fig/E.png)

---

- 本体に保存

---

   ![保存先の選択](fig/F.png)

---

- 新しいウィンドウを開き、作成したリポジトリのLaTeX_Thesis_templateフォルダを開く

---

   ![LaTeX_Thesis_templateフォルダを開く](fig/G.png)
---

- コンテナで再度開く

---

   ![コンテナで開く](fig/H.png)

---

- 開き中（少し時間がかかります）

---

   ![コンテナ起動中](fig/I.png)

---

- この画面になれば完了

---

   ![起動完了](fig/J.png)

---

- リポジトリを初期化

---

   ![リポジトリの初期化](fig/K.png)

---

- 変更をステージし、メッセージを入力しコミット

---

   ![コミットの実行](fig/L.png)

---

- ブランチの発行

---

   ![ブランチの発行](fig/M.png)

---

- リポジトリ名をLaTeX_Thesis_mainとし、プライベートリポジトリを作成

---

   ![リポジトリの発行設定](fig/N.png)

---

- リポジトリが正常に発行されましたと表示されればOK

---

   ![発行完了](fig/O.png)

---

### 4. ファイルの編集と保存

- ファイルを編集すると変更が表示される

---

   ![ファイルの編集](fig/P.png)

---

- 変更をステージし、コメントを入力しコミット

---

   ![変更のコミット](fig/Q.png)

---

- 変更の同期

---

   ![変更の同期](fig/R.png)

---

- 完了

---

   ![同期完了](fig/S.png)

---

- 1つ目に作成したリポジトリで変更を管理するのであれば2つ目のリポジトリは必要ない

---

   ![リポジトリの管理](fig/T.png)

--- 

## 4. GitHubの使い方

---

### 初回設定

1. **リポジトリの初期化（完了済み）**
   - すでにコンテナ起動時に初期化されています

2. **GitHubへのサインイン**
   - 左下のアカウントアイコンをクリック
   - 「GitHubでサインイン」を選択
   - ブラウザで認証を完了

---

### 基本的な操作手順

**1. 変更の確認**
- 左サイドバーの「ソース管理」アイコン（分岐マーク）をクリック
- 変更されたファイルが一覧表示されます

**2. ステージング（コミット準備）**
- 変更ファイルの右側の「+」をクリック
- または「すべての変更をステージ」をクリック

--- 

**3. コミット（変更の保存）**
- 上部のメッセージ欄に変更内容を記入
  - 例: 「第1章を追加」「図2.1を修正」
- 「✓ コミット」ボタンをクリック

**4. プッシュ（GitHubへアップロード）**
- 「変更の同期」または「プッシュ」をクリック
- GitHubに変更が反映されます

---

### 推奨されるコミット頻度

- **章ごとの執筆完了時**
- **図表の追加・修正時**
- **大きな構成変更時**
- **毎日の作業終了時**（習慣化推奨）
- **そうでなくてもまめにコミット。必要に応じてsquashやrebaseで整理可能**

---

### コミットメッセージの例

✅ **良い例:**
- 「第2章の初稿を完成」
- 「図3.5のキャプションを修正」
- 「参考文献にJohn2023を追加」

❌ **悪い例:**
- 「更新」
- 「修正」
- 「変更」
---

## 5. このテンプレートの利点

---

### Docker環境の利点

✅ **環境構築不要** - TeX Liveインストール不要  
✅ **再現性** - どのマシンでも同じ環境  
✅ **クリーン** - ホストシステムを汚さない

---

### このテンプレート固有の利点

✅ **卒論・修論に最適化** - 日本語環境完備  
✅ **uplatex対応** - 日本語組版に適した設定  
✅ **すぐに使える** - 設定済みで即執筆開始可能  
✅ **Git Graph** - バージョン管理の視覚化

---

## 6. 参考リンク

---

### テンプレート関連

- **このテンプレート**: [LaTeX_Thesis_template](https://github.com/ha211001-cmyk/LaTeX_Thesis_template)
- **being24/latex-docker**: [GitHub](https://github.com/being24/latex-docker)

---

### LaTeX関連

- [日本語LaTeXの新常識2021](https://qiita.com/wtsnjp/items/76557b1598445a1fc9da)
- [使ってはいけないLaTeXのコマンド・パッケージ](https://ichiro-maruta.blogspot.com/2013/03/latex.html)
- [amsmath数式環境まとめ](https://qiita.com/t_kemmochi/items/a4c390b4967b13f3afb7)

---

### Docker・VS Code

- **Docker公式**: [docker.com](https://www.docker.com/)
- **LaTeX Workshop**: [Marketplace](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)
