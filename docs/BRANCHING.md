# BRANCHING.md —— 分支、命名与合并规则

> 面向 3 人按角色分工（建模 / 编程 / 论文）的短周期高强度协作。
> 所有规则的设计目标只有一个：**让 `main` 任何时候都能跑出数、编出论文。**

---

## 1. 分支模型总览

```
                        main  ← 唯一真源。受保护。任何时刻必须：
                         │        · make check 通过
                         │        · make all 能产出 result1~4.xlsx
                         │        · make paper 能编出 PDF
                         │
        ┌────────────────┼────────────────┬────────────────┐
        │                │                │                │
   ┌────▼────┐     ┌─────▼─────┐    ┌─────▼─────┐    (临时)
   │  model  │     │   impl    │    │   paper   │    infra/*
   │ 建模集成 │     │  编程集成  │    │  论文集成分 │
   └────┬────┘     └─────┬─────┘    └─────┬─────┘
        │                │                │
   model/feat-*     impl/feat-*      paper/feat-*     ← 短特性分支，寿命 < 半天
   model/fix-*      impl/fix-*       paper/fix-*
```

**三条集成分支长期存在**，分别对应三个角色的所有权领地。因为三条线的文件集**互不相交**（见 `AGENTS.md` §2），它们之间几乎不会冲突。

**短特性分支寿命不超过半天。** 竞赛只有 3 天，一个存活超过半天的分支意味着你在囤积冲突。

---

## 2. 命名规范

```
<scope>/<type>-<short-desc>
```

| 段 | 取值 | 说明 |
|---|---|---|
| `scope` | `model` \| `impl` \| `paper` \| `infra` | **必填**。一眼看出该谁 review |
| `type` | `feat` \| `fix` \| `docs` \| `exp` \| `chore` | **必填** |
| `short-desc` | 小写英文 + 连字符 | 2~4 个词，说清干什么 |

**全部小写，用 `-` 不用 `_`，不用中文，不用空格。**

```bash
# ✅ 好
impl/feat-q1-crank-nicolson       # 实现问题1的CN格式
impl/fix-q2-mass-conservation     # 修问题2的质量不守恒
model/docs-q3-boundary-condition  # 建模：补问题3的边界条件推导
model/exp-implicit-vs-explicit    # 建模：比较显隐式稳定性（试验性）
paper/feat-q1-section             # 论文：写问题1那一节
paper/fix-table5-decimals         # 论文：修表5小数位
infra/chore-add-ci                # 基础设施：加CI
data/ 属 impl 线，用 impl/feat-parse-attachment1

# ❌ 坏（会被打回）
my-branch          # 不知道谁的、干什么的
zhangq1            # 人名不是信息
fix                # 修什么？
feature/q1         # scope 缺失，且用了未定义的 type
```

**正则校验**（CI 或 pre-push 可挂）：
`^(model|impl|paper|infra)/(feat|fix|docs|exp|chore)-[a-z0-9]+(-[a-z0-9]+)*$`

**集成分支**就叫 `model`、`impl`、`paper`、`infra`，不带前缀，是四个固定名字。

---

## 3. 日常流程

### 3.1 从集成分支开短分支

```bash
git switch impl                    # 切到自己的集成分支
git pull --rebase origin impl      # ⚠️ 关键：先同步，再开分支
git switch -c impl/feat-q1-crank-nicolson
```

### 3.2 干活、提交

提交信息格式（Conventional Commits 的简化版，**中文描述欢迎**）：

```
<type>(<scope>): <做什么>

# 例：
feat(q1): 实现预热阶段 Crank-Nicolson 离散
fix(q2): 修正表面蒸发潜热项的量纲错误
model(q3): 补充附录3变物性的量纲一致性推导
paper(q1): 完成表1表2与结果分析
docs: 更新符号表，D 的变量名统一为 diff_coef
```

`scope` 取值：`q1` `q2` `q3` `q4` `common` `paper` `data` `infra`。

**提交要小、要勤。** 每完成一个逻辑单元就提交一次。禁止「攒一天再提交」——那会让冲突解决变成手工考古，也让 AI 无法回滚到干净状态。

### 3.3 回合自己的集成分支

同一角色内部，**不需要 PR、不需要 review**，直接合：

```bash
git switch impl
git pull --rebase origin impl
git merge --squash impl/feat-q1-crank-nicolson   # 压成一个提交
git commit -m "feat(q1): 实现预热阶段 Crank-Nicolson 离散"
git push origin impl
git branch -d impl/feat-q1-crank-nicolson
```

