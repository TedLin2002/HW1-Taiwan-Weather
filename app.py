"""Taiwan weather dashboard powered by CWA Open Data."""

from __future__ import annotations

import os
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv
from cwa_client import cwa_forecast

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "weather_history.db"
load_dotenv(APP_DIR / ".env")
CITIES = {
    "臺北市": (25.0330, 121.5654), "新北市": (25.0169, 121.4628),
    "桃園市": (24.9936, 121.3010), "臺中市": (24.1477, 120.6736),
    "臺南市": (22.9999, 120.2269), "高雄市": (22.6273, 120.3014),
    "基隆市": (25.1276, 121.7392), "新竹市": (24.8138, 120.9675),
    "嘉義市": (23.4801, 120.4491), "新竹縣": (24.8387, 121.0177),
    "苗栗縣": (24.5602, 120.8214), "彰化縣": (24.0518, 120.5161),
    "南投縣": (23.9609, 120.9719), "雲林縣": (23.7092, 120.4313),
    "嘉義縣": (23.4589, 120.2919), "屏東縣": (22.5519, 120.5487),
    "宜蘭縣": (24.7021, 121.7378), "花蓮縣": (23.9872, 121.6015),
    "臺東縣": (22.7972, 121.0714), "澎湖縣": (23.5711, 119.5793),
    "金門縣": (24.4493, 118.3767), "連江縣": (26.1605, 119.9517),
}


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            searched_at TEXT NOT NULL,
            city TEXT NOT NULL,
            summary TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at TEXT NOT NULL,
            city TEXT NOT NULL,
            forecast_time TEXT NOT NULL,
            weather TEXT NOT NULL,
            temperature_c REAL,
            precipitation_probability REAL,
            source TEXT NOT NULL,
            UNIQUE (city, forecast_time, source)
        )""")


def save_search(city: str, summary: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO searches (searched_at, city, summary) VALUES (?, ?, ?)",
            (datetime.now().astimezone().isoformat(timespec="seconds"), city, summary),
        )


def read_history() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT searched_at AS 查詢時間, city AS 縣市, summary AS 預報摘要 "
            "FROM searches ORDER BY id DESC LIMIT 10", conn
        )


def save_forecast(city: str, forecast: pd.DataFrame, source: str) -> None:
    fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")
    rows = []
    for _, item in forecast.iterrows():
        forecast_time = pd.Timestamp(item["時間"]).isoformat()
        temperature = pd.to_numeric(item["溫度(°C)"], errors="coerce")
        precipitation = pd.to_numeric(item["降雨機率(%)"], errors="coerce")
        rows.append((
            fetched_at, city, forecast_time, str(item["天氣"]),
            None if pd.isna(temperature) else float(temperature),
            None if pd.isna(precipitation) else float(precipitation), source,
        ))
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany("""INSERT INTO forecasts
            (fetched_at, city, forecast_time, weather, temperature_c,
             precipitation_probability, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(city, forecast_time, source) DO UPDATE SET
              fetched_at=excluded.fetched_at, weather=excluded.weather,
              temperature_c=excluded.temperature_c,
              precipitation_probability=excluded.precipitation_probability""", rows)


def read_saved_forecasts(city: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("""SELECT forecast_time AS 預報時間,
            weather AS 天氣, temperature_c AS 溫度_C,
            precipitation_probability AS 降雨機率_pct, source AS 資料來源
            FROM forecasts WHERE city=? ORDER BY forecast_time LIMIT 12""",
            conn, params=(city,))


def configured_cwa_key() -> str:
    key = os.getenv("CWA_API_KEY", "").strip()
    if key:
        return key
    try:
        return str(st.secrets.get("CWA_API_KEY", "")).strip()
    except Exception:
        # Streamlit secrets are optional for local/offline use.
        return ""


def demo_forecast(city: str) -> pd.DataFrame:
    """Clearly labelled fallback data for trying the UI without an API key."""
    now = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
    conditions = ["多雲", "晴時多雲", "短暫陣雨", "多雲"]
    base = 27 + list(CITIES).index(city) % 5
    return pd.DataFrame([
        {"時間": now + timedelta(hours=6 * i), "天氣": conditions[i],
         "溫度(°C)": base + (1 if i == 1 else 0) - (2 if i == 3 else 0),
         "降雨機率(%)": [20, 10, 40, 30][i]}
        for i in range(4)
    ])


st.set_page_config(page_title="台灣天氣預報", page_icon="🌦️", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
.block-container { max-width: 1200px; padding-top: 2.5rem; }
</style>""", unsafe_allow_html=True)
init_db()

