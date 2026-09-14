# 环境设计、气固湿度基准与蒸发闭合

Owner：`@model`。2026-09-11。文献核验清单见 references-research.md。此文件记录可直接实现的最终规格；不同材料文献只能支持参考工况，不能证明未知药材的实验最优性。

## 1. 两种 kg/kg 不可混用

药材 $C=m_w/m_d$ 的分母是干药材；空气 $Y_\infty=m_v/m_a$ 的分母是干空气。附件1只写烘房“水分浓度 kg/kg”，本模型将其解释为空气干基湿含量Y，符合湿空气工程常用定义，但这是题面缺少基准说明后的建模解释。旧 $C_s-C_\infty$ 跨两种基准相减的闭合不再使用。

设相对湿度 $\phi$，总压 $p$，水蒸气分压 $p_v$，饱和蒸汽压 $e_s$。使用

$$e_s(T)=610.8\exp\left[\frac{17.27(T-273.15)}{T-273.15+237.3}\right]\quad\mathrm{Pa},$$
$$p_v=\phi e_s(T),\qquad
Y=\frac{\varepsilon p_v}{p-p_v},\qquad
p_v=\frac{pY}{\varepsilon+Y},\qquad
\varepsilon=0.621945.$$

饱和压来源：FAO56式(11)，<https://www.fao.org/4/x0490e/x0490e07.htm>。原式输出kPa，此处转Pa。湿含量关系参见ASHRAE Fundamentals及PsychroLib `GetHumRatioFromVapPres`（ASHRAE2017 Ch1 Eq20）：<https://psychrometrics.github.io/psychrolib/_modules/psychrolib.html>。正式实现与该来源统一使用分子量比0.621945。

压力取标准大气压 $p=101325\,\mathrm{Pa}$，是自主设计的标准工况，不是题给实测海拔压力。公式运行域为本文常温热风干燥范围，要求蒸汽分压小于总压；不得将公式无检查用于沸点附近或冰相。

## 2. 正式温湿方案

问题一0—1800s完全使用附件1。问题二至四前4h使用附件1逐点线性插值温度与Y，4h之后取

$$T_\infty=333.15\,\mathrm K\ (60^\circ\mathrm C),\qquad \phi_\infty=0.20,$$
$$Y_\infty=\frac{0.621945\times0.20 e_s(333.15)}{101325-0.20e_s(333.15)}.$$

药材状态在4h连续，环境设定允许阶跃并在该时刻重启积分；不另造未实测过渡曲线。既不将附件温度擅自外推成“测量值”，也不把空气20%RH作为药材20%含水率。

工况依据：《Hot-air Drying Kinetics of Yam Slices under Step Change in Relative Humidity》，International Journal of Food Engineering，2016，DOI <https://doi.org/10.1515/ijfe-2015-0340>。摘要给出60°C、1.5m/s以及恒20%RH对照和分阶段湿度方案。本模型取其中恒温20%RH参考，不声称复现论文最佳阶段方案；风速未用于反推题给h，因题内已有h、hm。

补充根类参考：American ginseng整根研究 DOI <https://doi.org/10.1080/07373937.2019.1597373>，考察45/50/55/60°C与20/30/40%RH，报告60°C可能形成凝胶表层，推荐55°C及40%RH前5h后20%RH。其结论提醒药材种类依赖，故55°C可作为敏感性工况，不能宣布60°C对全部中药材品质最优。

## 3. 供水/气膜互补条件

题给 $h_m=8\times10^{-7}\,\mathrm{m/s}$ 很小，作为固相基准的有效传质系数使用，构造供水能力

$$j_s=\rho_d h_m C_s.$$

不把该系数直接当作气相蒸汽密度驱动的膜系数。气膜能力由热质类比估计

$$K_M=\frac{h}{c_{p,m}}\mathrm{Le}^{-2/3},\qquad
j_g=K_M\{Y_{sat}(T_s,p)-Y_\infty\},$$
$$Y_{sat}(T_s,p)=\frac{0.621945e_s(T_s)}{p-e_s(T_s)},\quad
c_{p,m}=1006+1860Y_\infty\ \mathrm{J/(kg_{dry\ air}\,K)},\quad\mathrm{Le}=0.845.$$

