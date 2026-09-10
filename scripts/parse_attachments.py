"""解析 problem/附件 的附件 1、2 -> data/raw 与 data/processed。

运行： make data

产出：
    data/raw/attachment1.csv        附件 1 逐字副本
    data/raw/attachment2.csv        附件 2 逐字副本
    data/processed/ambient.csv      烘房条件 T_inf(t), C_inf(t)   [SI: K, kg/kg, s]
    data/processed/radius.csv       药材半径 R(t)                 [SI: m, s]

⚠️ 插值/外推方式由 docs/DECISIONS.md D-004（插值）与 D-009（4h 之后怎么办）决定。
   两个决策都还没定稿，因此**本脚本目前只做原样搬运，不做任何插值或外推**。
   决策定稿后在此处补齐，并在 DECISIONS.md 里引用本文件。
"""

from __future__ import annotations

import sys

import pandas as pd

from _bootstrap import setup

setup()

from common import io_excel, paths, units  # noqa: E402


def parse_attachment1() -> pd.DataFrame:
    """烘房环境条件。单位转为 SI（s, K, kg/kg）。"""
    raw = io_excel.read_attachment(1)
    out = pd.DataFrame(
        {
            "t_s": raw["时间"].to_numpy(dtype=float),
            "T_inf_K": units.c_to_k(raw["温度"].to_numpy(dtype=float)),
            "C_inf": raw["水分浓度"].to_numpy(dtype=float),
        }
    )
    return out


def parse_attachment2() -> pd.DataFrame:
    """药材半径随时间变化。单位转为 SI（s, m）。"""
    raw = io_excel.read_attachment(2)
    out = pd.DataFrame(
        {
            "t_s": raw["时间"].to_numpy(dtype=float),
            "R_m": raw["半径"].to_numpy(dtype=float) * units.CM_TO_M,
        }
    )
    return out


def coverage_report(a1: pd.DataFrame, a2: pd.DataFrame) -> str:
    """打印覆盖范围，并**显式警告缺口**——这是最容易在后期才发现的坑。"""
    t1_max = float(a1["t_s"].max())
    t2_max = float(a2["t_s"].max())
    lines = [
        "",
        "== 数据覆盖范围 ==",
        f"  附件1 烘房条件: 0 ~ {t1_max:.0f} s ({t1_max / 3600:.2f} h), "
        f"步长 {float(a1['t_s'].diff().dropna().iloc[0]):.0f} s, {len(a1)} 点",
        f"      T_inf: {a1['T_inf_K'].min() - 273.15:.3f} ~ {a1['T_inf_K'].max() - 273.15:.3f} °C",
        f"      C_inf: {a1['C_inf'].min():.5f} ~ {a1['C_inf'].max():.5f} kg/kg",
        f"  附件2 半径:     0 ~ {t2_max:.0f} s ({t2_max / 3600:.2f} h), "
        f"步长 {float(a2['t_s'].diff().dropna().iloc[0]):.0f} s, {len(a2)} 点",
        f"      R: {a2['R_m'].min() * 100:.4f} ~ {a2['R_m'].max() * 100:.4f} cm",
    ]

    if t2_max > t1_max * 4:
        lines += [
            "",
            "  ⚠️⚠️ 缺口警告：附件1 只覆盖 %.1f h，而烘干过程持续 %.1f h。" % (t1_max / 3600, t2_max / 3600),
            "      4 h 之后的烘房条件题目未给出。这**不是**可以自行假设的小事：",
            "      → 见 docs/DECISIONS.md D-009，定稿前不要实现外推逻辑。",
        ]

    c0 = 2.55
    if a1["C_inf"].max() < c0 / 10:
        lines += [
            "",
            "  ⚠️ 量级警告：烘房水分浓度最大 %.5f，而药材初始水分浓度 %.2f，相差 %.0f 倍。"
            % (a1["C_inf"].max(), c0, c0 / a1["C_inf"].max()),
            "      两者是否同一基准（干基/湿基/绝对湿度）题目未说明。",
            "      → 见 docs/DECISIONS.md D-011，定稿前不要写边界条件。",
        ]

    return "\n".join(lines)


def main() -> int:
    paths.ensure_output_dirs()

    a1 = parse_attachment1()
    a2 = parse_attachment2()

    p1 = paths.DATA_RAW / "attachment1.csv"
    p2 = paths.DATA_RAW / "attachment2.csv"
    a1.to_csv(p1, index=False)
    a2.to_csv(p2, index=False)

    pa = paths.DATA_PROCESSED / "ambient.csv"
    pr = paths.DATA_PROCESSED / "radius.csv"
    a1.to_csv(pa, index=False)
    a2.to_csv(pr, index=False)

    for p in (p1, p2, pa, pr):
        print(f"  写出 {paths.rel(p)}  ({p.stat().st_size} B)")
    print(coverage_report(a1, a2))
    print()
    print("  ⚠️ 当前未做任何插值/外推（D-004、D-009 未定稿）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
