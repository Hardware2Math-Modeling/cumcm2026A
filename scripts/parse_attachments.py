"""解析 problem/附件 的附件 1、2 -> data/raw 与 data/processed。

运行： make data

产出：
    data/raw/attachment1.csv        附件 1 的SI单位副本
    data/raw/attachment2.csv        附件 2 的SI单位副本
    data/processed/ambient.csv      烘房条件 T_inf(t), C_inf(t)   [SI: K, kg/kg, s]
    data/processed/radius.csv       药材半径 R(t)                 [SI: m, s]

本脚本只转换单位，不额外插值或外推。运行时边界由boundary.py负责，
四问潜热与两种后4h工况见当前docs/DECISIONS.md。
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
            "  附件1覆盖 %.1f h，附件2半径数据覆盖 %.1f h。" % (t1_max / 3600, t2_max / 3600),
            "  后续比较文献60°C和附件拟合温度两种恒温方案，RH均20%。",
            "  这是用户授权的工况设计，不是新增实测数据；见当前DECISIONS。",
        ]

    c0 = 2.55
    if a1["C_inf"].max() < c0 / 10:
        lines += [
            "",
            "  ⚠️ 量级警告：烘房水分浓度最大 %.5f，而药材初始水分浓度 %.2f，相差 %.0f 倍。"
            % (a1["C_inf"].max(), c0, c0 / a1["C_inf"].max()),
            "      当前模型将空气列解释为kg水/kg干空气，药材为kg水/kg干物质。",
            "      两者不直接相减，气膜/供水闭合见docs/model/environment.md。",
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
    print("  本脚本仅转换单位；线性插值和后续两种工况由Boundary负责。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
