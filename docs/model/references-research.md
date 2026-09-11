# 温湿度、蒸发潜热与气相传质：核验文献记录

核验日期：2026-09-11。任务委托：由 `@model` 委托研究角色只编辑本文件；不使用任何 skill，不修改 `problem/`，不执行 Git 或发布操作。期刊元数据通过 Crossref/OpenAlex 核验；可公开访问的 FAO、ASHRAE 与 PsychroLib 正文直接核验。下列“文献直接支持”与“本文自主假设”严格区分。

## 1. 可立即使用的证据与边界

- 四问均在表面能量平衡中扣除实际水质量通量乘汽化潜热。FAO 56 附录 3 式 (3-1) 直接支持随温度变化的纯水潜热线性关系；取表面水相温度属于本文相变位置假设。
- 恒温阶段 **60 °C、20% RH** 有山药热风干燥实验直接先例 [R1]；**55 °C、20% RH** 有整根西洋参干燥的晚期工况先例 [R2]。两者均可作为自主设计的可复现工况，而不是题中未指明药材的已证最优工况。
- 相对湿度是气相水蒸气分压与饱和分压之比；空气湿含量是水质量/干空气质量。两者均不等于药材水质量/干物质质量。**不能把空气湿含量直接称为固相平衡含水率。**
- ASHRAE 的 Lewis 关系支持通过给定换热系数估计气膜传质能力，既可用水蒸气质量浓度差，也可用空气湿含量差。题给 `h_m` 原本用于固相有效边界，不能仅因其单位也是 m/s 就直接当作气膜传质系数。
- 没有题中具体药材的解吸等温线、水活度关系或标定实验，不能确认其平衡干基含水率。饱和自由水表面、气膜容量与固相供水能力串联/互补的闭合属于**本文明确列出的建模假设**；不能说它由下列文献直接验证。

## 2. [R1] 山药：60 °C、20% RH 有直接实验先例

**引用**：Ju, Hao-Yu; Zhang, Qian; Mujumdar, A. S.; Fang, Xiao-Ming; Xiao, Hong-Wei; Gao, Zhen-Jiang. Hot-air Drying Kinetics of Yam Slices under Step Change in Relative Humidity. *International Journal of Food Engineering*, 2016, **12**(8): 783–792.

- DOI：<https://doi.org/10.1515/ijfe-2015-0340>
- Crossref 核验：<https://api.crossref.org/works/10.1515/ijfe-2015-0340>
- OpenAlex 独立核验：<https://api.openalex.org/works/https://doi.org/10.1515/ijfe-2015-0340>
- 证据位置：出版商存入 Crossref 的原摘要；OpenAlex 摘要一致。出版商正文页本次未返回可读全文，不宣称核验全文。
- 原文短摘："with 60 °C and 1.5 m/s as its constant drying temperature and air velocity"；"Compared to drying at constant 20 % RH"。
- 摘要还直接说明：首 15 min 保持 40% RH、之后降至 20% RH，比全程恒 20% RH 的对照更快；高早期湿度可减少表层结壳。

**可支持**：山药根茎类材料在 60 °C、20% RH 下热风干燥是已公开的实验工况；将其选为本题恒温阶段输入有文献依据。

**不可支持**：该工况对任何药材都最优；本文 25 cm 长、4 cm 直径整圆柱与文献山药薄片干燥时间相同；文献扩散系数可覆盖题给附录公式。风速 1.5 m/s 也不应替代题给换热、传质系数，除非另建一致换算模型。

## 3. [R2] 整根西洋参：55 °C 的质量折中证据

**引用**：Ju, Hao-Yu; Zhao, Shi-Hao; Mujumdar, Arun S.; Zhao, Hai-Yan; Duan, Xu; Zheng, Zhi-An; Gao, Zhen-Jiang; Xiao, Hong-Wei. Step-down relative humidity convective air drying strategy to enhance drying kinetics, efficiency, and quality of American ginseng root (*Panax quinquefolium*). *Drying Technology*, **2020**, **38**(7): 903–916. Online publication: 2019-04-03.

