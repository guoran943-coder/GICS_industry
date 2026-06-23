import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import db
import workflows.router
from gics_api_helpers import lookup_ticker_classification, load_static_ticker_map

app = FastAPI(title="GICS Classification API Server")

# Configure CORS so our Vue 3 frontend can access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CompanyCreate(BaseModel):
    ticker: str
    name: str
    gics_code: str
    description: Optional[str] = None

class ReportSave(BaseModel):
    report_md: str
    status: str = "completed"


class ClassificationBatchRequest(BaseModel):
    tickers: List[str] = Field(default_factory=list, max_length=64)


@app.get("/api/health")
def health_check():
    db_ok = False
    db_error = None
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        db_ok = True
    except Exception as exc:
        db_error = str(exc)

    static_map = load_static_ticker_map()
    return {
        "ok": db_ok or len(static_map) > 0,
        "service": "gics-industry-api",
        "database": {"ok": db_ok, "error": db_error},
        "static_map": {
            "ok": len(static_map) > 0,
            "ticker_count": len(static_map),
        },
    }


@app.get("/api/companies/{ticker}/classification")
def get_company_classification_json(ticker: str):
    """ThroatScan-compatible GICS classification JSON for one ticker."""
    payload = lookup_ticker_classification(ticker)
    if not payload:
        raise HTTPException(status_code=404, detail=f"No GICS classification found for {ticker.upper()}")
    return payload


@app.post("/api/companies/classifications")
def get_company_classifications_batch(body: ClassificationBatchRequest):
    """Batch GICS lookup for ThroatScan analyze pipeline."""
    results: dict[str, dict] = {}
    missing: list[str] = []
    for raw_ticker in body.tickers:
        ticker = raw_ticker.upper().strip()
        if not ticker:
            continue
        payload = lookup_ticker_classification(ticker)
        if payload:
            results[ticker] = payload
        else:
            missing.append(ticker)
    return {
        "count": len(results),
        "missing": missing,
        "results": results,
    }


@app.get("/api/gics/tree")
def get_gics_tree():
    """
    Constructs and returns the full hierarchical GICS tree
    with mapped companies and recursive company counts.
    """
    try:
        categories = db.get_all_categories()
        
        # Fetch all companies with report status
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.ticker, c.name, c.gics_code, c.description, r.status as report_status
                    FROM gics.companies c
                    LEFT JOIN gics.company_reports r ON c.ticker = r.ticker
                    ORDER BY c.ticker;
                """)
                companies = cur.fetchall()
                
        # Build node directory
        nodes = {}
        for cat in categories:
            code = cat["code"]
            nodes[code] = {
                "code": code,
                "name_en": cat["name_en"],
                "name_zh": cat["name_zh"],
                "level": cat["level"],
                "parent_code": cat["parent_code"],
                "companies": [],
                "children": [],
                "company_count": 0
            }
            
        # Attach companies to their leaf GICS sub-industry nodes
        for comp in companies:
            g_code = comp["gics_code"]
            if g_code in nodes:
                nodes[g_code]["companies"].append({
                    "ticker": comp["ticker"],
                    "name": comp["name"],
                    "description": comp["description"],
                    "report_status": comp.get("report_status")
                })
                
        # Build the tree relationships (Sector is root)
        roots = []
        for code, node in nodes.items():
            parent_code = node["parent_code"]
            if parent_code and parent_code in nodes:
                nodes[parent_code]["children"].append(node)
            else:
                roots.append(node)
                
        # Helper function to compute recursive company counts and sort children/companies
        def process_node(node):
            # Sort companies alphabetically by ticker
            node["companies"].sort(key=lambda x: x["ticker"])
            
            count = len(node["companies"])
            for child in node["children"]:
                count += process_node(child)
                
            # Sort children by code
            node["children"].sort(key=lambda x: x["code"])
            node["company_count"] = count
            return count

        for root in roots:
            process_node(root)
            
        # Sort roots (sectors) by code
        roots.sort(key=lambda x: x["code"])
        return roots
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate GICS tree: {str(e)}")

@app.get("/api/companies")
def get_all_companies():
    """Retrieve all companies and their GICS details."""
    try:
        sql = """
        SELECT c.ticker, c.name, c.gics_code, cat.name_en as industry_name_en, cat.name_zh as industry_name_zh, c.description, r.status as report_status
        FROM gics.companies c
        LEFT JOIN gics.categories cat ON c.gics_code = cat.code
        LEFT JOIN gics.company_reports r ON c.ticker = r.ticker
        ORDER BY c.ticker;
        """
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/companies")
def create_or_update_company(company: CompanyCreate):
    """Register or update a company's GICS classification."""
    try:
        db.upsert_company(
            ticker=company.ticker,
            name=company.name,
            gics_code=company.gics_code,
            description=company.description
        )
        return {"status": "success", "message": f"Company {company.ticker} upserted successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/companies/{ticker}")
