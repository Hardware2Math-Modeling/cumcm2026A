"""附件驱动边界；输入读取时统一转SI，外推假设见 D-013。"""

from dataclasses import dataclass

import numpy as np

from .io_excel import read_attachment
from .units import c_to_k, cm_to_m


@dataclass
class Boundary:
    ambient_t: np.ndarray
    T_amb: np.ndarray
    C_amb: np.ndarray
    radius_t: np.ndarray
    R: np.ndarray
    late_T_shift: float = 0.0
    late_C_shift: float = 0.0

    @classmethod
    def from_attachments(cls, **kwargs):
        a = read_attachment(1)
        b = read_attachment(2)
        return cls(a.iloc[:, 0].to_numpy(float), c_to_k(a.iloc[:, 1].to_numpy(float)),
                   a.iloc[:, 2].to_numpy(float, copy=True), b.iloc[:, 0].to_numpy(float),
                   cm_to_m(b.iloc[:, 1].to_numpy(float)), **kwargs)

    def ambient(self, t):
        late = np.asarray(t) > self.ambient_t[-1]
        return (np.interp(t, self.ambient_t, self.T_amb) + late * self.late_T_shift,
                np.interp(t, self.ambient_t, self.C_amb) + late * self.late_C_shift)

    def radius(self, t):
        if np.any(np.asarray(t) > self.radius_t[-1] + 1e-7):
            raise ValueError("超过附件2的72小时范围；不得自动外推收缩半径")
        return np.interp(t, self.radius_t, self.R)