- DOI：<https://doi.org/10.1080/07373937.2019.1597373>
- Crossref 元数据：<https://api.crossref.org/works/10.1080/07373937.2019.1597373>
- 摘要核验：OpenAlex 对该 DOI 的记录。出版年区分印刷卷期 2020 与在线 2019，不能因 DOI 含 2019 就把最终卷期年份写错。
- 原文短摘："temperature (45, 50, 55, and 60 °C), RH (20, 30, and 40%)"；"a gel layer was formed on the sample surface when dried at temperature of 60 °C"。
- 摘要结论：在研究评价指标和实验范围内，55 °C、40% RH 保持 5 h 再降至 20% RH 是作者提出的最佳整根西洋参干燥方案。总人参皂苷含量随干燥温度升高及 RH 降低而下降。

**可支持**：本题工况敏感性可选 55–60 °C、20–40% RH 的有文献覆盖范围；若自主选全程恒 55 °C、20% RH，应说明取自文献温度与晚期低湿设定。

**不可支持**：全程恒 55 °C、20% RH 就是该论文报告的最佳方案；温度越高、湿度越低越适合药材质量；未知药材已有质量损失校准。

## 4. [R3] FAO 56：潜热和饱和蒸汽压

**引用**：Allen, Richard G.; Pereira, Luis S.; Raes, Dirk; Smith, Martin. *Crop evapotranspiration—Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56. Rome: Food and Agriculture Organization of the United Nations, 1998. ISBN 92-5-104219-5.

- 标题、作者、年份、ISBN 官方核验：<https://www.fao.org/4/x0490e/x0490e00.htm>
- 附录 3 官方正文：<https://www.fao.org/4/x0490e/x0490e0k.htm>
- 第 3 章官方正文：<https://www.fao.org/4/x0490e/x0490e07.htm>

**直接公式证据**：附录 3 首项、式 (3-1) 显示

\[
\lambda=2.501-(2.361\times10^{-3})\,T_{\mathrm{C}},
\qquad [\lambda]=\mathrm{MJ\,kg^{-1}},\quad [T_{\mathrm{C}}]={}^{\circ}\mathrm{C}.
\]

因此代码内部输入开尔文时换算为

\[
\Delta H_{vap}(T_s)=2.501\times10^6-2361(T_s-273.15)\quad\mathrm{J\,kg^{-1}}.
\]

原文将温度写作空气温度；用于药材表面液态水相变时，以 `T_s` 评价纯水潜热是本文的局部相变近似，不是 FAO 给出药材干燥模型。应把这个换算放入 `src/common/correlations.py`，沿用项目内部 K 的约定。

第 3 章式 (10) 给相对湿度的分压比定义；式 (11) 和例 3 直接给 Tetens 型饱和蒸汽压计算：

\[
p_{sat}(T)=610.8\exp\left[\frac{17.27(T-273.15)}{T-273.15+237.3}\right]\quad\mathrm{Pa}.
\]

这是经验近似。若采用覆盖范围更宽的 ASHRAE 饱和蒸汽压式，可依据 [R5] 的已核验实现，不能把 Tetens 的简化式与 ASHRAE 系数混写。

**适用限制**：FAO 式为纯水汽化潜热，未含药材结合水的额外解吸焓。其农业蒸散方法不能整体移植为药材的热质 PDE；这里仅引用明确列出的水物性关系。

## 5. [R4] ASHRAE：空气湿含量、Lewis 气膜传质

**引用**：ASHRAE. *2021 ASHRAE Handbook—Fundamentals, SI Edition*. Atlanta, GA: ASHRAE, 2021. Chapter 1, Psychrometrics; Chapter 6, Mass Transfer.

- 第 1 章公开正文：<https://handbook.ashrae.org/Handbooks/F21/SI/F21_Ch01/F21_Ch01_si.aspx>
- 第 6 章公开正文：<https://handbook.ashrae.org/Handbooks/F21/SI/F21_Ch06/F21_Ch06_si.aspx>
- 第 6 章式 (39) 官方图：<https://handbook.ashrae.org/Handbooks/F21/SI/F21_Ch06/equations/F6_eq039.jpg>
- 第 6 章式 (45a) 官方图：<https://handbook.ashrae.org/Handbooks/F21/SI/F21_Ch06/equations/F6_eq045a.jpg>
- 第 6 章式 (46) 官方图：<https://handbook.ashrae.org/Handbooks/F21/SI/F21_Ch06/equations/F6_eq046.jpg>

