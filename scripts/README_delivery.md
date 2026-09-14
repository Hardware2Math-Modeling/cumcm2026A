# 本地审阅与复现说明

本项目用 Python 和 XeLaTeX 建立四问均包含蒸发潜热的药材干燥模型。主工况在附件 1 的 4 小时实测驱动结束后设为 60 °C、20% RH；第二工况用附件 1 的渐近温度拟合值，湿度仍为 20% RH。全部文件供本地审阅，没有自动提交到竞赛平台或 GitHub。

## 文件位置

- `results/result1.xlsx` 至 `results/result4.xlsx`：主工况正式结果。
- `results/scenarios/fitted_temperature/result2.xlsx` 至 `result4.xlsx`：第二工况结果，第一问沿用主工况。
- `results/validation/latent.json`：潜热模型的网格、时间算法交叉、敏感性和消融验证。
- `results/validation/ambient_fit.json`：四候选温度拟合、前 3 小时训练与后 1 小时验证、平台温度和条件 bootstrap 区间。
- `results/validation/fitted_numerics.json`：拟合温度情景的数值验证；其他最终全单元格回读证据也随两个结果包保留。
- `results/validation/accuracy-output-check.json`、`fitted-output-check.json`：当前主工况和拟合工况的全单元格核验；尽管前者名称含 accuracy，仍属于本轮有效证据。
- `docs/model/environment-fit.md`：拟合方法与解释；`docs/model/environment.md`、`numerics.md`：边界和数值规格。
- `paper/build/main.pdf`：最终可阅读论文，作为单独文件交付；支撑包内保留可编译 LaTeX、原题 PDF 和当前插图 PDF。
- `outputs/delivery/cumcm2026A_support.zip`：主工况源码、只读原题副本、结果、文档、验证、环境声明和论文源文件。
- `outputs/delivery/fitted_temperature_results.zip`：第二工况结果与拟合证据，须与主支撑包一起使用。
- `outputs/delivery/package_report.json`：包大小、SHA-256、成员完整性、结果文件来源一致性与是否超 20 MB。

如果主支撑包超过 20 MB，脚本额外生成 `cumcm2026A_source.zip` 和 `cumcm2026A_main_results.zip`，分别保留源文件和完整主结果。将两包解压到同一目录即可组合。原完整支撑包不删除。结果包或拟合包仍可能超过 20 MB；拆分不能保证单个大型 XLSX 变小，报告会如实标明，**不删行、不降低精度、不把结果拆成不可直接使用的片段**。

大小同时报告十进制 MB 与二进制 MiB，保守以 20,000,000 字节判断 20 MB。这里的包是完整本地审阅材料；正式提交时仍需根据当时平台规则组织，没有把超限材料标为提交合规。

## Windows 现有环境

下面命令使用用户指定的现有环境 `D:\anaconda\envs\26A`，不自动安装任何依赖。若将项目解压到其他位置，先把第一行目录换成实际解压根目录；后续相对脚本路径保持不变。不要依赖交互式 `conda activate`。

```powershell
Set-Location -LiteralPath 'D:\Download\cumcm2026A'
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python -c 'import sys,numpy,scipy,pandas,openpyxl,matplotlib; print(sys.executable); print(numpy.__version__, scipy.__version__, pandas.__version__, openpyxl.__version__, matplotlib.__version__)'
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/probe_templates.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/selfcheck.py
```

`environment.yml` 是项目依赖声明，其历史环境名可能与本机 `26A` 不同；本说明明确使用环境绝对路径。缺包时命令会报错，应审阅依赖声明后另行处理，不会静默换算法或安装软件。

## 从原附件重算

以下命令会更新计算结果、缓存、表图；如需保留正在审阅的交付，请先解压到另一个工作目录。`problem/` 全程只读。

完整一键入口同时完成两种工况、温度拟合、数值验证、工作簿全单元格回读、表图、论文与打包：

```powershell
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python -u scripts/run_pipeline.py
```

