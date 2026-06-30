#coding:gbk
#! /usr/bin/python 
# 
# 策略名称: 豆粕菜粕跨品种套利
# 策略类型: 套利策略
# 核心指标: 布林带(BOLL), 价比
# 交易逻辑: 价比突破布林带下轨→多豆粕空菜粕(做多价差); 价比突破布林带上轨→空豆粕多菜粕(做空价差)
# 风控方式: 浮亏15%减仓 + 浮亏25%全平 + 保证金上限15%
# 最后修改: 2026-07-01 初始版本
#

import numpy as np


def init(ContextInfo):
    ContextInfo.symbol_1 = 'm2609.DCE'
    ContextInfo.symbol_2 = 'rm2609.CZCE'
    ContextInfo.accID = account
    ContextInfo.set_account(ContextInfo.accID)
    ContextInfo.set_universe([ContextInfo.symbol_1, ContextInfo.symbol_2])

    ContextInfo.boll_period = 20
    ContextInfo.boll_std = 2.0
    ContextInfo.total_capital = 150000
    ContextInfo.max_margin_pct = 0.15
    ContextInfo.stop_loss_pct = 0.25
    ContextInfo.reduce_pos_pct = 0.15
    ContextInfo.batch_count = 2
    ContextInfo.fixed_size = 1

    ContextInfo.spread_history = []
    ContextInfo.position_state = 0
    ContextInfo.entry_spread = 0
    ContextInfo.entry_price_1 = 0
    ContextInfo.entry_price_2 = 0
    ContextInfo.entry_volume = 0
    ContextInfo.batch_filled = 0

    print("豆粕菜粕跨品种套利策略初始化完成")


