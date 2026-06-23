#encoding:gbk

import numpy as np
import pandas as pd

def init(ContextInfo):
	ContextInfo.canPrint = True
	ContextInfo.stockCode = '002736.SZ'
	ContextInfo.stockList = ['002736.SZ', '600519.SH', '600000.SH', '000001.SZ']
	ContextInfo.tradeDate = '20210401'
	ContextInfo.startDate = '20210401'
	ContextInfo.endDate = '20210406'
	ContextInfo.AIFactor = ['AI_MARKET_LEVEL_FORCAST.stk_p_ai',      # 股票下一交易日上涨概率
							'AI_MARKET_LEVEL_FORCAST.stk_sw1_p_ai',  # 申万一级行业指数下一交易日上涨概率
							'AI_MARKET_LEVEL_FORCAST.stk_sw2_p_ai',  # 申万二级行业指数下一交易日上涨概率
							'AI_MARKET_LEVEL_FORCAST.stk_sw3_p_ai',  # 申万三级行业指数下一交易日上涨概率
							'AI_MARKET_LEVEL_FORCAST.stk_zx1_p_ai',  # 中信一级行业指数下一交易日上涨概率
							'AI_MARKET_LEVEL_FORCAST.stk_zx2_p_ai',  # 中信二级行业指数下一交易日上涨概率
							'AI_MARKET_LEVEL_FORCAST.stk_zx3_p_ai']  # 中信三级行业指数下一交易日上涨概率

def handlebar(ContextInfo):
	if ContextInfo.canPrint == True:
		ContextInfo.canPrint = False
		# 场景一 : 单股票单日期 --- 返回pandas.Series数据结构 index=因子名称 values = 因子值
		df1 = ContextInfo.get_factor_data(ContextInfo.AIFactor, ContextInfo.stockCode, ContextInfo.tradeDate, ContextInfo.tradeDate)
		print('\n 场景一 : 单股票单日期获取因子数据 : \n', df1)
		
		# 场景二 : 单股票多日期 --- 返回pandas.DataFrame数据结构 index=时间 columns=因子名称 values = 因子值
		df2 = ContextInfo.get_factor_data(ContextInfo.AIFactor, ContextInfo.stockCode, ContextInfo.startDate, ContextInfo.endDate)
		print('\n 场景二 : 单股票多日期获取因子数据 : \n', df2)
		
		# 场景三 : 多股票单日期 --- 返回pandas.DataFrame数据结构 index=股票代码 columns=因子名称 values=因子值
		df3 = ContextInfo.get_factor_data(ContextInfo.AIFactor, ContextInfo.stockList, ContextInfo.tradeDate, ContextInfo.tradeDate)
		print('\n 场景三 : 多股票单日期获取因子数据 : \n', df3)
		
		# 场景四 : 多股票多日期 --- 返回dict数据结构 key=股票代码 values=pandas.DataFrame数据结构 index=时间 columns=因子名称 values=因子值
		df4 = ContextInfo.get_factor_data(ContextInfo.AIFactor, ContextInfo.stockList, ContextInfo.startDate, ContextInfo.endDate)
		print('\n 场景四 : 多股票多日期获取因子数据 : \n', df4)
		
		# 如何将返回结构的时间转换成熟悉的datetime格式 以场景二获取的数据为例
		df2.index = pd.to_datetime(df2.index, unit='ms')
		print('\n 场景五 : 将数据的时间转成datetime格式 : \n', df2)

