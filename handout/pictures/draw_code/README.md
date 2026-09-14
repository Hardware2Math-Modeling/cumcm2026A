# Handout 插图重绘

图 3、图 4 及两张 q2 幕片图的断轴上段统一压缩为此前高度的 **70%**：
`draw_fig3.field_height()` 以断点上缘为固定基准，仅缩短数值区间的纵向距离，
零点、断点、底面深度及片层留白不变，数据与刻度值不变。画幅同步降低。
两张 q2 图的距离轴标题以轴线中点为锚点、向外垂直偏移，保持居中且平行于轴线。

## 问题二：五个位置的逐秒演化幕片

```bash
conda run -n tf2 python handout/pictures/draw_code/draw_q2_summary.py
```

直接读取 `results/result2.xlsx` 的“温度”“水分浓度”工作表，
按列标题选取 0、0.5、1、1.5、2 cm 五个位置，绘制 0–10800 s 逐秒数据，
每个位置每个物理量均保留 **10801 个点**。不从 PDF 提取、不使用半小时表格连线，
不抽稀、不拟合、不平滑；Matplotlib 折线简化关闭。
Excel 温度为 °C，读入后转为 K，时间保持 s、距离转为 m，
仅在绘图时转为 h、cm、°C。原有半小时表值与选取的 Excel 数据已核对：
唯一差异为 1.5 h、2 cm 温度，当前 Excel 为 47.1400 °C，
旧表 `handout/tables/q2_T.tex` 为 47.1401 °C；其他表值一致。
新图严格保留 Excel 的数值，不为匹配旧表修改数据。

- 温度图：`handout/pictures/q2_temperature_waterfall.pdf`
- 含水率图：`handout/pictures/q2_moisture_waterfall.pdf`
- 同名 PNG 为预览；`q2_summary_source.json` 记录输入文件 SHA-256、工作表、时间和单位。

沿用 fig3/4 的绿至红渐变、0.10 透明度、1.6 pt 加深顶部曲线及 1 pt 侧边。
**每个幕片对应固定距离，横向为时间**，不是固定时刻的径向剖面。
温度图中心的绿色幕片在前；含水率图表面的红色幕片在前，
两图的前方留白一致，距离刻度和箭头随排列方向同步。
Z 轴从 0 起，经双斜线断轴跳至数据区间（温度约 27 °C、含水率约 0.8 kg/kg），
上段线性缩放；幕片面积没有积分意义。
图内仅坐标轴标题含中文，标题平行于对应投影轴。
原 `handout/figures/q2_summary.pdf`、Excel、论文及已有 fig1/3/4 均不修改。
新图包含原图未展示的前 0.5 h；若后续替换论文引用，
原图注“标记为0.5 h间隔表值，连线仅辅助阅读”应同步改为逐秒数据说明。

## 图 1：三维传热传质示意图

```bash
conda run -n tf2 python handout/pictures/draw_code/draw_fig1.py
```

按 `handout/pictures/IMG_5721.heic` 的手绘视角，绘制从左上向右下延伸的
半透明灰色圆柱。前端截面和内部均有红色径向向内的热量箭头、蓝色径向向外的
水分箭头；内部箭头透过外壳显示。只保留“热量”“水分”两个简短图例，
不显示尺寸、初始温度、初始含水率、附件说明或公式图注。
端面与内部统一为三圈同心箭头，每圈 12 支、红蓝交替；
圆柱内部沿轴向放置三组与端面完全相同的箭头阵列。
每支箭头长度为上一版的三分之一（0.18 倍半径），箭头头部和线宽相应缩小。
观察方向与轴线夹角由 20° 稍展开为 27°，使各组投影分开，避免箭头相互遮挡。
画面内圆柱倾角由 -28° 调平至 -12°，三维观察夹角仍为 27°；
图例移入右上角留白，不再单独占据底部一行，画幅降低为 8 × 3.8 英寸。
`RADIAL_BANDS`、`ARROWS_PER_RING`、`AXIAL_FRACTIONS` 分别控制圈位置、
每圈数量和轴向组位置，不改变物理数据。

这是**物理过程示意图，不是数值结果图**。圆柱几何直接读取
`common.problem_spec.Q1.geometry`，以 m 构造三维坐标，再进行正交投影；
观察方向靠近圆柱轴线，因此长度在正交投影中缩短，未改变真实几何长径比。
箭头在截面内沿径向运动，不代表端面上的轴向通量；箭头长度和数量仅为排版，
不表示求解器计算的热流或水分通量大小。程序不读取或修改数值解。

输出为 `handout/pictures/fig1_3d.pdf`（矢量 PDF）和同名 PNG 预览。
圆柱面及箭头均为矢量图形，外壳用真正的半透明填充；中文采用与图 3/4
相同的 Arial Unicode MS。`--output` 可以改输出文件名，但必须仍在
`handout/pictures` 内，且后缀为 `.pdf`，避免覆盖原图或其他目录。

原 `handout/figures/fig1.pdf` 保持不变，SHA-256：
`5cfab32654003e3b08cd1aebb1a8d2191ccb03b77ba69f8d5c90ac30ff2ce6b2`。
不改已有图 3、图 4。

