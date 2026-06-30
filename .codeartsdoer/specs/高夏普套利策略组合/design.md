# 技术设计文档：高夏普套利策略组合

## 版本记录
| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-07-01 | 初始版本 |

## 一、架构设计

### 1.1 策略文件结构
每个套利策略独立为一个.py文件，放置在 `python/` 目录下：

```
python/
├── 豆油棕榈油跨品种套利.py      # 第一梯队-策略1
├── 豆粕菜粕跨品种套利.py        # 第一梯队-策略2
├── 沪铜跨期正套.py              # 第一梯队-策略3
├── 生猪跨期反套.py              # 第二梯队-策略4
├── 卷螺差套利.py                # 第二梯队-策略5
├── 烧碱跨期反套.py              # 第二梯队-策略6
```

### 1.2 代码结构模板
```python
#coding:gbk
#! /usr/bin/python 
# 
# 策略名称: <名称>
# 策略类型: 套利策略
# 核心指标: 布林带(BOLL), 价差/价比
# 交易逻辑: 价差突破布林带下轨→做多价差; 价差突破布林带上轨→做空价差
# 风控方式: 浮亏15%减仓 + 浮亏25%全平
# 最后修改: 2026-07-01 初始版本
#

import numpy as np

# 辅助函数
def calc_bollinger(data, period, num_std):
    ...

def init(ContextInfo):
    # 品种配置
    # 策略参数
    # 状态变量
    ...

def handlebar(ContextInfo):
    # 获取行情
    # 计算价差
    # 计算布林带
    # 开平仓逻辑
    # 风控逻辑
    ...
```

## 二、核心算法设计

### 2.1 价差计算
- **跨品种套利**：价比 = 品种1收盘价 / 品种2收盘价
- **跨期套利**：价差 = 近月收盘价 - 远月收盘价

### 2.2 布林带信号
```
中轨 = SMA(价差, period)
上轨 = 中轨 + num_std * STD(价差, period)
下轨 = 中轨 - num_std * STD(价差, period)

做多信号: 价差 < 下轨 (价差偏低，预期回归)
做空信号: 价差 > 上轨 (价差偏高，预期回归)
平多信号: 价差 >= 中轨
平空信号: 价差 <= 中轨
```

### 2.3 下单接口
使用iQuant标准期货下单接口 `passorder()`：
```python
# 买入开仓
passorder(0, 1102, accID, symbol, 5, -1, volume, remark, 1, remark, ContextInfo)
# 卖出开仓
passorder(1, 1102, accID, symbol, 5, -1, volume, remark, 1, remark, ContextInfo)
# 买入平仓
passorder(2, 1102, accID, symbol, 5, -1, volume, remark, 1, remark, ContextInfo)
# 卖出平仓
passorder(3, 1102, accID, symbol, 5, -1, volume, remark, 1, remark, ContextInfo)
```

passorder参数说明：
- opType: 0=买入开仓, 1=卖出开仓, 2=买入平仓, 3=卖出平仓
- orderType: 1102=限价单
- pricetype: 5=最新价
- modelprice: -1=自动获取

### 2.4 持仓查询
通过 `iQuant_functools.Query_Details` 获取持仓：
```python
from iQuant_functools import Account, Query_Details
account = Account(accID, 'FUTURE')
query = Query_Details(account, [detail_func, credit_fund_func, credit_stk_func], ContextInfo)
pos = query.get_total_holding(code)
```

### 2.5 保证金计算
```python
inst = ContextInfo.get_instrumentdetail(symbol)
margin_ratio = inst['LongMarginRatio']  # 或 'ShortMarginRatio'
multiplier = inst['VolumeMultiple']
margin = price * multiplier * margin_ratio * volume
```

## 三、各策略参数设计

### 3.1 豆油棕榈油跨品种套利
| 参数 | 值 | 说明 |
|------|-----|------|
| symbol_1 | y2609.DCE | 豆油2609 |
| symbol_2 | p2609.DCE | 棕榈油2609 |
| boll_period | 20 | 布林带周期 |
| boll_std | 2.0 | 布林带标准差倍数 |
| max_margin_pct | 0.15 | 保证金占比上限15% |
| stop_loss_pct | 0.25 | 止损比例25% |
| reduce_pos_pct | 0.15 | 减仓比例15% |
| batch_count | 2 | 分2批建仓 |

### 3.2 豆粕菜粕跨品种套利
| 参数 | 值 | 说明 |
|------|-----|------|
| symbol_1 | m2609.DCE | 豆粕2609 |
| symbol_2 | rm2609.CZCE | 菜粕2609 |
| boll_period | 20 | 布林带周期 |
| boll_std | 2.0 | 布林带标准差倍数 |
| max_margin_pct | 0.15 | 保证金占比上限15% |
| stop_loss_pct | 0.25 | 止损比例25% |
| reduce_pos_pct | 0.15 | 减仓比例15% |
| batch_count | 2 | 分2批建仓 |

