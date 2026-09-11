# TASKS.md —— 任务看板

> ⚠️ **本文件被三个人同时编辑，是冲突第一高发区。**
> **铁律：只改自己角色标题下的内容。不重排、不格式化、不动别人的段落。**
> 详见 `docs/BRANCHING.md` §5。

**当前阶段**：`CP0 · 框架搭建` ← 每到一个冻结点手动更新这里
**下一个冻结点**：CP1 —— 问题 1 模型定稿 + `result1.xlsx` 产出

---

## 🔶 阻塞项（先看这里）

> 有阻塞项未解决时，下游工作**应该停下来**，而不是自己假设一个值往前推。

- [ ] **D-001~D-008 全部待决** —— `@model` 负责在 CP1 前清空 `docs/DECISIONS.md` 的待决区
- [ ] D-002/D-003（表面蒸发潜热、汽化潜热取值）阻塞问题 2/3 全部结果

---

## @model

- [ ] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [ ] 清空 `docs/DECISIONS.md` 待决区 D-001~D-008
- [ ] `docs/model/correlations.md`：整理附录 2/3/4 三套公式，逐个做量纲校验
- [ ] `docs/model/q1.md`：预热阶段控制方程 + 边界条件 + 离散格式
- [ ] `docs/model/q2.md`：全流程两阶段模型
- [ ] `docs/model/q3.md`：终点判据（$C < 0.15$）的数值求法
- [ ] `docs/model/q4.md`：移动边界坐标变换推导
- [ ] `docs/NOTATION.md` §7 待定项全部补齐
- [ ] 论证假设：一维径向简化（长径比 12.5）、轴向均匀、端面效应忽略

---

## @impl

- [x] 四问数值精度改进：2561节点、边界时间节点分段积分、5121节点参考、Bessel/Radau交叉验证；四个xlsx全单元格回读、独立目录完整复算一致；22项selfcheck与11项数值测试通过。本机无make/pytest/ruff，按规则采用selfcheck及unittest替代，未宣称lint通过（2026-09-11）。

- [ ] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [ ] `make setup` 建好 conda 环境，`make doctor` 全绿
- [ ] `scripts/parse_attachments.py`：附件 1/2 解析 → `data/processed/*.csv`
- [ ] **读模板**：用 `openpyxl` 打出 `result1~4.xlsx` 的真实结构（工作表名、行列数、表头、时间单位），结论写进 `docs/INTERFACES.md`
- [ ] `src/common/units.py`、`paths.py`、`problem_spec.py`
- [ ] `src/common/correlations.py`：三套 `PropertySet` 实现（依赖 D-001 定稿）
- [ ] `src/common/io_excel.py`：`read_template` / `read_attachment` / `write_result` + 校验
- [ ] `src/common/plotting.py`：中文字体回退、矢量 PDF 输出
- [ ] `src/q1/`：`bc.py` / `model.py` / `solver.py` / `post.py`
- [ ] `tests/test_q1.py`：质量守恒、网格收敛阶、边界条件、极限情形
- [ ] 评估问题 3/4 跑 2~3 天的总计算量，给出耗时估算（`AGENTS.md` §4.4）
- [ ] `scripts/make_tables.py`、`make_figs.py`

---

## @paper

- [ ] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [ ] `make paper` 跑通，产出 `paper/build/main.pdf`（确认中文字体正常、无豆腐块）
- [ ] `paper/preamble.tex`：加入 `docs/NOTATION.md` §0 的全部符号宏
- [ ] `paper/sections/03_notation.tex`：从 `docs/NOTATION.md` 生成符号表（**不要手抄**）
- [ ] 核对 2026 年官方论文格式规范（`problem/format2026.doc`）：字号、页边距、页码、摘要页、承诺书
- [ ] `02_assumptions.tex`：每条假设写清**代价**，不只写"我们假设"
- [ ] `01_restate.tex`：问题重述（背景 + 四个问题的数学化表述）
- [ ] `04_q1.tex` ~ `07_q4.tex`：等 `@model` 的 `docs/model/qN.md` 定稿后开工
- [ ] `00_abstract.tex`：**最后写**。摘要决定第一印象，要包含四个问题的具体结论数字

---

## 跨线需求（登记，不要自己动手）

- [ ] @model 请将 `results/validation/accuracy-methods.md` 的已验证数值设置同步至 `docs/model/numerics.md`；物理方程和边界插值保持原模型（@impl / 2026-09-11）。
- [ ] @paper 请依 `results/validation/accuracy-methods.md` 更新第一问正文中的641节点、时间容差及验证段落；生成表图由编程端重建（@impl / 2026-09-11）。

> 格式：`- [ ] @目标角色 需求描述（提出人 @xxx / 日期）`
> **看到属于自己的条目，做完勾掉并在群里说一声。**

- [ ] @paper 请把 `problem/format2026.doc` 的格式要求提取成 `docs/paper_format.md`（提出人 @impl / 待办）

---

## 已完成

> 完成的任务从上面移到下面，保留日期。这既是进度记录，也是验收依据。

### 框架搭建阶段（赛前）

- [x] 目录框架、所有权矩阵、分支规则、AI 上下文入口 —— `AGENTS.md` / `docs/BRANCHING.md` / `docs/OWNERS.md`
- [x] `.gitignore` / `.gitattributes`（xlsx、pdf 标记为 binary，防 Windows 行尾损坏）
- [x] conda 环境声明 `environment.yml` + `Makefile`（自动探测环境名）
- [x] Python 骨架：`src/common/`（paths/units/correlations/problem_spec/io_excel/export/plotting/solution）
- [x] 四题求解器占位：`src/q1~q4/solver.py`（抛 `NotImplementedError` 并列出前置条件）
- [x] LaTeX 论文骨架：`paper/main.tex` + 10 个 section + `preamble.tex`（XeLaTeX 可编译）
- [x] **`make probe` 实测四个交付模板结构** → 结论固化进 `io_excel.LAYOUTS`（见 `docs/DECISIONS.md` D-012）
- [x] 数据管道 `scripts/parse_attachments.py`，含两个数据缺口的自动警告
- [x] 交付层 `io_excel.write_result` 硬校验（表名/列结构/时间步长/NaN）
- [x] 验证：`make selfcheck` 22 项全通过；pytest 42 项全通过
- [x] `problem/.DS_Store` 曾被误跟踪，已 `git rm --cached` 并加入 `.gitignore`
