# TASKS.md —— 任务看板

> ⚠️ **本文件被三个人同时编辑，是冲突第一高发区。**
> **铁律：只改自己角色标题下的内容。不重排、不格式化、不动别人的段落。**
> 详见 `docs/BRANCHING.md` §5。

**当前阶段**：`CP1 ✅ · 问题 1 模型定稿 + result1.xlsx 产出` → 四问求解器与结果均已就绪，论文仅第一问
**下一个冻结点**：CP2 —— 问题 2、3 模型定稿；`result2/3.xlsx` 产出（**结果文件已产出**，待论文相关小节）

---

## 🔶 阻塞项（先看这里）

> 有阻塞项未解决时，下游工作**应该停下来**，而不是自己假设一个值往前推。

- [x] **D-001~D-011 已全部清空待决区** —— 见 `docs/DECISIONS.md` §1（2026-09-11 定稿）
- [x] D-002/D-003（表面蒸发潜热、汽化潜热取值）已定：**不引入潜热**，表面按纯对流显热边界。
      代价（高估表面温度）已写入论文局限，并做了灵敏度分析。

**当前无阻塞项。**

⚠️ 残留待办（不阻塞交付，但论文的加分点）：
- [ ] 用干物质守恒**反推** $R(t)$ 并与附件 2 对比（D-010 的「未解决」项）
- [ ] 两相浓度基准的实证（D-011 目前是**有效闭合假设**，非已证明）

---

## @model

- [x] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [x] 清空 `docs/DECISIONS.md` 待决区 D-001~D-011 → 全部落定为 ✅，并新增 D-013（否决：材料坐标不得再加对流项）
- [x] `docs/model/correlations.md`：整理附录 2/3/4 三套公式，逐个做量纲校验 → **已定稿**，
      并从 `problem/A题.pdf` 逐条核对（留痕见 `docs/model/correlations_verified.md`）
- [x] `docs/model/q1.md`：预热阶段控制方程 + 边界条件 + 离散格式
- [x] `docs/model/q2.md`：全流程两阶段模型（统一附录 3，不设阶段切换）
- [x] `docs/model/q3.md`：终点判据（$C < 0.15$）的数值求法（向下过零事件）
- [x] `docs/model/q4.md`：移动边界坐标变换推导（含"不得再加 $\xi\dot R/R$ 项"的警告）
- [x] `docs/NOTATION.md` §7 待定项全部补齐；§3 的 $h$、$h_m$ 取值改为四问同一组
- [x] 论证假设：一维径向简化（长径比 L/2R = 6.25）、轴向均匀、端面效应忽略（D-007）
- [ ] `docs/OWNERS.md` 的 handle 目前仍是占位 —— 需要三人各自补真实 GitHub 用户名

---

## @impl

- [x] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [x] `make setup` 建好 conda 环境，`make doctor` 全绿
- [x] `scripts/parse_attachments.py`：附件 1/2 解析 → `data/processed/*.csv`
- [x] **读模板**：用 `openpyxl` 打出 `result1~4.xlsx` 的真实结构 → 结论在 `docs/DECISIONS.md` D-012
- [x] `src/common/units.py`、`paths.py`、`problem_spec.py`
- [x] `src/common/correlations.py`：三套 `PropertySet` 全部实现，系数已对题目原文核对
- [x] `src/common/io_excel.py`：`read_template` / `read_attachment` / `write_result` + 硬校验
- [x] `src/common/plotting.py`：中文字体回退、矢量 PDF 输出
- [x] **四问算法**：`src/common/radial.py`（节点中心有限体积 + BDF），`src/q1~q4/solver.py` 转发
- [x] `tests/test_numerics.py`：质量/能量守恒、BDF 与 Bessel 解析解对照、边界符号、Jacobian 方向导数、移动边界退化检验
- [x] 评估问题 3/4 的计算量并实跑：内部自适应 BDF，四问合计约 90 s（见 `results/*_summary.json` 的 `wall_time_s`）
- [x] `scripts/make_tables.py`、`make_figs.py`（**四问**都出表出图，2026-09-11 修复）
- [x] `scripts/validate_numerics.py` 接入 Makefile（`make validate`），并作为 `tables` 的文件目标依赖
- [ ] `src/q1/` 细分为 `bc.py` / `model.py` / `solver.py` / `post.py` —— **未做，且不打算做**：
      四问共用 `src/common/radial.py` 更少重复；细分只会增加转发层。若确需细分，属重构而非补功能。
