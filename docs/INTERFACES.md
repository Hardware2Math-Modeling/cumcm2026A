# INTERFACES.md —— 模块接口契约

## 2026-09-11 当前潜热模型接口（优先于下方历史说明）

本轮用户要求四问均计入潜热，并比较文献恒温与附件曲线拟合恒温。模型与符号以当前 `docs/NOTATION.md`、`docs/model/numerics.md` 为准。下方早期签名示意中的“待实现/待决”已失效；实际类型使用 `InitialState.T/C`、`Grid.dt/t_end/r`。

- `Boundary.for_problem(problem, temperature_c=60.0, relative_humidity=0.20)`：前14400s读附件1；后三问其后使用设定温度与RH换算出的空气湿含量Y。兼容字段 `C_amb` 存储Y，绝不是药材平衡含水率。
- `psychrometrics.humidity_ratio(T, relative_humidity, pressure=101325.0)`：K输入，返回kg水/kg干空气。`gas_evaporation_capacity(T_s,Y_amb,h,lewis=.845)` 返回可正可负的kg/(m²s)。
- `RadialModel.surface_fluxes(t,T_s,C_s)`：返回 `(j_v/rho_d, h*(T_amb-T_s), latent_heat(T_s)*j_v)`。通量j_v由供水和气膜互补条件确定，禁止跨气固基准直接相减。
- `solve_radial(spec, **opts)` 默认启用潜热与上述边界，正式参数见 `numerical_settings.production_options`。`latent_heat=False`仅供消融或纯热解析验证；`moisture_boundary='legacy_effective'`仅供旧解析测试，不是正式结果。
- `Solution.meta` 保存连续阈值、首个整步严格合格时刻、质量残差、Q1净热量残差和模型描述。Q4参考r需乘R(t)/R0，表面列单独导出；固定物理位置超出当前药材域留空，这是有物理依据的唯一NaN例外。
- `scripts/fit_ambient_temperature.py` 生成 `results/validation/ambient_fit.json`；其中 `selected.T_inf_K` 是第二工况常数温度，区间是所选模型下的条件参数区间。
- `scripts/run_fitted_scenario.py` 将第二工况Q2—4写入 `results/scenarios/fitted_temperature/`，通过同一个 `io_excel.write_result` 校验，不覆盖主方案。
- `scripts/build_paper_assets.py` 从正式xlsx抽取规则时刻、从求解器事件记录取得非整步终点，生成全部表图及 `paper/tab/all_values.tex`。旧Q1专用宏和旧accuracy报告不再用于当前论文。
- `scripts/validate_latent.py` 是新模型数值审计入口；旧 `accuracy*.json`、`numerics.json` 仅作无潜热历史记录，不得用作当前模型证据。

本轮仅本地协作，遵照用户要求不推送GitHub、不创建PR。`make` 在本机不可用，使用 `D:/anaconda/Scripts/conda.exe run -p D:/anaconda/envs/26A --no-capture-output python ...` 等价运行。

> **Owner: `@impl`。** 这些签名是**冻结契约**。
> `@model` 和 `@paper` 依赖它来理解代码；`@impl` 内部的实现可以随便改，**签名不能随便改**。
> 改签名 = 破坏别人的调用，必须单独 PR + 通知全员。

---

## 1. 设计原则

1. **内部 SI，边界转换。** 所有函数内部收发的长度都是 m、温度都是 K。转换只发生在 `io_excel` 和 `plotting`。
2. **参数集是第一类对象。** ρ/c_p/k/D 不通过散装参数传递，而是传一个 `PropertySet` 或 `ProblemSpec`。
3. **求解器不负责 I/O。** `src/qN/solver.py` 只吃 numpy 数组、只吐 numpy 数组。写 xlsx 是 `scripts/` 的事。
4. **未知的实现留 `NotImplementedError`，不要返回假数据。** 见 `AGENTS.md` 铁律 2。

---

## 2. `src/common/paths.py` —— 路径常量

