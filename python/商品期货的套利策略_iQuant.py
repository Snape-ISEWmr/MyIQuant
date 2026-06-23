#coding:gbk
# 
# 策略名称: 商品期货跨品种套利策略（iQuant版）
# 策略类型: 套利策略
# 核心指标: 价差比率、BD1/BD2、SMA、highest/lowest
# 交易逻辑: BD1金叉且价差突破前高→开多（品种1买+品种2卖）；BD1死叉且价差跌破前低→开空（品种1卖+品种2买）
# 风控方式: 移动止损（TRS参数控制）
# 最后修改: 2026-06-23 从vnpy版本转换为iQuant适配版本
#

import numpy as np


def highest(data, period):
    """
    计算序列最后 period 个元素中的最高值，返回一个序列
    :param data: 数据序列
    :param period: 周期
    :return: 最后 period 个元素中的最高值序列
    """
    result = []
    start_index = max(0, len(data) - period)
    
    for i in range(start_index, len(data)):
        result.append(max(data[max(0, i - period + 1):i + 1]))
    
    return np.array(result)


def lowest(data, period):
    """
    计算序列最后 period 个元素中的最小值，返回一个序列
    :param data: 数据序列
    :param period: 周期
    :return: 最后 period 个元素中的最小值序列
    """
    result = []
    start_index = max(0, len(data) - period)
    
    for i in range(start_index, len(data)):
        result.append(min(data[max(0, i - period + 1):i + 1]))
    
    return np.array(result)


def sma(data, period, weight=1):
    """
    计算简单移动平均（SMA）的序列，仅计算最后 period 个元素
    :param data: 数据序列
    :param period: 周期
    :param weight: 权重
    :return: SMA序列
    """
    if len(data) < period:
        return np.convolve(data, np.ones((len(data),))/len(data), mode='valid')
    else:
        return np.convolve(data[-period:], np.ones((period,))/period, mode='valid')


def xaverage(data, period):
    """
    计算加权平均（WMA）的序列
    :param data: 数据序列
    :param period: 周期
    :return: WMA序列
    """
    if len(data) < period:
        weights = np.arange(1, len(data) + 1)
        return np.convolve(data, weights/weights.sum(), mode='full')[-len(data):]
    else:
        weights = np.arange(1, period + 1)
        return np.convolve(data[-period:], weights/weights.sum(), mode='full')[-period:]


def init(ContextInfo):
    """
    策略初始化函数
    """
    # 策略参数（从原vnpy策略移植）
    ContextInfo.N = 2          # 指标周期
    ContextInfo.M = 5          # 平滑周期
    ContextInfo.X = 5          # MA周期
    ContextInfo.TRS = 5        # 止损参数（千分比）
    ContextInfo.fixed_size = 1 # 固定手数
    
    # 数据容器（用于存储历史K线数据）
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
    ContextInfo.dliq_point = 0        # 多头止损价位
    ContextInfo.kliq_point = 0        # 空头止损价位
    ContextInfo.curbar_h = 0          # 金叉发生位置
    ContextInfo.curbar_l = 0          # 死叉发生位置
    ContextInfo.current_bar = 0       # K线计数器
    
    print("商品期货跨品种套利策略初始化完成")


