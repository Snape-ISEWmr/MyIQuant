#coding:gbk
#! /usr/bin/python 
# 
# 策略名称: 沪铜跨期正套
# 策略类型: 套利策略
# 核心指标: 布林带(BOLL), 近远月价差
# 交易逻辑: 价差突破布林带下轨→买近卖远(正套做多价差); 价差突破布林带上轨→卖近买远(反套做空价差)
# 风控方式: 浮亏15%减仓 + 浮亏25%全平 + 保证金上限15%
# 最后修改: 2026-07-01 初始版本
#

import numpy as np


def init(ContextInfo):
    ContextInfo.symbol_near = 'cu2609.SHF'
    ContextInfo.symbol_far = 'cu2701.SHF'
    ContextInfo.accID = account
    ContextInfo.set_account(ContextInfo.accID)
    ContextInfo.set_universe([ContextInfo.symbol_near, ContextInfo.symbol_far])

    ContextInfo.boll_period = 20
    ContextInfo.boll_std = 1.5
    ContextInfo.total_capital = 150000
    ContextInfo.max_margin_pct = 0.15
    ContextInfo.stop_loss_pct = 0.25
    ContextInfo.reduce_pos_pct = 0.15
    ContextInfo.batch_count = 2
    ContextInfo.fixed_size = 1

    ContextInfo.spread_history = []
    ContextInfo.position_state = 0
    ContextInfo.entry_spread = 0
    ContextInfo.entry_price_near = 0
    ContextInfo.entry_price_far = 0
    ContextInfo.entry_volume = 0
    ContextInfo.batch_filled = 0

    print("沪铜跨期正套策略初始化完成")


