# 怎样插入 final/main.tex

## 建议位置

`final/main.tex` 通过 `\input{sections/03_q2}` 加载问题二，因此不宜把片段直接放在这个 `\input` 前后：那会落在问题二标题之前或整段求解结果之后。

当前片段保留用户修改后的 `\subsubsection{问题二模型的建立}` 和 `\subsubsection*{step1 环境边界拟合}`。建议由论文 Owner 在 `final/sections/03_q2.tex` 的问题二 `\subsection` 标题之后，用以下输入替换原有的同名“问题二模型的建立”标题，避免重复标题；原有模型正文接在片段之后：

```tex
\input{../nihe/q2_boundary_fit}
```

这样在“问题二模型的建立”下面先呈现用户指定的“step1 环境边界拟合”，再衔接原有变物性建模内容。`final/main.tex` 本身无需改动。本任务未实际进行上述插入，也未修改 `final/` 的任何文件。

## 为什么这样写

- **主线**：两行目的说明 → 一段 Logistic 模型介绍 → 最小二乘拟合公式 → 稳定值 → 双面板原图。
- **正文取舍**：按用户要求删除模型比较表、数字标号、第三和第四部分；只保留“模型建立”“求温度与水分浓度的拟合值”两处段首加粗文字。完整验证和不确定性分析仍在 `REPORT.md`。
- **数值来源**：继续引用 `fit_values.tex` 中已经计算得到的参数与结果，保留原 `fit_for_paper.pdf`，未更改算法或拟合数值；比较表产物保留但不再输入正文。
- **符号衔接**：片段保留项目正式环境符号 `T_\infty`（K）、`C_\infty`（kg/kg）。与 `final/` 接入时温度需转换为 °C；有效 `C_e` 只是既有闭合假设，不能据此声称测得材料平衡含水率，更不能写成相对湿度。
- **不增加机理承诺**：Logistic 只是候选集合内验证误差最低的经验曲线，不声称是真实设备动力学或唯一最优模型。

## 不能忽略的结果一致性

`final/` 与仓库 `src/common/boundary.py` 不是同一套后期边界设置：

- `final/code/solve_model.py` 的 `PLATEAU` 取时间不小于 10800 s 的观测均值；前 4 h 使用线性插值，之后默认保持均值。
- `final/sections/06_validation.tex` 也明确对照了“3–4 h 均值保持”和“末次测量保持”，既有问题三、四时长属于这些方案。
- 本次拟合曲线尚未用于 PDE 重算。精简版按要求不再展开结果衔接说明，但这不表示既有表格已经采用新边界；该限制保留在本说明和完整报告中。

如果决定正式替换，应由相应 Owner 另行完成：

1. 统一符号表、环境边界假设与模型决策记录；若问题一仍用原插值，明确拟合只适用于问题二至四。
2. 初始化时拟合一次，计算中调用 `FittedBoundary.ambient(t)`；注意返回温度是 K，而 `final/` 的温度变量以 °C 展示，不能直接错接。
3. 重算问题二至四的场值、结果表、图件、终点事件及后期环境敏感性；原先约 0.3 h 的差值不是拟合方案的影响。
4. 重算后在后续求解段说明主计算方案，并替换旧结果。若全时段用光滑拟合，还应同步检查“观测折点处缩短步长”的文字是否仍适用。

## 文件和编译

- `q2_boundary_fit.tex`：可被 `\input` 的正文片段，无文档类、导言区或 `\begin{document}`。
- `demo.tex`：独立编译入口，复用 `final/main.tex` 的字号、页边距、行距及标题样式；demo 使用 TeX Live 自带的 Fandol 中文字体集，避开本机 mac 预设缺少 STFangsong、XeTeX 无法识别 Kaiti SC 的问题。正式插入时片段自动继承 `final/main.tex` 的字体，不改原文件。
- `demo.pdf`：独立排版预览。
- `fit_values.tex`、`fit_for_paper.pdf`：精简片段的同目录依赖，不要只搬走单个 `.tex` 文件。

从仓库根目录复现：

```bash
conda run -n tf2 python -B nihe/export_tex_demo.py
cd nihe
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build demo.tex
```

编译 PDF 位于 `nihe/build/demo.pdf`；交付副本为 `nihe/demo.pdf`。中间件和渲染预览仅留在 `nihe/build/` 与 `nihe/.cache/`。

路径约定与 `final/README.md` 一致：编译主文档时工作目录为 `final/`。片段默认资源路径 `../nihe/`，从 `nihe/` 编译 demo 时同样成立。资源整体移动后，可在输入片段前用 `\newcommand{\niheAssetPath}{新路径/}` 指定；所有标签均带 `nihe` 前缀，避免与正文现有标签冲突。

## 验收记录

- 精简版 XeLaTeX / latexmk 编译成功，独立 PDF 为 1 页 A4，图文结束后留有明显空白；日志无未定义引用、缺字、越界或排版警告，已渲染目视检查。
- 用户已修改的标题和原图保持不变；本轮只精简文稿，未修改数值算法或重跑 PDE。
- 前一版已通过 11 项拟合专项测试和 53 项仓库测试；本轮未重复运行代码测试。`tf2` 缺少 `ruff`，未宣称 lint 通过。