本次已直接读取正文，并视觉核验以上三张公式图。

**证据位置与内容**：

1. 第 6 章 `Lewis Relation` 节，式 (39) 为
   \[
   \frac{h}{h_M\rho c_p}=P_{Am}\left(\frac{\alpha}{D_v}\right)^{2/3}.
   \]
   `P_Am` 是气相扩散关系中的校正量。正文说明低扩散通量时近似为 1，并给空气与水蒸气 `Le=alpha/D_v=0.845`、`Le^(2/3)=0.894`。在该近似下得到气膜速度系数 `k_g=h/(rho_air*c_p_air)*Le^(-2/3)`。
2. 式 (40) 的 Lewis 近似将热、质扩散作用视为近似相等。正文短摘："The ratio of the heat transfer coefficient to the mass transfer coefficient equals the specific heat per unit volume"。
3. 同章 `Enthalpy Potential` 节式 (41)–(46) 改用空气湿含量 `W` 作驱动力，定义 `K_M` 单位为 kg/(s·m²)，并给 `h/K_M≈c_pm`。因此自由水表面容量可写为
   \[
   j_g=\frac{h}{c_{pm}}[Y_{sat}(T_s)-Y_\infty],
   \]
   其中 `c_pm` 用 J/(kg干空气·K)、`h` 用 W/(m²·K) 后，`j_g` 才是 kg水/(m²·s)。是否使用正部截断处理只蒸发模式、是否允许负值表示凝结，属于模型选择，不能隐含。
4. 该章例题给干空气 `c_p=1.006 kJ/(kg·K)=1006 J/(kg·K)`；第 1 章表 2、标准大气压 101.325 kPa 也提供空气热力性质。湿比热近似的数值系数见 [R5]。

**适用限制**：同章直接提醒热质传递 `j` 因子类比适用于低质量传递率，高蒸发吹出效应会改变边界层。湿含量版本使用稀混合物、干空气分密度变化较小等近似。采用 `Le=1` 简化和采用 `Le=0.845` 修正是两种不同精度选择，应在模型规格和代码中统一。

**不能据此声称**：由传热系数估得的气膜阻力与题给固相 `h_m` 是同一物理系数；两种不同基准的浓度可直接相减；串联供水/气膜公式已经针对本题具体药材实验标定。

## 6. [R5] PsychroLib：可复现的湿空气换算与常数

**引用**：Meyer, D.; Thevenard, D. PsychroLib: a library of psychrometric functions to calculate thermodynamic properties of air. *Journal of Open Source Software*, 2019, **4**(33): 1137.

- DOI：<https://doi.org/10.21105/joss.01137>
- 元数据：<https://api.crossref.org/works/10.21105/joss.01137>
- 官方 API：<https://psychrometrics.github.io/psychrolib/api_docs.html>
- 官方可读实现：<https://psychrometrics.github.io/psychrolib/_modules/psychrolib.html>

本次直接核验 `GetHumRatioFromVapPres`、`GetMoistAirEnthalpy`、`GetSatVapPres`。源码逐函数指明 ASHRAE Handbook—Fundamentals (2017) 第 1 章对应式号。

**湿含量**，其源码对应 ASHRAE 2017 第 1 章式 (20)：

\[
Y_\infty=0.621945\frac{p_{v,\infty}}{p-p_{v,\infty}},\qquad
p_{v,\infty}=\varphi_\infty p_{sat}(T_\infty).
\]

`Y` 单位为 kg水/kg干空气；`varphi` 为 0–1 分数；`p` 与 `p_v` 同用 Pa。取标准大气压 `p=101325 Pa` 是自主设定的工作压力，ASHRAE 第 1 章标准表采用该压力，并非题目已测压力。

**湿空气焓**，源码对应 ASHRAE 2017 第 1 章式 (30)：

\[
H=\{1.006T_{\mathrm C}+Y[2501+1.86T_{\mathrm C}]\}\times1000
\quad \mathrm{J/(kg\ dry\ air)}.
\]

在固定 `Y` 下对温度求偏导，**推导得到**

\[
c_{pm}=1006+1860Y\quad\mathrm{J/(kg\ dry\ air\,K)}.
\]

