#encoding:gbk
import sys
import signal 
import atexit
from os import path
from datetime import datetime 
from xtquant.xttype import StockAccount

# set to whatever, just make it unique, <= 8 chars!
# STRAT_NAME = r'Repo'+datetime.now().strftime('%m%d')
USERDATA_PATH = path.abspath(r"..\userdata")
TK_PKGS_PATH  = path.abspath(r"..\HTML\可视化策略")
sys.path.append(TK_PKGS_PATH)
from rev_repo import ConfigWindow
from tkUtils import BaseTradeAPI, TradeAPIWrapper

# API in another thread version
if __name__ == '__main__':
    # API started in another thread
    api_wrapper = TradeAPIWrapper(USERDATA_PATH)
    api_wrapper.start()

    # wait for API initialization
    while not api_wrapper.trade_api.initialized:
        continue

    # GUI + SPI start, points to API
    tk_gui = ConfigWindow(api_wrapper)
    # register SPI with API
    api_wrapper.trade_api.register_callback(tk_gui)
    tk_gui.start_app()















