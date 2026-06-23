# 项目架构约束

![技术栈概览](./images/06-tech-stack.png)

## 技术栈
- **语言**：Python 3.x
- **编码声明**：所有Python文件必须使用 `#coding:gbk` 或 `#encoding:gbk`
- **量化平台**：国信iQuant策略交易平台
- **回测框架**：vnpy（部分策略）
- **技术指标库**：talib、numpy

## 架构决策
- **目录结构**：严格遵循项目固定目录结构，禁止新增/删除/重命名一级、二级目录
- **策略接口**：所有策略必须实现 `init(ContextInfo)` 和 `handlebar(ContextInfo)` 两个核心函数
- **编码规范**：遵循项目现有命名风格（函数小写+下划线，类大驼峰）

## API 风格
- **策略接口**：ContextInfo对象传递策略上下文
- **行情接口**：通过ContextInfo.get_market_data等函数获取
- **交易接口**：通过ContextInfo.order_buy、order_sell等函数执行

## 编码规范
- **命名约定**：
  - 函数名：小写+下划线（handle_bar、get_market_data）
  - 变量名：小写+下划线（close_price、bar_pos）
  - 类名：大驼峰（ContextInfo、StrategyBase）
  - 常量：全大写+下划线（MAX_POSITIONS、DEFAULT_PERIOD）
- **文件组织**：
  1. 编码声明（#coding:gbk）
  2. 导入模块
  3. 全局变量声明
  4. 辅助函数定义
  5. 核心函数（init、handlebar）

## 部署方式
- **运行环境**：iQuant客户端Python解释器
- **策略部署**：将.py文件放入python/目录，通过iQuant终端加载运行

## 安全约束
- **禁止修改**：luaScripts/、userdata/、userdata_mini/、license/、customerDLL/、bin.x64/
- **敏感信息**：账户信息、密码、API密钥禁止提交到Git
- **未来函数禁令**：严禁使用未来函数（repainting indicators）
- **风控不可绕过**：止损逻辑不得被注释或条件跳过

---
*最后更新: 2026-06-23 — 初始化生成*