```python
ROOT: Path          # 仓库根
PROBLEM_DIR: Path   # problem/
DATA_RAW: Path
DATA_INTERIM: Path
DATA_PROCESSED: Path
RESULTS_DIR: Path   # results/
FIGURES_DIR: Path   # paper/figs/   ← 图片直接写到这里，不要再复制
TABLES_DIR: Path    # paper/tab/    ← 生成的 booktabs 片段
OUTPUTS_CACHE: Path # outputs/cache/
OUTPUTS_LOGS: Path

def rel(path) -> str: ...   # 转为相对 ROOT 的字符串，用于日志和 xlsx 溯源
```

**规则**：任何模块都**不许**自己拼 `"../.."` 相对路径。一律 `from common.paths import ROOT`。

---

## 3. `src/common/units.py` —— 单位换算

```python
CM_TO_M: float;  M_TO_CM: float
S_TO_H: float;   H_TO_S: float
C_TO_K: float;   K_TO_C: float

def cm_to_m(x): ...      # 标量或 ndarray，下同
def m_to_cm(x): ...
def c_to_k(x): ...
def k_to_c(x): ...
def s_to_h(x): ...
def h_to_s(x): ...
```

---

## 4. `src/common/problem_spec.py` —— 题目常量与案例定义

把"题目给的东西"集中成结构化对象，避免散落在代码里。

```python
@dataclass(frozen=True)
class Geometry:
    length: float        # L, m
    radius0: float       # R0, m

@dataclass(frozen=True)
class InitialState:
    T0: float            # K
    C0: float            # kg/kg (干基)

@dataclass(frozen=True)
class Grid:
    n_r: int             # 径向交付节点数
    n_t: int             # 时间交付步数
    dt_output: float     # s
    dr_output: float     # m
    def r(self) -> np.ndarray: ...      # 交付用的径向坐标 (m)

@dataclass(frozen=True)
class ProblemSpec:
    """一个问题的完整静态定义。"""
    name: str                  # "q1" | "q2" | "q3" | "q4"
    geometry: Geometry
    initial: InitialState
    grid: Grid
    properties: PropertySet    # 见 §5
    t_end: float               # s
    uses_shrinkage: bool       # 问题 4 为 True

Q1: ProblemSpec
Q2: ProblemSpec
Q3: ProblemSpec
Q4: ProblemSpec
```

---

## 5. `src/common/correlations.py` —— 物性公式（**三套，可切换**）

```python
class PropertySet(Protocol):
    """物性公式集。附录2/3/4 各实现一个。"""
    def rho(self, C, T) -> ArrayLike: ...   # kg/m^3，含湿表观密度
    def cp(self, C, T) -> ArrayLike: ...    # J/(kg·K)
    def k(self, C, T) -> ArrayLike: ...     # W/(m·K)
    def D(self, C, T) -> ArrayLike: ...     # m^2/s
    # 若某套公式不含 T 依赖，仍需接受 T 参数并忽略之 —— 统一签名

class Appendix2(PropertySet):  # 问题1：常数物性
    ...
class Appendix3(PropertySet):  # 问题2、3：变物性
    ...
class Appendix4(PropertySet):  # 问题4：变物性 + 收缩
    ...

# 对流系数（不是"物性"而是"工况"，但仍集中在这里）
def h_conv(spec: ProblemSpec) -> float: ...   # W/(m^2·K)
def h_mass(spec: ProblemSpec) -> float: ...   # m/s

# 水蒸气/水的物性（题目未给，需查表并记录出处）
def latent_heat_vaporization(T) -> ArrayLike: ...  # J/kg
```

**硬要求**：
- `C` 一律是**干基**含水率（kg/kg）。公式里需要湿基 $w=C/(1+C)$ 时**在函数内部换算**，不要把这个负担丢给调用方。
- `T` 一律是**开尔文**。实现里凡是出现 `exp(-3850/T)` 必须断言 `T > 200`。

