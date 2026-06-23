from .base import BaseWorkflow

class SoftwareWorkflow(BaseWorkflow):
    sector_name = "Software & Services"
    gics_prefix = "4510"
    
    @classmethod
    def get_system_guideline(cls) -> str:
        return super().get_system_guideline() + """
---
### 🚨 软件及 SaaS 行业专属要求
1. **经常性收入与增长率**：深度解构该公司的 ARR (年度经常性收入) 增速以及 NDR (净金额留存率)。
2. **LTV/CAC 评估**：审计该类 SaaS 公司的单元经济模型是否健康 (LTV/CAC > 3)。
3. **高迁移成本壁垒**：分析其软件的替换成本 (Switching Costs)，即客户更换为竞争对手产品的难度和代价。
"""

    @classmethod
    def get_search_queries(cls, ticker: str, company_name: str) -> list:
        return [
            f"{company_name} ARR NDR growth software",
            f"{company_name} LTV CAC cohort pricing model",
            f"{company_name} switching costs enterprise database enterprise software",
            f"{ticker} multiples Rule of 40 software valuation"
        ]