**为什么 squash**：短分支的中间提交（"改错了"、"再试一次"）是噪声。集成分支的历史应该读起来像进度报告。

### 3.4 集成分支 → `main`（唯一的正式关口）

```bash
git switch impl
git pull --rebase origin impl
git push origin impl

gh pr create --base main --head impl \
  --title "impl: 问题1求解器完成，产出 result1.xlsx" \
  --body "## 产出
- src/q1/solver.py：Crank-Nicolson，dt=0.1s 内部步长，插值到 1s 交付网格
- tests/test_q1.py：质量守恒 < 1e-8，网格收敛阶 1.98
- results/result1.xlsx 已重跑

## 需要 @model 确认
- 边界条件离散采用虚拟节点法，见 docs/model/q1.md 式(12)

## 自查
- [x] make check 通过
- [x] make q1 重跑过
- [x] docs/TASKS.md 已勾选"
```

**PR 合并条件（缺一不可）**：
1. `make check` 绿（**赛期内 CI 已暂停自动触发，见 §4.2 —— 改为本地跑 `make check` 并在 PR 描述里贴出结果**）
2. `make paper` 能编出 PDF（改了 `paper/` 或 `common/` 时必须）
3. `docs/OWNERS.md` §3 规定的 reviewer 已 approve
4. 分支已 rebase 到最新 `main`
5. 没有未解决的冲突标记（`<<<<<<<`）

**用 squash merge 还是 merge commit？**
- 三条集成分支 → `main`：用 **`--no-ff` merge commit**（保留「这是编程线的一次整体交付」这个语义，方便整体回滚）
- 短分支 → 集成分支：用 **squash**
- 禁止 **rebase merge**（会重写已推送的集成分支历史，其他人 pull 会炸）

---

## 4. 分支保护：赛期内**不启用**（零成本方案）

### 4.1 为什么不用

GitHub 对**私有仓库**的分支保护/rulesets 是**付费功能**。官方 API 描述的措辞是
"Protected branches are available in public repositories with GitHub Free and GitHub
Free for organizations" —— 反过来，私有仓库要 GitHub Team（约 $4/人/月）。

而本仓库**必须是私有**：CUMCM 规则要求参赛论文与解题过程赛期内不得公开。
**不要为了让功能免费而把仓库转 public**，那是拿参赛资格换每月 12 美元。

> **学生包也救不了**：GitHub Student Developer Pack 送的是**个人账号**的 Pro，
> **不会把组织升级到 Team**。本仓库挂在组织下，所以个人认证无效。

### 4.2 免费替代方案

| 分支保护原本要做什么 | 免费的替代 |
|---|---|
| 禁止直接提交 `main` | 约定 + 看 CI 红绿（见下） |
| 禁止 force push `main` | 约定。**这一条最需要自律** |
| PR 必须有人 approve | PR 描述里 `@` 指定 reviewer，人工确认 |
| 自动指派 reviewer（CODEOWNERS） | 同上，手动 `@` |
| Required status checks 拦截合并 | **CI 自 2026-09-11 起自动触发已暂停（见下）**；恢复触发后照常跑（私有仓库免费额度 2000 分钟/月，够用），只是不能设成"不绿就拦"。看红绿再点合并 |

**关键点：CI 本身是免费的**，`.github/workflows/ci.yml` 恢复触发后照常工作。
失去的只是"不绿就物理上合不了"这个强制力，而这一条在三人团队里靠人看就够了。

> **⚠️ 赛期内暂停 CI 自动触发（2026-09-11，用户决定）**
>
> `.github/workflows/ci.yml` 的 `push` / `pull_request` 已整块注释，只保留 `workflow_dispatch`。
> 因此 **Actions 不再给出红绿信号**，PR 合并条件里的"CI 自动跑"改由本地执行：
>
> | 原 CI 步骤 | 本地替代 |
> |---|---|
> | `ruff check / format` | `make lint`（本机无 ruff 时会提示并跳过） |
> | `scripts/selfcheck.py` | `make selfcheck` |
> | `pytest -q` | `make test` |
> | `probe_templates.py` + 论文产物已入库 | `make doctor` |
>
> **残留面**：只有 `main` 带上了这次改动；`model` / `impl` / `paper/**` 及其他远程分支在 rebase 到
> 新 `main` 之前仍是旧版 ci.yml（GitHub 按被推送 ref 上的 workflow 文件判定触发），
> push 到那些分支仍会跑 CI。若要**立即全局停用**，在网页 Actions → 左侧 `check` → "Disable workflow"。
>
> **恢复**：`git revert "$(git log --format=%H --grep='赛期内暂停 CI 自动触发' -1)"`（或按 ci.yml 里注释还原 `on:` 块）；
> 也可以只手动跑一次：Actions → `check` → Run workflow。