def handlebar(ContextInfo):
    result = ContextInfo.get_market_data_ex(
        fields=['close'],
        stock_code=[ContextInfo.symbol_near, ContextInfo.symbol_far],
        period=ContextInfo.period,
        count=ContextInfo.boll_period + 10,
        dividend_type='follow'
    )

    if ContextInfo.symbol_near not in result or ContextInfo.symbol_far not in result:
        return

    df_near = result[ContextInfo.symbol_near]
    df_far = result[ContextInfo.symbol_far]

    if df_near.empty or df_far.empty or len(df_near) < ContextInfo.boll_period or len(df_far) < ContextInfo.boll_period:
        return

    close_near = df_near['close'].values
    close_far = df_far['close'].values

    min_len = min(len(close_near), len(close_far))
    close_near = close_near[-min_len:]
    close_far = close_far[-min_len:]

    if len(close_near) < ContextInfo.boll_period:
        return

    price_near_now = float(close_near[-1])
    price_far_now = float(close_far[-1])

    if price_near_now <= 0 or price_far_now <= 0:
        return

    spread = close_near - close_far
    ContextInfo.spread_history.append(float(spread[-1]))

    if len(spread) < ContextInfo.boll_period:
        return

    spread_slice = spread[-ContextInfo.boll_period:]
    ma = np.mean(spread_slice)
    std = np.std(spread_slice)
    upper = ma + ContextInfo.boll_std * std
    lower = ma - ContextInfo.boll_std * std
    current_spread = float(spread[-1])

    inst_near = ContextInfo.get_instrumentdetail(ContextInfo.symbol_near)
    inst_far = ContextInfo.get_instrumentdetail(ContextInfo.symbol_far)

    if not inst_near or not inst_far:
        return

    multiplier_near = int(inst_near.get('VolumeMultiple', 5))
    multiplier_far = int(inst_far.get('VolumeMultiple', 5))
    margin_ratio_near_long = float(inst_near.get('LongMarginRatio', 0.10))
    margin_ratio_near_short = float(inst_near.get('ShortMarginRatio', 0.10))
    margin_ratio_far_long = float(inst_far.get('LongMarginRatio', 0.10))
    margin_ratio_far_short = float(inst_far.get('ShortMarginRatio', 0.10))

    max_margin = ContextInfo.total_capital * ContextInfo.max_margin_pct
    margin_per_lot_near = price_near_now * multiplier_near * max(margin_ratio_near_long, margin_ratio_near_short)
    margin_per_lot_far = price_far_now * multiplier_far * max(margin_ratio_far_long, margin_ratio_far_short)
    margin_per_pair = margin_per_lot_near + margin_per_lot_far
    max_volume = int(max_margin / margin_per_pair) if margin_per_pair > 0 else 1
    max_volume = max(1, min(max_volume, 10))

    target_volume = max_volume // ContextInfo.batch_count if ContextInfo.batch_count > 0 else max_volume
    target_volume = max(1, target_volume)

    from iQuant_functools import Account, Query_Details
    acc = Account(ContextInfo.accID, 'FUTURE')
    detail_func = ContextInfo.get_detail_data
    query = Query_Details(acc, [detail_func, detail_func, detail_func], ContextInfo)

    pos_near = query.get_total_holding(ContextInfo.symbol_near)
    pos_far = query.get_total_holding(ContextInfo.symbol_far)

    remark = '沪铜跨期正套'

    if ContextInfo.position_state == 0:
        if current_spread < lower:
            ContextInfo.position_state = 1
            ContextInfo.entry_spread = current_spread
            ContextInfo.entry_price_near = price_near_now
            ContextInfo.entry_price_far = price_far_now
            ContextInfo.entry_volume = target_volume
            ContextInfo.batch_filled = 1

            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            print("正套开仓: 买近卖远 %d手, 价差=%.0f" % (target_volume, current_spread))

        elif current_spread > upper:
            ContextInfo.position_state = -1
            ContextInfo.entry_spread = current_spread
            ContextInfo.entry_price_near = price_near_now
            ContextInfo.entry_price_far = price_far_now
            ContextInfo.entry_volume = target_volume
            ContextInfo.batch_filled = 1

            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            print("反套开仓: 卖近买远 %d手, 价差=%.0f" % (target_volume, current_spread))

    elif ContextInfo.position_state == 1:
        if ContextInfo.batch_filled < ContextInfo.batch_count and current_spread < lower:
            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            ContextInfo.batch_filled += 1
            ContextInfo.entry_volume += target_volume
            print("加仓正套第%d批 %d手" % (ContextInfo.batch_filled, target_volume))

        if current_spread >= ma:
            close_vol = ContextInfo.entry_volume
            if close_vol > 0:
                passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                print("正套平仓: 价差回归中轨 %.0f" % current_spread)
            ContextInfo.position_state = 0
            ContextInfo.entry_volume = 0
            ContextInfo.batch_filled = 0

        elif ContextInfo.entry_spread != 0:
            if ContextInfo.entry_spread > 0:
                pnl_pct = (current_spread - ContextInfo.entry_spread) / abs(ContextInfo.entry_spread)
            else:
                pnl_pct = (current_spread - ContextInfo.entry_spread) / (abs(ContextInfo.entry_spread) + 1)

            if pnl_pct <= -ContextInfo.reduce_pos_pct and ContextInfo.entry_volume > 1:
                reduce_vol = ContextInfo.entry_volume // 2
                if reduce_vol > 0:
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    ContextInfo.entry_volume -= reduce_vol
                    print("减仓: 浮亏%.1f%%, 减仓%d手" % (pnl_pct * 100, reduce_vol))

            if pnl_pct <= -ContextInfo.stop_loss_pct:
                close_vol = ContextInfo.entry_volume
                if close_vol > 0:
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    print("止损全平: 浮亏%.1f%%" % (pnl_pct * 100))
                ContextInfo.position_state = 0
                ContextInfo.entry_volume = 0
                ContextInfo.batch_filled = 0

    elif ContextInfo.position_state == -1:
        if ContextInfo.batch_filled < ContextInfo.batch_count and current_spread > upper:
            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            ContextInfo.batch_filled += 1
            ContextInfo.entry_volume += target_volume
            print("加仓反套第%d批 %d手" % (ContextInfo.batch_filled, target_volume))

        if current_spread <= ma:
            close_vol = ContextInfo.entry_volume
            if close_vol > 0:
                passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                print("反套平仓: 价差回归中轨 %.0f" % current_spread)
            ContextInfo.position_state = 0
            ContextInfo.entry_volume = 0
            ContextInfo.batch_filled = 0

        elif ContextInfo.entry_spread != 0:
            if ContextInfo.entry_spread > 0:
                pnl_pct = (ContextInfo.entry_spread - current_spread) / abs(ContextInfo.entry_spread)
            else:
                pnl_pct = (ContextInfo.entry_spread - current_spread) / (abs(ContextInfo.entry_spread) + 1)

            if pnl_pct <= -ContextInfo.reduce_pos_pct and ContextInfo.entry_volume > 1:
                reduce_vol = ContextInfo.entry_volume // 2
                if reduce_vol > 0:
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    ContextInfo.entry_volume -= reduce_vol
                    print("减仓: 浮亏%.1f%%, 减仓%d手" % (pnl_pct * 100, reduce_vol))

            if pnl_pct <= -ContextInfo.stop_loss_pct:
                close_vol = ContextInfo.entry_volume
                if close_vol > 0:
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_near, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_far, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    print("止损全平: 浮亏%.1f%%" % (pnl_pct * 100))
                ContextInfo.position_state = 0
                ContextInfo.entry_volume = 0
                ContextInfo.batch_filled = 0