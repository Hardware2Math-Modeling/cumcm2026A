# 问题二环境边界拟合

论文插入稿见 `q2_boundary_fit.tex`，精简版预览见 `demo.pdf`（单页，正文不足一页）；具体插入位置、符号衔接与结果一致性说明见 `INSERTION.md`。

仅从只读原件 `problem/附件/附件1.xlsx` 拟合烘房温度和水分浓度，所有产物留在本目录。**水分浓度单位是 kg/kg，不是相对湿度。** 不修改既有 PDE 求解器、论文或交付 Excel。

## 运行

在仓库根目录，使用已有 `tf2` 环境，无需安装依赖：

```bash
conda run -n tf2 python -B nihe/fit_boundary.py --bootstrap 300 --seed 20260912
conda run -n tf2 python -B -m unittest discover -s nihe -p 'test_*.py' -v
```

- `REPORT.md`：实际计算生成的数据来源、平台估计、完整模型比较、参数、时间留后验证、不确定性和局限。
- `fitted_curves.png` / `.pdf`：原始观测、渐近曲线、平台细节。
- `model_diagnostics.png` / `.pdf`：五类模型的残差和时间验证误差。
- `fit_boundary.py`：读取、拟合、验证、bootstrap、绘图及报告生成。
- `test_fit_boundary.py`：只读性、SI 单位、曲线性质、理想曲线参数恢复、时间验证防泄漏及复现测试。理想曲线仅用于单元测试，不是实验数据。

## Python 调用

从仓库根目录：

```python
from nihe.fit_boundary import fit_boundary

boundary = fit_boundary()
T_amb, C_amb = boundary.ambient([0, 1800, 10800, 259200])
```

`ambient()` 接受非负有限时间（秒），返回温度（K）与水分浓度（kg/kg）；标量和数组均可。`boundary.T_amb.plateau`、`boundary.C_amb.plateau` 是相应 SI 平台值。请只在初始化时调用一次 `fit_boundary()`，不要在 PDE 每一步重复拟合。

选择规则为三个时间滚动验证窗口的合并 RMSE 最小，最后半小时仅测试；选择后在全部观测上重拟合。5 类候选均有有限平台，平台、初始差值和时间尺度来自数据，而非指定为某个整数值。

4 小时以后的输出是“工况不变”假设下的外推，不是实测。区间为给定模型下的平台不确定性，不是对 2–3 天实际环境的保证。正式接入涉及其他 Owner 的文件，尚未在本任务中实施；报告保留交接说明。

## 本次验证记录

- `tf2` 实际为 Python 3.9.23；代码已在该环境完整运行，两次相同种子运行的 `REPORT.md` SHA-256 完全一致。
- 本目录 11 项 `unittest` 全部通过；Python 调用示例已验证，返回值使用 SI 单位。
- `make ENV=tf2 check` 完成，借用仓库已有 `.devtools/py` 运行的 53 项测试通过。`tf2` 缺少 `ruff`，Makefile 跳过了 lint，**不宣称 lint 已通过**，未安装或修改依赖。
- 输入 Excel 的 SHA-256 读取前后不变；PNG 与 PDF 渲染预览均已检查，无标签裁切或乱码。
- 从本地 `main` 创建分支 `impl/fix-q2-asymptotic-fit`，未提交或推送；原有 `docs/TASKS.md`、`handout/` 工作区内容未改动。