def delete_company(ticker: str):
    """Delete a company mapping from the database."""
    try:
        ticker = ticker.upper()
        sql = "DELETE FROM gics.companies WHERE ticker = %s;"
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (ticker,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Company not found")
            conn.commit()
        return {"status": "success", "message": f"Company {ticker} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== GICS Reports & Progress APIs ====================

@app.get("/api/reports/{ticker}")
def get_company_report(ticker: str):
    """Retrieve a company's generated GICS analysis report."""
    try:
        report = db.get_report(ticker)
        if not report:
            raise HTTPException(status_code=404, detail=f"No report found for company {ticker.upper()}")
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reports/{ticker}")
def save_company_report(ticker: str, report: ReportSave):
    """Save or update a company's GICS analysis report."""
    try:
        db.upsert_report(ticker, report.report_md, report.status)
        return {"status": "success", "message": f"Report for {ticker.upper()} saved with status: {report.status}."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/progress")
def get_analysis_progress():
    """Get the overall analysis progress stats and lists of completed/pending tickers."""
    try:
        # Fetch all companies
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ticker, name, gics_code FROM gics.companies;")
                all_companies = cur.fetchall()
                
        # Fetch all reports status
        reports = db.get_all_reports()
        reports_map = {r["ticker"]: r["status"] for r in reports}
        
        completed = []
        processing = []
        failed = []
        pending = []
        
        for c in all_companies:
            ticker = c["ticker"]
            status = reports_map.get(ticker)
            
            comp_info = {"ticker": ticker, "name": c["name"], "gics_code": c["gics_code"]}
            if status == "completed":
                completed.append(comp_info)
            elif status == "processing":
                processing.append(comp_info)
            elif status == "failed":
                failed.append(comp_info)
            else:
                pending.append(comp_info)
                
        return {
            "total": len(all_companies),
            "completed_count": len(completed),
            "processing_count": len(processing),
            "failed_count": len(failed),
            "pending_count": len(pending),
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "pending": pending
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== AI Org & Workflow Router APIs ====================

@app.get("/api/gics/workflow/{ticker}")
def get_company_workflow(ticker: str):
    """
    Get the tailored system guidelines and suggested web search queries for a company 
    based on its GICS classification.
    """
    try:
        result = db.get_company_classification_path(ticker)
        if not result:
            raise HTTPException(status_code=404, detail=f"Company {ticker.upper()} not found.")
            
        company = result["company"]
        gics_code = company["gics_code"]
        
        # Get tailored workflow strategy class from the router
        strategy = workflows.router.get_workflow_for_gics(gics_code)
        
        return {
            "ticker": company["ticker"],
            "name": company["name"],
            "gics_code": gics_code,
            "sector_name": strategy.sector_name,
            "system_prompt": strategy.get_system_guideline().strip(),
            "search_queries": strategy.get_search_queries(company["ticker"], company["name"])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gics/org/{ticker}")
def get_company_org(ticker: str):
    """
    Generate and return the specific AI employee team structure (Org Chart) and system prompts 
    for analyzing this company.
    """
    try:
        result = db.get_company_classification_path(ticker)
        if not result:
            raise HTTPException(status_code=404, detail=f"Company {ticker.upper()} not found.")
            
        company = result["company"]
        gics_code = company["gics_code"]
        
        # Get matched AI employees for this company's GICS code
        employees = db.get_employees_for_gics(gics_code)
        
        return {
            "ticker": company["ticker"],
            "name": company["name"],
            "gics_code": gics_code,
            "org_chart": employees
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=True)