### 4.3 赛期内唯一靠得住的是三条约定

分支保护给的是**强制力**，不是**正确性**。三个都有写权限的人，真想违规谁也拦不住。
所以下面三条靠自律，比任何设置都重要：

1. **不在 `main` 上直接提交。**
2. **不对 `main` 与三条集成分支 force push。** ← 这条一旦违反，直接抹掉别人的工作且无法恢复
3. **合并前 `make check` 是绿的，PR 描述里指了 reviewer。**

### 4.4 `.github/CODEOWNERS` 仍然保留

虽然赛期内不生效，但它有两个作用：
- 把所有权矩阵**编码进仓库**，是给队友和 AI 看的机器可读文档；
- **赛后仓库转 public，它立即生效，一行都不用改。**

**要做的**：把 `.github/CODEOWNERS` 里的 `<handle>` 填成真实用户名。

### 4.5 三条集成分支不要设保护

即使将来开了付费套餐，也**不要**给 `model` / `impl` / `paper` 设保护 ——
否则自己合自己还要等审批，平白增加摩擦。

---

## 5. 共享文件清单 ← 唯一需要额外规则的地方

三条线文件集不相交，**只有下列文件被多方触碰**。改这些文件前，**先在群里说一句**（或开 issue），并尽量合并到少数几个提交里。

| 文件 | Owner | 冲突风险 | 规则 |
|---|---|---|---|
| `environment.yml` | `@impl` | 中 | 加依赖必须说明理由。**禁止**为一个人临时方便加包 |
| `Makefile` | `@impl` | 中 | 加 target 要同步更新 `help` 段 |
| `AGENTS.md` | 全体 | 高 | **三人同意才能改**。改完必须同步 review 一次自己的 AI 会话 |
| `docs/NOTATION.md` | `@model` | **极高** | 符号变更是破坏性变更，必须单独一个 PR + 通知全员 |
| `docs/INTERFACES.md` | `@impl` | 高 | 改接口签名 = 破坏别人的调用，必须单独 PR |
| `paper/main.tex` | `@paper` | 高 | 只做 `\input` 和宏包，**正文一个字都不写在这里** |
| `paper/preamble.tex` | `@paper` | 中 | 改宏包要确认所有人本地能编译 |
| `.gitignore` / `.gitattributes` | `@impl` | 低 | 改完跑 `git status` 确认没误伤交付物 |
| `docs/TASKS.md` | 全体 | **极高** | 见下 |

### `docs/TASKS.md` 的特殊处理

三人同时编辑同一个 markdown 必然冲突。**规则：每人只改自己那一段。**

```markdown
## @model
- [x] ...

## @impl
- [x] ...

## @paper
- [x] ...

## 跨线需求（登记，不要自己动手）
- [ ] @impl 请在 correlations.py 增加附录4公式集  ← 提出人 @model / 日期
```

**不要重排整个文件、不要重排别人的段落、不要全局格式化。** 只在自己的标题下追加或勾选。

---

## 6. 二进制文件：永远单人写

**这是硬规则，没有例外。**

| 文件 | 唯一写入者 | 原因 |
|---|---|---|
| `results/result1~4.xlsx` | `@impl`（通过 `make qN`） | 二进制，git 无法合并。两人同时生成 = 必丢一个人的结果 |
| `paper/figs/*.pdf` | `@impl`（通过 `make figs`） | 同上 |
| `paper/tab/*.tex` | `@impl`（通过 `make tables`） | 生成的，手改会被下次生成覆盖 |
| `problem/**/*.xlsx` | 无人 | 只读冻结 |

`@paper` **绝对不要手工编辑 `paper/tab/*.tex`**。格式不对 → 去改 `scripts/make_tables.py`（提需求给 `@impl`），不要改产物。

---

## 7. 冲突解决手册

### 7.1 通用流程

```bash
git fetch origin
git switch impl/feat-xxx
git rebase origin/impl          # 或 git merge origin/impl，看情况
# 解决冲突...
git add <解决的文件>
git rebase --continue
```

**冲突解决的三条铁律**：
1. **不要盲目选一边（`--ours`/`--theirs`）。** 冲突往往意味着两边都有新信息，要理解后重写。
2. **不确定就喊人。** 尤其是 `NOTATION.md`、`main.tex`、`INTERFACES.md` 的冲突——这三个文件的语义冲突比文本冲突严重得多。
3. **解决完必须重跑验证**：`make check`，如果碰了数值代码还要 `make qN` 确认结果没变。

