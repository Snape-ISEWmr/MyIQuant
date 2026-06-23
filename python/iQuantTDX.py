import numpy as np
import pandas as pd

#------------------ 0级：核心工具函数 --------------------------------------------    
#四舍五入取D位小数   
def RD(N,D=3):
    return np.round(N,D)        

#返回序列倒数第N个值,默认返回最后一个
def RET(S,N=1):
    return np.array(S)[-N]      

#返回N的绝对值
def ABS(S):
    return np.abs(S)            

#序列max
def MAX(S1,S2):  
    return np.maximum(S1,S2)    

#序列min
def MIN(S1,S2):  
    return np.minimum(S1,S2)    

#求序列的N日平均值 返回序列         
def MA(S,N):                                
    return pd.Series(S).rolling(N).mean().values    

#对序列整体下移动N 返回序列(shift后会产生NAN)  
def REF(S, N=1):            
    return pd.Series(S).shift(N).values  

#前一个值减后一个值 前面会产生nan (np.diff(S)直接删除nan，会少一行)
def DIFF(S, N=1):         
    return pd.Series(S).diff(N).values     

#求序列的N日标准差 返回序列  
def STD(S,N):               
    return  pd.Series(S).rolling(N).std(ddof=0).values     

 #序列布尔判断 return=S_TRUE if S_BOOL==True  else  S_FALSE
def IF(S_BOOL,S_TRUE,S_FALSE):  
    return np.where(S_BOOL, S_TRUE, S_FALSE)

#对序列求N天累计和 返回序列 N=0对序列所有依次求和   
def SUM(S, N):                  
    return pd.Series(S).rolling(N).sum().values if N>0 else pd.Series(S).cumsum().values  

#HHV(C, 5) 最近5天收盘最高价     
def HHV(S,N):                
    return pd.Series(S).rolling(N).max().values     

 #LLV(C, 5) 最近5天收盘最低价  
def LLV(S,N):               
    return pd.Series(S).rolling(N).min().values    

#指数移动平均 为了精度 S>4*N  EMA至少需要120周期 alpha=2/(span+1)    
def EMA(S,N):             
    return pd.Series(S).ewm(span=N, adjust=False).mean().values     

#中国式的SMA 至少需要120周期才精确 (雪球180周期)  alpha=1/(1+com) com=N-M/M
def SMA(S, N, M=1):       
    return pd.Series(S).ewm(alpha=M/N,adjust=True).mean().values          

#S序列的动态移动平均 A作平滑因子,必须 0<A<1 
def DMA(S, A):            
    return pd.Series(S).ewm(alpha=A, adjust=False).mean().values

#通达信S序列的N日加权移动平均 Yn = (1*X1+2*X2+3*X3+...+n*Xn)/(1+2+3+...+Xn)
def WMA(S, N):            
    weights = np.array(range(1,N + 1));    w = weights/np.sum(weights)    
    return  pd.Series(S).rolling(N).apply(lambda x:np.sum(w*x),raw=False).values

#平均绝对偏差  (序列与其平均值的绝对差的平均值)   
def AVEDEV(S, N):         
    return pd.Series(S).rolling(N).apply(lambda x: (np.abs(x - x.mean())).mean()).values 

#返S序列N周期回线性回归斜率       
def SLOPE(S, N):           
    return pd.Series(S).rolling(N).apply(lambda x: np.polyfit(x.index,x,deg=1)[0],raw=False).values  

#返回S序列N周期回线性回归后的预测值
def FORCAST(S, N):           
    return pd.Series(S).rolling(N).apply(lambda x:np.polyval(np.polyfit(range(N),x,deg=1),N-1),raw=False).values  

 
#------------------   1级：应用层函数(通过0级核心函数实现） ----------------------------------
# COUNT(CLOSE>O, N) 最近N天满足CLOSE>O的天数  True的天数
def COUNT(S, N):                       
    return SUM(S,N)    

# EVERY(CLOSE>O, N) 最近N天是否都是True
def EVERY(S, N):                      
    return  IF(SUM(S,N)==N,True,False)

#从前A日到前B日一直满足S_BOOL条件, 要求A>B & A>0 & B>0              
def LAST(S, A, B):                     
    return np.array(pd.Series(S).rolling(A+1).apply(lambda x:np.all(x[::-1][B:]),raw=False),dtype=bool)

# EXIST(CLOSE>3000, N=5) N日内是否存在一天大于3000点  
def EXIST(S, N):                      
    return IF(SUM(S,N)>0,True,False)

 # FILTER函数，S满足条件后，将其后N周期内的数据置为0 例：FILTER(C==H,5) 涨停后，后5天不再发出信号
def FILTER(S, N):                     
    for i in range(len(S)):  
        if S[i]: S[i+1:i+1+N]=0
    return S    

