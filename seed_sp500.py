import urllib.request
import re
import json
from bs4 import BeautifulSoup
import db

def clean_name(name):
    """Normalize string for soft matching: lowercase, alphanumeric only, deal with plurals."""
    if not name:
        return ""
    name = name.lower()
    name = name.replace("&", "and")
    # Remove punctuation and whitespace
    name = re.sub(r'[^a-z0-9]', '', name)
    # Strip trailing 's' for soft plural matching (e.g. Semiconductors vs Semiconductor)
    if name.endswith('s'):
        name = name[:-1]
    return name

def main():
    # 1. Fetch GICS leaf categories from database to build matching dictionary
    print("Loading GICS categories from database...")
    categories = db.get_all_categories()
    
    # We map companies to Level 4 (Sub-Industry) codes
    sub_industries = [c for c in categories if c["level"] == 4]
    
    name_to_code = {}
    for sub in sub_industries:
        clean = clean_name(sub["name_en"])
        name_to_code[clean] = sub["code"]
        
    print(f"Loaded {len(sub_industries)} leaf GICS sub-industries.")

    # 2. Fetch and parse S&P 500 companies from Wikipedia
    wiki_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    print(f"Fetching S&P 500 constituents from Wikipedia: {wiki_url}...")
    
    req = urllib.request.Request(
        wiki_url, 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read()
    except Exception as e:
        print(f"ERROR: Failed to download Wikipedia page: {e}")
        return

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "constituents"})
    if not table:
        print("ERROR: Could not find the constituents table on Wikipedia.")
        return

    rows = table.find_all("tr")[1:] # Skip header
    print(f"Found {len(rows)} company rows in table. Processing and mapping...")

    success_count = 0
    fail_count = 0
    missing_mappings = set()

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
            
        # Extract data columns
        ticker = cols[0].text.strip().replace('.', '-') # Wikipedia sometimes uses dots for classes, e.g., BRK.B
        company_name = cols[1].text.strip()
        gics_sector = cols[2].text.strip()
        gics_sub_industry_name = cols[3].text.strip()
        
        # Determine GICS Code
        clean_sub_name = clean_name(gics_sub_industry_name)
        gics_code = name_to_code.get(clean_sub_name)
        
        # Soft fallback: try matching with the sector/industry group if sub-industry name mismatch
        if not gics_code:
            # Let's try some manual overrides for common Wikipedia GICS name discrepancies
            overrides = {
                "biotechnology": "35201010",
                "pharmaceutical": "35202010",
                "semiconductor": "45301020",
                "applicationsoftware": "45103010",
                "systemsoftware": "45103020",
                "technologyhardwarestorageandperipheral": "45202030",
                "interactivemediaandservice": "50203010",
                "beverage": "30201010"
            }
            gics_code = overrides.get(clean_sub_name)
            
        if gics_code:
            try:
                # Add to DB
                db.upsert_company(
                    ticker=ticker,
                    name=company_name,
                    gics_code=gics_code,
                    description=f"S&P 500 Constituent. Sector: {gics_sector}, Sub-Industry: {gics_sub_industry_name}."
                )
                success_count += 1
            except Exception as e:
                print(f"Failed to insert {ticker}: {e}")
                fail_count += 1
        else:
            fail_count += 1
            missing_mappings.add(gics_sub_industry_name)

    print("-" * 50)
    print(f"Import complete!")
    print(f"Successfully mapped & imported: {success_count} companies.")
    print(f"Failed or unmapped: {fail_count} companies.")
    if missing_mappings:
        print(f"Unmapped GICS Sub-Industries ({len(missing_mappings)}):")
        for m in sorted(missing_mappings):
            print(f"  - {m}")
            
if __name__ == "__main__":
    main()
