# Feature: 20260623_F001 - convert-arbitrage-strategy-to-iquant

## 需求背景
项目现有`python/商品期货的套利策略.py`是基于vnpy框架实现的跨品种套利策略，无法直接在iQuant平台运行。该策略实现了两个商品期货品种之间的价差套利，包含完整的指标计算、信号生成、持仓管理和止损止盈逻辑。

为使策略能在iQuant平台运行，需要将其转换为适配iQuant平台的版本，保留核心套利逻辑，使用iQuant的`init/handlebar`接口。

## 目标
- **核心目标1**：将vnpy套利策略转换为iQuant平台可运行版本
- **核心目标2**：保留所有指标计算逻辑（价比、SMA、BD1/BD2、highest/lowest等）
- **核心目标3**：实现跨品种套利交易（两个品种价差交易）
- **核心目标4**：支持回测和实盘两种运行模式

## 方案设计

### 转换方案选择

采用**直接接口映射转换**方案：
- 保留原策略所有指标计算逻辑
- 将vnpy接口直接映射为iQuant接口
- 符合项目"增量开发原则"和"策略模板强制套用原则"

### 核心策略逻辑（保留）

#### 1. 价差计算
```
c_jb = close_1 / close_2  # 两个品种收盘价比
copen = open_1 / open_2   # 开盘价比
chigh = max(high_1/high_2, copen, c_jb)  # 最高价比
clow = min(low_1/low_2, copen, c_jb)     # 最低价比
```

#### 2. 指标计算
- **BD1**：基于价比的加权平均指标
- **BD2**：BD1的平滑指标
- **MA1**：价比的移动平均
- **highest/lowest**：周期内最高/最低价

#### 3. 开仓信号
- **做多信号**：BD1>BD2（金叉）且 价差突破前高 且 价差>MA
- **做空信号**：BD1<BD2（死叉）且 价差跌破前低 且 价差<MA

#### 4. 持仓管理
- **做多时**：品种1买入，品种2卖出（对冲）
- **做空时**：品种1卖出，品种2买入（对冲）

#### 5. 止损止盈
- 基于TRAILING_STOP参数的移动止损
- 多头止损：价差跌破 low_after_entry - TRS
- 空头止损：价差涨破 high_after_entry + TRS

### 接口转换映射

| vnpy接口 | iQuant接口 | 说明 |
|---------|-----------|------|
| `am.update_bar(bar)` | `ContextInfo.get_market_data` | 更新K线数据 |
| `am.close_array` | 数据数组管理 | 获取收盘价数组 |
| `self.get_pos(vt_symbol)` | `ContextInfo.get_position` | 获取持仓 |
| `self.buy(vt_symbol, price, size)` | `ContextInfo.order_buy` | 买入开仓 |
| `self.sell(vt_symbol, price, size)` | `ContextInfo.order_sell` | 卖出平仓 |
| `self.short(vt_symbol, price, size)` | `ContextInfo.order_sell` | 卖出开仓（期货） |
| `self.cover(vt_symbol, price, size)` | `ContextInfo.order_buy` | 买入平仓（期货） |
| `self.write_log(msg)` | `print(msg)` | 日志输出 |

### 策略文件结构

```
python/商品期货的套利策略_iQuant.py
├── 编码声明：#coding:gbk
├── 导入模块：numpy
├── 全局变量：策略参数（N, M, X, TRS, fixed_size）
├── 辅助函数：
│   ├── highest(data, period) - 计算最高值序列
│   ├── lowest(data, period) - 计算最低值序列
│   ├── sma(data, period) - 简单移动平均
│   └── xaverage(data, period) - 加权平均
├── init(ContextInfo) - 初始化函数
│   ├── 设置策略参数
│   ├── 初始化数据容器
│   └── 初始化状态变量
└── handlebar(ContextInfo) - 逐K线执行函数
    ├── 获取两个品种行情数据
    ├── 更新数据数组
    ├── 计算价比和指标
    ├── 判断开仓/平仓信号
    └── 执行交易订单
```

### init函数设计

```python
def init(ContextInfo):
    # 策略参数（从原策略移植）
    ContextInfo.N = 2          # 指标周期
    ContextInfo.M = 5          # 平滑周期
    ContextInfo.X = 5          # MA周期
    ContextInfo.TRS = 5        # 止损参数（千分比）
    ContextInfo.fixed_size = 1 # 固定手数
    
    # 数据容器（用于存储历史数据）
    ContextInfo.close_1 = []   # 品种1收盘价数组
    ContextInfo.close_2 = []   # 品种2收盘价数组
    ContextInfo.open_1 = []    # 品种1开盘价数组
    ContextInfo.open_2 = []    # 品种2开盘价数组
    ContextInfo.high_1 = []    # 品种1最高价数组
    ContextInfo.high_2 = []    # 品种2最高价数组
    ContextInfo.low_1 = []     # 品种1最低价数组
    ContextInfo.low_2 = []     # 品种2最低价数组
    
    # 状态变量
    ContextInfo.KG = 0              # 持仓状态（1做多，-1做空，0空仓）
    ContextInfo.high_after_entry = 0  # 入场后最高价
    ContextInfo.low_after_entry = 0   # 入场后最低价
    ContextInfo.curbar_h = 0          # 金叉发生位置
    ContextInfo.curbar_l = 0          # 死叉发生位置
    ContextInfo.current_bar = 0       # K线计数器
```

