# encoding:gbk
import logging
from datetime import datetime, timedelta
from decimal import Decimal as D
from decimal import InvalidOperation

logging.basicConfig(level=logging.INFO)

# 挂单失败后的等待时长，以秒计
TIMEOUT_ON_FAIL_SEC = 30
# 等待account_callback的时长
# RUN_TIME_DELAY = 30

# how is this not defined in package??
MORNING_START = datetime.strptime(datetime.now().strftime('%Y%m%d') + '093000', '%Y%m%d%H%M%S')
MORNING_END = datetime.strptime(datetime.now().strftime('%Y%m%d') + '113000', '%Y%m%d%H%M%S')
NOON_START = datetime.strptime(datetime.now().strftime('%Y%m%d') + '130000', '%Y%m%d%H%M%S')
NOON_END = datetime.strptime(datetime.now().strftime('%Y%m%d') + '153000', '%Y%m%d%H%M%S')

# for SH only
TRANS_COST_1D = D('5e-6')
TRANS_COST_LONG = D('1.5e-7')
TRANS_COST_MAX = 100

# ORDER LIMITS
SH_UPPER = 1e7
SH_LOWER = 1e5
SZ_UPPER = 1e8
SZ_LOWER = 1e3

# ASSET NAME DICT
SH_REV_REPO = {'上交所1天': '204001.SH', '上交所2天': '204002.SH', '上交所3天': '204003.SH',
               '上交所4天': '204004.SH', '上交所7天': '204007.SH', '上交所14天': '204014.SH',
               '上交所28天': '204028.SH', '上交所91天': '204091.SH', '上交所182天': '204182.SH',
               }

SZ_REV_REPO = {'深交所3天': '131800.SZ', '深交所7天': '131801.SZ', '深交所14天': '131802.SZ',
               '深交所28天': '131803.SZ', '深交所91天': '131805.SZ', '深交所182天': '131806.SZ',
               '深交所4天': '131809.SZ', '深交所1天': '131810.SZ', '深交所2天': '131811.SZ',
               }


def init(ContextInfo):
    ContextInfo.accID = account
    ContextInfo.set_account(ContextInfo.accID)
    ContextInfo.use_all_cap = False if ALL_CAP == '否' else True

    # global trading control, set to False if detected error on user's side
    # stop() does not halt strat
    ContextInfo.order_control = False

    if not ContextInfo.use_all_cap:
        try:
            ContextInfo.dollar_vol = float(D(DOLLAR_VOL))
        except InvalidOperation:
            ContextInfo.order_control = True
            raise ValueError('读取资金量失败')
    else:
        if DOLLAR_VOL != '':
            logging.warning('已设定使用全部账户资金，忽略所设置资金量')

    try:
        ContextInfo.start_time = datetime.strptime(datetime.now().strftime('%Y%m%d') + str(START_TIME), '%Y%m%d%H%M%S')
        ContextInfo.asset_name = SH_REV_REPO[ASSET_NAME]
    except KeyError:
        ContextInfo.asset_name = SZ_REV_REPO[ASSET_NAME]
    except ValueError as error:
        if 'unconverted data remains' in str(error):
            ContextInfo.order_control = True
            raise ValueError('读取挂单时间失败')

    if not (MORNING_END > ContextInfo.start_time >= MORNING_START) \
            and not (NOON_END > ContextInfo.start_time >= NOON_START):
        ContextInfo.order_control = True
        raise ValueError('挂单时间不在可交易时间内')

    ContextInfo.can_order = False
    ContextInfo.order_done = False

    if not ContextInfo.order_control:
        ContextInfo.run_time("place_order", "{0}nSecond".format(TIMEOUT_ON_FAIL_SEC),
                             ContextInfo.start_time.strftime('%Y-%m-%d %H:%M:%S'), 'SH')


