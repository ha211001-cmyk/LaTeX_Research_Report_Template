% =====================================================================
% umlab.bst  （卒論・修論要旨 LaTeX_Thesis_Abstract 用）
%
% 書式:
%   日本語エントリ（漢字を含む）: 装飾なし（斜体などは使わない）
%     @book:          苗字 名前, 苗字 名前, 「書籍タイトル」, 出版社, 発行年．
%     @inproceedings: 苗字 名前, 苗字 名前, “発表タイトル”, 学会名, 発表年．
%     @article:       苗字 名前, 苗字 名前, “論文タイトル”, 雑誌名,
%                     50巻, 6号, pp.10-15, 2024年．
%   英語エントリ: ieeetrans.bst をベースにした簡易書式（DOI 等は出力しない）
%     @article:       A. Author, “Title,” Journal, vol. 50, no. 6,
%                     pp. 10-15, 2024.
%   URL: url フィールドがある場合、末尾に
%        "[Online]. Available: \url{...}" を付加する（\url パッケージ必須）。
%
% 前提: upLaTeX + upBibTeX（漢字判定 is.kanji.str$ は upBibTeX 組み込み）
% =====================================================================

ENTRY
  { address
    author
    booktitle
    chapter
    edition
    editor
    howpublished
    institution
    journal
    key
    month
    note
    number
    organization
    pages
    publisher
    school
    series
    title
    type
    url
    volume
    year
  }
  { is.kanji.entry }
  { label }

INTEGERS { output.state before.all mid.sentence after.sentence after.block
           nameptr namesleft numnames multiresult }

STRINGS { s t u v }

