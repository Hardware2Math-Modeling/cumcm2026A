# TASKS.md —— 任务看板

> ⚠️ **本文件被三个人同时编辑，是冲突第一高发区。**
> **铁律：只改自己角色标题下的内容。不重排、不格式化、不动别人的段落。**
> 详见 `docs/BRANCHING.md` §5。

**当前阶段**：四问潜热模型、双恒温方案、论文与本地交付包全部完成（2026-09-11）
**冻结记录**：压缩包全部成员完整性、七份工作簿来源一致性检查通过；大小与SHA256以 outputs/delivery/package_report.json 为准

---

## 🔶 阻塞项（先看这里）

> 有阻塞项未解决时，下游工作**应该停下来**，而不是自己假设一个值往前推。

- [x] 旧D-001—D-014由本轮D-015—D-023取代，历史记录保存在docs/model/decisions_before_latent_20260911.md。
- [x] 潜热/湿度闭合已确认：FAO潜热、ASHRAE热质类比、供水与气膜互补；不存在旧“潜热待定”阻塞。

---

## @model

- [ ] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [x] 清空旧 D-001~D-008 待决状态，按本轮授权形成 D-015~D-023，旧记录完整归档（2026-09-11）
- [x] `docs/model/correlations.md`：整理附录 2/3/4 三套公式，逐个做量纲校验
- [x] `docs/model/q1.md`：预热阶段控制方程 + 边界条件 + 离散格式
- [x] `docs/model/q2.md`：全流程两阶段模型
- [x] `docs/model/q3.md`：终点判据（$C < 0.15$）的数值求法
- [x] `docs/model/q4.md`：移动边界坐标变换推导
- [x] `docs/NOTATION.md` 全部当前符号与物性、湿空气、潜热、拟合符号补齐（2026-09-11）
- [x] 论证一维径向、轴向均匀和端面近似；纠正长度/直径为6.25，长度/半径才为12.5（2026-09-11）

- [x] 四问潜热与供水/气膜互补定稿；否决跨气固浓度基准造成低于露点的旧闭合，记录局限（2026-09-11）
- [x] 核验温湿、潜热、Lewis与湿空气文献；形成60°C/20%RH主方案和附件拟合渐近温度第二方案（2026-09-11）
- [x] docs/model/numerics.md 同步当前1281节点、新模型验证采样边界与质量/能量审计；旧无潜热验证失效（2026-09-11）

---

## @impl

- [x] 四问加入有正负号的相变潜热，气固湿度基准分离，加入气膜能力与内部供水互补边界；11项物理单元测试通过。
- [x] 使用26A环境核实原模板与附件；附件升温曲线四候选比较及500次残差bootstrap已完成，拟合平台约50.0082°C。
- [x] 新模型两种工况共7个xlsx完整重算、网格/BDF-Radau/敏感性验证、全单元格回读与LaTeX表图生成；22项框架+14项物理/精度测试通过。Q4薄层精度限制已单列。
- [x] 最终论文与源码附录编译核验，交付包逐成员CRC/SHA256/字节数通过；主完整包与拟合结果包超20,000,000字节，完整保留并在报告标明，另提供源文件与主结果分包。未推送GitHub或创建PR。

- [x] 历史无潜热模型的数值精度改进：2561节点、边界时间节点分段积分、5121节点参考、Bessel/Radau交叉验证；四个xlsx全单元格回读、独立目录完整复算一致；22项selfcheck与11项数值测试通过。本条仅保留历史记录，不能作为本轮潜热模型证据。本轮设置与验证见上方条目及 results/validation/latent.json。

- [ ] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [x] 复用用户指定26A环境并核验依赖；make/pytest/ruff不可用，使用等价Python入口和selfcheck/unittest，不声称lint通过。
- [x] `scripts/parse_attachments.py`：附件 1/2 解析 → `data/processed/*.csv`
- [x] **读模板**：openpyxl实测四个模板，当前接口已同步 `docs/INTERFACES.md`
- [x] `src/common/units.py`、`paths.py`、`problem_spec.py`
- [x] `src/common/correlations.py`：三套PropertySet与有来源的潜热
- [x] `src/common/io_excel.py`：模板读写与硬校验；两方案全单元格回读
- [x] `src/common/plotting.py`及生成器：中文矢量PDF与页面字号检查
- [x] 四问solver入口调用共用radial.py有限体积实现，边界与后处理分别在common模块管理。
- [x] `tests/test_numerics.py`与`test_accuracy.py`：守恒、边界、凝结、潜热、收缩及解析极限验证
- [x] 1281节点正式计算与2561参考实际耗时写入验证报告；整流程按分钟级到数十分钟估计。
- [x] `scripts/make_tables.py`、`make_figs.py`与全部自动数值宏

---

## @paper

- [ ] 填写 `docs/OWNERS.md` 的真实姓名与 GitHub handle
- [x] `make paper` 跑通，产出 `paper/build/main.pdf`（确认中文字体正常、无豆腐块）
- [x] `paper/preamble.tex`：加入 `docs/NOTATION.md` §0 的全部符号宏
- [x] `paper/sections/03_notation.tex`：从 `docs/NOTATION.md` 生成符号表（**不要手抄**）
- [x] 核对 2026 年官方论文格式规范（`problem/format2026.doc`）：字号、页边距、页码、摘要页、承诺书
- [x] `02_assumptions.tex`：每条假设写清**代价**，不只写"我们假设"
- [x] `01_restate.tex`：问题重述（背景 + 四个问题的数学化表述）
- [x] `04_q1.tex` ~ `07_q4.tex`：等 `@model` 的 `docs/model/qN.md` 定稿后开工
- [x] `00_abstract.tex`：**最后写**。摘要决定第一印象，要包含四个问题的具体结论数字

---


- [x] 四问潜热/气膜边界、材料坐标收缩、真实文献、附件温度拟合第二工况及完整源码附录已写入；已编译为141页PDF，摘要1页、正文含参考文献20页，附录120页；无缺字、溢出框、未定义引用，完成正文全页渲染与附录抽样核验（2026-09-11）。

## 跨线需求（登记，不要自己动手）

- [x] 旧无潜热accuracy交接已被本輪latent.json及新模型文档取代；不得继续沿旧物理模型（@impl / 2026-09-11）。
- [x] 全四问论文改用当前1281节点、新潜热验证与两温度工况，旧Q1专用交接失效（@impl / 2026-09-11）。

> 格式：`- [ ] @目标角色 需求描述（提出人 @xxx / 日期）`
> **看到属于自己的条目，做完勾掉并在群里说一声。**

- [x] 格式原件已由@paper核对并记录在其拥有的 `paper/FORMAT_CHECK.md`（@impl确认）。

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
