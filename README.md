# Quant Stock Tool

一个轻量级股票量化研究工具，当前支持：

- CSV 日线数据导入
- 移动均线交叉策略
- 固定比例仓位控制
- 手续费、滑点、止损风控
- 回测指标：总收益、年化收益、最大回撤、胜率、夏普比率
- CLI 命令行运行

> 这不是投资建议，也不保证盈利。默认流程只用于研究、回测和模拟交易，真实资金接入前需要做更多测试、合规和风控。

## 快速开始

```bash
cd "/Users/ys/Documents/New project/quant-stock-tool"
python3 -m quanttool.cli backtest --data examples/sample_aapl.csv --cash 100000
```

## 实时网站

启动本地网站：

```bash
cd "/Users/ys/Documents/New project/quant-stock-tool"
python3 server.py
```

然后打开：

```text
http://127.0.0.1:8765
```

可选 API Key：

```bash
export ALPHA_VANTAGE_API_KEY="你的 Alpha Vantage key"
export POLYGON_API_KEY="你的 Polygon key"
export FINNHUB_API_KEY="你的 Finnhub key"
python3 server.py
```

未配置 API Key 时，网站仍会尝试 Yahoo Finance 的公开行情接口；其他数据源会显示为未启用。实际是否能做到每秒真实更新，取决于数据套餐、交易时段、限流和交易所授权。

实时榜单里的“Next-day score”是模型评分，不是第二天必涨的承诺。当前评分综合了当日涨幅、盘中强度、开盘跳空、日内区间位置、成交量量级和多数据源一致性。

## 部署到 finance.trysql.us

这是一个带 Python 后端的实时网站，部署平台需要支持长驻 Web 服务，不能只用静态网站托管。服务已经支持云平台常见的 `PORT` 环境变量。

推荐部署方式之一是 Render / Railway / Fly.io：

```bash
HOST=0.0.0.0 PORT=8765 python server.py
```

Docker 部署：

```bash
docker build -t quant-stock-tool .
docker run -p 8765:8765 \
  -e HOST=0.0.0.0 \
  -e FINNHUB_API_KEY="你的 Finnhub key" \
  -e ALPHA_VANTAGE_API_KEY="你的 Alpha Vantage key" \
  -e POLYGON_API_KEY="你的 Polygon key" \
  quant-stock-tool
```

域名设置：

- 在托管平台添加自定义域名 `finance.trysql.us`
- 到 `trysql.us` 的 DNS 管理里新增平台要求的 `CNAME` 或 `A` 记录
- 开启平台自动签发的 HTTPS 证书

## CSV 格式

需要这些列名：

```csv
date,open,high,low,close,volume
2025-01-02,100,102,99,101,1000000
```

## 示例命令

```bash
python3 -m quanttool.cli backtest \
  --data examples/sample_aapl.csv \
  --cash 100000 \
  --fast 5 \
  --slow 20 \
  --position-pct 0.95 \
  --stop-loss-pct 0.08 \
  --fee-bps 1 \
  --slippage-bps 2
```

## 后续可以扩展

- 接入数据源：Polygon、Alpha Vantage、Yahoo Finance、Tushare、AkShare
- 策略库：动量、均值回归、多因子、配对交易
- 投组层：多股票调仓、行业/因子暴露约束
- 模拟交易：记录订单、成交、持仓和每日权益
- 实盘接口：Alpaca、Interactive Brokers、富途、华泰等
