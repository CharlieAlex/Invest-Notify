# Invest Notify

本地執行的台股追蹤工具：
- 定期抓取指定股票價格（可切換 `mock` / `twse`）
- 儲存價格資料到本地 CSV
- 繪製近 3 個月趨勢圖（seaborn）

## 快速開始

```bash
make init
cp config/stocks.example.yaml config/stocks.yaml
make fetch
make plot
```

## 指令

```bash
make run      # 常駐排程
make fetch    # 立即抓一次
make plot     # 畫近 3 個月圖
make test
make lint
```
