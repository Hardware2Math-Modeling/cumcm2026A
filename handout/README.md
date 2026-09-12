# handout —— 论文 LaTeX 编译包

从 `lyz/A题/论文/` 里**只搬走了编译这篇论文所必需的文件**，其余（`checks/`、`A题.pdf`、
`附件/`、原 `main.pdf`、未参与编译的 `code/*.py`、`README.md`、`.aux/.log` 等）仍留在原处。

## 目录内容

| 路径 | 作用 |
|---|---|
| `main.tex` | 论文主文件，`\input` 各章节 |
| `sections/*.tex` | 正文十节（含摘要、四问、检验、评价、结论、参考文献、代码附录） |
| `tables/*.tex` | 被 `\input` 的结果表片段 |
| `figures/*.pdf` | 被 `\includegraphics` 引用的矢量图 |
| `code/solve_model.py` | **编译依赖**：附录 B 用 `\lstinputlisting` 摘录它，缺了会编译失败 |
| `.latexmkrc` | 固定 XeLaTeX 引擎 + 输出到 `build/` |

## 编译

中文必须用 **XeLaTeX**（`ctexart` 用 pdflatex 会炸）。两种等价做法：

```bash
cd handout

# 方式一：latexmk（推荐，自动判定重编次数；引擎已在 .latexmkrc 里定成 XeLaTeX）
latexmk main.tex            # 产出 build/main.pdf
latexmk -gg main.tex        # 强制全量重编
latexmk -c                  # 清理中间件（-C 连 PDF 一起删）

# 方式二：直接调 xelatex，连编两遍（交叉引用/目录要第二遍才稳）
xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

`build/` 目录已被根 `.gitignore` 的 `build/` 规则忽略，中间件不会入库。

## 和原稿的唯一差别：字体集

原稿写的是 `fontset=windows`（SimSun / SimHei / KaiTi），这套字体只存在于 Windows。
在 macOS 上编译**不会报错**，但会把所有汉字悄悄丢掉 —— 出一份 30 页的「无字天书」，
log 里是成片的 `Missing character: There is no 考 (U+8003) in font ...`。

所以本目录的 `main.tex` 改成了 `fontset=macnew`，用 macOS 自带的
Songti SC / Heiti SC / PingFang SC。**要拿回 Windows 上编，把 `macnew` 改回 `windows` 即可。**
（找不到这些字体时，`fontset=fandol` 是最保险的跨平台回退，TeX Live 自带 Fandol 字体。）

## 在 VSCode 里保存即编译

需要 LaTeX Workshop 扩展 + 两项设置（`.vscode/` 在本仓库被 `.gitignore` 忽略，
所以这两项要各自在本机加一次）：

```jsonc
{
  // 默认 recipe 是 "latexmk"，它带 -pdf，即 pdflatex —— 中文必炸。必须换成这个：
  "latex-workshop.latex.recipe.default": "latexmk (xelatex)",
  "latex-workshop.latex.outDir": "%DIR%/build",
  "latex-workshop.latex.autoBuild.run": "onSave"
}
```

- 只打开 `handout/` 这个目录时：写进 `handout/.vscode/settings.json`。
- 打开整个仓库根目录时：写进仓库根的 `.vscode/settings.json`（`handout/.vscode/` 就不会被读到了）。
- `sections/*.tex` 第一行有 `% !TEX root = ../main.tex`，保证改某一节时也去编 `main.tex`
  而不是把该节当独立文稿编。
