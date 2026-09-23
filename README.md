# HW1｜台灣天氣預報

以 Streamlit、Python、SQLite 與中央氣象署（CWA）開放資料 API 製作的互動式天氣儀表板。可查看台灣各縣市的位置、36 小時天氣預報與最近查詢紀錄。

## 功能

- 選擇縣市，讀取中央氣象署 36 小時天氣預報（資料集 `F-C0032-001`）。
- 以互動地圖呈現縣市位置，並用圖表比較未來各時段溫度。
- 將查詢紀錄與每個預報時段的天氣、溫度、降雨機率及來源存入本機 SQLite 資料庫 `weather_history.db`。
- 未設定 API 金鑰或 API 暫時無法連線時，以內建示範資料展示介面；畫面會清楚標記資料來源。
- 使用 VCR cassette 回放固定的合成 CWA 回應，離線驗證資料解析；cassette 不含真實授權碼。API 金鑰使用 HTTP Authorization 標頭，不放在 URL。

## 執行方式

需要 Python 3.10 或更新版本。

```bash
cd HW1
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

設定 CWA API 授權碼（至[中央氣象署開放資料平台](https://opendata.cwa.gov.tw/)申請）：

複製 `.env.example` 為 `.env`，填入授權碼：

```dotenv
CWA_API_KEY=你的授權碼
```

應用程式啟動時會自動載入 `.env`。也可以用環境變數覆寫，或在 Streamlit 側邊欄輸入：

```powershell
$env:CWA_API_KEY="你的授權碼"
streamlit run app.py
```

macOS / Linux：`export CWA_API_KEY="你的授權碼"` 後執行 `streamlit run app.py`。也可以在 Streamlit 側邊欄輸入授權碼；金鑰不會寫入資料庫。

部署到 Streamlit Community Cloud 時，請在 app 的 **Settings → Secrets** 設定 `CWA_API_KEY = "你的授權碼"`。應用程式從伺服器端讀取 Secrets，不會將該值預填到瀏覽器欄位，也不要把金鑰提交到 GitHub。

未設定金鑰時仍可執行，應用程式會使用標示為「示範資料」的範例預報。`.env`、SQLite 資料庫與虛擬環境均不應上傳 GitHub。開發階段與驗收關卡見 [workflow.md](workflow.md)。

## 離線回放檢查

安裝開發依賴並回放 VCR cassette（不會連線至 CWA）：

```powershell
pip install -r requirements-dev.txt
python -m pytest -q -p no:cacheprovider
```

## 專案結構

```text
HW1/
├── app.py                 # Streamlit 介面、CWA API、地圖與圖表
├── cwa_client.py          # CWA API 用戶端與回應解析
├── workflow.md            # 開發階段與驗收關卡
├── requirements-dev.txt   # pytest 與 VCR 開發依賴
└── tests/                 # VCR 回放檢查與不含金鑰的 cassette
    └── cassettes/
```

SQLite 資料庫會在首次執行後自動建立，已加入 `.gitignore`，不會被提交到 Git。
