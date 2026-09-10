# AGENTS.md —— CUMCM 2026 A 项目宪法

> **这是 AI 助理与本仓库任何自动化工具的唯一上下文入口。**
> 在本仓库开始任何工作前，先读完本文件。它与 `README.md` 冲突时，以本文件为准。
> 镜像：`CLAUDE.md`、`.github/copilot-instructions.md` 均为指向本文件的软链接，**只改本文件**。

---

## 0. 项目是什么

**2026 年高教社杯全国大学生数学建模竞赛 A 题：药材的烘干问题。**

圆柱形中药材（长 25 cm、半径 2 cm）在热风烘房中的干燥过程。物理本质是**圆柱坐标下耦合的传热-传质 PDE**，分「预热平衡」与「恒温干燥」两阶段；问题 4 进一步引入**失水收缩导致的移动边界**。

交付物两件：**论文一篇（LaTeX）** + **四个结果文件 `result1~4.xlsx`**。

题意原文在 `problem/A题.pdf`。**不要凭记忆或网络资料推断题意，一切以 `problem/` 里的原件为准。**

---

## 1. 十条铁律（违反即回滚重做）

1. **`problem/` 只读冻结。** 不许修改、移动、重命名、格式化其中任何文件，包括 `.DS_Store`。需要清洗后的数据，复制到 `data/` 再动。
2. **不许编造数据。** 任何数字必须有出处：题目附录、附件文件、或本仓库代码的实际输出。禁止「为了填满表格」而凭经验估值。做不到就在 `docs/TASKS.md` 里记一条待办。
3. **不许猜交付物格式。** `result*.xlsx` 的列名、行数、单位、工作表名，**以 `problem/附件/附件3/` 的模板文件为唯一真源**——写代码前先 `openpyxl.load_workbook(template)` 把结构读出来，不要自己发明。
4. **单位不得混用。** 代码内部一律 SI（见 §4）。长度在代码里是 **m**，温度在代码里是 **K**。只在「写入 xlsx / 画图」的最后一步才转成 cm / °C。
5. **不许硬编码物性参数。** ρ、c_p、k、D 全部通过 `src/common/correlations.py` 取得，且必须能按题号切换公式集（附录 2 / 附录 3 / 附录 4 是三套不同公式）。**在 `src/q*/` 里直接写 `0.36` 这类数字属于严重错误。**
6. **不许跨所有权改文件。** 你不是所有角色。见 §2 的所有权矩阵，只改自己那一列标 `Owner` 的路径。
7. **不许直接推 `main`。** 见 `docs/BRANCHING.md`。所有改动走分支 + PR。
8. **不许提交可重建的产物。** `outputs/`、`data/interim/`、`paper/build/` 已在 `.gitignore` 里；`results/`、`paper/figs/`、`paper/tab/` 是交付物，**必须提交**。
9. **改符号/公式必须同步 `docs/NOTATION.md`。** 论文、代码、表格里的符号必须逐字一致。只改一边视为未完成。
10. **不许静默降级。** 数值不收敛、边界条件对不上、质量不守恒——**报告出来**，写进 `docs/DECISIONS.md`，不要悄悄换个算法让它「看起来能跑」。

---

## 2. 目录地图与所有权矩阵

**3 人按角色分工：建模 / 编程 / 论文。** 这种切法的唯一防冲突手段是**物理隔离 + 强制交接**：三个人创作的文件集合**互不相交**。

| 路径 | 内容 | 建模 | 编程 | 论文 |
|---|---|:--:|:--:|:--:|
| `problem/` | 原始题目与附件 | 🚫 | 🚫 | 🚫 |
| `AGENTS.md` `README.md` `Makefile` `environment.yml` `pyproject.toml` `.gitignore` `.gitattributes` | 项目基础设施 | C | C | C |
| `docs/NOTATION.md` | **符号与单位唯一真源** | **Owner** | R | R |
| `docs/DECISIONS.md` | 建模决策记录（含 AI 会话结论） | **Owner** | C | C |
| `docs/model/**` | 数学推导、公式整理、假设论证 | **Owner** | R | R |
| `data/**` `scripts/**` `src/**` `tests/**` | 数据管道与求解代码 | C | **Owner** | — |
| `results/**` | 交付物 `result1~4.xlsx` + 论文用数值表 | C | **Owner** | R |
| `paper/**` | LaTeX 论文 | C | — | **Owner** |
| `docs/OWNERS.md` `docs/BRANCHING.md` `docs/INTERFACES.md` `docs/TASKS.md` | 协作规则 | C | C | C |