#上一次条件成立到当前的周期, BARSLAST(C/REF(C,1)>=1.1) 上一次涨停到今天的天数 
def BARSLAST(S):                      
    M=np.concatenate(([0],np.where(S,1,0)))  
    for i in range(1, len(M)):  
        M[i]=0 if M[i] else M[i-1]+1    
    return M[1:]                       
      
 #判断向上金叉穿越 CROSS(MA(C,5),MA(C,10)) 判断向下死叉穿越 CROSS(MA(C,10),MA(C,5)) 
def CROSS(S1, S2):                    
    S = np.nan_to_num(S1) > np.nan_to_num(S2)         
    return np.concatenate(([False], np.logical_not(S[:-1]) & S[1:]))   

#两条线维持一定周期后交叉,S1在N周期内都小于S2,本周期从S1下方向上穿过S2时返回1,否则返回0      
def LONGCROSS(S1,S2,N):                
    T=np.logical_and(REF(EVERY(S1<S2,N),1),(S1>S2))
    return  np.array(T,dtype=bool)     #序列进序列出 

#------------------   2级：技术指标函数(全部通过0级，1级函数实现） ------------------------------
# 调用二级指标 最好数据长度取S取120

# MACD指标
def MACD(CLOSE,SHORT=12,LONG=26,M=9):             
    DIF = EMA(CLOSE,SHORT)-EMA(CLOSE,LONG);  
    DEA = EMA(DIF,M);      MACD=(DIF-DEA)*2
    return RD(DIF),RD(DEA),RD(MACD)

# KDJ指标
def KDJ(CLOSE,HIGH,LOW, N=9,M1=3,M2=3):           
    RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
    K = EMA(RSV, (M1*2-1));    D = EMA(K,(M2*2-1));        J=K*3-D*2
    return K, D, J

# RSI指标,和通达信小数点2位相同
def RSI(CLOSE, N=24):                           
    DIF = CLOSE-REF(CLOSE,1) 
    return RD(SMA(MAX(DIF,0), N) / SMA(ABS(DIF), N) * 100)  

# W&R 威廉指标
def WR(CLOSE, HIGH, LOW, N=10, N1=6):            
    WR = (HHV(HIGH, N) - CLOSE) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
    WR1 = (HHV(HIGH, N1) - CLOSE) / (HHV(HIGH, N1) - LLV(LOW, N1)) * 100
    return RD(WR), RD(WR1)

# BIAS乖离率
def BIAS(CLOSE,L1=6, L2=12, L3=24):              
    BIAS1 = (CLOSE - MA(CLOSE, L1)) / MA(CLOSE, L1) * 100
    BIAS2 = (CLOSE - MA(CLOSE, L2)) / MA(CLOSE, L2) * 100
    BIAS3 = (CLOSE - MA(CLOSE, L3)) / MA(CLOSE, L3) * 100
    return RD(BIAS1), RD(BIAS2), RD(BIAS3)

# BOLL指标 布林带    
def BOLL(CLOSE,N=20, P=2):                       
    MID = MA(CLOSE, N); 
    UPPER = MID + STD(CLOSE, N) * P
    LOWER = MID - STD(CLOSE, N) * P
    return RD(UPPER), RD(MID), RD(LOWER)    

# 心理线
def PSY(CLOSE,N=12, M=6):  
    PSY=COUNT(CLOSE>REF(CLOSE,1),N)/N*100
    PSYMA=MA(PSY,M)
    return RD(PSY),RD(PSYMA)

# 商品路径指标
def CCI(CLOSE,HIGH,LOW,N=14):  
    TP=(HIGH+LOW+CLOSE)/3
    return (TP-MA(TP,N))/(0.015*AVEDEV(TP,N))

# 真实波动N日平均值    
def ATR(CLOSE,HIGH,LOW, N=20):                    
    TR = MAX(MAX((HIGH - LOW), ABS(REF(CLOSE, 1) - HIGH)), ABS(REF(CLOSE, 1) - LOW))
    return MA(TR, N)

# BBI多空指标 
def BBI(CLOSE,M1=3,M2=6,M3=12,M4=20):               
    return (MA(CLOSE,M1)+MA(CLOSE,M2)+MA(CLOSE,M3)+MA(CLOSE,M4))/4    

# 动向指标 结果和同花顺，通达信完全一致
def DMI(CLOSE,HIGH,LOW,M1=14,M2=6):               
    TR = SUM(MAX(MAX(HIGH - LOW, ABS(HIGH - REF(CLOSE, 1))), ABS(LOW - REF(CLOSE, 1))), M1)
    HD = HIGH - REF(HIGH, 1);     LD = REF(LOW, 1) - LOW
    DMP = SUM(IF((HD > 0) & (HD > LD), HD, 0), M1)
    DMM = SUM(IF((LD > 0) & (LD > HD), LD, 0), M1)
    PDI = DMP * 100 / TR;         MDI = DMM * 100 / TR
    ADX = MA(ABS(MDI - PDI) / (PDI + MDI) * 100, M2)
    ADXR = (ADX + REF(ADX, M2)) / 2
    return PDI, MDI, ADX, ADXR  

