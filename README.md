# Invest Notify

本地執行的股票追蹤工具：
- 定期抓取指定股票價格（可切換 `mock` / `twse` / `live`）
- 支援上市（TWSE）、上櫃（TPEx）、興櫃（ESB）與美股（NASDAQ ticker）
- 儲存價格資料到本地 CSV（覆蓋）與 SQLite（upsert 累積）
- 輸出單檔個股圖與市場分組子圖（`n x 3`）
- 繪製近 3 個月趨勢圖（seaborn）

## 快速開始

```bash
make init
cp config/stocks.example.yaml config/stocks.yaml
make fetch
make plot
```

## stocks.yaml 範例

```yaml
twse_stock:
  - "0050"
  - "0056"
tpex_stock:
  - "6462"
esb_stock:
  - "5297"
nasdaq_stock:
  - "QQQ"
```

## 指令

```bash
make run      # 常駐排程
make fetch    # 立即抓一次
make plot     # 畫近 3 個月圖
make test
make lint
```
