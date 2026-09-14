# final/.latexmkrc —— 让裸 `latexmk main.tex` 也固定使用 XeLaTeX
#
# ctexart 文档不能用默认的 pdfLaTeX；这里与 handout 的配置保持一致，
# 并把中间件集中到 build/，避免污染源码目录。

$pdf_mode = 5;    # 5 = xelatex
$xelatex  = 'xelatex -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 %O %S';
$out_dir  = 'build';