工作区根目录 `REPRODUCE.md` 也包含这一入口。仅需分步复现时使用以下命令：

```powershell
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/parse_attachments.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/fit_ambient_temperature.py --bootstrap 500
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python run_all.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/run_fitted_scenario.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/validate_latent.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/validate_fitted_scenario.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/audit_q4_boundary_layer.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python -m unittest discover -s tests -p test_numerics.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python -m unittest discover -s tests -p test_accuracy.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/verify_accuracy_outputs.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/verify_accuracy_outputs.py --fitted
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/build_paper_assets.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python paper/build_sources.py
```

细网格验证与每秒完整 XLSX 写出需要时间；不要在这些命令仍运行时打包。缓存未纳入交付 ZIP，因此首次复现需要真正求解。根目录 `run_all.py` 经 `scripts/run_q123_accuracy.py` 做依赖/模板预检并生成主工况四问；文件名称虽保留历史 accuracy 字样，仍是当前正式入口依赖，必须保留。拟合情景另存子目录，不覆盖主工况。后期空气湿度是独立设计值，不能解释为由温度拟合得出的湿度。

如果现有环境含 pytest，可再运行框架测试：

```powershell
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python -m pytest tests/test_framework.py
```

## 编译论文

已知本机 TeX Live 路径如下。编译产物只进入 `paper/build/`；中文使用 XeLaTeX。

```powershell
& 'D:\texlive\2026\bin\windows\latexmk.exe' -xelatex -interaction=nonstopmode -halt-on-error -cd -outdir=build paper/main.tex
```

最终论文若需要重新生成表图，必须先完成上面的两个工况求解与验证。直接编译已交付的 LaTeX 源码可使用包内现成表图；支撑包不会夹带历史编译 PDF 或缓存。

## 打包与完整性检查

仅在主工况、拟合工况、验证、论文均已完成时执行：

```powershell
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/package_delivery.py
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python scripts/package_delivery.py --verify-only
```

打包使用 Python 标准库，成员顺序、ZIP 内时间戳、权限固定；相同输入文件字节和同一 Python/zlib 运行时下可得到相同压缩包。每个包内有 `PACKAGE_MANIFEST.json`，包含所有实际文件的字节数和 SHA-256。脚本先检查 XLSX 自身 CRC 及其运行清单散列，再检查每个 ZIP 的 CRC、全部成员散列和字节数，未完成的结果或验证会阻止创建包。

脚本默认阻止“当前源码散列与结果计算时源码散列不同”的混合交付。应首先查清差异并重新计算必要结果。若差异经人工核实无需重算，可显式用 `--allow-source-drift` 打包；该选项仍把每一项差异写入包内清单和包外报告，不会声称来源一致。

打包排除 `.git`、工具元数据、计算缓存、`__pycache__`、Word 的 `~$` 临时文件、LaTeX 中间文件以及明确列举的旧报告：`accuracy.json`、`accuracy-q4.json`、`accuracy-reproduction.json`、`accuracy-methods.md`、`numerics.json`。不按 accuracy 前缀一刀切。

当前 `tests/test_accuracy.py` 保留：其中无潜热热解析解作为消融极限验证，另有潜热 BDF/Radau 与启动检查。它依赖 `scripts/validate_accuracy.py` 的 `bessel_heat` 函数，因此该辅助模块也保留；**不要单独运行该文件的历史主函数来替代当前潜热验证**。最新 `verify_accuracy_outputs.py` 同时支持主工况和 `--fitted` 的全单元格回读，必须保留。打包前脚本通过 AST 追踪主入口、完整流程入口及当前测试的本地导入和明确脚本调用，确认全部出现在计划 ZIP 清单。

原题只在压缩包里标记只读，工作目录中的原件不会被改名、改权限或重写。

潜热质量通量采用两场一致的表面边界，低含水率吸附等温线与结合水额外解吸焓尚无题中材料标定。数值守恒、网格加密以及很窄的温度拟合参数区间均不能证明未知药材的实际最优工况或真实实验误差。