# 唐安奇通道(海龟)交易指标
def TAQ(HIGH,LOW,N):                               
    UP=HHV(HIGH,N);    DOWN=LLV(LOW,N);    MID=(UP+DOWN)/2
    return UP,MID,DOWN

# 肯特纳交易通道 默认N选20日 ATR选10日
def KTN(CLOSE,HIGH,LOW,N=20,M=10):                 
    MID=EMA((HIGH+LOW+CLOSE)/3,N)
    ATRN=ATR(CLOSE,HIGH,LOW,M)
    UPPER=MID+2*ATRN;   LOWER=MID-2*ATRN
    return UPPER,MID,LOWER       

# 三重指数平滑平均线
def TRIX(CLOSE,M1=12, M2=20):                      
    TR = EMA(EMA(EMA(CLOSE, M1), M1), M1)
    TRIX = (TR - REF(TR, 1)) / REF(TR, 1) * 100
    TRMA = MA(TRIX, M2)
    return TRIX, TRMA

# VR容量比率
def VR(CLOSE,VOL,M1=26):                            
    LC = REF(CLOSE, 1)
    return SUM(IF(CLOSE > LC, VOL, 0), M1) / SUM(IF(CLOSE <= LC, VOL, 0), M1) * 100

# 简易波动指标 
def EMV(HIGH,LOW,VOL,N=14,M=9):                    
    VOLUME=MA(VOL,N)/VOL;       MID=100*(HIGH+LOW-REF(HIGH+LOW,1))/(HIGH+LOW)
    EMV=MA(MID*VOLUME*(HIGH-LOW)/MA(HIGH-LOW,N),N);    MAEMV=MA(EMV,M)
    return EMV,MAEMV

# 区间震荡线
def DPO(CLOSE,M1=20, M2=10, M3=6):                  
    DPO = CLOSE - REF(MA(CLOSE, M1), M2);    MADPO = MA(DPO, M3)
    return DPO, MADPO

# BRAR-ARBR 情绪指标
def BRAR(OPEN,CLOSE,HIGH,LOW,M1=26):                   
    AR = SUM(HIGH - OPEN, M1) / SUM(OPEN - LOW, M1) * 100
    BR = SUM(MAX(0, HIGH - REF(CLOSE, 1)), M1) / SUM(MAX(0, REF(CLOSE, 1) - LOW), M1) * 100
    return AR, BR

# 平行线差指标 (通达信指标叫DMA 同花顺叫新DMA)
def DFMA(CLOSE,N1=10,N2=50,M=10):                    
    DIF=MA(CLOSE,N1)-MA(CLOSE,N2); DIFMA=MA(DIF,M)   
    return DIF,DIFMA

# 动量指标
def MTM(CLOSE,N=12,M=6):                             
    MTM=CLOSE-REF(CLOSE,N);         MTMMA=MA(MTM,M)
    return MTM,MTMMA

# 梅斯线
def MASS(HIGH,LOW,N1=9,N2=25,M=6):                   
    MASS=SUM(MA(HIGH-LOW,N1)/MA(MA(HIGH-LOW,N1),N1),N2)
    MA_MASS=MA(MASS,M)
    return MASS,MA_MASS

# 变动率指标
def ROC(CLOSE,N=12,M=6):                             
    ROC=100*(CLOSE-REF(CLOSE,N))/REF(CLOSE,N);    MAROC=MA(ROC,M)
    return ROC,MAROC  

# EMA指数平均数指标
def EXPMA(CLOSE,N1=12,N2=50):                        
    return EMA(CLOSE,N1),EMA(CLOSE,N2);

# 能量潮指标
def OBV(CLOSE,VOL):                                  
    return SUM(IF(CLOSE>REF(CLOSE,1),VOL,IF(CLOSE<REF(CLOSE,1),-VOL,0)),0)/10000

# MFI指标是成交量的RSI指标
def MFI(CLOSE,HIGH,LOW,VOL,N=14):                    
    TYP = (HIGH + LOW + CLOSE)/3
    V1=SUM(IF(TYP>REF(TYP,1),TYP*VOL,0),N)/SUM(IF(TYP<REF(TYP,1),TYP*VOL,0),N)  
    return 100-(100/(1+V1))     

# 振动升降指标
def ASI(OPEN,CLOSE,HIGH,LOW,M1=26,M2=10):            
    LC=REF(CLOSE,1);      AA=ABS(HIGH-LC);     BB=ABS(LOW-LC);
    CC=ABS(HIGH-REF(LOW,1));   DD=ABS(LC-REF(OPEN,1));
    R=IF( (AA>BB) & (AA>CC),AA+BB/2+DD/4,IF( (BB>CC) & (BB>AA),BB+AA/2+DD/4,CC+DD/4));
    X=(CLOSE-LC+(CLOSE-OPEN)/2+LC-REF(OPEN,1));
    SI=16*X/R*MAX(AA,BB);   ASI=SUM(SI,M1);   ASIT=MA(ASI,M2);
    return ASI,ASIT   