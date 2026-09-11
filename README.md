# CUMCM 2026 A —— 药材的烘干问题

**2026-09-11 当前交付：四问潜热模型与双恒温方案。** 使用用户指定的 `D:\anaconda\envs\26A`，不使用skill，不推送GitHub或创建PR。

主工况为前4h沿附件、其后60°C/20%RH，Q3/Q4时长分别46.9964h/44.0360h；第二工况采用附件曲线拟合的50.0082°C/20%RH，分别62.7635h/58.2928h。数值来自正式计算，各处低于0.15的严格输出时刻另记在结果JSON中。

- 完整复现：`REPRODUCE.md`，入口 `scripts/run_pipeline.py`。
- 论文：`paper/main.tex`，PDF为 `paper/build/main.pdf`。
- 主结果：`results/result1.xlsx`—`result4.xlsx`；拟合工况：`results/scenarios/fitted_temperature/`。
- 新模型验证：`results/validation/latent.json`、`fitted_numerics.json`、两套全单元格回读报告。
- Q4亚微米表层尚无统一全场四位精度保证；输出位置和终点误差、模型未识别的解吸闭合详见论文。

模型、符号、数值验证和解释以当前 `docs/DECISIONS.md`、`docs/NOTATION.md` 及正式结果为准；旧模型记录已单独归档。

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

本机已有 26A 环境，直接运行：

```powershell
& 'D:\anaconda\Scripts\conda.exe' run -p 'D:\anaconda\envs\26A' --no-capture-output python -u scripts/run_pipeline.py
```

完整说明见 `REPRODUCE.md`。以下 Makefile 命令仅供已安装 make 的环境使用；本机无 make、pytest、ruff，已用等价 Python 入口完成计算、22 项框架自检和 14 项单元测试，未宣称 lint 通过。

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

> 本机所有 Python 调用都通过 `conda run -p D:\anaconda\envs\26A`；不依赖交互式 `conda activate`。Makefile 的历史环境名不替代用户指定环境。

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
├── tests/                 框架、守恒、边界与解析极限测试
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
    ├── DECISIONS.md       当前潜热与双恒温模型决策；旧决策另行归档
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
3. **环境延续和浓度基准**：附件 1 只覆盖前 4 小时，之后使用文献工况或附件温度拟合平台。空气湿含量按 kg 水/kg 干空气解释，与药材干基含水率分别处理，通过表面质量通量耦合，不能直接相减。所用假设及其局限见当前 `docs/DECISIONS.md`。

---

## 当前状态

四问潜热求解、两种恒温工况、全部七份工作簿及数值审计已完成。论文包含摘要、20 页正文及参考文献、完整源码附录。文件位置与复现方法见 `scripts/README_delivery.md`；最终压缩包完整性和来源核验见 `outputs/delivery/package_report.json`。

全部材料保留在本地工作分支，未推送 GitHub 或创建 PR。具体药材的解吸等温线与结合水附加解吸焓尚无标定，结果是所列模型和工况下的条件性计算；Q4 极薄表层不宣称统一四位小数精度。
