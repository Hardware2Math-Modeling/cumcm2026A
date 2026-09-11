# =============================================================================
# CUMCM 2026 A —— 一键命令入口
# 用 `make` 或 `make help` 查看全部可用目标。
#
# 环境自动探测：优先用 environment.yml 声明的 cumcm2026a；
# 若本机没有该环境，则回退到已存在的 tf2（自带 numpy/scipy/pandas/matplotlib/openpyxl）。
# 也可以手动指定：  make ENV=我的环境名 check
#
# 所有 python 命令都走 `conda run -n $(ENV)`，这样无需在 shell 里
# `conda activate`，非交互式终端 / CI / AI agent 也能直接跑。
# =============================================================================
CONDA ?= conda

# 探测顺序：命令行 ENV > 环境变量 ENV > cumcm2026a > tf2
ENV ?= $(shell $(CONDA) env list 2>/dev/null | awk '$$1=="cumcm2026a"{print "cumcm2026a"; exit}')
ifeq ($(strip $(ENV)),)
ENV := $(shell $(CONDA) env list 2>/dev/null | awk '$$1=="tf2"{print "tf2"; exit}')
endif
ifeq ($(strip $(ENV)),)
ENV := cumcm2026a
endif

CONDA_RUN := $(CONDA) run -n $(ENV) --no-capture-output
PY        := $(CONDA_RUN) python
PYTEST    := $(CONDA_RUN) pytest
RUFF      := $(CONDA_RUN) ruff
LATEXMK   := latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd

.DEFAULT_GOAL := help
.PHONY: help env setup doctor data probe q1 q2 q3 q4 all tables figs paper check test \
        test-fast selfcheck lint fmt clean clean-all status validate

# --------------------------------------------------------------------------- #
env:  ## 显示当前环境与依赖状态
	@echo "当前 ENV = $(ENV)"
	@$(PY) -c "import sys; print('python', sys.version.split()[0], '@', sys.executable)"
	@$(PY) -c "import numpy,scipy,pandas,matplotlib,openpyxl; print('numpy',numpy.__version__,'| scipy',scipy.__version__,'| pandas',pandas.__version__,'| mpl',matplotlib.__version__,'| openpyxl',openpyxl.__version__)" || echo "!! 科学计算依赖不全"
	@$(PYTEST) --version >/dev/null 2>&1 && echo "pytest ok" || echo "!! 缺 pytest（make test / make check 不可用）"
	@$(RUFF) --version >/dev/null 2>&1 && echo "ruff ok" || echo "!! 缺 ruff（make lint 不可用）"

help:  ## 显示本帮助
	@echo "CUMCM 2026 A —— 药材的烘干问题    [conda 环境: $(ENV)]"
	@echo ""
	@echo "  环境"
	@echo "    make env          显示当前环境与依赖状态"
	@echo "    make setup        创建/同步 conda 环境（唯一允许的装依赖方式）"
	@echo "    make doctor       体检：检查依赖、LaTeX、目录是否齐全"
	@echo ""
	@echo "  计算"
	@echo "    make probe        【必做】打印交付模板与附件的真实结构"
	@echo "    make data         解析 problem/ 附件 -> data/processed"
	@echo "    make q1|q2|q3|q4  跑单题，产出 results/result<N>.xlsx"
	@echo "    make all          跑全部四题 + 数值验证 + 表格 + 插图"
	@echo "    make validate     重跑数值验证 -> results/validation/numerics.json"
	@echo "    make tables       生成论文表格片段 paper/tab/*.tex"
	@echo "    make figs         生成论文插图 paper/figs/*.pdf"
	@echo ""
	@echo "  论文"
	@echo "    make paper        编译 paper/main.tex -> paper/build/main.pdf"
	@echo "                      （自动先跑 tables 与 figs）"
	@echo ""
	@echo "  质量"
	@echo "    make check        提交前必跑：lint + test"
	@echo "    make lint         代码风格（ruff）"
	@echo "    make test         全部测试"
	@echo "    make test-fast    跳过 slow 标记的测试"
	@echo "    make selfcheck    框架自检（不依赖 pytest）"
	@echo "    make fmt          自动格式化"
	@echo ""
	@echo "  杂项"
	@echo "    make status       当前分支 + 工作区状态 + 该不该 rebase"
	@echo "    make clean        清理可重建产物"
	@echo "    make clean-all    连 LaTeX 中间件一起清"
	@echo ""
	@echo "  换个环境跑： make ENV=<环境名> <目标>"

# --------------------------------------------------------------------------- #
setup:  ## 创建或同步 conda 环境
	@if conda env list | grep -qE '^$(ENV)\s'; then \
		echo ">> 环境已存在，执行 update --prune"; \
		conda env update -f environment.yml --prune; \
	else \
		echo ">> 首次创建环境"; \
		conda env create -f environment.yml; \
	fi
	@echo ">> 完成。激活： conda activate $(ENV)"

doctor:  ## 环境与工具链体检（有问题时以非 0 退出，可当提交前门禁）
	@fail=0; \
	echo "== python =="; $(PY) -c "import sys; print(sys.version)" || fail=1; \
	echo "== 依赖 =="; $(PY) -c "import numpy,scipy,pandas,matplotlib,openpyxl; print('numpy',numpy.__version__,'| scipy',scipy.__version__,'| pandas',pandas.__version__,'| mpl',matplotlib.__version__,'| openpyxl',openpyxl.__version__)" || fail=1; \
	echo "== LaTeX =="; command -v latexmk >/dev/null && latexmk -v | head -2 || { echo "  !! 缺 latexmk，make paper 不可用"; fail=1; }; \
	echo "== ctex（中文支持）=="; kpsewhich ctexart.cls >/dev/null && echo "  ok" || { echo "  !! 缺 ctex，中文论文编不出来"; fail=1; }; \
	echo "== 目录 =="; for d in problem data/raw data/processed src/common docs paper/sections paper/tab paper/figs results results/tables; do \
		[ -d "$$d" ] && echo "  ok   $$d" || { echo "  !!   $$d 缺失"; fail=1; }; done; \
	echo "== 论文生成产物 =="; for f in paper/tab/q1_values.tex paper/tab/q1_temp.tex paper/figs/fig1-T-profiles.pdf; do \
		[ -f "$$f" ] && echo "  ok   $$f" || { echo "  !!   $$f 缺失 —— 先跑 make tables figs"; fail=1; }; done; \
	if [ $$fail -ne 0 ]; then echo; echo ">> 体检未通过（上面有 !! 项）"; else echo; echo ">> 体检通过"; fi; \
	exit $$fail