FUNCTION {not}
{ { #0 } { #1 } if$ }

FUNCTION {and}
{ 'skip$ { pop$ #0 } if$ }

FUNCTION {or}
{ { pop$ #1 } 'skip$ if$ }

% -------------------- 出力状態の初期化 --------------------

FUNCTION {init.state.consts}
{ #0 'before.all :=
  #1 'mid.sentence :=
  #2 'after.sentence :=
  #3 'after.block :=
}

FUNCTION {field.or.null}
{ duplicate$ empty$
    { pop$ "" }
    'skip$
  if$
}

% エントリが日本語（漢字を含む）かどうかを判定
% 作者・タイトル・編集者・雑誌・学会名・シリーズのいずれかに漢字があれば日本語扱い
FUNCTION {set.is.kanji.entry}
{ author field.or.null is.kanji.str$
  title field.or.null is.kanji.str$ or
  editor field.or.null is.kanji.str$ or
  journal field.or.null is.kanji.str$ or
  booktitle field.or.null is.kanji.str$ or
  series field.or.null is.kanji.str$ or
  'is.kanji.entry :=
}

% -------------------- 出力パイプライン --------------------

FUNCTION {output.nonnull}
{ 's :=
  output.state mid.sentence =
    { is.kanji.entry
        { "，" * write$ newline$ }
        { duplicate$ #-1 #1 substring$ "”" =
            { #-2 global.max$ substring$ ",”" * write$ newline$ }
            { ", " * write$ newline$ }
          if$
        }
      if$
    }
    { write$ }
  if$
  mid.sentence 'output.state :=
  s
}

FUNCTION {output}
{ duplicate$ empty$
    'pop$
    'output.nonnull
  if$
}

FUNCTION {output.check}
{ 't :=
  duplicate$ empty$
    { pop$ "empty " t * " in " * cite$ * warning$ }
    'output.nonnull
  if$
}

FUNCTION {output.bibitem}
{ newline$
  "\bibitem{" write$
  cite$ write$
  "}" write$
  newline$
  ""
  before.all 'output.state :=
}

% -------------------- 終了処理 --------------------

% 日本語エントリの末尾を「．」にする
% （add.period$ が付けた "." を全角句点に置換）
FUNCTION {add.kanji.period}
{ add.period$ duplicate$
  #-1 #1 substring$ "." =
    { #-2 global.max$ substring$ "．" * }
    'skip$
  if$
}

FUNCTION {format.url}
{ url empty$
    { "" }
    { "[Online]. Available: \url{" url * "}" * }
  if$
}

FUNCTION {fin.entry}
{ format.url
  duplicate$ empty$
    { pop$ }
    { is.kanji.entry
        { "，" swap$ * * }
        { ", " swap$ * * }
      if$
    }
  if$
  is.kanji.entry
    { add.kanji.period }
    { add.period$ }
  if$
  write$
  newline$
}

% -------------------- 著者名 --------------------

% 個々の名前を整形
%   漢字名: 苗字と名前をそのまま（スペース区切りで再構成）
%   欧文名: イニシャル形式（ieeetrans 風）
FUNCTION {format.names}
{ 's :=
  #1 'nameptr :=
  s num.names$ 'numnames :=
  numnames 'namesleft :=
  { namesleft #0 > }
  {
    s nameptr "{ff }{vv }{ll}{ jj}" format.name$ is.kanji.str$
      { s nameptr "{ff}" format.name$ 'u :=
        u empty$
          { s nameptr "{ll}" format.name$ 't := }
          { s nameptr "{ll}" format.name$ 'v :=
            v empty$
              { u 't := }
              { u " " * v * 't := }
            if$
          }
        if$
      }
      { s nameptr "{f. }{vv~}{ll}{, jj}" format.name$ 't := }
    if$
    nameptr #1 >
      { namesleft #1 >
          { is.kanji.entry
              { "，" * t * }
              { ", " * t * }
            if$
          }
          { t "others" =
              { is.kanji.entry
                  { "，他" * }
                  { ", et~al." * }
                if$
              }
              { is.kanji.entry
                  { "，" * t * }
                  { numnames #2 =
                      { " and " * t * }
                      { ", and " * t * }
                    if$
                  }
                if$
              }
            if$
          }
        if$
      }
      't
    if$
    nameptr #1 + 'nameptr :=
    namesleft #1 - 'namesleft :=
  }
  while$
}

FUNCTION {format.authors}
{ author empty$
    { "" }
    { author format.names }
  if$
}

FUNCTION {format.editors}
{ editor empty$
    { "" }
    { editor format.names
      editor num.names$ #1 >
        { is.kanji.entry
            { "（編）" * }
            { ", eds." * }
          if$
        }
        { is.kanji.entry
            { "（編）" * }
            { ", ed." * }
          if$
        }
      if$
    }
  if$
}

% -------------------- タイトル・雑誌名 --------------------

% 論文タイトル（“ ”で囲む）
FUNCTION {format.title}
{ title empty$
    { "" }
    { "“" title * "”" * }
  if$
}

% 書籍タイトル（日本語: 「」, 英語: イタリック）
FUNCTION {format.btitle}
{ title empty$
    { "" }
    { is.kanji.entry
        { "「" title * "」" * }
        { "{\em " title * "}" * }
      if$
    }
  if$
}

% 雑誌名（英語エントリのみイタリック）
FUNCTION {format.journal}
{ journal empty$
    { "" }
    { is.kanji.entry
        { journal }
        { "{\em " journal * "}" * }
      if$
    }
  if$
}

% 学会名・書名（英語エントリのみイタリック）
FUNCTION {format.booktitle}
{ booktitle empty$
    { "" }
    { is.kanji.entry
        { booktitle }
        { "{\em " booktitle * "}" * }
      if$
    }
  if$
}

% -------------------- 巻・号・ページ --------------------

FUNCTION {n.dashify}
{ 't :=
  ""
  { t empty$ not }
  { t #1 #1 substring$ "-" =
      { t #1 #2 substring$ "--" = not
          { "--" *
            t #2 global.max$ substring$ 't := }
          { { t #1 #1 substring$ "-" = }
              { "-" *
                t #2 global.max$ substring$ 't := }
            while$
          }
        if$
      }
      { t #1 #1 substring$ * t #2 global.max$ substring$ 't := }
    if$
  }
  while$
}

FUNCTION {multi.page.check}
{ 't :=
  #0 'multiresult :=
  { multiresult not t empty$ not and }
  { t #1 #1 substring$
    duplicate$ "-" =
    swap$ duplicate$ "," =
    swap$ "+" =
    or or
      { #1 'multiresult := }
      { t #2 global.max$ substring$ 't := }
    if$
  }
  while$
  multiresult
}

FUNCTION {format.pages}
{ pages empty$
    { "" }
    { pages multi.page.check
        { is.kanji.entry
            { "pp." pages n.dashify * }
            { "pp. " pages n.dashify * }
          if$
        }
        { is.kanji.entry
            { "p." pages * }
            { "p. " pages * }
          if$
        }
      if$
    }
  if$
}

% 要素を累積文字列の末尾に「，」または「, 」で連結する
FUNCTION {add.part}
{ 's :=
  s empty$
    'skip$
    { duplicate$ empty$
        { pop$ s }
        { is.kanji.entry
            { "，" s * * }
            { ", " s * * }
          if$
        }
      if$
    }
  if$
}

% 巻・号・ページをまとめて整形
FUNCTION {format.vol.num.pages}
{ ""
  volume empty$
    'skip$
    { is.kanji.entry
        { volume is.kanji.str$ { volume } { volume "巻" * } if$ }
        { "vol. " volume * }
      if$
      add.part
    }
  if$
  number empty$
    'skip$
    { is.kanji.entry
        { number is.kanji.str$ { number } { number "号" * } if$ }
        { "no. " number * }
      if$
      add.part
    }
  if$
  pages empty$
    'skip$
    { is.kanji.entry
        { "pp." pages n.dashify * }
        { "pp. " pages n.dashify * }
      if$
      add.part
    }
  if$
}

% -------------------- 日付・版・出版社 --------------------

% 年（日本語エントリは「2024年」のように「年」を付ける）
FUNCTION {format.date}
{ year empty$
    { "" }
    { is.kanji.entry
        { year is.kanji.str$ { year } { year "年" * } if$ }
        { year }
      if$
    }
  if$
}

FUNCTION {format.edition}
{ edition empty$
    { "" }
    { is.kanji.entry
        { edition is.kanji.str$
            { edition }
            { "第" edition * "版" * }
          if$
        }
        { edition "l" change.case$ " ed." * }
      if$
    }
  if$
}

% 出版社（address があれば "address: publisher" の形にする）
FUNCTION {format.publisher}
{ publisher empty$
    { address empty$
        { "" }
        { address }
      if$
    }
    { address empty$
        { publisher }
        { is.kanji.entry
            { address "：" * publisher * }
            { address ": " * publisher * }
          if$
        }
      if$
    }
  if$
}

% 学位論文の種別（type フィールドがあればそれを優先）
FUNCTION {format.thesis.type}
{ 't :=
  type empty$
    { t }
    { type }
  if$
}

% =====================================================================
% 各エントリ型
% =====================================================================

% @article
% 日本語: 著者, “タイトル”, 雑誌名, 50巻, 6号, pp.10-15, 2024年．
% 英語:   A. Author, “Title,” Journal, vol. 50, no. 6, pp. 10-15, 2024.
FUNCTION {article}
{ output.bibitem
  format.authors "author" output.check
  format.title "title" output.check
  format.journal "journal" output.check
  format.vol.num.pages output
  format.date "year" output.check
  note output
  fin.entry
}

% @book
% 日本語: 著者, 「書籍タイトル」, 出版社, 発行年．
% 英語:   A. Author, Book Title, Publisher, year.
FUNCTION {book}
{ output.bibitem
  author empty$
    { format.editors "author and editor" output.check }
    { format.authors output.nonnull }
  if$
  format.btitle "title" output.check
  format.edition output
  format.publisher "publisher" output.check
  format.date "year" output.check
  note output
  fin.entry
}

FUNCTION {booklet}
{ output.bibitem
  format.authors output
  format.title "title" output.check
  howpublished output
  address output
  format.date output
  note output
  fin.entry
}

FUNCTION {inbook}
{ output.bibitem
  author empty$
    { format.editors "author and editor" output.check }
    { format.authors output.nonnull }
  if$
  format.btitle "title" output.check
  chapter empty$
    'skip$
    { is.kanji.entry
        { "第" chapter * "章" * output }
        { "chapter " chapter * output }
      if$
    }
  if$
  format.pages output
  format.publisher "publisher" output.check
  format.date "year" output.check
  note output
  fin.entry
}

FUNCTION {incollection}
{ output.bibitem
  format.authors "author" output.check
  format.title "title" output.check
  booktitle empty$
    { organization output }
    { format.booktitle "booktitle" output.check }
  if$
  format.pages output
  format.publisher output
  format.date "year" output.check
  note output
  fin.entry
}

% @inproceedings
% 日本語: 著者, “発表タイトル”, 学会名, pp.10-15, 発表年．
% 英語:   A. Author, “Title,” Conference Name, pp. 10-15, year.
FUNCTION {inproceedings}
{ output.bibitem
  format.authors "author" output.check
  format.title "title" output.check
  booktitle empty$
    { organization output }
    { format.booktitle "booktitle" output.check }
  if$
  format.pages output
  format.date "year" output.check
  note output
  fin.entry
}

FUNCTION {conference} { inproceedings }

FUNCTION {manual}
{ output.bibitem
  author empty$
    { organization output }
    { format.authors output }
  if$
  format.btitle "title" output.check
  format.edition output
  address output
  format.date output
  note output
  fin.entry
}

FUNCTION {mastersthesis}
{ output.bibitem
  format.authors "author" output.check
  format.title "title" output.check
  is.kanji.entry
    { "修士論文" }
    { "Master's thesis" }
  if$
  format.thesis.type output
  school "school" output.check
  address output
  format.date "year" output.check
  note output
  fin.entry
}

FUNCTION {phdthesis}
{ output.bibitem
  format.authors "author" output.check
  format.title "title" output.check
  is.kanji.entry
    { "博士論文" }
    { "PhD thesis" }
  if$
  format.thesis.type output
  school "school" output.check
  address output
  format.date "year" output.check
  note output
  fin.entry
}

FUNCTION {proceedings}
{ output.bibitem
  editor empty$
    { organization output }
    { format.editors output }
  if$
  format.btitle "title" output.check
  format.publisher output
  format.date "year" output.check
  note output
  fin.entry
}

FUNCTION {techreport}
{ output.bibitem
  format.authors "author" output.check
  format.title "title" output.check
  institution output
  number empty$
    'skip$
    { is.kanji.entry
        { number is.kanji.str$
            { number output }
            { "No. " number * output }
          if$
        }
        { "Tech. Rep. " number * output }
      if$
    }
  if$
  format.date "year" output.check
  note output
  fin.entry
}

FUNCTION {unpublished}
{ output.bibitem
  format.authors "author" output.check
  format.title "title" output.check
  note output
  format.date output
  fin.entry
}

FUNCTION {misc}
{ output.bibitem
  format.authors output
  format.title output
  howpublished output
  format.date output
  note output
  fin.entry
}

FUNCTION {default.type} { misc }

% -------------------- 月名マクロ --------------------

MACRO {jan} {"Jan."}
MACRO {feb} {"Feb."}
MACRO {mar} {"Mar."}
MACRO {apr} {"Apr."}
MACRO {may} {"May"}
MACRO {jun} {"Jun."}
MACRO {jul} {"Jul."}
MACRO {aug} {"Aug."}
MACRO {sep} {"Sep."}
MACRO {oct} {"Oct."}
MACRO {nov} {"Nov."}
MACRO {dec} {"Dec."}
MACRO {january} {"Jan."}
MACRO {february} {"Feb."}
MACRO {march} {"Mar."}
MACRO {april} {"Apr."}
MACRO {june} {"Jun."}
MACRO {july} {"Jul."}
MACRO {august} {"Aug."}
MACRO {september} {"Sep."}
MACRO {october} {"Oct."}
MACRO {november} {"Nov."}
MACRO {december} {"Dec."}

% -------------------- 主要学会誌・雑誌マクロ --------------------

MACRO {acmcs} {"ACM Comput. Surv."}
MACRO {acta} {"Acta Inf."}
MACRO {cacm} {"Commun. ACM"}
MACRO {ibmjrd} {"IBM J. Res. Dev."}
MACRO {ibmsj} {"IBM Syst. J."}
MACRO {ieeese} {"IEEE Trans. Softw. Eng."}
MACRO {ieeetc} {"IEEE Trans. Comput."}
MACRO {ieeetcad} {"IEEE Trans. Comput.-Aided Design Integrated Circuits"}
MACRO {ipl} {"Inf. Process. Lett."}
MACRO {jacm} {"J. ACM"}
MACRO {jcss} {"J. Comput. Syst. Sci."}
MACRO {scp} {"Sci. Comput. Programming"}
MACRO {sicomp} {"SIAM J. Comput."}
MACRO {tocs} {"ACM Trans. Comput. Syst."}
MACRO {tods} {"ACM Trans. Database Syst."}
MACRO {tog} {"ACM Trans. Gr."}
MACRO {toms} {"ACM Trans. Math. Softw."}
MACRO {toois} {"ACM Trans. Office Inf. Syst."}
MACRO {toplas} {"ACM Trans. Prog. Lang. Syst."}
MACRO {tcs} {"Theoretical Comput. Sci."}
MACRO {tieice} {"信学論"}
MACRO {tipsj} {"情報処理学会論文誌"}
MACRO {jipsj} {"J. Inf. Process. Soc. Jpn."}
MACRO {jorsj} {"J. Oper. Res. Soc. Jpn."}

% -------------------- 実行 --------------------

READ

% 各エントリの日本語判定
ITERATE {set.is.kanji.entry}

% thebibliography 環境の引数（最大ラベル幅）を求める
STRINGS { longest.label }

INTEGERS { number.label longest.label.width }

FUNCTION {initialize.longest.label}
{ "" 'longest.label :=
  #1 'number.label :=
  #0 'longest.label.width :=
}

FUNCTION {longest.label.pass}
{ number.label int.to.str$ 'label :=
  number.label #1 + 'number.label :=
  label width$ longest.label.width >
    { label 'longest.label :=
      label width$ 'longest.label.width := }
    'skip$
  if$
}

EXECUTE {initialize.longest.label}

ITERATE {longest.label.pass}

FUNCTION {begin.bib}
{ preamble$ empty$
    'skip$
    { preamble$ write$ newline$ }
  if$
  "\begin{thebibliography}{" longest.label * "}" * write$ newline$
}

EXECUTE {begin.bib}

EXECUTE {init.state.consts}

ITERATE {call.type$}

FUNCTION {end.bib}
{ newline$
  "\end{thebibliography}" write$ newline$
}

EXECUTE {end.bib}




