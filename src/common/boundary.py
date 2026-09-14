"""附件驱动边界；输入读取时统一转SI，4小时之外的外推假设见 D-009。"""

from dataclasses import dataclass

import numpy as np

from .io_excel import read_attachment
from .units import c_to_k, cm_to_m
from .psychrometrics import humidity_ratio


@dataclass
class Boundary:
    ambient_t: np.ndarray
    T_amb: np.ndarray
    C_amb: np.ndarray
    radius_t: np.ndarray
    R: np.ndarray
    late_T_shift: float = 0.0
    late_C_shift: float = 0.0
    late_T: float | None = None
    late_Y: float | None = None
    description: str = "attachment 1 humidity interpreted as kg water/kg dry air"

    @classmethod
    def for_problem(cls, problem, temperature_c=60.0, relative_humidity=0.20):
        if problem == "q1":
            return cls.from_attachments()
        T = float(c_to_k(temperature_c))
        return cls.from_attachments(late_T=T, late_Y=float(humidity_ratio(T, relative_humidity)),
                                   description=f"attachment 1 through 4 h; then {temperature_c:g} degC, {100*relative_humidity:g}% RH at 101325 Pa")

    @classmethod
    def from_attachments(cls, **kwargs):
        a = read_attachment(1)
        b = read_attachment(2)
        return cls(a.iloc[:, 0].to_numpy(float), c_to_k(a.iloc[:, 1].to_numpy(float)),
                   a.iloc[:, 2].to_numpy(float, copy=True), b.iloc[:, 0].to_numpy(float),
                   cm_to_m(b.iloc[:, 1].to_numpy(float)), **kwargs)

    def ambient(self, t):
        late = np.asarray(t) > self.ambient_t[-1]
        T = np.interp(t, self.ambient_t, self.T_amb)
        Y = np.interp(t, self.ambient_t, self.C_amb)
        if self.late_T is not None:
            T = np.where(late, self.late_T, T)
        if self.late_Y is not None:
            Y = np.where(late, self.late_Y, Y)
        return T + late * self.late_T_shift, Y + late * self.late_C_shift

    def radius(self, t):
        if np.any(np.asarray(t) > self.radius_t[-1] + 1e-7):
            raise ValueError("超过附件2的72小时范围；不得自动外推收缩半径")
        return np.interp(t, self.radius_t, self.R)
