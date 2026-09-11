# NOTATION.md：符号、单位与实现映射

Owner：@model。2026-09-11同步四问潜热及供水/气膜互补模型。本文件为当前符号唯一真源；旧“C∞同时代表空气湿度和固相含水率”的定义取消。原题、建模假设、文献参数与实际计算值必须区分。

## 0. 三层命名映射

|论文符号|LaTeX宏|Python名称|定义|
|---|---|---|---|
|T|`\T`|T|药材温度，内部K|
|C|`\C`|C|药材干基含水率，kg水/kg干物质|
|t|`\t`|t|时间s|
|r|`\rpos`|r|物理径向距离m|
|R|`\R`|R|当前半径m|
|R0|`\Rzero`|R0|初始半径m|
|L|`\Llen`|L|长度m|
|rho|`\rho`|rho|题定经验密度，用于有效热容量|
|cp|`\cp`|cp|题定比热J/(kg K)|
|k|`\kcond`|k|导热系数W/(m K)|
|D|`\Ddiff`|D|有效水分扩散系数m²/s|
|h|`\hconv`|h_conv|对流换热系数W/(m² K)|
|hm|`\hmass`|h_mass|固相基准的有效供水系数m/s|
|T∞|`\Tinf`|T_amb|烘房温度K|
|Y∞|`\Yinf`|Y_amb|空气湿含量kg水/kg干空气；Boundary.C_amb为兼容旧接口的存储名|
|Ysat|`\Ysat`|humidity_ratio(T_s,1)|表面温度下饱和空气湿含量|
|Yint|`\Yint`|Y_interface|反算的界面空气湿含量|
|phi|`\RH`|relative_humidity|相对湿度0—1|
|p|`\pair`|pressure|空气总压Pa|
|pv|`\pvap`|vapor_pressure|水蒸气分压Pa|
|es|`\psat`|saturation_pressure|饱和蒸汽压Pa|
|epsilon|`\epsratio`|MOLECULAR_MASS_RATIO|水蒸气/干空气分子量比0.621945|
|cpm|`\cpm`|humid_heat|每kg干空气的湿空气比热1006+1860Y∞，J/(kg干空气 K)|
|Le|`\Le`|lewis|Lewis数，热扩散率/水蒸气扩散率|
|KM|`\KM`|gas_transfer|气膜湿含量驱动系数kg干空气/(m² s)|
|Ts|`\Ts`|T_s|药材表面温度|
|Cs|`\Cs`|C_s|药材表面干基含水率|
|rho_d|`\rhod`|dry_density(t)|参考干物质密度kg/m³|
|rho_d0|`\rhodzero`|rho_d0|初始参考干密度rho(C0,T0)/(1+C0)|
|jv|`\jvap`|j_v|向外相变质量通量kg/(m² s)，负号为冷凝|
|js|`\jsupply`|supply|内部供水能力kg/(m² s)|
|jg|`\jgas`|gas|气膜排湿能力kg/(m² s)|
|DeltaH_vap|`\Lvap`|latent_heat_vaporization|纯水汽化潜热J/kg|
|w|`\wfrac`|wet_basis(C)|湿基水质量分数C/(1+C)|
|xi|`\xi`|xi|材料坐标r/R|
|v|`\vmat`|v|材料径向速度r Rdot/R，m/s|
|Md|`\Mdry`|dry_mass|干物质总质量kg|
|Mw|`\Mwater`|water_mass|水总质量kg|
|M(t)|`\Cmax`|max_C|全内部场最大含水率|
|t*|`\tstar`|event_time_s|全场达到0.15的连续阈值时刻s|
|Delta t|`\dt`|dt|时间步长s，必须区分内部与输出|
|Delta r|`\dr`|dr|径向间距m|
|Nr|`\Nr`|n_internal|内部径向节点数|
|Vi|`\Vi`|weights[i]|无量纲环形控制体积权重|
|FT,FC|`\FT`,`\FC`|qT,qC|材料域的面通量，见numerics.md|

可保留旧 `\Cinf` 宏仅用于说明已否决的历史有效边界，不可在正式模型中拿其与Cs相减。CE/平衡药材含水率未有实测值，不是正式参数。

## 1. 题给几何与初值

L=0.25m，R0=0.02m，T0=301.15K，C0=2.55kg/kg。原题展示单位25cm、2cm、28°C。长度/直径6.25，长度/半径12.5。周向、轴向均匀是一维近似，端面/侧面积比R0/L=.08并非严格误差界。

输出径向0.1cm=0.001m；问题1/2每1s，问题3/4每60s。内部采用自适应时间积分和表面加密网格，并非输出网格直接求解。