该 `c_pm` 与以每 kg 湿空气为分母的 `c_p` 不可混用。它可与 [R4] 的湿含量驱动力 Lewis 关系直接配套。

**饱和蒸汽压**，源码对应 ASHRAE 2017 第 1 章式 (5)、(6)：液态水分支、开尔文 `T` 为

\[
\ln p_{sat}=-5800.2206/T+1.3914993-0.048640239T
 +4.1764768\times10^{-5}T^2-1.4452093\times10^{-8}T^3
 +6.5459673\ln T,
\]

`p_sat` 单位 Pa。源码区分冰/水分支并覆盖 −100 到 200 °C 的输入检查；本题正常液态水温度无需冰分支。引用源码与论文是关系可复现的证据，不要求新增或安装该依赖；若在项目内实现公式，仍通过 `correlations.py` 统一管理。

## 7. [R6] 解吸等温线存在，但未知药材参数不能由 RH 唯一确定

**引用**：Njie, D. N. Desorption Isotherms of Water in Trifoliate Yam (*Dioscorea dumetorum* Pax.). *Drying Technology*, 1999, **17**(6): 1161–1171.

- DOI：<https://doi.org/10.1080/07373939908917601>
- 核验：<https://api.openalex.org/works/https://doi.org/10.1080/07373939908917601>
- 证据层级：元数据与摘要；本次没有取得闭源全文或参数表，**不引用其未读 GAB 参数**。
- 摘要短摘："temperatures of 20°, 34°, 46° and 62°C, in the relative humidity range from 11 to 86%"；"The GAB model gave the best fit"。
- 摘要直接报告的净等量吸附热：干基含水率 0.05 kg/kg 时 1412 kJ/kg，0.20 kg/kg 时 325 kJ/kg。这是该山药物种的文献值，不是题中药材物性，也不写入正式数值求解器。

另查得姜片开放全文：Alakali, Joseph; Irtwange, Simon Verlumun; Satimehin, Adesola. *Moisture adsorption characteristics of ginger slices*. 2009. DOI <https://doi.org/10.1590/S0101-20612009000100024>；全文 <https://www.scielo.br/j/cta/a/4x3rCqzYsbPN8TSzb4T6PSn/?lang=en>。其试验为干姜吸附，20–50 °C、RH 约 37.1–93.9%，预处理对含湿量有显著影响；**不能将其参数无说明地外推至 60 °C、20% RH 的未知药材解吸过程**。

**必要关系**：要建立固相平衡边界，应有对应物种、预处理和温度的解吸关系 `C_e=f(T_s,a_w)`。空气 RH 需先转水汽分压；若表面与环境温度不同，固相平衡所需水活度应由表面温度下的分压比处理，不能把环境 RH 不加区别地代入表面等温线。

**本任务可实现且不伪造材料参数的建议**：保留题给扩散与固相有效供水参数，用 [R4]–[R5] 的气膜蒸发能力限制质量通量，并让能量和质量方程使用完全相同的 `j`。明确把自由水饱和表面、固相供水—气膜组合关系、忽略结合水额外解吸热列为模型假设；报告数值收敛、质量/能量收支及工况敏感性，不把数值精确性当作物种实测准确性。对低含水率的长期平衡及结合水阶段，模型适用性仍需物种解吸实验补充。

## 8. 给论文与代码角色的交接

- 论文应至少引用 [R1]/[R2] 中与最终工况对应的文献、[R3] 潜热、[R4] 气膜传质、[R5] 湿空气换算；[R6] 可用于解释解吸参数缺失与局限。
- 最终选择 60 °C 或 55 °C 由 `@model` 在决策记录中冻结；本记录不冒充最终工况规格。
- 公式新增符号由 `@model` 同步 `docs/NOTATION.md`，本角色不越权编辑。
- 代码必须区分 `C`（水/干药材）、`Y`（水/干空气）、`RH`（分压比），确保表面潜热项使用 kg水/(m²·s) 的实际通量，而不是未乘质量基准的“m/s × kg/kg”。
- 文献只支持各物性/传质关系及相近材料实验工况；本文的完整药材模型、阻力组合和具体数值结果仍须由题目输入、明确假设与实际求解输出建立。
