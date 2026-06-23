import os
import json
from mcp.server.fastmcp import FastMCP
import db

# Create the FastMCP instance
mcp = FastMCP("GICS Industry Classification Server")

# Get default seed path relative to this script
DEFAULT_SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gics_seed.json")

@mcp.tool()
def init_database() -> str:
    """
    Initialize the database schema and tables for GICS.
    Creates schema 'gics', table 'gics.categories', and table 'gics.companies' in PostgreSQL.
    """
    try:
        db.init_db()
        return "SUCCESS: Database initialized successfully. Schema 'gics' and tables 'categories', 'companies' created."
    except Exception as e:
        return f"ERROR: Failed to initialize database: {str(e)}"

@mcp.tool()
def sync_gics_categories(seed_path: str = None) -> str:
    """
    Sync GICS categories from a JSON seed file to the database.
    If seed_path is not specified, it defaults to the local 'gics_seed.json'.
    """
    path_to_use = seed_path if seed_path else DEFAULT_SEED_PATH
    
    if not os.path.exists(path_to_use):
        return f"ERROR: Seed file not found at {path_to_use}. Please verify the path."
    
    try:
        with open(path_to_use, "r", encoding="utf-8") as f:
            categories = json.load(f)
            
        count = 0
        for cat in categories:
            db.upsert_gics_category(
                code=cat["code"],
                name_en=cat["name_en"],
                name_zh=cat.get("name_zh"),
                level=cat["level"],
                parent_code=cat.get("parent_code")
            )
            count += 1
            
        return f"SUCCESS: Synced {count} GICS categories from {path_to_use}."
    except Exception as e:
        return f"ERROR: Failed to sync categories: {str(e)}"

@mcp.tool()
def get_company_classification(ticker: str) -> str:
    """
    Get the full GICS classification path (Level 1 to Level 4) for a company by its stock ticker (e.g. 'AAPL', 'MSFT').
    """
    try:
        result = db.get_company_classification_path(ticker)
        if not result:
            return f"INFO: Company with ticker '{ticker.upper()}' was not found in the database. Use 'update_company_gics' to add it."
        
        company = result["company"]
        path = result["path"]
        
        output = []
        output.append(f"### Company: {company['name']} ({company['ticker']})")
        if company['description']:
            output.append(f"**Description**: {company['description']}")
        output.append("")
        output.append("#### GICS Classification Path:")
        
        if not path:
            output.append("* No GICS classification path assigned yet.")
        else:
            for item in path:
                level_names = {1: "Sector (一级板块)", 2: "Industry Group (二级行业组)", 3: "Industry (三级行业)", 4: "Sub-Industry (四级子行业)"}
                level_str = level_names.get(item['level'], f"Level {item['level']}")
                zh_part = f" / {item['name_zh']}" if item['name_zh'] else ""
                output.append(f"- **{level_str}** [{item['code']}]: {item['name_en']}{zh_part}")
                
        return "\n".join(output)
    except Exception as e:
        return f"ERROR: Failed to fetch company classification: {str(e)}"

@mcp.tool()
def get_companies_by_gics(gics_code: str) -> str:
    """
    Get all companies belonging to a GICS category code.
    Supports prefix matching, e.g. '45' for all technology companies, '4520' for hardware.
    """
    try:
        companies = db.get_companies_by_gics_code(gics_code)
        if not companies:
            return f"INFO: No companies found belonging to GICS code '{gics_code}' or its children."
        
        output = []
        output.append(f"### Companies under GICS code '{gics_code}' (found {len(companies)}):")
        output.append("")
        output.append("| Ticker | Company Name | GICS Code | Industry (EN) | Industry (ZH) |")
        output.append("|---|---|---|---|---|")
        
        for c in companies:
            zh_part = c['industry_name_zh'] if c['industry_name_zh'] else "-"
            en_part = c['industry_name_en'] if c['industry_name_en'] else "-"
            output.append(f"| {c['ticker']} | {c['name']} | {c['gics_code']} | {en_part} | {zh_part} |")
            
        return "\n".join(output)
    except Exception as e:
        return f"ERROR: Failed to fetch companies by GICS code: {str(e)}"

@mcp.tool()
def update_company_gics(ticker: str, name: str, gics_code: str, description: str = None) -> str:
    """
    Add a new company or update an existing company's GICS code and description.
    ticker: Stock symbol (e.g. 'NVDA')
    name: Company name (e.g. 'NVIDIA Corporation')
    gics_code: 8-digit GICS sub-industry code (e.g. '45301020')
    description: Optional business description
    """
    try:
        db.upsert_company(ticker, name, gics_code, description)
        return f"SUCCESS: Upserted company {name} ({ticker.upper()}) mapped to GICS code {gics_code}."
    except psycopg.errors.ForeignKeyViolation:
        return f"ERROR: GICS code '{gics_code}' does not exist in the categories table. Please sync categories first or check the code."
    except Exception as e:
        return f"ERROR: Failed to update company: {str(e)}"

if __name__ == "__main__":
    mcp.run()