```python
def _assert_kelvin(T):
    """防呆：附录3/4 的 D 公式里 T 必须是 K。传摄氏度会静默出错。"""
    ...
```

---

## 6. `src/common/io_excel.py` —— 交付物读写

```python
TIME_HEADER = "时间\\到药材中心的距离"   # A1 斜线表头（实测原文）
SURFACE_HEADER = "药材表面"              # result4 末列（文字，非数值）
DECIMALS = 4
N_DISTANCE_COLUMNS = 21                  # 0 ~ 2 cm，步长 0.1 cm

@dataclass(frozen=True)
class ResultLayout:
    problem: str
    sheets: tuple[tuple[str, str], ...]   # (工作表名, "T"|"C")
    dt_s: float                            # 交付时间步长（秒）
    last_header: str = "2"
    def sheet_names(self) -> tuple[str, ...]: ...
    def distance_headers(self) -> list[str]: ...
    def expected_columns(self) -> list[str]: ...

LAYOUTS: dict[str, ResultLayout]

def layout(problem: str) -> ResultLayout: ...
    """交付布局。**唯一真源**，来自 `make probe` 实测，不是从题目文字猜的。"""

def read_attachment(n: int) -> pd.DataFrame: ...
    """读 problem/附件/附件<N>.xlsx。n=1 烘房条件，n=2 半径。
    单位与原件一致（时间 s、半径 cm、温度 °C）。"""

def read_template(problem: str) -> dict[str, pd.DataFrame]: ...
    """读交付模板的原始内容（含 '…' 示意列）。仅用于探查与交叉核对。"""

def verify_layout_against_template(problem: str) -> list[str]: ...
    """把实测布局与实际模板对一遍，返回不一致项。
    **CI 与 selfcheck 都跑这个**：赛方更新模板时会立刻报出来。"""

def write_result(problem: str, sheets: dict[str, pd.DataFrame]) -> Path: ...
    """写 results/result<N>.xlsx。校验不通过直接 raise，不写出文件。"""

def write_table_csv(df: pd.DataFrame, name: str) -> Path: ...
```

### 实测布局（`make probe`，赛前核对过）

| 文件 | 工作表名 | 时间步长 | 末列表头 |
|---|---|---|---|
| `result1` | `温度`、`水分浓度` | 1 s | `2` |
| `result2` | `温度`、`水分浓度` | 1 s | `2` |
| `result3` | **`Sheet1`** | 60 s | `2` |
| `result4` | **`Sheet1`** | 60 s | **`药材表面`** |

**四条最容易踩的实测结论**：
1. **时间列单位是秒**，尽管题目表 3~表 6 的表头写的是 h。交付用秒，论文表格才用小时。
2. **距离列是完整 21 列**（0, 0.1, …, 2.0）。模板里的 `…` 是一个文字单元格，是省略示意。
3. **result3/result4 的工作表名是 `Sheet1`**，不是「水分浓度」。
4. **result4 末列是文字 `药材表面`**；前 20 列是固定位置 0~1.9，末列是当时的表面值。

### 校验清单（`write_result` 内部硬失败，不通过就 raise）

- 工作表名与 `layout()` 一致
- 列结构完全等于 `expected_columns()`（1 列时间 + 21 列距离）
- 时间列单调且步长均匀等于 `dt_s`
- 所有值 `isfinite`；写出前统一 `round(4)`
- 空工作表拒绝写出

> 校验失败的报错信息必须**指名道姓**说是哪个表、哪一列错了，并提示跑 `make probe`。

---

## 7. `src/common/plotting.py` —— 论文插图

