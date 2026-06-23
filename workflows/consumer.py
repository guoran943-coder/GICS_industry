from .base import BaseWorkflow

class ConsumerWorkflow(BaseWorkflow):
    sector_name = "Consumer Staples"
    gics_prefix = "30"
    
    @classmethod
    def get_system_guideline(cls) -> str:
        return super().get_system_guideline() + """
---
### 🚨 必选消费品与食品饮料行业专属要求
1. **品牌心智与定价权**：分析其产品的消费者忠诚度、溢价心智壁垒以及对抗通胀的定价权 (Pricing Power)。
2. **销售渠道与货架占用**：审计其分销渠道（超市、电商、分销商）渗透深度以及终端零售的排他性货架占有度。
3. **原材料周期与毛利率**：分析大宗原材料（如糖、铝、大豆）价格波动对毛利的影响，以及消费者高频复购的持续性特征。
"""

    @classmethod
    def get_search_queries(cls, ticker: str, company_name: str) -> list:
        return [
            f"{company_name} brand loyalty pricing power inflation",
            f"{company_name} retail distribution channels supermarket shelf space",
            f"{company_name} raw material cost price transfer gross margin",
            f"{ticker} dividend history cash flow stability payout"
        ]