- [ ] 网格**收敛阶**的显式拟合测试 —— 目前只有加密差值表（`tab/q1_validation`），未拟合观测阶
- [ ] `src/common/plotting.py` 无任何测试覆盖

---

## @paper

- [x] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [x] `make paper` 跑通，产出 `paper/build/main.pdf`（9 页，无未定义引用）
- [x] `paper/preamble.tex`：加入 `docs/NOTATION.md` §0 的全部符号宏，以及 `\geninput` / `\qonevalues`
- [x] `paper/sections/03_notation.tex`：符号表由 `make tables` 从 `docs/NOTATION.md` 生成（**不手抄**）
- [x] `02_assumptions.tex`：每条假设写清**代价**
- [x] `01_restate.tex`：问题重述与求解范围
- [x] **`04_q1.tex`：问题一完整章节**（控制方程、边界、有限体积离散、BDF、表 1/表 2、插图、结果分析）
- [x] `00_abstract.tex`：含第一问的具体结论数字（由 `\QOne*` 宏引入，不手抄）
- [x] `08_evaluation.tex`：守恒/解析解核验、空间与时间误差、优缺点与局限
- [ ] 核对 2026 年官方论文格式规范（`problem/format2026.doc`）：字号、页边距、页码、摘要页、承诺书
- [ ] **`05_q2.tex` / `06_q3.tex` / `07_q4.tex` 仍是占位**（`\instruction{}` 提示框），
      且 `main.tex` 尚未 `\input` 它们。表格与插图**已生成**，缺的是正文。
      ⚠️ 注意：这三节的目标是**同一篇论文**，合稿时应把标题从"问题一…"改成全卷标题。
- [ ] `paper/refs.bib` 目前是空骨架（0 条目、无人加载）；`main.tex` 用的是手写 `thebibliography`。二选一对齐

---

## 跨线需求（登记，不要自己动手）

> 格式：`- [ ] @目标角色 需求描述（提出人 @xxx / 日期）`
> **看到属于自己的条目，做完勾掉并在群里说一声。**

- [ ] @paper 请把 `problem/format2026.doc` 的格式要求提取成 `docs/paper_format.md`（提出人 @impl / 待办）
- [ ] @model 请确认 `AGENTS.md` §4.3「恒温干燥阶段：对流换热 + 蒸发潜热耦合」与本项目实际采用的
      纯对流闭合（D-002）不一致 —— 宪法文件需**三人同意**才能改（`docs/BRANCHING.md` §5），
      故目前只在 D-002 里记录了差异（提出人 @impl / 2026-09-11）

---

## 已完成

> 完成的任务从上面移到下面，保留日期。这既是进度记录，也是验收依据。

### 框架搭建阶段（赛前）

- [x] 目录框架、所有权矩阵、分支规则、AI 上下文入口 —— `AGENTS.md` / `docs/BRANCHING.md` / `docs/OWNERS.md`
- [x] `.gitignore` / `.gitattributes`（xlsx、pdf 标记为 binary，防 Windows 行尾损坏）
- [x] conda 环境声明 `environment.yml` + `Makefile`（自动探测环境名）
- [x] Python 骨架：`src/common/`（paths/units/correlations/problem_spec/io_excel/export/plotting/solution）
- [x] **`make probe` 实测四个交付模板结构** → 结论固化进 `io_excel.LAYOUTS`（见 `docs/DECISIONS.md` D-012）
- [x] 数据管道 `scripts/parse_attachments.py`，含两个数据缺口的自动警告
- [x] 交付层 `io_excel.write_result` 硬校验（表名/列结构/时间步长/NaN）
- [x] LaTeX 论文骨架：`paper/main.tex` + 10 个 section + `preamble.tex`（XeLaTeX 可编译）
- [x] `problem/.DS_Store` 曾被误跟踪，已 `git rm --cached` 并加入 `.gitignore`

### 四问求解阶段（2026-09-10）