## 2. 三套物性

|量|附录2|附录3|附录4|SI单位|
|---|---|---|---|---|
|rho|820|650+128C|760+90C|kg/m³|
|cp|2600|1450+2736C/(1+C)|1850+2150C/(1+C)|J/(kg K)|
|k|.36|.21+.38C/(1+C)|.12+.20C/(1+C)|W/(m K)|
|D|7e-9 exp(-.89/C)|2.4e-3 exp(-.45/C-3850/T)|4.2e-4 exp(-.30/C-3850/T)|m²/s|

附录2用于Q1，附录3全程用于Q2/Q3，附录4用于Q4。h=25，hm=8e-7来自附录2，后三问沿用是同装置假设。指数温度一律K，C=0时D按右极限0，C<0拒绝。

rho_d0=rho(C0,T0)/(1+C0)。Q1—3保持常数，Q4乘(R0/R)²。经验rho仅用于有效热容量，不强迫它等于rho_d(1+C)，也不把rho*C当水质量密度。

## 3. 最终湿度、气膜与潜热

令theta=T−273.15，es=610.8 exp[17.27theta/(theta+237.3)]Pa；Y=epsilon phi es/(p−phi es)，epsilon=.621945，p=101325Pa。来源FAO56与ASHRAE，见docs/model/environment.md。

cpm=1006+1860Y∞ J/(kg干空气 K)，Le=.845，KM=h/cpm*Le^(-2/3)。js=rho_d hm Cs，jg=KM(Ysat(Ts)−Y∞)，jv=min(js,jg)。通量可负冷凝，气固含水率不直接相减。

潜热DeltaH_vap=2.501e6−2361(Ts−273.15)J/kg。表面−rho_d D C_r=jv；k T_r=h(T∞−Ts)−DeltaH_vap*jv。Q4转换为D C_xi=−R jv/rho_d和k T_xi=R[h(T∞−Ts)−DeltaH_vap*jv]。

## 4. 环境及模型适用范围

Q1用附件1；Q2—4前4h用附件1逐点线性插值，之后333.15K、20%RH，空气湿含量按上式求。两控制段的药材状态连续。标准压力和控制温湿度是设计工况，不是题给实测值。

Q4 R(t)由附件2线性插值，范围0—72h，不能无依据外推。长度不变、均匀径向材料收缩v=rRdot/R；材料导数与变换项抵消，不额外加收缩对流。

未知具体药材的解吸等温线与结合水额外潜热，供水/气膜条件属于透明近似；没有需捏造参数才能继续的待定项，但物理局限必须报告。设计参数研究文献与核验细节见references-research.md。

## 5. 单位转换和显示

代码内部全部SI，温度K、长度m、时间s。输入附件转换在读取边界，物性相关式需摄氏度时只在公共相关函数转换。展示使用cm、°C，论文Q2—4时间h；四个xlsx时间均s。所有表值四位小数，数值精度和模型不确定性另行说明。

CM_TO_M=1e-2，M_TO_CM=1e2，H_TO_S=3600，S_TO_H=1/3600，C_TO_K=273.15，K_TO_C=−273.15。转换统一从src/common/units.py取得。

## 6. 附件温度拟合符号

|论文符号|LaTeX宏|Python名称|含义与单位|
|---|---|---|---|
|S|`\Tplateau`|plateau_K|拟合渐近温度K，非实测恒温设定|
|B|`\Bshape`|shape_B|logistic曲线无量纲形状参数|
|tau|`\taufit`|tau_s|拟合升温时间尺度s|
|T0,air|`\Tairzero`|T0_air|拟合固定的附件初始空气温度K，须区别药材初温T0|
|Tfit(t)|`\Tfit`|temperature_fit|拟合空气温度K|
|n_obs|`\Nobs`|n_obs|拟合观测数量|
|RMSE|`\RMSE`|rmse_K|拟合/时间留出预测均方根误差K|
|CI95|`\CI`|plateau_interval_K|所选回归模型条件下S的95%区间K|

候选固定初温logistic：
$$T_{fit}(t)=S-(S-T_{0,air})\frac{1+B}{1+B\exp(t/\tau)}.$$

t为s。T0,air须来自附件首行或明确的固定输入，不能未经说明混用药材初温。该曲线在t=0等于T0,air、t趋于无穷时等于S。条件区间不包含外推模型误设或烘房后续控制变化的不确定性。

## 7. 未采用的材料闭合

本轮未取得药材平衡含水率或解吸等温线参数，不采用Ce=0.05情景，不赋予其正式符号或物理标定含义。正式供水能力始终js=rho_d hm Cs。
