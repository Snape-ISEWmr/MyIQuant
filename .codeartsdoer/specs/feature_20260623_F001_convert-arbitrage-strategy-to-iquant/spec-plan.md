# 跨品种套利策略转换执行计划

**目标:** 将vnpy跨品种套利策略转换为iQuant平台适配版本

**技术栈:** Python 3.x, numpy, iQuant ContextInfo接口

**设计文档:** spec-design.md

---

### Task 1: 创建策略文件框架

**涉及文件:**
- 新建: `python/商品期货的套利策略_iQuant.py`

**执行步骤:**
- [ ] 创建策略文件，添加编码声明和策略头注释
  - 文件头包含：#coding:gbk、策略名称、类型、核心指标、交易逻辑、风控方式、最后修改
- [ ] 导入必要模块
  - 导入numpy用于数值计算
- [ ] 实现辅助函数
  - highest(data, period)：计算序列最高值
  - lowest(data, period)：计算序列最低值
  - sma(data, period, weight)：计算简单移动平均
  - xaverage(data, period)：计算加权平均

**检查步骤:**
- [ ] 验证文件编码声明正确
  - `python -c "import sys; sys.path.insert(0, 'python'); exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read().split('def')[0])"`
  - 预期: 无编码错误
- [ ] 验证辅助函数可调用
  - `python -c "import sys; sys.path.insert(0, 'python'); exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read()); print('highest' in dir())"`
  - 预期: 输出 True

---

### Task 2: 实现init初始化函数

**涉及文件:**
- 修改: `python/商品期货的套利策略_iQuant.py`

**执行步骤:**
- [ ] 实现init(ContextInfo)函数
  - 设置策略参数：N=2, M=5, X=5, TRS=5, fixed_size=1
- [ ] 初始化数据容器
  - 创建8个列表存储两个品种的开高低收数据
- [ ] 初始化状态变量
  - KG=0（持仓状态）、high_after_entry、low_after_entry、curbar_h、curbar_l、current_bar

**检查步骤:**
- [ ] 验证init函数存在
  - `python -c "import sys; sys.path.insert(0, 'python'); exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read()); print('init' in dir())"`
  - 预期: 输出 True
- [ ] 验证init函数签名正确
  - `python -c "import inspect; exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read()); print(inspect.signature(init))"`
  - 预期: 输出包含 ContextInfo

---

### Task 3: 实现handlebar核心交易逻辑

**涉及文件:**
- 修改: `python/商品期货的套利策略_iQuant.py`

**执行步骤:**
- [ ] 实现handlebar(ContextInfo)函数框架
  - 获取两个品种行情数据（通过ContextInfo.get_market_data）
  - 更新数据数组和K线计数器
- [ ] 实现价比计算逻辑
  - 计算c_jb（收盘价比）、copen（开盘价比）、chigh（最高价比）、clow（最低价比）
- [ ] 实现指标计算逻辑
  - 计算var1-var9、bd1、bd2、ma1等指标
  - 判断金叉死叉信号
- [ ] 实现开仓逻辑
  - 做多信号：品种1买入，品种2卖出
  - 做空信号：品种1卖出，品种2买入
- [ ] 实现止损止盈逻辑
  - 移动止损计算
  - 触发止损时平仓

**检查步骤:**
- [ ] 验证handlebar函数存在
  - `python -c "import sys; sys.path.insert(0, 'python'); exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read()); print('handlebar' in dir())"`
  - 预期: 输出 True
- [ ] 验证代码无语法错误
  - `python -m py_compile python/商品期货的套利策略_iQuant.py`
  - 预期: 无输出（无错误）

---

### Task 4: 跨品种套利策略转换验收

**前置条件:**
- 启动命令: 无需启动服务，静态代码检查
- 测试数据准备: 无
- 其他环境准备: Python 3.x环境

**端到端验证:**

1. 验证策略文件符合iQuant规范
   - `python -c "code = open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read(); checks = ['#coding:gbk' in code, 'def init(ContextInfo)' in code, 'def handlebar(ContextInfo)' in code]; print('All checks passed:', all(checks))"`
   - Expected: All checks passed: True
   - On failure: check Task 1 策略文件框架

2. 验证辅助函数实现正确
   - `python -c "exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read()); import numpy as np; data = np.array([1,2,3,4,5]); print(highest(data, 3)[-1] == 5 and lowest(data, 3)[-1] == 3)"`
   - Expected: True
   - On failure: check Task 1 辅助函数实现

3. 验证策略参数初始化正确
   - `python -c "class C: pass; exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read()); c = C(); init(c); print(hasattr(c, 'N') and c.N == 2)"`
   - Expected: True
   - On failure: check Task 2 init函数实现

4. 验证代码无语法错误且可导入
   - `python -c "import sys; sys.path.insert(0, 'python'); exec(open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read()); print('Strategy loaded successfully')"`
   - Expected: Strategy loaded successfully
   - On failure: check Task 3 handlebar函数实现

5. 验证策略头注释完整
   - `python -c "code = open('python/商品期货的套利策略_iQuant.py', encoding='gbk').read(); required = ['策略名称', '策略类型', '核心指标', '交易逻辑', '风控方式', '最后修改']; print(all(r in code for r in required))"`
   - Expected: True
   - On failure: check Task 1 策略头注释