def handlebar(ContextInfo):
    result = ContextInfo.get_market_data_ex(
        fields=['close'],
        stock_code=[ContextInfo.symbol_1, ContextInfo.symbol_2],
        period=ContextInfo.period,
        count=ContextInfo.boll_period + 10,
        dividend_type='follow'
    )

    if ContextInfo.symbol_1 not in result or ContextInfo.symbol_2 not in result:
        return

    df1 = result[ContextInfo.symbol_1]
    df2 = result[ContextInfo.symbol_2]

    if df1.empty or df2.empty or len(df1) < ContextInfo.boll_period or len(df2) < ContextInfo.boll_period:
        return

    close_1 = df1['close'].values
    close_2 = df2['close'].values

    min_len = min(len(close_1), len(close_2))
    close_1 = close_1[-min_len:]
    close_2 = close_2[-min_len:]

    if len(close_1) < ContextInfo.boll_period:
        return

    price_1_now = float(close_1[-1])
    price_2_now = float(close_2[-1])

    if price_1_now <= 0 or price_2_now <= 0:
        return

    spread = close_1 / close_2
    ContextInfo.spread_history.append(float(spread[-1]))

    if len(spread) < ContextInfo.boll_period:
        return

    spread_slice = spread[-ContextInfo.boll_period:]
    ma = np.mean(spread_slice)
    std = np.std(spread_slice)
    upper = ma + ContextInfo.boll_std * std
    lower = ma - ContextInfo.boll_std * std
    current_spread = float(spread[-1])

    inst1 = ContextInfo.get_instrumentdetail(ContextInfo.symbol_1)
    inst2 = ContextInfo.get_instrumentdetail(ContextInfo.symbol_2)

    if not inst1 or not inst2:
        return

    multiplier_1 = int(inst1.get('VolumeMultiple', 10))
    multiplier_2 = int(inst2.get('VolumeMultiple', 10))
    margin_ratio_1_long = float(inst1.get('LongMarginRatio', 0.08))
    margin_ratio_1_short = float(inst1.get('ShortMarginRatio', 0.08))
    margin_ratio_2_long = float(inst2.get('LongMarginRatio', 0.08))
    margin_ratio_2_short = float(inst2.get('ShortMarginRatio', 0.08))

    max_margin = ContextInfo.total_capital * ContextInfo.max_margin_pct
    margin_per_lot_1 = price_1_now * multiplier_1 * max(margin_ratio_1_long, margin_ratio_1_short)
    margin_per_lot_2 = price_2_now * multiplier_2 * max(margin_ratio_2_long, margin_ratio_2_short)
    margin_per_pair = margin_per_lot_1 + margin_per_lot_2
    max_volume = int(max_margin / margin_per_pair) if margin_per_pair > 0 else 1
    max_volume = max(1, min(max_volume, 10))

    target_volume = max_volume // ContextInfo.batch_count if ContextInfo.batch_count > 0 else max_volume
    target_volume = max(1, target_volume)

    from iQuant_functools import Account, Query_Details
    acc = Account(ContextInfo.accID, 'FUTURE')
    detail_func = ContextInfo.get_detail_data
    query = Query_Details(acc, [detail_func, detail_func, detail_func], ContextInfo)

    pos_1 = query.get_total_holding(ContextInfo.symbol_1)
    pos_2 = query.get_total_holding(ContextInfo.symbol_2)

    remark = '豆粕菜粕套利'

    if ContextInfo.position_state == 0:
        if current_spread < lower:
            ContextInfo.position_state = 1
            ContextInfo.entry_spread = current_spread
            ContextInfo.entry_price_1 = price_1_now
            ContextInfo.entry_price_2 = price_2_now
            ContextInfo.entry_volume = target_volume
            ContextInfo.batch_filled = 1

            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            print("做多价差: 多豆粕空菜粕 %d手, 价比=%.4f" % (target_volume, current_spread))

        elif current_spread > upper:
            ContextInfo.position_state = -1
            ContextInfo.entry_spread = current_spread
            ContextInfo.entry_price_1 = price_1_now
            ContextInfo.entry_price_2 = price_2_now
            ContextInfo.entry_volume = target_volume
            ContextInfo.batch_filled = 1

            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            print("做空价差: 空豆粕多菜粕 %d手, 价比=%.4f" % (target_volume, current_spread))

    elif ContextInfo.position_state == 1:
        if ContextInfo.batch_filled < ContextInfo.batch_count and current_spread < lower:
            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            ContextInfo.batch_filled += 1
            ContextInfo.entry_volume += target_volume
            print("加仓做多价差第%d批 %d手" % (ContextInfo.batch_filled, target_volume))

        if current_spread >= ma:
            close_vol = ContextInfo.entry_volume
            if close_vol > 0:
                passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                print("平多价差: 价比回归中轨 %.4f" % current_spread)
            ContextInfo.position_state = 0
            ContextInfo.entry_volume = 0
            ContextInfo.batch_filled = 0

        elif ContextInfo.entry_spread > 0:
            pnl_pct = (current_spread - ContextInfo.entry_spread) / ContextInfo.entry_spread
            if pnl_pct <= -ContextInfo.reduce_pos_pct and ContextInfo.entry_volume > 1:
                reduce_vol = ContextInfo.entry_volume // 2
                if reduce_vol > 0:
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    ContextInfo.entry_volume -= reduce_vol
                    print("减仓: 浮亏%.1f%%, 减仓%d手" % (pnl_pct * 100, reduce_vol))

            if pnl_pct <= -ContextInfo.stop_loss_pct:
                close_vol = ContextInfo.entry_volume
                if close_vol > 0:
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    print("止损全平: 浮亏%.1f%%" % (pnl_pct * 100))
                ContextInfo.position_state = 0
                ContextInfo.entry_volume = 0
                ContextInfo.batch_filled = 0

    elif ContextInfo.position_state == -1:
        if ContextInfo.batch_filled < ContextInfo.batch_count and current_spread > upper:
            passorder(1, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            passorder(0, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, target_volume, remark, 1, remark, ContextInfo)
            ContextInfo.batch_filled += 1
            ContextInfo.entry_volume += target_volume
            print("加仓做空价差第%d批 %d手" % (ContextInfo.batch_filled, target_volume))

        if current_spread <= ma:
            close_vol = ContextInfo.entry_volume
            if close_vol > 0:
                passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                print("平空价差: 价比回归中轨 %.4f" % current_spread)
            ContextInfo.position_state = 0
            ContextInfo.entry_volume = 0
            ContextInfo.batch_filled = 0

        elif ContextInfo.entry_spread > 0:
            pnl_pct = (ContextInfo.entry_spread - current_spread) / ContextInfo.entry_spread
            if pnl_pct <= -ContextInfo.reduce_pos_pct and ContextInfo.entry_volume > 1:
                reduce_vol = ContextInfo.entry_volume // 2
                if reduce_vol > 0:
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, reduce_vol, remark, 1, remark, ContextInfo)
                    ContextInfo.entry_volume -= reduce_vol
                    print("减仓: 浮亏%.1f%%, 减仓%d手" % (pnl_pct * 100, reduce_vol))

            if pnl_pct <= -ContextInfo.stop_loss_pct:
                close_vol = ContextInfo.entry_volume
                if close_vol > 0:
                    passorder(2, 1102, ContextInfo.accID, ContextInfo.symbol_1, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    passorder(3, 1102, ContextInfo.accID, ContextInfo.symbol_2, 5, -1, close_vol, remark, 1, remark, ContextInfo)
                    print("止损全平: 浮亏%.1f%%" % (pnl_pct * 100))
                ContextInfo.position_state = 0
                ContextInfo.entry_volume = 0
                ContextInfo.batch_filled = 0