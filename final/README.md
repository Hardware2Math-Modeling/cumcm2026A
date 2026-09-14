# A题论文交付说明

题目：药材的烘干问题。

## 内容来源

- 原题：上级目录A题.pdf；附件：上级目录附件。
- 主模型及结果：C:/Users/Lyz22/Documents/A题计算工作记录_20260910/。
- 详细推导：C:/Users/Lyz22/Documents/A题阅读制作/完整思路排版/完整讲义内容.md。
- 本次读取此前保存的摘要、核验、图像和代码，没有重新运行PDE模型，没有改变原结果。
- 桌面其他“A题”项目为不同题目，未混用其算法和数值。

## 结构与编译

八部分依次为问题背景与重述、问题分析、模型假设、符号说明、模型的建立与求解、模型检验与误差分析、模型评价与推广改进、结论。四问各自包含建模、求解及结果。结论后依次放置简短AI说明、参考文献、代码附录。

在本目录执行：

    latexmk -gg main.tex

产物为 `build/main.pdf`。如果不使用 latexmk，也可以连续执行两次：

    xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
    xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex

使用现有 MiKTeX/XeLaTeX（或 macOS 上的 TeX Live）及嵌入字体的 PDF 图片。编译不需要
Python，也不会运行数值求解脚本。

### Windows / macOS 字体切换

`main.tex` 默认通过 `font-config.tex` 让 CTeX 自动识别系统：Windows 使用
SimSun/SimHei/KaiTi，macOS 使用 Songti SC/Heiti SC/PingFang SC，其他系统回退到
TeX Live 自带的 Fandol。通常不需要改源码，因此同一份稿件可直接在两种系统编译。

若要强制选择字体集，只改 `font-config.tex` 中的 `\providecommand{\CJKFontset}{auto}`：
可选值为 `auto`、`windows`、`macnew`、`fandol`。强制 `windows` 或 `macnew` 时，
对应的系统字体必须已安装。

用户指定的tf2环境应在未来运行原模型时沿用，不需要重新下载。当前工具会话未发现可调用的conda入口；本次仅使用机器已有Python完成JSON转表和排版检查，没有新建或安装Python环境。

## 修改位置

- main.tex：字体、字号、页边距、标题格式、居中页码。
- font-config.tex：跨平台字体配置，默认自动识别 Windows/macOS，可手动强制字体集。
- .latexmkrc：固定使用 XeLaTeX，并将编译中间件放入 `build/`。
- sections：各章节正文。
- tables：从既有摘要生成的结果表。
- figures：已有矢量图和问题二补充图。
- 图表改绘建议.md：每幅图、每张表的重画方向与数据约束。
- code：原始算法备份，未执行。运行依赖原工作记录目录结构，不能直接把论文目录当作完整仿真目录。
- checks：数值来源、引用核对、排版检查与预览。

## 结果说明

2026-09-12修订：第三问改以中心候选与全域扫描组织终点判定；读取既有第三、四问终点场，分别复核全部2561个节点，结果见checks/center_endpoint_check.json。原程序仍是全域最大值事件，数值结果未重新积分。原两问综合比较图移至第四问结果之后，第三问改为中心预判/全域确认流程图。

- 时间依赖有效空气湿度边界、无显式潜热和4h后环境延长方式。
- 第三、四问报告最大含水率达到0.15的临界时间，严格低于发生在其后。
- 第四问同时改变物性和几何，6.3820h差值不能全部归因为收缩。
- 既有result2.xlsx保存前3h逐秒温湿结果；模型继续用于问题三。论文没有声称该文件包含约57h全过程逐秒温湿记录。
- 参考文献包括基础专著、干燥综述、数值方法和软件文档。DOI核对记录保存在checks；搜索中的同名书评未替代原书引用。
- 页数、缺字、越界和引用的最终检查以checks/pdf_audit.json为准。
