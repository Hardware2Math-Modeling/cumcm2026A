# 本地复现

本次未使用任何skill，未推送GitHub或创建PR。原始 `problem/` 保持只读。

使用已有26A环境，运行完整计算、两方案、验证、论文与交付打包：

```powershell
Set-Location D:\Download\cumcm2026A
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python -u scripts/run_pipeline.py
```

仅重算主方案：`python run_all.py`。仅重算拟合方案：先运行 `scripts/fit_ambient_temperature.py`，再运行 `scripts/run_fitted_scenario.py`。这些相对命令也应通过上述conda环境前缀调用。

完整流程需要数分钟至数十分钟，2561节点参考计算和逐单元格回读最耗时；所有代码仅写当前仓库。程序失败会停止，不裁剪负含水率、不自动外推72h后的收缩数据、不伪造结果。

数学与科学计算依赖使用已有numpy、scipy、pandas、openpyxl、matplotlib；版本写入结果清单。不自动安装依赖。论文使用PATH中的XeLaTeX与latexmk，输出 `paper/build/main.pdf`；需要已有中文字体。当前机器无make、pytest、ruff，验证采用22项selfcheck及14项unittest；不能因此声称ruff lint通过。

新模型验证入口是 `scripts/validate_latent.py` 与 `scripts/validate_fitted_scenario.py`。旧无潜热accuracy报告只供追溯，不得用于当前论文。完整输出清单与限制见 `results/README.md`，ZIP规则见 `scripts/README_delivery.md`。
