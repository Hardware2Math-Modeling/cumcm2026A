"""论文插图。

规则（AGENTS.md §2 / docs/INTERFACES.md §7）：
    - 输出一律 **PDF（矢量）**，不要 PNG。
    - 图片直接写到 paper/figs/，论文用 \\includegraphics{figs/xxx.pdf} 引用。
      **不要再往论文目录复制图片。**
    - 轴标签必须含单位；图里的单位是 **cm 和 °C**（展示单位），
      因此本模块负责从 SI 转换，调用方传进来的一律还是 SI。
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from . import paths


def _ensure_cache_dir(env_var: str, default_dir: Path, repo_dir: Path) -> None:
    """给 matplotlib / fontconfig 找一个可写的缓存目录。

    默认位置在受限环境（容器、CI、只读 HOME）里常常不可写，matplotlib 会退回
    临时目录并**每次重新扫描字体**——中文环境下这个开销很明显，fontconfig 还会
    直接报 "No writable cache directories"。

    策略：先试默认位置；**不可写时**才回退到仓库内（outputs/ 已被 gitignore）。
    不无条件覆盖环境变量，以免擅自搬动别人机器上的缓存。

    ⚠️ 必须在 `import matplotlib` **之前**调用 —— matplotlib 在自身导入期间就会
       解析配置目录，之后再设环境变量已经太晚了（实测确认）。
    """
    if os.environ.get(env_var):
        return
    probe = default_dir / ".write_test"
    try:
        default_dir.mkdir(parents=True, exist_ok=True)
        probe.touch()
        probe.unlink()
        return  # 默认位置可写，不动它
    except OSError:
        pass

    fallback = repo_dir / "mplconfig"
    fallback.mkdir(parents=True, exist_ok=True)
    os.environ[env_var] = str(fallback)


# 必须在 import matplotlib 之前设置
_ensure_cache_dir("MPLCONFIGDIR", Path.home() / ".matplotlib", paths.OUTPUTS_CACHE)
# fontconfig 用的是 XDG_CACHE_HOME（Linux/容器里常见报错源）
_ensure_cache_dir("XDG_CACHE_HOME", Path.home() / ".cache", paths.OUTPUTS_CACHE)

import matplotlib  # noqa: E402

# 必须在 import pyplot 之前设置，否则在无头环境（CI / 服务器）会失败
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np

from . import units  # noqa: E402
from .solution import Solution  # noqa: E402

#: 中文字体候选。macOS 优先，回退到常见 Linux/Windows 字体，避免"豆腐块"。
_CJK_FONTS = (
    "Songti SC",
    "Heiti SC",
    "PingFang SC",
    "STSong",
    "SimSun",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Noto Serif CJK SC",
    "WenQuanYi Zen Hei",
    "DejaVu Sans",
)

_FIGSIZE = (6.0, 4.0)
_DPI = 300


def apply_style() -> None:
    """全局设置。每个脚本入口调用一次即可。"""
    plt.rcParams.update(
        {
            "font.sans-serif": list(_CJK_FONTS),
            "font.family": "sans-serif",
            "axes.unicode_minus": False,  # 负号用 ASCII，避免中文字体缺字形
            "font.size": 9,
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "figure.figsize": _FIGSIZE,
            "figure.dpi": 120,
            "savefig.dpi": _DPI,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "grid.linestyle": "--",
            "lines.linewidth": 1.4,
            "pdf.fonttype": 42,  # 嵌入 TrueType，投稿/打印不出问题
            "ps.fonttype": 42,
        }
    )


def _out_path(out: str | Path) -> Path:
    """把相对名转成 paper/figs/<name>.pdf。"""
    p = Path(out)
    if p.suffix != ".pdf":
        p = p.with_suffix(".pdf")
    if p.parent == Path("."):
        p = paths.FIGURES_DIR / p.name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _cjk_warning() -> str | None:
    """若没有任何中文字体可用，返回警告文本（论文里出现豆腐块是致命的）。"""
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    if not available & set(_CJK_FONTS):
        return (
            "⚠️ 未找到任何候选中文字体，图中中文会显示为方块。\n"
            f"   候选：{_CJK_FONTS}\n"
            "   请安装中文字体（macOS 自带 Songti SC；Linux: fonts-noto-cjk）。"
        )
    return None


# --- 图 1：某一时刻的径向分布 -------------------------------------------------


def plot_profiles(
    sol: Solution,
    *,
    field: str,
    times: Sequence[float],
    out: str | Path,
    title: str | None = None,
    r_scale: float | None = None,
) -> Path:
    """画若干时刻的径向分布。

    Parameters
    ----------
    field : "T" 或 "C"
    times : 要画的时刻，单位 **s**（内部会找最近的网格点）
    r_scale : 若给定，用 r/r_scale 作横坐标（问题 4 的无量纲坐标 ξ 用）
    """
    field = field.upper()
    if field not in {"T", "C"}:
        raise ValueError(f"field 只能是 'T' 或 'C'，收到 {field!r}")

    label = "温度" if field == "T" else "水分浓度"
    ylabel = "温度 / °C" if field == "T" else "水分浓度 / (kg/kg, 干基)"

    fig, ax = plt.subplots()
    for t_req in times:
        i = int(np.argmin(np.abs(sol.t - t_req)))
        if field == "T":
            y = units.k_to_c(sol.T[i])
            t_show = f"{sol.t[i] / 60:.0f} min" if sol.t[i] < 3600 else f"{sol.t[i] / 3600:.1f} h"
        else:
            y = sol.C[i]
            t_show = f"{sol.t[i] / 3600:.2f} h"

        if r_scale is None:
            x = units.m_to_cm(sol.r)
            xlabel = "到药材中心的距离 / cm"
        else:
            x = sol.r / r_scale
            xlabel = r"无量纲径向坐标 $\xi = r/R(t)$"

        ax.plot(x, y, marker="o", markersize=2.5, label=f"t = {t_show}")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or f"{label}的径向分布")
    ax.legend()
    fig.savefig(_out_path(out))
    plt.close(fig)
    return _out_path(out)


# --- 图 2：若干位置的时间历程 -------------------------------------------------


def plot_history(
    sol: Solution,
    *,
    locations_cm: Sequence[float],
    field: str = "C",
    out: str | Path,
    title: str | None = None,
) -> Path:
    """画若干径向位置的时间历程。locations_cm 单位 **cm**（展示单位）。"""
    field = field.upper()
    label = "温度" if field == "T" else "水分浓度"
    ylabel = "温度 / °C" if field == "T" else "水分浓度 / (kg/kg, 干基)"

    t_h = units.s_to_h(sol.t)
    fig, ax = plt.subplots()
    for r_cm in locations_cm:
        i = int(np.argmin(np.abs(units.m_to_cm(sol.r) - r_cm)))
        y = units.k_to_c(sol.T[:, i]) if field == "T" else sol.C[:, i]
        ax.plot(t_h, y, label=f"r = {units.m_to_cm(sol.r[i]):.1f} cm")

    ax.set_xlabel("时间 / h")
    ax.set_ylabel(ylabel)
    ax.set_title(title or f"{label}的时间历程")
    ax.legend()
    fig.savefig(_out_path(out))
    plt.close(fig)
    return _out_path(out)


# --- 图 3：网格收敛性（log-log）---------------------------------------------


def plot_grid_convergence(
    errors: Mapping[float, float],
    *,
    out: str | Path,
    expected_order: float | None = None,
    title: str = "网格收敛性验证",
) -> Path:
    """画误差随步长的变化（双对数），用于论文的模型验证一节。

    Parameters
    ----------
    errors : {步长 h: 误差 E(h)}
    expected_order : 若给定，画一条斜率参考线，便于目视判断实测阶数
    """
    if len(errors) < 2:
        raise ValueError("至少需要两个步长点才能画收敛曲线。")

    h = np.array(sorted(errors), dtype=float)
    e = np.array([errors[k] for k in h], dtype=float)
    if np.any(e <= 0):
        raise ValueError("误差必须为正，否则无法在双对数图上表示。")

    # 实测收敛阶：相邻点斜率的中位数
    slopes = np.diff(np.log(e)) / np.diff(np.log(h))
    order_est = float(np.median(slopes))

    fig, ax = plt.subplots()
    ax.loglog(h, e, "o-", label=f"实测（阶数 ≈ {order_est:.2f}）")
    if expected_order is not None:
        ref = e[0] * (h / h[0]) ** expected_order
        ax.loglog(h, ref, "k--", alpha=0.6, label=f"参考斜率 {expected_order}")

    ax.set_xlabel("步长 h")
    ax.set_ylabel("误差 E(h)")
    ax.set_title(title)
    ax.legend()
    fig.savefig(_out_path(out))
    plt.close(fig)
    return _out_path(out)


def check_fonts(verbose: bool = True) -> bool:
    """检查中文字体。返回 True 表示可以画中文图。"""
    msg = _cjk_warning()
    if verbose:
        print(msg if msg else "✓ 中文字体可用")
    return msg is None


# 便利常量：供脚本引用，避免拼字符串
FIGS = paths.FIGURES_DIR
if os.environ.get("MPLBACKEND") is None:
    apply_style()
