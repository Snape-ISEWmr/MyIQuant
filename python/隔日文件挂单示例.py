# encoding:gbk
import logging
import pandas as pd
from datetime import datetime, timedelta, time
from decimal import InvalidOperation
from decimal import Decimal as D
from READFILE import read_file

logging.basicConfig(level=logging.INFO)
# 挂单失败后的等待时长，以秒计
TIMEOUT_ON_FAIL_SEC = 30
# 规避 account_callback 的 Racing Condition
RUN_TIME_DELAY = 10

# global FILEPATH, DIR, PRICE, VOL, START_TIME, account
SH_pattern = r'^[1-9]\d{5}\.(sh|SH)$'
SZ_pattern = r'^(?!39)\d{6}\.(sz|SZ)$'
SH_prefix = ['5', '6', '9', '11']
SZ_prefix = ['0', '2', '30', '12', '159']
COLNAMES = ['direction', 'vol', 'price', 'start_time']


def init(ContextInfo):
    ContextInfo.accID = account
    ContextInfo.set_account(ContextInfo.accID)

    ContextInfo.can_order = False
    ContextInfo.all_order_done = False

    if not load_file_order(ContextInfo):
        load_sys_order(ContextInfo)

    # load_file_order(ContextInfo)
    ContextInfo.run_time("place_order", "{0}nSecond".format(TIMEOUT_ON_FAIL_SEC),
                         (datetime.now() + timedelta(seconds=RUN_TIME_DELAY)).strftime('%Y-%m-%d %H:%M:%S'), 'SH')


def account_callback(ContextInfo, accountInfo):
    if not ContextInfo.can_order:
        ContextInfo.can_order = True


def handlebar(ContextInfo):
    return


def load_file_order(ContextInfo):
    def _price_vol_filtering(row):
        if not isinstance(row.start_time, time):
            logging.warning('读取{0}指令时间失败: {1}'.format(row.name, row.start_time))
            return None
        if row.direction not in ['买', '卖']:
            logging.warning('读取{0}买卖方向失败: {1}'.format(row.name, row.direction))
            return None
        try:
            # parse start_time
            curr_start_time = datetime.now().strftime('%Y-%m-%d ') + row.start_time.strftime('%H:%M:%S')
            curr_start_time = datetime.strptime(curr_start_time, '%Y-%m-%d %H:%M:%S')
            # parse direction
            curr_direction = 23 if row.direction == '买' else 24
            # parse price and vol
            price = D(row.price)
            vol = int(row.vol)
            return pd.Series([curr_direction, vol, price, curr_start_time])
        except InvalidOperation:
            logging.warning("读取 {0} 指令价格失败: {1}".format(row.name, row.price))
            return None
        except ValueError:
            logging.warning('读取 {0} 下单总量失败: {1}'.format(row.name, row.vol))
            return None

    def _name_parser(asset_name):
        # 目前默认用户输入.SH 或.SZ时标的名称正确
        if '.SH' in asset_name or '.SZ' in asset_name:
            # todo: SH/SZ_pattern regex check here?
            return asset_name
        else:
            raise ValueError('{0} 标的代码不合法'.format(asset_name))

    try:
        tmp_df = read_file(FILEPATH, names=COLNAMES, index_col=0)
    except:
        logging.warning('读取挂单配置文件失败或挂单配置文件为空，尝试交易读取配置面板参数')
        return None
    if tmp_df.empty:
        logging.warning('读取挂单配置文件失败或挂单配置文件为空，尝试交易读取配置面板参数')
        return None

    tmp_df.index = tmp_df.index.to_series().astype(str)
    tmp_df.index = tmp_df.index.str.strip()
    tmp_df.index = tmp_df.index.str.upper()
    tmp_df.index = tmp_df.index.to_series().apply(_name_parser).dropna()
    tmp_df = tmp_df.apply(_price_vol_filtering, axis=1, broadcast=True).dropna()
    if tmp_df.empty:
        logging.warning('读取挂单配置文件失败或挂单配置文件为空，尝试交易读取配置面板参数')
        return False

    tmp_df.set_axis(COLNAMES, axis='columns', inplace=True)
    # 挂单成功Flag
    tmp_df['finished'] = [False] * tmp_df.shape[0]
    ContextInfo.order_df = tmp_df
    ContextInfo.set_universe(ContextInfo.order_df.index.tolist())
    return True


def load_sys_order(ContextInfo):
    try:
        asset_name = ContextInfo.stockcode + '.' + ContextInfo.market
        ContextInfo.set_universe([asset_name])
        direction = 23 if DIR == '买入' else 24
        start_time = datetime.strptime(datetime.now().strftime('%Y%m%d') + str(START_TIME), '%Y%m%d%H%M%S')
        price = D(PRICE)
        vol = int(VOL)
    except BaseException:
        raise ValueError("读取策略面板交易配置失败。请尝试修正挂单配置文件或者策略面板参数。")

    price = float(price)
    ContextInfo.order_df = pd.DataFrame(data=[direction, vol, price, start_time], index=COLNAMES,
                                        columns=[asset_name]).T
    ContextInfo.order_df['finished'] = False
    return


def place_order(ContextInfo):
    if not ContextInfo.can_order or ContextInfo.all_order_done:
        return
    for curr_asset in ContextInfo.get_universe():
        if not ContextInfo.order_df.loc[curr_asset].finished \
                and datetime.now() > ContextInfo.order_df.loc[curr_asset].start_time:
            curr_order = ContextInfo.order_df.loc[curr_asset]
            direction = int(curr_order.direction)
            txt_direction = '买入' if direction == 23 else '卖出'
            price = float(D(curr_order.price))
            vol = int(curr_order.vol)
            order_remark = '隔日文件挂单: 以 {0} {1} {2}'.format(price, txt_direction, curr_asset)
            passorder(direction, 1101, ContextInfo.accID, curr_asset, 11, price, vol, order_remark, 1, order_remark,
                      ContextInfo)
            ContextInfo.order_df.loc[curr_asset, 'finished'] = True

    ContextInfo.all_order_done = all(ContextInfo.order_df['finished'].tolist())


def order_callback(ContextInfo, orderInfo):
    curr_asset = orderInfo.m_strInstrumentID + '.' + orderInfo.m_strExchangeID
    curr_remark = orderInfo.m_strRemark
    curr_status = orderInfo.m_nOrderStatus
    if '隔日文件挂单' in curr_remark and curr_status == 57:
        ContextInfo.order_df.loc[curr_asset, 'finished'] = False
        ContextInfo.all_order_done = False
        logging.error('{0} 隔日文件挂单：报单废单 (柜台返回失败)，原因：{1} 尝试重报'.format(curr_asset, orderInfo.m_strCancelInfo))
    elif '隔日文件挂单' in curr_remark and curr_status == 50:
        logging.info('{0} 隔日文件挂单：报单成功'.format(curr_asset))
    return


def orderError_callback(ContextInfo, orderArgs, errMsg):
    curr_asset = orderArgs.orderCode
    if '隔日文件挂单' in orderArgs.strategyName:
        ContextInfo.order_df.loc[curr_asset, 'finished'] = False
        ContextInfo.all_order_done = False
        logging.error('{0} 隔日文件挂单：账号下单异常 (COS/iQuant校验失败), 错误消息：{1} 尝试重报'.format(curr_asset, errMsg))
        return