- **Owner** = 唯一有权直接修改的人（或该角色的 AI）。分支上只有 Owner 的提交能碰这些文件。
- **R** = 只读消费。**需要改就提需求**（PR comment 或 `docs/TASKS.md`），不要自己动手。
- **C** = 可以提建议、可以改，但必须走 PR 并知会另外两方。
- **🚫** = 任何人任何情况下都不许碰。

> **跨所有权改动的正确做法**：在 `docs/TASKS.md` 加一行 `- [ ] @impl 请在 correlations.py 增加附录4公式集（@model 提）`，而不是自己开编辑器。

### 三条角色线之间的交接协议

```
建模 (@model)                   编程 (@impl)                    论文 (@paper)
─────────────                   ─────────────                   ─────────────
docs/model/qN.md          ──►    src/qN/                  ──►    paper/sections/0N_qN.tex
（控制方程、离散格式、            （实现 + tests 验证）             （搬运公式、排版）
  边界条件、求解策略）                                              ▲
docs/NOTATION.md          ──►    src/common/correlations.py ──►    │
（符号、单位、参数表）            results/resultN.xlsx      ──►    paper/tab/tabN.tex
                                 （交付物 + 自动生成表格片段）─────┘
```

**关键机制：论文里的表 1~表 6 不允许手抄数字。** 由 `scripts/make_tables.py` 从 `results/*.xlsx` 生成 `paper/tab/*.tex`（booktabs 片段），论文用 `\input{tab/tab1}` 引入。数字永远只有一处来源。同理插图：程序直接输出到 `paper/figs/`，论文 `\includegraphics` 引用，**不要往论文目录复制图片**。

---

## 3. 环境与命令

```bash
make setup     # 首次：按 environment.yml 创建 conda 环境 cumcm2026a
make env       # 显示当前实际使用的 conda 环境与依赖状态
make doctor    # 体检：依赖、LaTeX、目录
make probe     # 【开工必做】打印交付模板与附件的真实结构
make data      # 解析附件 -> data/processed
make all       # 四问求解 -> 表格 -> 插图
make paper     # 编译论文 -> paper/build/main.pdf
make check     # 提交前必跑（lint + test）
make selfcheck # 框架自检，不依赖 pytest，任何环境都能跑
make status    # 我该 rebase 了吗
```

细则：
- **依赖只能改 `environment.yml`**，改完跑 `conda env update -f environment.yml --prune`。禁止 `pip install` 后直接提交代码。
- 所有 python 调用统一走 `conda run -n $(ENV) ...`（Makefile 已封装），**不要依赖 `conda activate`**，因为非交互式 shell 里它不生效。
- **环境名自动探测**：优先 `cumcm2026a`，没有则回退到已有的 `tf2`。也可手动指定 `make ENV=<名字> <目标>`。
- 若环境里没有 `pytest`/`ruff`，`make check` 会给出安装提示并回退到 `make selfcheck` —— **不要因此跳过验证**。
- 论文用 `latexmk -xelatex`（中文需要 XeLaTeX，`ctexart` 已确认可用）。**不要用 `pdflatex`**，中文会炸。
- 编译产物一律进 `paper/build/`（通过 `-outdir=build`）。不要在 `paper/` 根目录留 `.aux`。

---

## 4. 领域约定（AI 最容易在这里犯错）

### 4.1 单位铁律