- [x] 四问求解器实现并实跑：`result1~4.xlsx` 全部产出（问题 1/2 按 1 s，问题 3/4 按 60 s）
- [x] 数值验证报告 `results/validation/numerics.json`：网格加密、时间容差、环境敏感性、固定半径对照
- [x] 附录 2/3/4 公式逐条对照 `problem/A题.pdf` 核对（`docs/model/correlations_verified.md`）
- [x] 质量与能量守恒审计通过（相对残差 $\sim10^{-15}$）
- [x] 与圆柱 Bessel 级数解析解对照，最大温度差 $< 2\times10^{-4}$ K（问题 1）

### 收尾与修复阶段（2026-09-11）

- [x] **修复：论文从未编出过可用 PDF。** 5 处 `\input` 无保护 + `paper/tab`、`paper/figs` 产物未入库
      → 新增 `\geninput` / `\qonevalues` 宏（缺失时打印醒目占位框，不静默跳过）；
      `make paper` 改为依赖 `tables figs`；生成产物入库；CI 增加"产物已入库"校验
- [x] **修复：`make_figs.py` 只出第一问的图**（`for n in (1,)`）→ 四问都出
- [x] **修复：`make_tables.py` 的 `legacy_all_tables()` 是死代码**，论文引用的 `tab3~tab6` 无任何代码路径能产出
      → 重命名为 `tables_from_csvs()` 并接入 `main()`；表名对齐为 `q2_temp`/`q3_moist` 等
- [x] **修复：论文第二~四问的表缺时间单位** → 表头统一为 `时间/s`（表 1/2）与 `时间/h`（表 3~6）
- [x] **修复：验证报告永不更新。** `validate_numerics.py` 未接入 Makefile，`make tables` 一直读旧报告，
      已实测导致论文验证表的温度收敛差值印成 `9.38e-05`（正确值 `9.35e-05`）
      → 新增 `make validate`，并把 `results/validation/numerics.json` 设为 `tables` 的文件目标依赖
- [x] **修复：`probe_templates.py` 无条件 `return 0`**，四个模板全丢时 CI 仍判通过（静默失效）→ 改为非 0 退出
- [x] **修复：CI 的 `branches: [main, model, impl, paper]` 匹配不到 `impl/feat-*`**（`*` 不跨 `/`），
      这条分支的 CI 从未触发过 → 改为显式列出集成分支 + `'impl/**'` 等通配
- [x] **修复：`paper/main.synctex(busy)` 与根 `.DS_Store` 被 git 跟踪** → 取消跟踪；`.gitignore` 的
      `*.synctex.gz` 改为 `*.synctex*`（前者挡不住崩溃时留下的无扩展名变体）
- [x] **修复：`make doctor` 每条都带 `|| true`，永远不会失败** → 改为有问题时非 0 退出，
      并补上 `paper/tab`、`paper/figs`、`results/tables` 三项目录与生成产物检查
- [x] **修复：`make branch` 在 `.PHONY` 里但没有规则** → 静默退出 0，已移除
- [x] **修复：三处 F401 未用导入**（`make_tables.py` 的 `Path`、`read_attachment`，`validate_numerics.py` 的 `time`）
- [x] **修复：陈旧 docstring / 失效引用** —— `_runner.py`（称求解器未实现）、`correlations.py`（称实现待填）、
      `boundary.py`（引用不存在的 D-013 → 改为 D-009）
- [x] `docs/DECISIONS.md`：D-001~D-011 从待决区落定为已定条目；新增 D-013（否决项）；补 AI 会话记录
- [x] `docs/NOTATION.md`：§7 八条待定项全部落定；§3 的 $h$、$h_m$ 由"待定"改为四问同一组
- [x] `docs/model/correlations.md`：从空骨架补成完整公式表 + 量纲校验 + 附录 3/4 逐项对比
- [x] 本 `docs/TASKS.md` 从"CP0 框架搭建"同步到实际进度

### 待办（明确未做，不要当成已完成）

- [ ] 论文问题二/三/四正文（`05_q2.tex` / `06_q3.tex` / `07_q4.tex`）与合稿
- [ ] `docs/paper_format.md`（从 `problem/format2026.doc` 提取官方格式要求）
- [ ] 干物质守恒反推 $R(t)$ 与附件 2 对比（D-010）
- [ ] 网格收敛阶的显式拟合测试；`plotting.py` 的测试覆盖
- [ ] `paper/refs.bib` 与 `main.tex` 的参考文献机制二选一对齐
