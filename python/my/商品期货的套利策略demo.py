from typing import List, Dict
from datetime import datetime

from vnpy_portfoliostrategy import (
    StrategyEngine,
    StrategyTemplate,
    TickData,
    BarData,
    TradeData,
    ArrayManager,
)

from vnpy.trader.utility import Interval
from vnpy_portfoliostrategy.utility import PortfolioBarGenerator
import numpy as np
import talib as ta


class vProfit(StrategyTemplate):
    """"""

    author = "www"
    
    N = 2
    M = 5
    X = 5
    TRS=5
    
    fixed_size=1
    
    am_1=0
    am_2=0
    current_bar=0
    
    parameters = [
        "N",
        "M",
        "X",
        "fixed_size",
        "TRS"
    ]
    variables = []

    def __init__(
        self,
        strategy_engine: StrategyEngine,
        strategy_name: str,
        vt_symbols: List[str],
        setting: dict
    ):
        """"""
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)

        self.KG=0
        self.high_after_entry=0
        self.low_after_entry=0
        self.dliq_point=0
        self.kliq_point=0
        self.curbar_h = np.zeros(100)  # 例如，初始化为长度为 100 的数组
        self.curbar_l = np.zeros(100)
        # 初始化 hd 属性
        self.hd = np.zeros(100)  # 例如，初始化为长度为 100 的数组
        self.ld = np.zeros(100)  # 例如，初始化为长度为 100 的数组
        self.targets: Dict[str, int] = {}
        self.last_tick_time: datetime = None

        # Obtain contract info
        self.ams: Dict[str, ArrayManager] = {}
        for vt_symbol in self.vt_symbols:
            self.ams[vt_symbol] = ArrayManager(100)
            self.targets[vt_symbol] = 0

        self.pbg = PortfolioBarGenerator(self.on_bars, 2, self.on_2hour_bars, Interval.HOUR)

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")

        self.load_bars(10)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.pbg.update_tick(tick)

    def on_bars(self, bars: Dict[str, BarData]):
        """
        Callback of new bars data update.
        """
        self.pbg.update_bars(bars)

      
    def on_2hour_bars(self, bars: Dict[str, BarData]):
        """"""
        self.cancel_all()
        # 初始化
        nx = 0

        # 获取合约的数据
        for vt_symbol, bar in bars.items():
            nx += 1
            # 更新 ArrayManager
            am: ArrayManager = self.ams[vt_symbol]
            am.update_bar(bar)
            #print(vt_symbol)
            # 如果 ArrayManager 还未初始化完毕，则跳过
            if not am.inited:
                return
            # 将第一个和第二个合约的 ArrayManager 分别保存下来
            if nx == 1:
                self.am_1 = am
            elif nx == 2:
                self.am_2 = am
                
        am_1=self.am_1 
        am_2=self.am_2

        self.current_bar=self.current_bar+1 #Bar线计数
        # 计算相关指标
        c_jb = am_1.close_array / am_2.close_array   # 计算价比
        copen = am_1.open_array / am_2.open_array    # 计算开比
        chigh = np.maximum(np.maximum(am_1.high_array / am_2.high_array, copen), c_jb)
        clow = np.minimum(np.minimum(am_1.low_array / am_2.low_array, copen), c_jb)
        
        # 计算多个指标的序列
        var1 = self.highest(chigh, self.N) - self.lowest(clow, self.N)
        var2 = self.highest(chigh, self.N) - c_jb[-self.N:]
        var3 = c_jb[-self.N:] - self.lowest(clow, self.N)
        var4 = var2 / var1 * 100 - 70
        var5 = (c_jb[-self.N:] - self.lowest(clow, self.N)) / var1 * 100
        var6 = (2 * c_jb + chigh + clow) / 4
        var7 = self.sma(var3 / var1 * 100, 3, 1)
        var8 = self.lowest(clow, self.M)
        var9 = self.sma(var7, 3, 1) - self.sma(var4, 9, 1)
        vara = self.highest(chigh, self.M)
        bd1 = self.xaverage((var6[-self.M:] - var8) / (vara - var8) * 100, self.M)
        bd2 = self.xaverage(bd1, self.X)
        ma1 = self.xaverage(c_jb, self.X)
        # 检查金叉 (BD1 从小于 BD2 变为大于 BD2)
        dk_up = bd1[-1] > bd2[-1] and bd1[-2] <= bd2[-1]

        # 检查死叉 (BD1 从大于 BD2 变为小于 BD2)
        kk_dn = bd1[-1] < bd2[-1] and bd1[-2] >= bd2[-1]

        # 确保 dk_up 和 kk_dn 不为空
        if dk_up:
            self.curbar_h = self.current_bar  # 在最后一次金叉发生时更新 curbar_h
            period = max(self.curbar_h - self.curbar_l, self.M)
            
            # 确保 period 不超过 chigh 的长度
            if len(chigh) >= period:
                Highup = max(chigh[-period:-1])
        else:
            Highup = max(chigh[-self.M:-1])  # 如果 period 超出范围，则取整个序列的最大值
                
        if kk_dn:
            self.curbar_l = self.current_bar  # 在最后一次死叉发生时更新 curbar_l
            period = max(self.curbar_l - self.curbar_h, self.M)
            
            # 确保 period 不超过 clow 的长度
            if len(clow) >= period:
                Lowdown = min(clow[-period:-1])
        else:
            Lowdown = min(clow[-self.M:-1])  # 如果 period 超出范围，则取整个序列的最小值
        
        #print(f'bd1[-1]{bd1[-1] },bd2[-1] {bd2[-1]},chigh[-1]{chigh[-1]},Highup{Highup},c_jb[-1]{c_jb[-1]},ma1[-1]{ma1[-1]}')
        # 开仓条件
        cond_dk = (bd1[-1] > bd2[-1]) & (chigh[-1] >= Highup) & (c_jb[-1] > ma1[-1])
        cond_kk = (bd1[-1] < bd2[-1]) & (clow[-1] <= Lowdown) & (c_jb[-1] < ma1[-1])

        self.KG = np.where(cond_dk, 1, np.where(cond_kk, -1, 0))
        
        #print(self.KG)
        #开仓部分
        nx=0
        for vt_symbol, bar in bars.items():
            nx+=1
            am: ArrayManager = self.ams[vt_symbol]
            if not am.inited:
                return
            price = bar.close_price
            current_pos = self.get_pos(vt_symbol)
            #print(nx,current_pos,self.KG)
            #数据源1：
            if nx==1:
                #开多
                if self.KG>0 : 

                        if current_pos<0:
                            self.cover(vt_symbol, price, self.fixed_size)
                            self.buy(vt_symbol, price, self.fixed_size)
                            self.low_after_entry = clow[-1]
                        if current_pos==0:
                            self.buy(vt_symbol, price, self.fixed_size)
                            self.low_after_entry = clow[-1]
                #开空      
                if self.KG<0  : 
                        if current_pos > 0:
                            self.sell(vt_symbol, price, self.fixed_size)
                            self.short(vt_symbol, price, self.fixed_size)
                            self.high_after_entry = chigh[-1]
                        if current_pos == 0:
                            self.short(vt_symbol, price, self.fixed_size)
                            self.high_after_entry = chigh[-1]
            #数据源2
            elif nx==2:
                #开多
                if self.KG>0: 
                        if current_pos < 0:
                            self.cover(vt_symbol, price, self.fixed_size)
                            self.short(vt_symbol, price, self.fixed_size)
                            self.high_after_entry = chigh[-1]   
                        if current_pos == 0:
                            self.short(vt_symbol, price, self.fixed_size)
                            self.high_after_entry = chigh[-1]                              
                #开空      
                if self.KG<0 and current_pos >= 0 :
                    if current_pos > 0 :
                        self.sell(vt_symbol, price, self.fixed_size)
                        self.buy(vt_symbol, price, self.fixed_size)
                        self.low_after_entry = clow[-1]     
                    if current_pos == 0 :
                        self.buy(vt_symbol, price, self.fixed_size)
                        self.low_after_entry = clow[-1]                      
        #移动出场
        if self.KG == 0:
            self.high_after_entry = chigh[-1]
            self.low_after_entry = clow[-1]
        elif self.KG != 0:
            self.high_after_entry = min(self.high_after_entry, chigh[-1])
            self.low_after_entry = max(self.low_after_entry, clow[-1])

        # Calculate liquidation points
        if self.KG > 0:
            self.dliq_point = self.low_after_entry - (copen[-1] * self.TRS / 1000)
        elif self.KG < 0:
            self.kliq_point = self.high_after_entry + (copen[-1] * self.TRS / 1000)

        nx=0
        # print("多头",c_jb[-1],self.dliq_point)
        # print("空头",c_jb[-1],self.kliq_point)
        for vt_symbol, bar in bars.items():
            nx+=1
            am: ArrayManager = self.ams[vt_symbol]
            if not am.inited:
                return
            price = bar.close_price
            current_pos = self.get_pos(vt_symbol)
            
            #数据源1
            if nx==1:
                
                if self.KG > 0 and c_jb[-1]<= self.dliq_point and self.dliq_point > 0 and current_pos>0:
                        self.sell(vt_symbol, price, current_pos)
                if self.KG < 0 and c_jb[-1] >= self.kliq_point and self.kliq_point > 0 and current_pos<0:
                        self.cover(vt_symbol, price, current_pos)
            #数据源2
            if nx==2:
                if self.KG > 0 and c_jb[-1]<= self.dliq_point and self.dliq_point > 0 and current_pos<0:
                        self.cover(vt_symbol, price, current_pos)
                if self.KG < 0 and c_jb[-1] >= self.kliq_point and self.kliq_point > 0 and current_pos>0:
                        self.sell(vt_symbol, price, current_pos)

        self.put_event()


    def highest(self, data, period):
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


    def lowest(self, data, period):
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


    def sma(self, data, period, weight=1):
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




    def xaverage(self, data, period):
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



    def HHV(self, data, period):
        """
        计算给定数据序列中最后 period 个元素的最大值
        :param data: 数据序列
        :param period: 周期
        :return: 最后 period 个元素的最大值
        """
        if len(data) == 0:
            return None  # 如果数据为空，返回 None 或者抛出异常

        if period > len(data):
            period = len(data)  # 如果 period 超出数据长度，则取数据长度

        return max(data[-period:])
    
    
    def LLV(self, data, period):
        """
        计算给定数据序列中最后 period 个元素的最小值
        :param data: 数据序列
        :param period: 周期
        :return: 最后 period 个元素的最小值
        """
        if len(data) == 0:
            return None  # 如果数据为空，返回 None 或者抛出异常

        if period > len(data):
            period = len(data)  # 如果 period 超出数据长度，则取数据长度

        return min(data[-period:])