| 物理量 | 题目/论文单位 | **代码内部单位** | 转换位置 |
|---|---|---|---|
| 长度、半径、位置 | cm | **m** | 仅 `io_excel` 写出 / `plotting` 画图时 ×0.01 |
| 温度 | °C | **K** | 仅写出/画图时 −273.15 |
| 时间 | s（Q1）、h（Q2~Q4 展示） | **s** | 仅写出时 ÷3600 |
| 水分浓度 C（干基） | kg/kg | kg/kg | 不转换 |
| 密度 ρ | kg/m³ | kg/m³ | — |
| 比热 c_p | J/(kg·K) | J/(kg·K) | — |
| 导热系数 k | W/(m·K) | W/(m·K) | — |
| 对流换热系数 h | W/(m²·K) | W/(m²·K) | — |
| 对流传质系数 h_m | m/s | m/s | — |
| 扩散系数 D | m²/s | m²/s | — |

> ⚠️ **最经典的坑**：附录 3/4 的 D 公式含因子 `e^(−3850/T)`，这里的 **T 必须是开尔文**。若把 60 °C 当成 60 代进去，结果会错得离谱且「看起来还在合理范围」。凡是出现指数项，先确认温度单位。

### 4.2 几何与网格

- 圆柱：长 **L = 0.25 m**，初始半径 **R₀ = 0.02 m**。题目给的是**到药材中心的距离 r**，不是半径坐标的某种变换——`r = 0` 是轴心，`r = R` 是表面。
- 空间上是一维轴对称（沿半径方向），周向与轴向均匀。
- 交付精度：**空间步长 0.1 cm = 1 mm**，**时间步长 1 s**（问题 3/4 完整结果按 60 s 输出，见模板）。
- 论文表格的展示网格：`r = 0, 0.5, 1, 1.5, 2` cm；问题 4 的最后一列是**当时**的药材表面位置（会随时间收缩）。
- **数值求解的内部步长可以比交付步长更细**（例如 dt=0.1 s 做稳定性），最后插值到交付网格。若这么做，必须在 `docs/DECISIONS.md` 里写明并给出步长无关性验证。

### 4.3 两个阶段的物理差异

| | 预热平衡阶段 | 恒温干燥阶段 |
|---|---|---|
| 主导 | 热量传入、温度上升，水分变化慢 | 水分向外扩散、蒸发耗热 |
| 表面条件 | 对流换热为主 | 对流换热 + 蒸发潜热耦合 |
| 参数集 | 附录 2（常数物性） | 附录 3（ρ、c_p、k、D 均为 C、T 的函数） |
| 出现于 | 问题 1 | 问题 2、3、4（问题 4 用附录 4） |

**附录 2 / 3 / 4 是三套独立参数化，不要混用。** 问题 1 用常数物性，问题 2/3 用附录 3 的变物性，问题 4 用附录 4 的变物性**外加**尺寸变化。

### 4.4 数值方法的现实约束

- 变物性 + 非线性（D 依赖 C 和 T 的指数形式）→ 显式格式对 dt 的要求可能非常苛刻。**先做稳定性分析再选格式**，优先考虑隐式/半隐式（Crank–Nicolson）或 `scipy.integrate.solve_ivp`（method of lines），把空间离散后用稀疏矩阵交给 `scipy.sparse`。
- 问题 3/4 要跑到 **2~3 天 = 172800~259200 s**。若 dt=1 s，那是 17~26 万步——**必须评估总计算量**，必要时用变步长或自适应积分器。别写完才发现要跑 8 小时。
- 问题 4 的移动边界：优先考虑**坐标变换到固定计算域**（例如令 ξ = r/R(t)），比真正的移动网格实现简单一个数量级。这是建模决策，写进 `docs/DECISIONS.md`。

---

## 5. 交付物规范（`results/resultN.xlsx`）

**唯一真源是 `problem/附件/附件3/resultN.xlsx` 模板。** 写代码前先跑 `make probe` 把它读出来。

以下结构是 **`make probe` 实测**得到的（不是从题目文字猜的），已固化在
`src/common/io_excel.py` 的 `LAYOUTS`，并由 `tests` 与 `make selfcheck` 守门：