### 3.3 沪铜跨期正套
| 参数 | 值 | 说明 |
|------|-----|------|
| symbol_1 | cu2609.SHF | 沪铜2609（近月） |
| symbol_2 | cu2701.SHF | 沪铜2701（远月） |
| boll_period | 20 | 布林带周期 |
| boll_std | 1.5 | 布林带标准差倍数（跨期波动更小） |
| max_margin_pct | 0.15 | 保证金占比上限15% |
| stop_loss_pct | 0.25 | 止损比例25% |
| reduce_pos_pct | 0.15 | 减仓比例15% |
| batch_count | 2 | 分2批建仓 |

### 3.4 生猪跨期反套
| 参数 | 值 | 说明 |
|------|-----|------|
| symbol_1 | lh2609.DCE | 生猪2609（近月） |
| symbol_2 | lh2701.DCE | 生猪2701（远月） |
| boll_period | 20 | 布林带周期 |
| boll_std | 2.5 | 布林带标准差倍数（波动更大） |
| max_margin_pct | 0.10 | 保证金占比上限10% |
| stop_loss_pct | 0.25 | 止损比例25% |
| reduce_pos_pct | 0.15 | 减仓比例15% |
| batch_count | 3 | 分3批建仓 |

### 3.5 卷螺差套利
| 参数 | 值 | 说明 |
|------|-----|------|
| symbol_1 | rb2609.SHF | 螺纹钢2609 |
| symbol_2 | hc2609.SHF | 热卷2609 |
| boll_period | 20 | 布林带周期 |
| boll_std | 2.0 | 布林带标准差倍数 |
| max_margin_pct | 0.10 | 保证金占比上限10% |
| stop_loss_pct | 0.25 | 止损比例25% |
| reduce_pos_pct | 0.15 | 减仓比例15% |
| batch_count | 3 | 分3批建仓 |

### 3.6 烧碱跨期反套
| 参数 | 值 | 说明 |
|------|-----|------|
| symbol_1 | sh2607.CZCE | 烧碱2607（近月） |
| symbol_2 | sh2608.CZCE | 烧碱2608（远月） |
| boll_period | 20 | 布林带周期 |
| boll_std | 2.0 | 布林带标准差倍数 |
| max_margin_pct | 0.10 | 保证金占比上限10% |
| stop_loss_pct | 0.25 | 止损比例25% |
| reduce_pos_pct | 0.15 | 减仓比例15% |
| batch_count | 3 | 分3批建仓 |

## 四、风控逻辑设计

### 4.1 仓位控制
```python
def calc_max_volume(ContextInfo, symbol, max_margin_pct):
    inst = ContextInfo.get_instrumentdetail(symbol)
    margin_ratio = float(inst['LongMarginRatio'])
    multiplier = int(inst['VolumeMultiple'])
    price = ContextInfo.get_market_data_ex(['close'], [symbol], 
             period=ContextInfo.period, count=1, dividend_type='follow')
    total_capital = 150000  # 总资金
    max_margin = total_capital * max_margin_pct
    max_vol = int(max_margin / (price * multiplier * margin_ratio))
    return max(1, max_vol)
```

### 4.2 浮亏止损
```python
# 计算浮亏比例
entry_cost = entry_price * multiplier * margin_ratio * volume
current_value = current_price * multiplier * margin_ratio * volume
pnl_pct = (current_value - entry_cost) / entry_cost

if pnl_pct <= -reduce_pos_pct:  # -15%减仓
    close_volume = volume // 2
if pnl_pct <= -stop_loss_pct:   # -25%全平
    close_volume = volume
```

## 五、接口映射

| 功能 | 接口 | 说明 |
|------|------|------|
| 获取行情 | ContextInfo.get_market_data_ex() | 返回pd.DataFrame |
| 买入开仓 | passorder(0, 1102, ...) | opType=0 |
| 卖出开仓 | passorder(1, 1102, ...) | opType=1 |
| 买入平仓 | passorder(2, 1102, ...) | opType=2 |
| 卖出平仓 | passorder(3, 1102, ...) | opType=3 |
| 查询持仓 | iQuant_functools.Query_Details | get_total_holding() |
| 合约信息 | ContextInfo.get_instrumentdetail() | 保证金比例/乘数 |
| 合约乘数 | ContextInfo.get_contract_multiplier() | 独立获取乘数 |