### handlebar函数设计

```python
def handlebar(ContextInfo):
    # 1. 获取行情数据（两个品种）
    # 通过ContextInfo获取当前K线的开高低收价格
    
    # 2. 更新数据数组
    ContextInfo.current_bar += 1
    
    # 3. 计算价比序列
    c_jb = np.array(ContextInfo.close_1) / np.array(ContextInfo.close_2)
    copen = np.array(ContextInfo.open_1) / np.array(ContextInfo.open_2)
    chigh = np.maximum(np.maximum(np.array(ContextInfo.high_1) / np.array(ContextInfo.high_2), copen), c_jb)
    clow = np.minimum(np.minimum(np.array(ContextInfo.low_1) / np.array(ContextInfo.low_2), copen), c_jb)
    
    # 4. 计算指标（保留原策略逻辑）
    var1 = highest(chigh, N) - lowest(clow, N)
    var2 = highest(chigh, N) - c_jb[-N:]
    var3 = c_jb[-N:] - lowest(clow, N)
    # ... 其他指标计算 ...
    bd1 = xaverage((var6[-M:] - var8) / (vara - var8) * 100, M)
    bd2 = xaverage(bd1, X)
    ma1 = xaverage(c_jb, X)
    
    # 5. 判断金叉死叉
    dk_up = bd1[-1] > bd2[-1] and bd1[-2] <= bd2[-1]  # 金叉
    kk_dn = bd1[-1] < bd2[-1] and bd1[-2] >= bd2[-1]  # 死叉
    
    # 6. 计算开仓条件
    cond_dk = (bd1[-1] > bd2[-1]) and (chigh[-1] >= Highup) and (c_jb[-1] > ma1[-1])
    cond_kk = (bd1[-1] < bd2[-1]) and (clow[-1] <= Lowdown) and (c_jb[-1] < ma1[-1])
    
    # 7. 执行交易（使用iQuant接口）
    # 获取当前持仓
    pos_1 = ContextInfo.get_position(symbol_1)
    pos_2 = ContextInfo.get_position(symbol_2)
    
    # 开多仓
    if cond_dk and KG == 0:
        ContextInfo.order_buy(symbol_1, price, fixed_size)   # 品种1买入
        ContextInfo.order_sell(symbol_2, price, fixed_size)  # 品种2卖出
        KG = 1
    
    # 开空仓
    if cond_kk and KG == 0:
        ContextInfo.order_sell(symbol_1, price, fixed_size)  # 品种1卖出
        ContextInfo.order_buy(symbol_2, price, fixed_size)   # 品种2买入
        KG = -1
    
    # 8. 止损止盈
    # 计算移动止损价位并执行平仓
```

## 实现要点

### 关键技术决策
1. **数据管理**：使用列表存储历史K线数据，替代vnpy的ArrayManager
2. **指标计算**：保留numpy实现，确保计算精度和性能
3. **持仓管理**：使用ContextInfo.get_position获取持仓，支持多品种
4. **订单执行**：使用iQuant标准接口order_buy/order_sell

### 技术难点
1. **品种配置**：需要在iQuant终端配置两个交易品种
2. **数据同步**：确保两个品种K线数据对齐（时间戳匹配）
3. **持仓对冲**：确保两个品种持仓方向相反、数量相等

### 依赖
- **numpy**：数值计算（项目已有）
- **iQuant平台**：ContextInfo接口（平台提供）

## 约束一致性

本方案与`.codeartsdoer/specs/global/constraints.md`中架构约束的一致性：

1. **编码规范**：使用`#coding:gbk`声明 ✅
2. **策略接口**：实现`init(ContextInfo)`和`handlebar(ContextInfo)` ✅
3. **目录结构**：策略文件放置在`python/`目录 ✅
4. **命名规范**：函数小写+下划线，类大驼峰 ✅
5. **禁止修改**：不修改luaScripts/、userdata/等保护目录 ✅
6. **未来函数禁令**：所有数据读取使用已确认K线 ✅
7. **风控不可绕过**：保留止损逻辑 ✅

## 验收标准
- [ ] 策略文件包含`#coding:gbk`编码声明
- [ ] 实现`init(ContextInfo)`初始化函数
- [ ] 实现`handlebar(ContextInfo)`逐K线执行函数
- [ ] 保留原策略所有指标计算逻辑（highest/lowest/sma/xaverage）
- [ ] 使用iQuant接口替换vnpy接口（get_market_data、order_buy、order_sell）
- [ ] 策略文件放置在`python/`目录
- [ ] 策略头注释符合规范（策略名称、类型、核心指标、交易逻辑、风控方式、最后修改）
- [ ] 代码通过Python语法检查（无语法错误）
- [ ] 不引入未来函数（所有数据读取使用已确认K线）
- [ ] 包含止损止盈逻辑