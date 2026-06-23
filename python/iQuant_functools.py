#encoding:gbk

class Account:
    def __init__(self, accountid, accounttype):
        self.accID = accountid
        self.accType = accounttype

class Query_Details:
    def __init__(self, account:Account, detail_func, context):
        self.accID = account.accID
        self.accType = account.accType
        self.detail_func = detail_func[0]
        self.credit_fund_func = detail_func[1]
        self.credit_stk_func = detail_func[2]
        self.context = context

    def get_available_cash(self):
        cash = 0.0
        for i in self.detail_func(self.accID, self.accType, 'ACCOUNT'):
            cash = i.m_dAvailable
        return cash

    def get_available_margin_balance(self):
        cash = 0.0
        if self.accType != 'CREDIT':
            return cash
        for i in self.detail_func(self.accID, self.accType, 'ACCOUNT'):
            cash = i.m_dEnableBailBalance
        return cash

    def get_available_holding(self, code=''):
        if code == '':
            code = self.context.stockcode + '.' + self.context.market
        hold = 0
        for i in self.detail_func(self.accID, self.accType, 'POSITION'):
            if i.m_strInstrumentID + '.' + i.m_strExchangeID == code:
                hold = i.m_nCanUseVolume
        return hold

    def get_total_holding(self, code=''):
        if code == '':
            code = self.context.stockcode + '.' + self.context.market
        hold = 0
        for i in self.detail_func(self.accID, self.accType, 'POSITION'):
            if i.m_strInstrumentID + '.' + i.m_strExchangeID == code:
                hold = i.m_nVolume
        return hold

    def get_max_credit_fund_buy(self, code=''):
        pass

    def get_max_credit_stk_lend(self, code=''):
        pass

    def get_avialable_sec_lend(self, code=''):
        if code == '':
            code = self.context.stockcode + '.' + self.context.market
        hold = 0 
        return hold

    def check_sec_on_order(self, code='', rmk_base = ''):
        if code == '':
            code = self.context.stockcode + '.' + self.context.market
        result = False
        for i in self.detail_func(self.accID, self.accType, 'ORDER'):
            if i.m_strInstrumentID + '.' + i.m_strExchangeID == code and rmk_base in i.m_strRemark:
                if i.m_nOrderStatus in [53, 54, 56, 57]:
                    continue
                elif i.m_nOrderStatus in [49, 50, 51, 52, 55]:
                    result = True
                    break
        return result

    def check_sec_on_order_by_side(self, code='', dir = 'buy', rmk_base = ''):
        if code == '':
            code = self.context.stockcode + '.' + self.context.market
        result = False
        direction = 48 if dir.lower() == 'buy' else 49
        for i in self.detail_func(self.accID, self.accType, 'ORDER'):
            if i.m_strInstrumentID + '.' + i.m_strExchangeID == code and i.m_nOffsetFlag == direction and rmk_base in i.m_strRemark:
                if i.m_nOrderStatus in [53, 54, 56, 57]:
                    continue
                elif i.m_nOrderStatus in [49, 50, 51, 52, 55]:
                    result = True
                    break
        return result        