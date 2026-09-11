# 当前数值证据

本轮模型版本为 `latent-v2`：四问均含潜热，采用气膜/供水互补边界，主方案60°C/20%RH，第二方案由附件1拟合渐近温度。

- `latent.json`：当前主模型网格加密、BDF/Radau交叉、温湿度与结构假设比较。场误差只针对报告中声明的采样，非严格全局误差界。
- `ambient_fit.json`：温度拟合候选、末1h留出、500次残差bootstrap及可识别性检查。
- `energy_audit.json`：变物性模型瞬时离散热量收支；不冒称总焓守恒。
- `accuracy-output-check.json`：运行新回读脚本后，为当前工作簿与未舍入求解缓存的全单元格核验（以SHA256判断版本）。

`accuracy.json`、`accuracy-q4.json`、`accuracy-reproduction.json`、`accuracy-methods.md`、`numerics.json` 是本轮以前**无潜热有效边界**的历史记录。保留用于追溯，不作为本轮模型或论文验证证据。不要运行旧accuracy缓存脚本来替代 `validate_latent.py`。
