"""FAO56饱和汽压及ASHRAE热质类比；SI输入，湿含量为kg水/kg干空气。

来源及适用限制：docs/model/references-research.md、docs/model/numerics.md。
"""

import numpy as np

from .units import assert_kelvin, k_to_c

STANDARD_PRESSURE_PA = 101325.0
DRY_AIR_CP = 1006.0
WATER_VAPOR_CP = 1860.0
LEWIS_NUMBER = 0.845
MOLECULAR_MASS_RATIO = 0.621945


def saturation_pressure(T):
    """FAO56式(11)，输出Pa。"""
    assert_kelvin(T, where="saturation_pressure")
    T_C = k_to_c(np.asarray(T, dtype=float))
    return 610.8 * np.exp(17.27 * T_C / (T_C + 237.3))


def humidity_ratio(T, relative_humidity, pressure=STANDARD_PRESSURE_PA):
    """相对湿度用0—1；输出气相湿含量Y，不是药材平衡含水率。"""
    phi = np.asarray(relative_humidity, dtype=float)
    if np.any((phi < 0) | (phi > 1)):
        raise ValueError("相对湿度必须在0—1范围")
    vapor = phi * saturation_pressure(T)
    if np.any(vapor >= pressure):
        raise ValueError("蒸汽分压必须小于总压")
    return MOLECULAR_MASS_RATIO * vapor / (pressure - vapor)


def vapor_pressure(Y, pressure=STANDARD_PRESSURE_PA):
    return pressure * np.asarray(Y) / (MOLECULAR_MASS_RATIO + np.asarray(Y))


def relative_humidity(T, Y, pressure=STANDARD_PRESSURE_PA):
    return vapor_pressure(Y, pressure) / saturation_pressure(T)


def gas_evaporation_capacity(T_s, Y_amb, h, lewis=LEWIS_NUMBER):
    """由Lewis类比得到气膜输水能力kg/(m²s)，保留冷凝负号。"""
    moist_air_cp = DRY_AIR_CP + WATER_VAPOR_CP * np.asarray(Y_amb)
    return h / moist_air_cp * lewis**(-2.0/3.0) * (humidity_ratio(T_s, 1.0) - Y_amb)
