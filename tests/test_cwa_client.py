from pathlib import Path

import vcr

from cwa_client import cwa_forecast

CASSETTE = Path(__file__).parent / "cassettes" / "cwa_taipei.yaml"


def test_cwa_forecast_replays_recorded_response():
    cassette = vcr.VCR(
        record_mode="none",
        filter_query_parameters=[("Authorization", "REDACTED_TEST_TOKEN")],
        match_on=("method", "scheme", "host", "path"),
    )
    with cassette.use_cassette(str(CASSETTE)):
        # Synthetic credential matches the redacted cassette value; no real key is stored.
        forecast = cwa_forecast("臺北市", "REDACTED_TEST_TOKEN")

    assert len(forecast) == 2
    assert forecast.iloc[0]["天氣"] == "多雲"
    assert forecast.iloc[0]["溫度(°C)"] == 27
    assert forecast.iloc[0]["降雨機率(%)"] == 20