# --------------------------------------------------------------------------- #
probe:  ## 【必做】打印交付模板与附件的真实结构
	$(PY) scripts/probe_templates.py

data:  ## 解析附件
	$(PY) scripts/parse_attachments.py

q1:  ## 问题 1
	$(PY) scripts/run_q1.py
q2:  ## 问题 2
	$(PY) scripts/run_q2.py
q3:  ## 问题 3
	$(PY) scripts/run_q3.py
q4:  ## 问题 4
	$(PY) scripts/run_q4.py

all: data q1 q2 q3 q4 validate tables figs  ## 全流程（含数值验证）

#: 数值验证报告。它是论文验证表 tab/q1_validation 的**唯一数据源**，
#: 所以做成文件目标：脚本或求解器一变就自动重跑，避免论文引用到旧报告
#: （AGENTS.md 铁律 10「不许静默降级」）。
#: 依赖只列**真正影响数值**的模块 —— 否则改个 docstring 也要重算十几分钟。
VALIDATION_JSON := results/validation/numerics.json
NUMERIC_SRC := $(wildcard src/common/radial.py src/common/boundary.py \
                          src/common/correlations.py src/common/problem_spec.py \
                          src/common/units.py)
$(VALIDATION_JSON): scripts/validate_numerics.py $(NUMERIC_SRC)
	$(PY) scripts/validate_numerics.py

validate:  ## 强制重跑数值验证（网格/时间/敏感性/固定半径对照）
	$(PY) scripts/validate_numerics.py

tables: $(VALIDATION_JSON)  ## 生成论文表格片段 paper/tab/*.tex
	$(PY) scripts/make_tables.py

figs:  ## 生成论文插图 paper/figs/*.pdf（四问）
	$(PY) scripts/make_figs.py

# --------------------------------------------------------------------------- #
# paper 依赖 tables figs：否则干净检出下 tab/ 与 figs/ 是空的，
# 正文里的 \geninput 会全部落到占位分支。
paper: tables figs  ## 编译论文（自动先生成表格与插图）
	@mkdir -p paper/build
	$(LATEXMK) -outdir=build paper/main.tex
	@echo ">> 产物： paper/build/main.pdf"

# --------------------------------------------------------------------------- #
check: lint test  ## 提交前必跑
lint:  ## 代码风格（环境里没有 ruff 时给出提示并跳过）
	@if $(RUFF) --version >/dev/null 2>&1; then \
		$(RUFF) check . && $(RUFF) format --check .; \
	else \
		echo "!! conda 环境「$(ENV)」里没有 ruff，已跳过 lint。"; \
		echo "   安装： conda run -n $(ENV) pip install ruff"; \
	fi

fmt:  ## 自动格式化（需要 ruff）
	@$(RUFF) --version >/dev/null 2>&1 || { echo "!! 缺 ruff。安装： conda run -n $(ENV) pip install ruff"; exit 1; }
	$(RUFF) check --fix .
	$(RUFF) format .

test:  ## 全部测试（conda 无 pytest 时回退到本地 .devtools/py，再回退到 selfcheck）
	@if $(PYTEST) --version >/dev/null 2>&1; then \
		$(PYTEST); \
	elif [ -d .devtools/py ]; then \
		echo ">> 用本机 .devtools/py 里的 pytest"; \
		PYTHONPATH=.devtools/py $(PY) -m pytest -q; \
	else \
		echo "!! conda 环境「$(ENV)」里没有 pytest。"; \
		echo "   安装： conda run -n $(ENV) pip install pytest pytest-cov"; \
		echo "   本次回退到框架自检（不依赖 pytest）："; \
		$(PY) scripts/selfcheck.py; \
	fi

selfcheck:  ## 框架自检（不依赖 pytest，任何环境都能跑）
	$(PY) scripts/selfcheck.py

test-fast:  ## 跳过 slow 标记的测试
	@if $(PYTEST) --version >/dev/null 2>&1; then \
		$(PYTEST) -m "not slow"; \
	else \
		echo "!! 缺 pytest，已跳过。安装： conda run -n $(ENV) pip install pytest"; \
	fi

# --------------------------------------------------------------------------- #
status:  ## 分支与工作区状态
	@echo "== 当前分支 =="; git branch --show-current
	@echo "== 工作区 =="; git status --short
	@echo "== 与 main 的差异（左=落后 右=领先）=="; git rev-list --left-right --count main...HEAD 2>/dev/null || echo "(无 main)"
	@echo "== 最近提交 =="; git log --oneline -5

clean:  ## 清理可重建产物（不动 results/ 与 paper/figs）
	rm -rf outputs/cache/* outputs/logs/* data/interim/*
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
	@echo ">> 已清理。注意：results/ paper/figs/ paper/tab/ 未动。"

clean-all: clean  ## 连 LaTeX 中间件一起清
	rm -rf paper/build/*
	@echo ">> 已清理 paper/build（含 main.pdf）"