```python
apply_style() -> None
    """全局设置中文字体 + 论文可用字号。调用一次即可。
    中文字体：macOS 用 'Songti SC'/'Heiti SC'，需回退列表，防止 Linux/CI 上豆腐块。"""

def plot_profiles(results: dict, spec: ProblemSpec, *, field: str,
                  times: Sequence[float], out: str | Path) -> Path:
    """画某一物理量在若干时刻的径向分布。
    field: "T" 或 "C"
    输出：paper/figs/<name>.pdf（矢量，插图必须用 PDF 不用 PNG）"""

def plot_history(results: dict, spec: ProblemSpec, *, locations: Sequence[float],
                 out) -> Path:
    """画若干位置的时间历程。"""

def plot_grid_convergence(errors: dict, out) -> Path:
    """画网格收敛性曲线（log-log），用于论文的模型验证一节。"""
```

**规则**：
- 插图输出格式一律 **PDF**（矢量），不要 PNG。像素图在论文里会糊。
- 所有图**必须**有轴标签含单位，字号不小于 9pt。
- 图里的单位是 **cm 和 °C**（展示单位），所以 `plotting` 内部要调用 `units` 做转换。

---

## 8. `src/qN/solver.py` —— 求解器

> `Solution` 定义在 **`src/common/solution.py`**（不是 solver 里），
> 这样 `plotting` / `io_excel` 不必反向依赖 `src/qN/`。

```python
def solve(spec: ProblemSpec, **opts) -> Solution:
    """求解第 N 问。

    参数
    ----
    spec : ProblemSpec
    opts : 各题自定义。建议至少支持 dt_internal（内部时间步长，s）与 theta。

    返回
    ----
    Solution —— 形状与单位见 src/common/solution.py
    """
```

`src/common/solution.py`：

```python
@dataclass
class Solution:
    t: np.ndarray   # (n_t,)     s
    r: np.ndarray   # (n_r,)     m
    T: np.ndarray   # (n_t, n_r) K
    C: np.ndarray   # (n_t, n_r) kg/kg (干基)
    meta: dict      # dt_internal, theta, 迭代次数, 残差, wall_time ...

    # 便利方法（已实现，直接用）
    def center_series(self) -> np.ndarray: ...      # 轴心 C(t)
    def surface_series(self) -> np.ndarray: ...     # 表面 C(t)
    def max_C_over_r(self) -> np.ndarray: ...       # 各时刻全场最大 C
    def first_time_below(self, target: float, *, strict: bool = True) -> float: ...
        # 问题 3/4 的终点判据。取 max_r（题目说"各处"），达不到时**抛错**，不静默返回
    def summary(self) -> str: ...
```

**`meta` 里必须记录**（用于论文的可复现性一节与问题排查）：
`dt_internal`、`theta`、`n_iterations`、`residual`、`wall_time_s`。
若内部步长与交付步长不同，**必须在 `docs/DECISIONS.md` 记录并给出步长无关性验证**。

**每个 `src/qN/` 内部建议结构**（不强制，但推荐）：
```
src/qN/
├── __init__.py
├── model.py     # 组装 PDE 右端项 / 系数矩阵（纯函数，好测）
├── bc.py        # 边界条件离散（单独文件，因为最容易出错）
├── solver.py    # 时间步进主循环
└── post.py      # 后处理：插值到交付网格、计算派生量
```

**`bc.py` 必须单独有测试。** 边界条件是数模竞赛最高频的错误来源（符号错、虚拟节点系数错、对称条件写错）。

---

## 9. `scripts/` 入口契约

```python
# scripts/run_q1.py
def main() -> int:
    spec = problem_spec.Q1
    sol = solver.solve(spec)
    io_excel.write_result("q1", build_sheets(sol, spec))
    io_excel.write_table_csv(...)
    return 0
```

**要求**：
- 每个脚本 `main()` 返回 int 退出码，0 为成功。Makefile 依赖退出码判断成败。
- 脚本**不许**有交互式输入、不许 `plt.show()`。必须在无头环境能跑通。
- 跑完打印一行摘要（节点数、步数、耗时、关键结果），便于在日志里追溯。

---

## 10. 变更记录

| 日期 | 变更 | 提出人 | PR |
|---|---|---|---|
| — | 初始契约 | `@impl` | — |
