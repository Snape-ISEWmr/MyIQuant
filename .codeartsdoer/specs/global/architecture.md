# 架构全景

![系统架构](./images/03-system-architecture.png)

## 系统组件
- **策略引擎**：init()初始化 + handlebar()逐K线执行
- **行情模块**：实时行情订阅和推送（quoter/）
- **交易模块**：订单管理、持仓管理、账户管理
- **回测引擎**：历史数据回放、绩效评估
- **风控模块**：止损止盈、仓位控制、资金管理

## 模块划分
- **python/**：策略脚本主目录
  - **策略文件**：网格策略.py、双均线实盘示例PY.py、商品期货的套利策略.py等
  - **工具库**：iQuant_functools.py（账户查询）、iQuantTDX.py（通达信接口）
  - **策略模块**：STOQ.py、STOM.py、STOA.py
- **config/**：平台配置文件
- **data/**：历史数据和回测数据
- **userdata/**：用户账户和交易数据（禁止修改）

## 数据流
![数据流](./images/04-data-flow.png)

行情数据 → 策略handlebar() → 信号计算 → 订单生成 → 交易执行 → 持仓更新

## 外部集成
- **iQuant API**：通过ContextInfo接口调用平台功能
- **通达信**：iQuantTDX模块封装通达信行情和交易接口
- **vnpy**：部分策略使用vnpy_portfoliostrategy框架

## 部署拓扑
- **客户端**：iQuant终端运行Python策略脚本
- **数据源**：行情服务器、交易服务器
- **本地存储**：userdata/存储账户和交易记录

---
*最后更新: 2026-06-23 — 初始化生成*