def account_callback(ContextInfo, accountInfo):
    if not ContextInfo.can_order:
        ContextInfo.can_order = True
        if ContextInfo.use_all_cap:
            ContextInfo.dollar_vol = accountInfo.m_dAvailable
        else:
            if ContextInfo.dollar_vol > accountInfo.m_dAvailable:
                ContextInfo.order_control = True
                raise ValueError('下单额度大于账户可用资金')

        # check if order satisfies lower limit for each exchange
        if ('SH' in ContextInfo.asset_name and ContextInfo.dollar_vol < SH_LOWER) \
                or ('SZ' in ContextInfo.asset_name and ContextInfo.dollar_vol < SZ_LOWER):
            ContextInfo.order_control = True
            raise ValueError('下单额度低于交易所最低限额')

        # checks dollar_vol and rounds the total amount
        if 'SH' in ContextInfo.asset_name and ContextInfo.dollar_vol % SH_LOWER != 0:
            ContextInfo.dollar_vol = (ContextInfo.dollar_vol // SH_LOWER) * SH_LOWER
            logging.warning('下单额度已规整为：{0}'.format(ContextInfo.dollar_vol))
        elif 'SZ' in ContextInfo.asset_name and ContextInfo.dollar_vol % SZ_LOWER != 0:
            ContextInfo.dollar_vol = (ContextInfo.dollar_vol // SZ_LOWER) * SZ_LOWER
            logging.warning('下单额度已规整为：{0}'.format(ContextInfo.dollar_vol))

        '''
        if 'SH' in ContextInfo.asset_name:
            num_batch_order = int(ContextInfo.dollar_vol // SH_UPPER)
            remain_order = ContextInfo.dollar_vol - num_batch_order * SH_UPPER
            if ContextInfo.asset_name == '204001.SH':
                transaction_cost = TRANS_COST_MAX * num_batch_order + remain_order * TRANS_COST_1D
            else:
                transaction_cost = TRANS_COST_MAX * num_batch_order + remain_order * TRANS_COST_LONG
            if transaction_cost + ContextInfo.dollar_vol > accountInfo.m_dAvailable:
                ContextInfo.order_control = True
                raise ValueError('可用资金不足以垫付交易金额与手续费')
       '''

        ContextInfo.remain_vol = ContextInfo.dollar_vol


def handlebar(ContextInfo):
    return


def place_order(ContextInfo):
    if not ContextInfo.can_order or ContextInfo.order_control:
        return

    if not ContextInfo.order_done:
        if 'SH' in ContextInfo.asset_name:
            num_batch_order = int(ContextInfo.remain_vol // SH_UPPER)
            remain_order = ContextInfo.remain_vol - num_batch_order * SH_UPPER
            for _ in range(num_batch_order):
                order_remark = '国债逆回购：尝试报单{0}元 {1}'.format(SH_UPPER, ContextInfo.asset_name)
                passorder(24, 1102, ContextInfo.accID, ContextInfo.asset_name, 5, -1, SH_UPPER, order_remark, 1,
                          order_remark, ContextInfo)
        else:
            num_batch_order = int(ContextInfo.remain_vol // SZ_UPPER)
            remain_order = ContextInfo.remain_vol - num_batch_order * SZ_UPPER
            for _ in range(num_batch_order):
                order_remark = '国债逆回购：尝试报单{0}元 {1}'.format(SZ_UPPER, ContextInfo.asset_name)
                passorder(24, 1102, ContextInfo.accID, ContextInfo.asset_name, 5, -1, SZ_UPPER, order_remark, 1,
                          order_remark, ContextInfo)

        order_remark = '国债逆回购：尝试报单{0}元 {1}'.format(remain_order, ContextInfo.asset_name)
        passorder(24, 1102, ContextInfo.accID, ContextInfo.asset_name, 5, -1, remain_order, order_remark, 1,
                  order_remark, ContextInfo)

        ContextInfo.remain_vol = 0
        ContextInfo.order_done = True


def order_callback(ContextInfo, orderInfo):
    curr_remark = orderInfo.m_strRemark
    curr_status = orderInfo.m_nOrderStatus

    if '国债逆回购' in curr_remark and ContextInfo.asset_name in curr_remark and curr_status == 57:
        ContextInfo.order_done = False
        # up the leftover dollar vol by failed amount
        # logging.info('reported trade amount:{0}, reported_trade_volume:{1}'.format(orderInfo.m_dTradeAmount, orderInfo.m_nVolumeTotal))
        # 单张100元
        ContextInfo.remain_vol += orderInfo.m_nVolumeTotal * 100
        if '交易时间不合法' in orderInfo.m_strCancelInfo:
            ContextInfo.order_control = True
            raise ValueError('国债逆回购：未能在交易时间内完成下单，停止报单。余量{0}元未报'.format(ContextInfo.remain_vol))
        logging.warning('国债逆回购：报单废单，原因：\"{0}\"，尝试重报'.format(orderInfo.m_strCancelInfo))
    elif '国债逆回购' in curr_remark and ContextInfo.asset_name in curr_remark and curr_status == 50:
        logging.info('国债逆回购：报单{0}元成功'.format(orderInfo.m_nVolumeTotal * 100))
    return