## 图 3、图 4：三维瀑布曲线

按 `handout/pictures/IMG_5718.heic` 的构图重绘，不运行 PDE 求解器。
使用斜投影展示径向位置、实际时间、温度；时间轴按秒数线性排列，不把不等时间间隔画成等距。
曲线边缘采用适度提亮的柔和绿、橄榄绿、土黄、赭橙、红色渐变，曲线下方采用同色浅透明幕片。
全部时间切片与对应刻度沿时间方向整体后移，前方留白仅用于排版，
不改变实际时刻和时间间隔；时间轴不加断点，标题为“时间 / s”。
100 s 片面与距离轴的间距为上一版的一半，其余片面与刻度同步平移。
温度底面为 **0 °C**，Z 轴用双斜线标出跳至 27 °C 附近的断轴，
其后按实际温度线性排列，首个上段刻度为 28 °C；幕片面积不表示热量。
顶部曲线为 1.6 pt，颜色在对应片层颜色基础上略加深（RGB × 0.88）；
侧边与底边仍为 1 pt，填充保持半透明。图内中文只用于三个坐标轴标题，
各标题与对应投影轴平行。
中文由 Matplotlib 的 `axes.text()` 排版，使用本机 Arial Unicode MS 字体并嵌入 PDF，
不是图像生成或手写；候选回退字体为 Songti SC、DejaVu Sans。

## 运行

```bash
conda run -n tf2 python handout/pictures/draw_code/draw_fig3.py
```

直接输出 `handout/pictures/fig3_waterfall.pdf`，保留原始
`handout/figures/fig3.pdf`，不改其他图、模型或结果表。
可用 `--output <路径.pdf>` 输出另一份 PDF；程序拒绝覆盖原始 `fig3.pdf`。
`COLORS` 控制颜色，`figsize` 控制画幅，`project()` 控制斜投影视角。

## 数据来源与精度边界

原绘图程序是 `lyz/A题/论文/code/make_figures.py`，选取
100、300、600、1200、1800 s；其引用的 `绘图与摘要数据.npz` 不在当前仓库。
因此 `fig3_profiles.csv` 保存的是原始 `handout/figures/fig3.pdf` 的
**矢量折线顶点**，经原图坐标刻度反变换得到，并以 s、m、K 存储。
这些点精确复现 PDF 已显示的折线，不等同于缺失的完整数值解；
不平滑、不拟合、不插补，也不拿另一套求解结果替代。
原 PDF 后端已进行折线简化，因此各时刻顶点数不同。
反变换使用 PDF 的 0、2 cm 横轴定位和 28、36 °C 纵轴定位。

原 PDF 的 SHA-256：
`54ff16c46bb7ace2e3309560ea063336013d7ed6d3183f3927d493a4bc75f93e`。
首次提取使用 `--extract-source <原始PDF>`；该参数严格校验哈希，
不会误把新生成的图当作原始数据。日常重绘只读已保存 CSV。

## 验证

```bash
conda run -n tf2 python -m unittest discover -s handout/pictures/draw_code -p 'test_*.py'
```

## 图 4：含水率幕片

```bash
conda run -n tf2 python handout/pictures/draw_code/draw_fig4.py
```

输出 `handout/pictures/fig4_waterfall.pdf`，原始 `handout/figures/fig4.pdf`
保持不变。`fig4_waterfall.png` 仅供预览，论文使用矢量 PDF。
图 4 直接复用 `draw_fig3.py` 的绘图函数（`field="C"`），
保持图 3 最终版的配色、透明度、顶部曲线加粗加深、1 pt 侧边、
时间轴间距、中文字体和轴标题方向。
图 4 时间轴反向：由近至远为 1800、1200、600、300、100 s，
红色 1800 s 幕片在最前方，与距离轴的间距等于反向前 100 s 幕片的间距。
时间刻度与片层同步反向，箭头指向时间增大的近端；数值间隔仍按实际秒数线性缩放。
Z 轴改为“干基含水率 / (kg/kg)”：底面为 0，断轴跳至 1.4 kg/kg 附近，
上段线性缩放，显示 1.6–2.6 kg/kg 刻度。幕片面积不表示水分总量。
原始图 3、图 4 PDF 均不改动。

`fig4_profiles.csv` 存储原图的 **179 个矢量折线顶点**，单位为 s、m、kg/kg。
与图 3 一样，源 NPZ 缺失，故只复现 PDF 中实际显示的折线；
不平滑、不拟合，不用其他求解结果替代。
坐标反变换以原 PDF 的 0、2 cm 和 1.6、2.6 kg/kg 刻度为基准：
PDF 横坐标为 43.2625、632.007333 pt，纵坐标为 61.749475、216.739461 pt。
首次提取命令为：

```bash
conda run -n tf2 python handout/pictures/draw_code/draw_fig4.py \
  --extract-source handout/figures/fig4.pdf
```

提取时校验原 PDF SHA-256：
`6b2be140ebe0e3bbee46df93b52376ab205f6f3dd45577e5fde27f94afed2aff`。
`--output` 可指定其他 PDF 路径，但禁止输出到原图目录 `handout/figures`。