def handlebar(ContextInfo):
    """
    逐K线执行函数
    """
    # 获取两个品种的行情数据
    # 假设用户在iQuant终端配置了两个品种：stockcode为品种1，第二个品种通过参数传入
    # 这里需要根据实际iQuant配置调整品种代码获取方式
    
    # 获取品种1数据（当前策略绑定的品种）
    symbol_1 = ContextInfo.stockcode + '.' + ContextInfo.market
    close_1 = ContextInfo.get_market_data([[symbol_1], [ContextInfo.barpos], [5]])  # 5=收盘价
    open_1 = ContextInfo.get_market_data([[symbol_1], [ContextInfo.barpos], [4]])   # 4=开盘价
    high_1 = ContextInfo.get_market_data([[symbol_1], [ContextInfo.barpos], [6]])   # 6=最高价
    low_1 = ContextInfo.get_market_data([[symbol_1], [ContextInfo.barpos], [7]])    # 7=最低价
    
    # 获取品种2数据（需要用户配置第二个品种代码）
    # 建议在策略参数中配置symbol_2，或通过ContextInfo.get_other_stock获取
    # 这里假设用户在策略属性中设置了symbol_2参数
    if not hasattr(ContextInfo, 'symbol_2'):
        print("请在策略属性中配置symbol_2参数（第二个品种代码）")
        return
    
    symbol_2 = ContextInfo.symbol_2
    close_2 = ContextInfo.get_market_data([[symbol_2], [ContextInfo.barpos], [5]])
    open_2 = ContextInfo.get_market_data([[symbol_2], [ContextInfo.barpos], [4]])
    high_2 = ContextInfo.get_market_data([[symbol_2], [ContextInfo.barpos], [6]])
    low_2 = ContextInfo.get_market_data([[symbol_2], [ContextInfo.barpos], [7]])
    
    # 检查数据有效性
    if close_1 is None or close_2 is None or close_1 <= 0 or close_2 <= 0:
        return
    
    # 更新数据数组
    ContextInfo.close_1.append(close_1)
    ContextInfo.close_2.append(close_2)
    ContextInfo.open_1.append(open_1)
    ContextInfo.open_2.append(open_2)
    ContextInfo.high_1.append(high_1)
    ContextInfo.high_2.append(high_2)
    ContextInfo.low_1.append(low_1)
    ContextInfo.low_2.append(low_2)
    
    ContextInfo.current_bar += 1
    
    # 数据不足时跳过
    if len(ContextInfo.close_1) < max(ContextInfo.N, ContextInfo.M, ContextInfo.X) + 10:
        return
    
    # 转换为numpy数组
    close_arr_1 = np.array(ContextInfo.close_1)
    close_arr_2 = np.array(ContextInfo.close_2)
    open_arr_1 = np.array(ContextInfo.open_1)
    open_arr_2 = np.array(ContextInfo.open_2)
    high_arr_1 = np.array(ContextInfo.high_1)
    high_arr_2 = np.array(ContextInfo.high_2)
    low_arr_1 = np.array(ContextInfo.low_1)
    low_arr_2 = np.array(ContextInfo.low_2)
    
    # 计算价比序列
    c_jb = close_arr_1 / close_arr_2   # 收盘价比
    copen = open_arr_1 / open_arr_2    # 开盘价比
    chigh = np.maximum(np.maximum(high_arr_1 / high_arr_2, copen), c_jb)  # 最高价比
    clow = np.minimum(np.minimum(low_arr_1 / low_arr_2, copen), c_jb)     # 最低价比
    
    # 计算多个指标的序列
    var1 = highest(chigh, ContextInfo.N) - lowest(clow, ContextInfo.N)
    var2 = highest(chigh, ContextInfo.N) - c_jb[-ContextInfo.N:]
    var3 = c_jb[-ContextInfo.N:] - lowest(clow, ContextInfo.N)
    var4 = var2 / var1 * 100 - 70
    var5 = (c_jb[-ContextInfo.N:] - lowest(clow, ContextInfo.N)) / var1 * 100
    var6 = (2 * c_jb + chigh + clow) / 4
    var7 = sma(var3 / var1 * 100, 3, 1)
    var8 = lowest(clow, ContextInfo.M)
    var9 = sma(var7, 3, 1) - sma(var4, 9, 1)
    vara = highest(chigh, ContextInfo.M)
    bd1 = xaverage((var6[-ContextInfo.M:] - var8) / (vara - var8) * 100, ContextInfo.M)
    bd2 = xaverage(bd1, ContextInfo.X)
    ma1 = xaverage(c_jb, ContextInfo.X)
    
    # 检查金叉死叉
    dk_up = bd1[-1] > bd2[-1] and bd1[-2] <= bd2[-1]  # 金叉
    kk_dn = bd1[-1] < bd2[-1] and bd1[-2] >= bd2[-1]  # 死叉
    
    # 计算Highup和Lowdown
    if dk_up:
        ContextInfo.curbar_h = ContextInfo.current_bar
        period = max(ContextInfo.curbar_h - ContextInfo.curbar_l, ContextInfo.M)
        if len(chigh) >= period:
            Highup = max(chigh[-period:-1])
        else:
            Highup = max(chigh[-ContextInfo.M:-1])
    else:
        Highup = max(chigh[-ContextInfo.M:-1])
    
    if kk_dn:
        ContextInfo.curbar_l = ContextInfo.current_bar
        period = max(ContextInfo.curbar_l - ContextInfo.curbar_h, ContextInfo.M)
        if len(clow) >= period:
            Lowdown = min(clow[-period:-1])
        else:
            Lowdown = min(clow[-ContextInfo.M:-1])
    else:
        Lowdown = min(clow[-ContextInfo.M:-1])
    
    # 开仓条件
    cond_dk = (bd1[-1] > bd2[-1]) and (chigh[-1] >= Highup) and (c_jb[-1] > ma1[-1])
    cond_kk = (bd1[-1] < bd2[-1]) and (clow[-1] <= Lowdown) and (c_jb[-1] < ma1[-1])
    
    # 更新持仓状态
    if cond_dk:
        ContextInfo.KG = 1
    elif cond_kk:
        ContextInfo.KG = -1
    
    # 获取当前持仓
    pos_1 = ContextInfo.get_position(symbol_1)
    pos_2 = ContextInfo.get_position(symbol_2)
    
    # 执行开仓交易
    # 品种1
    if ContextInfo.KG > 0:  # 做多信号
        if pos_1 < 0:  # 持有空头，先平仓再开多
            ContextInfo.order_buy(symbol_1, close_1, abs(pos_1))  # 平空
            ContextInfo.order_buy(symbol_1, close_1, ContextInfo.fixed_size)  # 开多
            ContextInfo.low_after_entry = clow[-1]
        elif pos_1 == 0:  # 空仓，直接开多
            ContextInfo.order_buy(symbol_1, close_1, ContextInfo.fixed_size)
            ContextInfo.low_after_entry = clow[-1]
    elif ContextInfo.KG < 0:  # 做空信号
        if pos_1 > 0:  # 持有多头，先平仓再开空
            ContextInfo.order_sell(symbol_1, close_1, pos_1)  # 平多
            ContextInfo.order_sell(symbol_1, close_1, ContextInfo.fixed_size)  # 开空
            ContextInfo.high_after_entry = chigh[-1]
        elif pos_1 == 0:  # 空仓，直接开空
            ContextInfo.order_sell(symbol_1, close_1, ContextInfo.fixed_size)
            ContextInfo.high_after_entry = chigh[-1]
    
    # 品种2（对冲）
    if ContextInfo.KG > 0:  # 做多信号（品种1买，品种2卖）
        if pos_2 < 0:  # 持有空头，先平仓再开空
            ContextInfo.order_buy(symbol_2, close_2, abs(pos_2))  # 平空
            ContextInfo.order_sell(symbol_2, close_2, ContextInfo.fixed_size)  # 开空
            ContextInfo.high_after_entry = chigh[-1]
        elif pos_2 == 0:  # 空仓，直接开空
            ContextInfo.order_sell(symbol_2, close_2, ContextInfo.fixed_size)
            ContextInfo.high_after_entry = chigh[-1]
    elif ContextInfo.KG < 0:  # 做空信号（品种1卖，品种2买）
        if pos_2 > 0:  # 持有多头，先平仓再开多
            ContextInfo.order_sell(symbol_2, close_2, pos_2)  # 平多
            ContextInfo.order_buy(symbol_2, close_2, ContextInfo.fixed_size)  # 开多
            ContextInfo.low_after_entry = clow[-1]
        elif pos_2 == 0:  # 空仓，直接开多
            ContextInfo.order_buy(symbol_2, close_2, ContextInfo.fixed_size)
            ContextInfo.low_after_entry = clow[-1]
    
    # 移动止损计算
    if ContextInfo.KG == 0:
        ContextInfo.high_after_entry = chigh[-1]
        ContextInfo.low_after_entry = clow[-1]
    elif ContextInfo.KG != 0:
        ContextInfo.high_after_entry = min(ContextInfo.high_after_entry, chigh[-1])
        ContextInfo.low_after_entry = max(ContextInfo.low_after_entry, clow[-1])
    
    # 计算止损价位
    if ContextInfo.KG > 0:
        ContextInfo.dliq_point = ContextInfo.low_after_entry - (copen[-1] * ContextInfo.TRS / 1000)
    elif ContextInfo.KG < 0:
        ContextInfo.kliq_point = ContextInfo.high_after_entry + (copen[-1] * ContextInfo.TRS / 1000)
    
    # 执行止损平仓
    # 品种1
    if ContextInfo.KG > 0 and c_jb[-1] <= ContextInfo.dliq_point and ContextInfo.dliq_point > 0 and pos_1 > 0:
        ContextInfo.order_sell(symbol_1, close_1, pos_1)
    if ContextInfo.KG < 0 and c_jb[-1] >= ContextInfo.kliq_point and ContextInfo.kliq_point > 0 and pos_1 < 0:
        ContextInfo.order_buy(symbol_1, close_1, abs(pos_1))
    
    # 品种2
    if ContextInfo.KG > 0 and c_jb[-1] <= ContextInfo.dliq_point and ContextInfo.dliq_point > 0 and pos_2 < 0:
        ContextInfo.order_buy(symbol_2, close_2, abs(pos_2))
    if ContextInfo.KG < 0 and c_jb[-1] >= ContextInfo.kliq_point and ContextInfo.kliq_point > 0 and pos_2 > 0:
        ContextInfo.order_sell(symbol_2, close_2, pos_2)