来源：ASHRAE Handbook—Fundamentals2021 SI Ch6，Lewis Relation Eq39/40与Enthalpy Potential节，<https://handbook.ashrae.org/Handbooks/F21/SI/F21_Ch06/F21_Ch06_si.aspx>。该章给空气—水蒸气Le=0.845及低传质率关系；1006J/(kgK)为干空气比热。正式实现使用湿空气比热 $c_{p,m}=1006+1860Y_\infty$。它由ASHRAE2017 Ch1 Eq30的湿空气焓对温度求偏导得到，PsychroLib源码逐项给出1006与1860。$\mathrm{Le}^{-2/3}$ 是从热质类比保留的近似修正，忽略低传质率下接近1的压力修正因子。

最终有符号通量

$$j_v=\min(j_s,j_g).$$

此式表示相变速率受内部供水能力和气膜输运能力共同限制，是机制层面的分支闭合。它不是将不收敛状态或温度裁剪为“合理值”。若 $j_g<0$ 则发生冷凝，保留负号；若 $j_s<j_g$，供水受限，可反算

$$Y_{int}=Y_\infty+j_v/K_M\le Y_{sat}(T_s).$$

当 $j_g\le j_s$ 时界面饱和。该条件使表面处于空气露点温度时 $j_g=0$，露点以下则凝结放热，避免旧无限蒸发需求在不足供热时仍强制低于露点。

## 4. 潜热与模型局限

$$\Delta H_{vap}(T_s)=2.501\times10^6-2361(T_s-273.15)\ \mathrm{J/kg},$$
$$-\rho_dD C_r=j_v,\qquad kT_r=h(T_\infty-T_s)-\Delta H_{vap}j_v.$$

FAO56附录3式(3-1)：<https://www.fao.org/4/x0490e/x0490e0k.htm>。两场使用同一通量，不再额外加体内潜热源，以免双重计数。

**明确未识别的材料信息**：未提供具体药材种类、解吸等温线或界面水活度，故未拟造GAB/Henderson参数。供水上限取理想干燥界面，没有描述非零平衡含水率或结合水额外解吸焓。Njie1999山药等温线研究 DOI <https://doi.org/10.1080/07373939908917601> 确认这些量具温度、含水率与材料依赖，但没有取得可核验的完整参数，不用于替代本题材料。

互补闭合的计算结果为该模型和设计工况下的条件预测；数值守恒和网格加密不能证明材料物理真实性。可改变hm、Le、温度、RH做敏感性；若用正平衡含水率修正供水能力，必须明确其为设计情景而非实测参数。Q4附件半径在新工况下的可迁移性也未由实验验证。


## 5. 附件1温度拟合的第二工况

依用户追加要求，保留60°C/20%RH主方案，同时建立第二种温度来源。用附件1的0—4h空气温度拟合带有限渐近平台的曲线，比较单指数、logistic及Weibull等候选；不使用药材干燥终点反过来调拟合参数。

候选固定初温logistic写为
$$T_{fit}(t)=S-(S-T_{0,air})\frac{1+B}{1+B\exp(t/\tau)}.$$

S为渐近温度K，B无量纲，tau为s。T0,air是附件首行空气温度，不默认与药材T0相同。记录拟合残差、前段训练后段时间留出预测、残差相关性和参数区间。拟合最终选择与计算参数以environment-fit.md及results/validation/ambient_fit.json为准。

第二工况前4h仍保留附件实测插值；4h后令温度恒等于所选曲线渐近S，相对湿度仍20%，每个温度下重新由RH求空气Y，不能保持60°C的Y又称20%RH。保持相同含湿模型、物性和数值精度，以便比较温度来源的影响。

有限4h数据得到的S是条件外推值，不代表已经观测到长期稳态。窄的回归/自助法区间只涵盖所选曲线与残差模型下的统计不确定性；不同候选曲线平台的差异与未来控制变化另列为结构不确定性。拟合数值不在本说明手填，正式表图由结果自动生成。

本轮不采用缺少材料依据的Ce=0.05吸附/供水阈值情景，正式敏感性仅包括温度、RH、Lewis数、潜热关闭和固定半径。未测平衡含水率保留为模型局限，不称已由数值扰动验证。
