"""正式数值精度设置；物理模型与物性不在此处定义。"""


def production_options(problem):
    if problem in {"q1", "q2", "q3", "q4"}:
        return dict(n_internal=2561, rtol=2e-11, atol=2e-12,
                    max_step=60.0, align_boundary_knots=True)
    raise ValueError(f"未知题号: {problem}")
