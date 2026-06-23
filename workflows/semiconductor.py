from .base import BaseWorkflow

class SemiconductorWorkflow(BaseWorkflow):
    sector_name = "Semiconductors & Semiconductor Equipment"
    gics_prefix = "4530"
    
    @classmethod
    def get_system_guideline(cls) -> str:
        return super().get_system_guideline() + """
---
### 🚨 半导体与芯片设备行业专属要求
1. **产品与封装工艺**：剖析其芯片制程节点（如 3nm/5nm/7nm）以及先进封装工艺（如 CoWoS, Chiplet）。
2. **产能与供应链利用率**：重点评估晶圆代工厂（Foundry）产能利用率、排产 Lead Time 以及产业链的供需周期。
3. **软件与生态壁垒**：分析其由底层驱动或专用编程生态（如英伟达的 CUDA 生态，ASML 的光刻机独占系统）构成的强大开发者与产业链壁垒。
"""

    @classmethod
    def get_search_queries(cls, ticker: str, company_name: str) -> list:
        return [
            f"{company_name} nanometer process node advanced packaging technology",
            f"{company_name} software ecosystem CUDA developers moat",
            f"{company_name} supply chain foundry capacity utilization",
            f"{ticker} profit margin cyclicality inventory correction semiconductor"
        ]