### 7.2 分类型的应对

| 冲突文件 | 应对 |
|---|---|
| `docs/TASKS.md` | 保留**两边的新增行**，不要重排。这是最无害的一类 |
| `.tex`（不同章节） | 几乎不该发生（一人一文件）。发生了说明有人越界改了别人的 section，**先问为什么** |
| `main.tex` | 保留双方的 `\input` 行；若双方都改了 preamble，合并宏包列表 |
| `NOTATION.md` | **停下，喊 `@model`。** 符号冲突是建模层面的分歧 |
| `.xlsx` / `.pdf` | **无法解决。** `git checkout --ours` 选一个，然后由 `@impl` 重新生成一遍 |
| `environment.yml` | 两边依赖取并集，然后所有人重跑 `make setup` |
| `.ipynb` | 见 §8 |
| `Makefile` | 取并集，人工确认 target 名没撞车 |

---

## 8. Notebook 的处理

`.ipynb` 是 JSON，冲突几乎不可读。**规则：**

1. **Notebook 不作为协作载体。** 探索性 notebook 只放 `notebooks/`，且**一人一文件**，文件名的第一段就是角色名：`notebooks/impl-q2-explore.ipynb`。
2. **结论必须落回 markdown 或模块。** notebook 里发现的东西，要么写进 `docs/DECISIONS.md`，要么变成 `src/` 里的函数。**没有落地的 notebook 等于没做过。**
3. 交付路径（`src/`、`scripts/`、`results/`）**只能由 .py 文件产出**，不许由 notebook 产出——否则 `make` 复现不了。

---

## 9. 冻结点（Checkpoint）

赛程内设若干冻结点。**冻结后 `main` 只接受 `fix/*` 分支**。

| 冻结点 | 建议时点 | 通过标准 |
|---|---|---|
| **CP1** | D1 结束 | 问题 1 模型定稿（`docs/model/q1.md` 完成），`result1.xlsx` 产出 |
| **CP2** | D2 中午 | 问题 2、3 模型定稿；`result2/3.xlsx` 产出 |
| **CP3** | D2 结束 | 问题 4 模型定稿；`result4.xlsx` 产出；四问插图齐 |
| **CP4** | D3 中午 | **论文初稿合稿完成**，`make paper` 出 PDF，图表齐全 |
| **CP5** | D3 下午 | **内容冻结**：只允许改错别字、格式、小数位。不许再动模型和数字 |
| **提交** | D3 晚 | 提交 `main` 的 tag 指向的版本 |

冻结时打 tag：

```bash
git switch main && git pull --rebase origin main
git tag -a cp1 -m "CP1: 问题1定稿，result1 产出"
git push origin cp1
```

**超过冻结点还没通过的，砍功能不砍质量。** 宁可少写一节分析，不要交一份数字对不上的论文。

---

## 10. 禁忌清单

| 🚫 | 为什么 |
|---|---|
| `git push --force` 到 `main` / 集成分支 | 直接抹掉别人的工作，无法恢复 |
| 直接在 `main` 上提交 | 绕过唯一的质量关口 |
| 直接把 `main` 合进特性分支而不 rebase | 制造无意义的 merge commit 噪声 |
| 提交时跳过 `make check` | `main` 变红会让三个人一起停摆 |
| 手工编辑 `results/*.xlsx` / `paper/tab/*.tex` / `paper/figs/*` | 下次 `make` 就覆盖了，你的修改会静默消失 |
| 把数据集/中间缓存塞进 git | 仓库膨胀；且这些是可重建产物 |
| 长命分支（> 1 天） | 冲突随时间的平方增长 |
| 一个 PR 改三个角色领地 | reviewer 无法判断，且回滚时牵连过广 |
| 冲突时 `--ours` 一把梭 | 静默丢失对方工作 |

---

## 11. 速查卡

```bash
# 开始一项工作
git switch impl && git pull --rebase origin impl
git switch -c impl/feat-q1-crank-nicolson

# 提交
git add -p && git commit -m "feat(q1): 实现 Crank-Nicolson 离散"

# 合回自己的集成分支
git switch impl && git pull --rebase origin impl
git merge --squash impl/feat-q1-crank-nicolson && git commit
git push origin impl && git branch -d impl/feat-q1-crank-nicolson

# 交到 main
gh pr create --base main --head impl

# 我落后 main 多少？
git rev-list --left-right --count origin/main...HEAD

# 谁在改什么？（开赛前看一眼，避免撞车）
git log --all --oneline --since="2 hours ago" --name-only
```
