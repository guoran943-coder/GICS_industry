#!/usr/bin/env python3
"""
Export S&P 500 GICS mappings for ThroatScan Oracle (Phase 1 — static sync).

Uses gics_seed.json + Wikipedia S&P 500 table. PostgreSQL is optional:
when DATABASE_URL is reachable, exports from gics.companies instead.

Default output:
  ../agent_hub/projects/throatscan-oracle/data/gics-sp500-map.json
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SEED = SCRIPT_DIR / "gics_seed.json"
DEFAULT_OUT = (
    SCRIPT_DIR.parent
    / "agent_hub"
    / "projects"
    / "throatscan-oracle"
    / "data"
    / "gics-sp500-map.json"
)

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

SUB_INDUSTRY_OVERRIDES = {
    "biotechnology": "35201010",
    "pharmaceutical": "35202010",
    "semiconductor": "45301020",
    "applicationsoftware": "45103010",
    "systemsoftware": "45103020",
    "technologyhardwarestorageandperipheral": "45202030",
    "interactivemediaandservice": "50203010",
    "beverage": "30201010",
}


def clean_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower().replace("&", "and")
    name = re.sub(r"[^a-z0-9]", "", name)
    if name.endswith("s"):
        name = name[:-1]
    return name


def load_categories(seed_path: Path) -> dict[str, dict]:
    with seed_path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    return {row["code"]: row for row in rows}


def path_from_code(gics_code: str, categories: dict[str, dict]) -> list[dict]:
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


def classification_from_path(path: list[dict]) -> dict[str, str | None]:
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


def export_from_database(categories: dict[str, dict]) -> tuple[dict, dict]:
    import db  # noqa: WPS433 — optional dependency when Postgres is available

    tickers: dict[str, dict] = {}
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker, name, gics_code, description
                FROM gics.companies
                WHERE gics_code IS NOT NULL
                ORDER BY ticker;
                """
            )
            rows = cur.fetchall()

    for row in rows:
        ticker = row["ticker"].upper()
        gics_code = row["gics_code"]
        path = path_from_code(gics_code, categories)
        if len(path) < 4:
            continue
        entry = classification_from_path(path)
        entry["gics_code"] = gics_code
        entry["company_name"] = row["name"]
        entry["description"] = row.get("description")
        tickers[ticker] = entry

    stats = {
        "mode": "database",
        "mapped": len(tickers),
        "source_rows": len(rows),
    }
    return tickers, stats


def fetch_wikipedia_html() -> bytes:
    headers = {"User-Agent": "ThroatScan-GICS-Export/1.0"}
    try:
        req = urllib.request.Request(WIKI_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
    except Exception as urllib_error:
        print(f"urllib fetch failed ({urllib_error}); trying curl…", file=sys.stderr)
        result = subprocess.run(
            ["curl", "-fsSL", "-A", headers["User-Agent"], WIKI_URL],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode("utf-8", errors="replace") or "curl failed") from urllib_error
        return result.stdout


def export_from_wikipedia(categories: dict[str, dict]) -> tuple[dict, dict]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise SystemExit("beautifulsoup4 is required for Wikipedia export. Run: pip install beautifulsoup4") from exc

    sub_industries = [row for row in categories.values() if row["level"] == 4]
    name_to_code = {clean_name(row["name_en"]): row["code"] for row in sub_industries}

    html = fetch_wikipedia_html()
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "constituents"})
    if not table:
        raise RuntimeError("Could not find S&P 500 constituents table on Wikipedia.")

    tickers: dict[str, dict] = {}
    unmapped: set[str] = set()
    rows = table.find_all("tr")[1:]

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        ticker = cols[0].text.strip().replace(".", "-").upper()
        company_name = cols[1].text.strip()
        gics_sector = cols[2].text.strip()
        gics_sub_industry_name = cols[3].text.strip()

        clean_sub = clean_name(gics_sub_industry_name)
        gics_code = name_to_code.get(clean_sub) or SUB_INDUSTRY_OVERRIDES.get(clean_sub)
        if not gics_code:
            unmapped.add(gics_sub_industry_name)
            continue

        path = path_from_code(gics_code, categories)
        if len(path) < 4:
            unmapped.add(gics_sub_industry_name)
            continue

        entry = classification_from_path(path)
        entry["gics_code"] = gics_code
        entry["company_name"] = company_name
        entry["description"] = (
            f"S&P 500 constituent. Sector: {gics_sector}; sub-industry: {gics_sub_industry_name}."
        )
        tickers[ticker] = entry

    stats = {
        "mode": "wikipedia",
        "mapped": len(tickers),
        "wiki_rows": len(rows),
        "unmapped_sub_industries": sorted(unmapped),
        "unmapped_count": len(unmapped),
    }
    return tickers, stats


def main() -> None:
    out_path = Path(os.environ.get("THROATSCAN_GICS_OUT", DEFAULT_OUT))
    seed_path = Path(os.environ.get("GICS_SEED_PATH", DEFAULT_SEED))

    if not seed_path.exists():
        raise SystemExit(f"Seed file not found: {seed_path}")

    categories = load_categories(seed_path)
    tickers: dict[str, dict]
    stats: dict

    use_db = os.environ.get("GICS_EXPORT_MODE", "auto").lower()
    if use_db in {"db", "database"}:
        tickers, stats = export_from_database(categories)
    elif use_db in {"wiki", "wikipedia"}:
        tickers, stats = export_from_wikipedia(categories)
    else:
        try:
            import db  # noqa: WPS433

            db.get_connection().close()
            tickers, stats = export_from_database(categories)
        except ImportError:
            print("psycopg not installed — using Wikipedia + gics_seed.json", file=sys.stderr)
            tickers, stats = export_from_wikipedia(categories)
        except Exception:
            print("PostgreSQL unavailable — falling back to Wikipedia + gics_seed.json", file=sys.stderr)
            tickers, stats = export_from_wikipedia(categories)

    payload = {
        "schema_version": "throatscan-gics-sp500-v1",
        "source": "gics_industry",
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "gics_seed_path": str(seed_path.name),
        "stats": stats,
        "tickers": tickers,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    cache_path = Path(
        os.environ.get(
            "GICS_STATIC_CACHE_OUT",
            SCRIPT_DIR / "data" / "throatscan-gics-cache.json",
        )
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {len(tickers)} ticker mappings → {out_path}")
    print(f"Wrote API static cache → {cache_path}")
    print(f"Mode: {stats.get('mode')} | mapped: {stats.get('mapped')}")


if __name__ == "__main__":
    main()
