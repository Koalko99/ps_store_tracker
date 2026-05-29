import json

import pytest

from app.core.config import load_settings


def test_load_settings_from_json(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "max_retries": 5,
                "request_timeout": 30,
                "regions": [{"code": "en-tr", "divide_price_by_100": False}],
                "PROXIES": ["https://proxy.example", "socks5://ignored"],
            },
        ),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.max_retries == 5
    assert settings.request_timeout == 30
    assert settings.region_codes == ["en-tr"]
    assert settings.proxies == ["https://proxy.example"]


def test_load_settings_rejects_invalid_region(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"regions": [{"code": "bad", "divide_price_by_100": False}]}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Invalid application settings"):
        load_settings(config_path)
