# handout/.latexmkrc —— 让裸 `latexmk main.tex` 也走 XeLaTeX
#
# 为什么要这个文件：latexmk 的默认引擎是 pdflatex，而本文档是 ctexart + 中文，
# pdflatex 直接编不出来。这里把引擎固定成 XeLaTeX（$pdf_mode = 5），
# 并把中间件全部收进 build/，源码目录保持干净。
#
# 用法：在本目录执行 `latexmk main.tex`，产出 build/main.pdf。
# 强制全量重编：    latexmk -gg main.tex
# 清掉中间件：      latexmk -c      （-C 连 PDF 一起删）

$pdf_mode = 5;    # 5 = xelatex
$xelatex  = 'xelatex -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 %O %S';
$out_dir  = 'build';
