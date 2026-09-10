# CUMCM 2026 A —— 药材的烘干问题

2026 年高教社杯全国大学生数学建模竞赛 A 题。圆柱形中药材（长 25 cm、半径 2 cm）在热风烘房中的干燥过程，本质是**圆柱坐标下耦合的传热-传质 PDE**，问题 4 进一步引入**失水收缩导致的移动边界**。

**交付物**：论文一篇（LaTeX）+ `result1~4.xlsx` 四个结果文件。

---

## ⚠️ 先读这个

**`AGENTS.md` 是本仓库的宪法**，也是 AI 助理的唯一上下文入口。
它与本文件冲突时，以 `AGENTS.md` 为准。开工前必读。

| 我要… | 去看 |
|---|---|
| 了解规则 / 让 AI 干活 | **`AGENTS.md`** |
| 知道谁负责什么 | `docs/OWNERS.md` |
| 开分支 / 合并 / 解冲突 | `docs/BRANCHING.md` |
| 查符号和单位 | `docs/NOTATION.md` |
| 调别人的模块 | `docs/INTERFACES.md` |
| 查为什么这么建模 | `docs/DECISIONS.md` |
| 找活干 / 登记需求 | `docs/TASKS.md` |
| 看题目原文 | `problem/A题.pdf` |

---

## 快速开始

```bash
make setup     # 建 conda 环境（cumcm2026a），只需一次，约 3~5 分钟
make doctor    # 体检：依赖、LaTeX、目录
make probe     # 【必做】打印交付模板的真实结构
make data      # 解析附件
make all       # 四问求解 + 表格 + 插图
make paper     # 编译论文 -> paper/build/main.pdf
make check     # 提交前必跑（lint + fast test）
```

`make` 或 `make help` 看全部命令。

> 所有 python 调用都走 `conda run -n cumcm2026a`，**不需要 `conda activate`**，
> 非交互式终端、CI、AI agent 都能直接跑。

---

## 目录结构

```
cumcm2026A/
├── AGENTS.md              ★ AI 上下文入口 / 项目宪法（CLAUDE.md 等是它的软链）
├── README.md  Makefile  environment.yml  pyproject.toml
├── .gitignore  .gitattributes  .github/{CODEOWNERS,workflows/ci.yml}
│
├── problem/               【只读冻结】原始题目与附件，任何人不许改
├── data/                  数据管道（raw 入库 / interim 忽略 / processed 入库）
├── src/
│   ├── common/            共享层：units / paths / correlations / io_excel / plotting ...
│   ├── q1/ q2/ q3/ q4/    一题一目录，互不 import（只依赖 common）
├── scripts/               入口：parse_attachments / run_qN / make_tables / make_figs
├── tests/                 框架级冒烟测试（物理验证由 @impl 补）
├── results/               ★ 交付物 result1~4.xlsx（入库）
├── outputs/               可重建缓存与日志（忽略）
├── paper/
│   ├── main.tex  preamble.tex  refs.bib
│   ├── sections/          00_abstract … 09_conclusion（可并行写）
│   ├── figs/  tab/        ★ 由脚本生成（入库）
│   └── build/             编译产物（忽略）
└── docs/
    ├── OWNERS.md          分工与所有权矩阵
    ├── BRANCHING.md       ★ 分支命名与合并规则
    ├── NOTATION.md        ★ 符号与单位唯一真源
    ├── INTERFACES.md      模块接口契约
    ├── DECISIONS.md       建模决策记录（D-001 ~ D-011）
    ├── TASKS.md           任务看板
    └── model/             建模线工作区（q1~q4.md, correlations.md）
```

---

## 分工方式：按角色切

| 角色 | 主战场 | 职责 |
|---|---|---|
| `@model` 建模 | `docs/model/**`、`docs/NOTATION.md`、`docs/DECISIONS.md` | 说清「解什么方程、为什么这么解」 |
| `@impl` 编程 | `src/**`、`scripts/**`、`tests/**`、`data/**`、`results/**` | 让模型跑出数，并且数是对的 |
| `@paper` 论文 | `paper/**` | 把前两人的产出变成一篇能得分的文章 |

**按角色切分工是冲突最严重的切法**，所以本仓库用两条机制把冲突压到最低：

1. **文件级隔离**——三条线创作的文件集合**互不相交**，物理上改不到同一个文件。
2. **脚本化交接**——论文的表 1~表 6 由 `scripts/make_tables.py` 从 `results/*.xlsx` 生成 `paper/tab/*.tex`，插图由 `scripts/make_figs.py` 直接从交付物重绘。**数字永远只有一处来源，论文里不许手抄。**

详见 `AGENTS.md` §2 与 `docs/OWNERS.md`。

---

## 三条最容易出错的地方

1. **单位**。代码内部一律 SI（长度 m、温度 K）。`e^{-3850/T}` 里的 T 必须是开尔文——传摄氏度进去会静默产生「看起来合理」的错误结果。`src/common/units.py` 有防呆断言。
2. **附录 2/3/4 是三套不同公式**。问题 1 用附录 2（常数物性），问题 2/3 用附录 3，问题 4 用附录 4。**不可混用**，`tests` 里有断言守着。
3. **两个数据缺口**（已在 `docs/DECISIONS.md` 登记）：
   - 附件 1 只覆盖前 **4 小时**，而烘干过程持续 **72 小时** → D-009
   - 烘房水分浓度（~0.02）与药材水分浓度（2.55）**差 50~130 倍**，基准是否一致题目未说明 → D-011

---

## 当前状态

框架搭建阶段。**四个求解器均未实现**（抛 `NotImplementedError` 并在提示里列出前置条件），这是预期状态：

```bash
$ make q1
⏸  q1 的求解器尚未实现。这不是故障，是框架的预期状态。
   ...
   下一步：
     1. @model 完成 docs/model/q1.md
     2. @impl 实现 src/q1/solver.py
     3. 重跑 make q1
```

**下一步**：见 `docs/TASKS.md`。第一优先级是 `@model` 清空 `docs/DECISIONS.md` 的待决区（D-001 ~ D-011 全部阻塞下游）。