with st.sidebar:
    st.title("🌦️ 天氣設定")
    city = st.selectbox("選擇縣市", list(CITIES))
    entered_api_key = st.text_input("CWA API 授權碼（可留空使用伺服器設定）", value="", type="password",
                                    help="可在本機 .env 或部署平台 Secrets 設定；輸入欄不會預載伺服器金鑰。")
    api_key = entered_api_key.strip() or configured_cwa_key()
    refresh = st.button("更新天氣資料", type="primary", use_container_width=True)
    st.caption("資料來源：中央氣象署開放資料平台。無金鑰時使用示範資料。")

st.title("台灣天氣預報")
st.markdown("##### 各縣市天氣一覽 · 36 小時預報")

if refresh:
    st.cache_data.clear()

@st.cache_data(ttl=900, show_spinner=False)
def get_forecast(selected_city: str, key: str) -> tuple[pd.DataFrame, str]:
    if key:
        return cwa_forecast(selected_city, key), "中央氣象署即時資料"
    return demo_forecast(selected_city), "示範資料（尚未設定 API 金鑰）"

try:
    forecast, source = get_forecast(city, api_key)
except (requests.RequestException, ValueError, KeyError) as exc:
    # Keep diagnostics useful in Streamlit Cloud without ever logging the key,
    # response body, or exception text (which may contain sensitive details).
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        diagnostic = f"HTTP {exc.response.status_code}"
    elif isinstance(exc, requests.Timeout):
        diagnostic = "request timeout"
    elif isinstance(exc, requests.ConnectionError):
        diagnostic = "connection error"
    else:
        diagnostic = type(exc).__name__
    logging.warning("CWA query failed (%s)", diagnostic)
    forecast, source = demo_forecast(city), "示範資料"

first = forecast.iloc[0]
save_forecast(city, forecast, source)
search_signature = (city, source, str(forecast.iloc[0]["時間"]))
if st.session_state.get("last_logged_search") != search_signature:
    save_search(city, f"{first['天氣']}，{first['溫度(°C)']}°C")
    st.session_state["last_logged_search"] = search_signature
lat, lon = CITIES[city]
st.caption(f"{city} · 資料來源：{source} · 更新時間：{datetime.now().astimezone():%Y-%m-%d %H:%M %Z}")

c1, c2, c3 = st.columns(3)
c1.metric("目前預報", str(first["天氣"]))
c2.metric("預報溫度", f"{first['溫度(°C)']} °C" if pd.notna(first["溫度(°C)"]) else "—")
c3.metric("降雨機率", f"{first['降雨機率(%)']} %" if pd.notna(first["降雨機率(%)"]) else "—")

left, right = st.columns([1, 1.35])
with left:
    st.subheader("縣市位置")
    map_data = pd.DataFrame([{"lat": coords[0], "lon": coords[1], "縣市": name}
                             for name, coords in CITIES.items()])
    st.map(map_data, latitude="lat", longitude="lon", color="#1687a7", size=100,
           zoom=5, use_container_width=True)
with right:
    st.subheader("未來天氣趨勢")
    chart_data = forecast.dropna(subset=["溫度(°C)"])
    if not chart_data.empty:
        fig = px.line(chart_data, x="時間", y="溫度(°C)", markers=True,
                      color_discrete_sequence=["#1687a7"], hover_data=["天氣", "降雨機率(%)"])
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), yaxis_title="溫度 (°C)",
                          xaxis_title="預報時間", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("目前沒有溫度資料可繪製圖表。")

st.subheader("預報明細")
display = forecast.copy()
display["時間"] = pd.to_datetime(display["時間"]).dt.strftime("%m/%d %H:%M")
st.dataframe(display, hide_index=True, use_container_width=True)

with st.expander("最近查詢紀錄（SQLite）"):
    history = read_history()
    if history.empty:
        st.caption("尚無查詢紀錄。")
    else:
        st.dataframe(history, hide_index=True, use_container_width=True)

with st.expander("此縣市已儲存的預報資料（SQLite）"):
    saved_forecasts = read_saved_forecasts(city)
    if saved_forecasts.empty:
        st.caption("尚無已儲存的預報資料。")
    else:
        st.dataframe(saved_forecasts, hide_index=True, use_container_width=True)

st.divider()
st.caption("HW1 · Streamlit × Python × SQLite · 預報僅供參考，請以中央氣象署最新公告為準。")