| 文件 | 工作表名 | 时间步长 | 末列表头 |
|---|---|---|---|
| `result1` | `温度`、`水分浓度` | **1 s** | `2` |
| `result2` | `温度`、`水分浓度` | **1 s** | `2` |
| `result3` | **`Sheet1`** | **60 s** | `2` |
| `result4` | **`Sheet1`** | **60 s** | **`药材表面`** |

**四条最容易踩的实测结论（每一条都足以让交付物作废）：**

1. **时间列单位是秒**，尽管题目表 3~表 6 的表头写的是 `h`。
   交付文件用**秒**；**论文表格才用小时**。别混。
2. **距离列是完整的 21 列**：`0, 0.1, 0.2, …, 2.0`。
   模板里的 `…` 是一个**文字单元格**，是省略示意，不代表只有 4 列。
3. **result3 / result4 的工作表名是 `Sheet1`**，不是「水分浓度」。
4. **result4 末列是文字 `药材表面`**；前 20 列是固定物理位置 `0 ~ 1.9`，
   末列是**当时**的表面值（表面会从 2.0 收缩到 1.198 cm）。

其余规则：
- A1 是斜线表头 `时间\到药材中心的距离`（既表时间也表距离）。
- 所有数值**保留 4 位小数**。
- 交付由一个额外产出：论文表格专用的展示网格，放 `results/tables/*.csv`，供 `make tables` 消费。
- `io_excel.write_result()` 会**硬校验**表名/列结构/时间步长/NaN，不合格直接抛异常且不写文件。
  **不要绕过它，也不要捕获它的异常继续跑** —— 格式错了就是错了。

> 赛方若更新模板，`tests/test_framework.py::test_layout_matches_real_template` 与
> `scripts/selfcheck.py` 会立刻失败。跑 `make probe` 看差异，然后更新 `io_excel.LAYOUTS`。

---

## 6. AI 的工作协议

### 开工前（缺一不可）
1. 读本文件。
2. 读 `docs/TASKS.md` 确认要做什么、是不是已经有人在做。
3. 读 `docs/NOTATION.md`——**用里面的符号，不要自己发明新符号**。
4. 读 `docs/INTERFACES.md`——调用别人的模块前先看契约，不要猜函数签名。
5. `make status` 确认自己在正确的分支上（不是 `main`）。

### 工作中
- **一次只做一件事**，提交信息写清「哪个题、哪个阶段」。参考格式：
  `feat(q1): 预热阶段 Crank-Nicolson 离散与边界条件`
  `model(q2): 补充附录3变物性的量纲一致性推导`
  `paper(q3): 完成问题三结果分析与表5`
- 需要别人所有权下的改动 → 写进 `docs/TASKS.md`，**不要直接改**。
- 遇到题意不清、参数缺失、方法有分歧 → 记入 `docs/DECISIONS.md` 的「待决」区，然后停下问人。**不要自行假设一个值继续推进。**

### 收工前（Definition of Done）
- [ ] `make check` 通过（lint + fast test）
- [ ] 新代码有对应测试；物理相关代码有守恒律 / 收敛性验证
- [ ] 若产出交付物：`make qN` 重跑过，`results/resultN.xlsx` 已更新
- [ ] 若改了符号 / 公式 / 参数：`docs/NOTATION.md` 与 `docs/DECISIONS.md` 已同步
- [ ] 若论文数字变了：`make tables figs` 重跑，`paper/tab/*.tex` 与插图已更新
- [ ] `docs/TASKS.md` 勾掉对应条目
- [ ] 提交信息符合规范；分支名符合 `docs/BRANCHING.md`

---

## 7. 索引

| 我要… | 去看 |
|---|---|
| 知道谁负责什么 | `docs/OWNERS.md` |
| 开分支 / 合并 / 解冲突 | `docs/BRANCHING.md` |
| 查符号和单位 | `docs/NOTATION.md` |
| 调别人的模块 | `docs/INTERFACES.md` |
| 查为什么这么建模 | `docs/DECISIONS.md` |
| 找活干 / 登记需求 | `docs/TASKS.md` |
| 看题目原文 | `problem/A题.pdf` |
| 看交付模板 | `problem/附件/附件3/result1.xlsx` |
