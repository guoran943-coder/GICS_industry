"""Shared helpers for ThroatScan-compatible GICS JSON responses."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_STATIC_MAP = SCRIPT_DIR / "data" / "throatscan-gics-cache.json"


def classification_from_path(path: list[dict[str, Any]]) -> dict[str, str | None]:
    by_level = {row["level"]: row for row in path}

    def pick(level: int, field: str) -> str | None:
        row = by_level.get(level)
        if not row:
            return None
        value = row.get(field)
        return value or None

    return {
        "sector": pick(1, "name_en") or "",
        "industry_group": pick(2, "name_en") or "",
        "industry": pick(3, "name_en") or "",
        "sub_industry": pick(4, "name_en"),
        "sector_zh": pick(1, "name_zh"),
        "industry_group_zh": pick(2, "name_zh"),
        "industry_zh": pick(3, "name_zh"),
        "sub_industry_zh": pick(4, "name_zh"),
    }


def path_from_code(gics_code: str, categories: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    prefixes: list[str] = []
    if len(gics_code) >= 2:
        prefixes.append(gics_code[0:2])
    if len(gics_code) >= 4:
        prefixes.append(gics_code[0:4])
    if len(gics_code) >= 6:
        prefixes.append(gics_code[0:6])
    if len(gics_code) >= 8:
        prefixes.append(gics_code[0:8])
    return [categories[code] for code in prefixes if code in categories]


@lru_cache(maxsize=1)
def load_static_categories() -> dict[str, dict[str, Any]]:
    seed_path = Path(os.environ.get("GICS_SEED_PATH", SCRIPT_DIR / "gics_seed.json"))
    with seed_path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    return {row["code"]: row for row in rows}


@lru_cache(maxsize=1)
def load_static_ticker_map() -> dict[str, dict[str, Any]]:
    map_path = Path(os.environ.get("GICS_STATIC_MAP_PATH", DEFAULT_STATIC_MAP))
    if not map_path.exists():
        return {}
    with map_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("tickers", {})


def lookup_static_classification(ticker: str) -> dict[str, Any] | None:
    entry = load_static_ticker_map().get(ticker.upper())
    if not entry:
        return None
    classification = {
        "sector": entry.get("sector", ""),
        "industry_group": entry.get("industry_group", ""),
        "industry": entry.get("industry", ""),
        "sub_industry": entry.get("sub_industry"),
        "sector_zh": entry.get("sector_zh"),
        "industry_group_zh": entry.get("industry_group_zh"),
        "industry_zh": entry.get("industry_zh"),
        "sub_industry_zh": entry.get("sub_industry_zh"),
    }
    return {
        "ticker": ticker.upper(),
        "gics_code": entry.get("gics_code"),
        "company_name": entry.get("company_name"),
        "description": entry.get("description"),
        "classification": classification,
        "source": "static_map",
    }


def lookup_database_classification(ticker: str) -> dict[str, Any] | None:
    import db  # noqa: WPS433

    result = db.get_company_classification_path(ticker)
    if not result:
        return None

    company = result["company"]
    path = result["path"]
    if len(path) < 4:
        return None

    return {
        "ticker": company["ticker"].upper(),
        "gics_code": company.get("gics_code"),
        "company_name": company.get("name"),
        "description": company.get("description"),
        "classification": classification_from_path(path),
        "source": "database",
    }


def lookup_ticker_classification(ticker: str) -> dict[str, Any] | None:
    ticker = ticker.upper()
    try:
        payload = lookup_database_classification(ticker)
        if payload:
            return payload
    except Exception:
        pass
    return lookup_static_classification(ticker)
