#encoding:gbk
import sys
import atexit
from os import path
from datetime import datetime 
from xtquant.xttype import StockAccount

USERDATA_PATH = path.abspath(r"..\userdata")
TK_PKGS_PATH  = path.abspath(r"..\HTML\可视化策略")
sys.path.append(TK_PKGS_PATH)

from conv_bond_arb import ConfigWindow
from tkUtils import TradeAPIWrapper

# API in another thread version
if __name__ == '__main__':
    api_wrapper = TradeAPIWrapper(USERDATA_PATH)
    api_wrapper.start()

    # wait for API initialization
    while not api_wrapper.trade_api.initialized:
        continue

    config_window = ConfigWindow(api_wrapper)
    config_window.start_app()














