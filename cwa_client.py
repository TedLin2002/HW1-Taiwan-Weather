"""Client and response parsing for the CWA county forecast endpoint."""

import pandas as pd
import requests

API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"


def cwa_forecast(city: str, api_key: str) -> pd.DataFrame:
    response = requests.get(API_URL, params={"Authorization": api_key}, timeout=15)
    response.raise_for_status()
    payload = response.json()
    records = payload.get("records", {}).get("location", [])
    location = next((item for item in records if item.get("locationName") == city), None)
    if location is None:
        raise ValueError("API 回應中找不到所選縣市。")

    elements = {item["elementName"]: item.get("time", [])
                for item in location.get("weatherElement", [])}
    weather = elements.get("Wx", [])
    temps = elements.get("平均溫度", []) or elements.get("溫度", [])
    min_temps = elements.get("MinT", [])
    max_temps = elements.get("MaxT", [])
    rain = elements.get("PoP", [])
    if not weather:
        raise ValueError("API 沒有回傳可用的預報時段。")

    rows = []
    for index, period in enumerate(weather):
        start = period.get("startTime") or period.get("dataTime")
        if not start:
            continue
        try:
            when = pd.Timestamp(start)
        except ValueError:
            continue
        description = period.get("parameter", {}).get("parameterName", "資料未提供")
        temperature = temps[index].get("parameter", {}).get("parameterName") if index < len(temps) else None
        if temperature is None and index < len(min_temps) and index < len(max_temps):
            low = pd.to_numeric(min_temps[index].get("parameter", {}).get("parameterName"), errors="coerce")
            high = pd.to_numeric(max_temps[index].get("parameter", {}).get("parameterName"), errors="coerce")
            temperature = (low + high) / 2 if pd.notna(low) and pd.notna(high) else None
        probability = rain[index].get("parameter", {}).get("parameterName") if index < len(rain) else None
        rows.append({
            "時間": when,
            "天氣": description,
            "溫度(°C)": pd.to_numeric(temperature, errors="coerce"),
            "降雨機率(%)": pd.to_numeric(probability, errors="coerce"),
        })
    if not rows:
        raise ValueError("無法解析 API 預報資料。")
    return pd.DataFrame(rows)
