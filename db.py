import os
import json
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://guoying@localhost:5432/industry")

def get_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    """Initialize the GICS schema and tables in PostgreSQL."""
    sql_statements = [
        "CREATE SCHEMA IF NOT EXISTS gics;",
        """
        CREATE TABLE IF NOT EXISTS gics.categories (
            code VARCHAR(8) PRIMARY KEY,
            name_en VARCHAR(255) NOT NULL,
            name_zh VARCHAR(255),
            level INT NOT NULL CHECK (level IN (1, 2, 3, 4)),
            parent_code VARCHAR(8) REFERENCES gics.categories(code) ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_categories_parent ON gics.categories(parent_code);",
        """
        CREATE TABLE IF NOT EXISTS gics.companies (
            ticker VARCHAR(10) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            gics_code VARCHAR(8) REFERENCES gics.categories(code) ON UPDATE CASCADE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_companies_gics ON gics.companies(gics_code);",
        """
        CREATE TABLE IF NOT EXISTS gics.company_reports (
            ticker VARCHAR(10) PRIMARY KEY REFERENCES gics.companies(ticker) ON DELETE CASCADE,
            report_md TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'completed',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS gics.employees (
            role_slug VARCHAR(50) PRIMARY KEY,
            role_name VARCHAR(100) NOT NULL,
            system_prompt_template TEXT NOT NULL,
            gics_prefix VARCHAR(8) NOT NULL
        );
        """
    ]
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            for statement in sql_statements:
                cur.execute(statement)
            
            # Seed default AI employees if table is empty
            cur.execute("SELECT COUNT(*) FROM gics.employees;")
            count = cur.fetchone()["count"]
            if count == 0:
                employee_seeds = [
                    ("ceo", "首席战略决策官 (CEO)", "你是一个顶尖的首席战略决策官 (CEO)。你的任务是阅读财务分析师、合规风险官和行业技术专家的专项分析报告，结合客观的外部数据进行统筹综合分析。撰写符合行业八维行研规范的最终分析报告，并给出结论。", "*"),
                    ("cfo", "财务分析师 (CFO)", "你是一个资深的财务分析师 (CFO)。负责从资产负债表、利润表和现金流量表出发，剖析公司的盈利质量、利润池占比、毛利空间与资本运营情况，并提供核心的行业估值定价分析（PE, PS, PEG, DCF 或 FCF 收益率）。", "*"),
                    ("cro", "合规与风险官 (CRO)", "你是一个敏锐的合规与风险官 (CRO)。专注于宏观外部因素 (PEST) 中的政治合规（如关税限制、双反政策）、宏观流动性周期（美联储利率波动）以及替代品对竞争格局构成的中长期威胁。", "*"),
                    ("software_expert", "SaaS度量专家", "你是一个资深的 SaaS 度量专家。专注于应用软件及 SaaS 类公司分析：审计其核心经营指标，包括 ARR 经常性收入、NDR 净金额留存、LTV/CAC 单元经济模型健康度，以及公司以高迁移成本（Switching Costs）和软件粘性构建的护城河壁垒。", "4510"),
                    ("semi_expert", "半导体工艺与生态专家", "你是一个顶尖的半导体工艺与生态专家。专注于半导体产业链分析：审计目标公司的产品制程节点（3nm/5nm等）、先进封装、代工厂产能利用率，以及公司通过 CUDA 生态或独占性软件库构建的庞大开发者生态壁垒。", "4530"),
                    ("consumer_expert", "消费品牌与渠道专家", "你是一个资深的消费品牌与渠道专家。专注于必选消费及包装食品饮料行业分析：审计公司的品牌溢价心智壁垒、线上线下全渠道渗透力、原材料周期以及消费者高频复购与粘性特征。", "30")
                ]
                for seed in employee_seeds:
                    cur.execute(
                        """
                        INSERT INTO gics.employees (role_slug, role_name, system_prompt_template, gics_prefix)
                        VALUES (%s, %s, %s, %s);
                        """,
                        seed
                    )
        conn.commit()

def upsert_gics_category(code, name_en, name_zh, level, parent_code=None):
    """Upsert a GICS category in the database."""
    sql = """
    INSERT INTO gics.categories (code, name_en, name_zh, level, parent_code)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (code) DO UPDATE 
    SET name_en = EXCLUDED.name_en,
        name_zh = EXCLUDED.name_zh,
        level = EXCLUDED.level,
        parent_code = EXCLUDED.parent_code;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (code, name_en, name_zh, level, parent_code))
        conn.commit()

def upsert_company(ticker, name, gics_code, description=None):
    """Upsert a company's GICS classification and description."""
    ticker = ticker.upper()
    sql = """
    INSERT INTO gics.companies (ticker, name, gics_code, description)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (ticker) DO UPDATE
    SET name = EXCLUDED.name,
        gics_code = EXCLUDED.gics_code,
        description = COALESCE(EXCLUDED.description, gics.companies.description);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (ticker, name, gics_code, description))
        conn.commit()

def get_company_classification_path(ticker):
    """
    Retrieve the full classification path (Level 1 to 4) for a company.
    Returns the company details and a list of GICS categories in order.
    """
    ticker = ticker.upper()
    
    # First, get the company and its GICS code
    company_sql = """
    SELECT ticker, name, gics_code, description 
    FROM gics.companies 
    WHERE ticker = %s;
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(company_sql, (ticker,))
            company = cur.fetchone()
            
            if not company:
                return None
            
            gics_code = company["gics_code"]
            if not gics_code:
                return {"company": company, "path": []}
            
            # Since GICS codes are structured (e.g. 45202030), we can extract the parent codes:
            # Level 1: code[0:2]
            # Level 2: code[0:4]
            # Level 3: code[0:6]
            # Level 4: code[0:8]
            codes = []
            if len(gics_code) >= 2:
                codes.append(gics_code[0:2])
            if len(gics_code) >= 4:
                codes.append(gics_code[0:4])
            if len(gics_code) >= 6:
                codes.append(gics_code[0:6])
            if len(gics_code) >= 8:
                codes.append(gics_code[0:8])
            
            # Query all parent categories
            path_sql = """
            SELECT code, name_en, name_zh, level 
            FROM gics.categories 
            WHERE code = ANY(%s)
            ORDER BY level;
            """
            cur.execute(path_sql, (codes,))
            path = cur.fetchall()
            
            return {
                "company": company,
                "path": path
            }

def get_companies_by_gics_code(gics_code):
    """
    Get all companies belonging to a GICS category code (supports prefix matching,
    e.g., '45' for all tech companies, '4520' for tech hardware).
    """
    sql = """
    SELECT c.ticker, c.name, c.gics_code, cat.name_en as industry_name_en, cat.name_zh as industry_name_zh, c.description
    FROM gics.companies c
    LEFT JOIN gics.categories cat ON c.gics_code = cat.code
    WHERE c.gics_code LIKE %s
    ORDER BY c.ticker;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (f"{gics_code}%",))
            return cur.fetchall()

def get_all_categories():
    """Retrieve all GICS categories sorted by code."""
    sql = "SELECT code, name_en, name_zh, level, parent_code FROM gics.categories ORDER BY code;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

def upsert_report(ticker, report_md, status="completed"):
    """Insert or update a company's GICS analysis report."""
    ticker = ticker.upper()
    sql = """
    INSERT INTO gics.company_reports (ticker, report_md, status, updated_at)
    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (ticker) DO UPDATE
    SET report_md = EXCLUDED.report_md,
        status = EXCLUDED.status,
        updated_at = CURRENT_TIMESTAMP;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (ticker, report_md, status))
        conn.commit()

def get_report(ticker):
    """Retrieve a company's analysis report."""
    ticker = ticker.upper()
    sql = "SELECT ticker, report_md, status, updated_at FROM gics.company_reports WHERE ticker = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (ticker,))
            return cur.fetchone()

def get_all_reports():
    """Retrieve all generated reports' status and metadata."""
    sql = "SELECT ticker, status, updated_at FROM gics.company_reports ORDER BY ticker;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

def get_employees_for_gics(gics_code):
    """
    Get all AI employees matching a GICS code.
    Includes general employees (gics_prefix = '*') and matching specific experts
    (whose gics_prefix is a prefix of the company's gics_code).
    """
    sql = "SELECT role_slug, role_name, system_prompt_template, gics_prefix FROM gics.employees;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            all_employees = cur.fetchall()
            
    matched = []
    for emp in all_employees:
        prefix = emp["gics_prefix"]
        if prefix == "*" or (gics_code and gics_code.startswith(prefix)):
            matched.append(emp)
    return matched
