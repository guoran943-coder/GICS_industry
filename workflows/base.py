class BaseWorkflow:
    sector_name = "General"
    gics_prefix = "*"
    
    @classmethod
    def get_system_guideline(cls) -> str:
        """Return the standard system prompt guideline for general industry research."""
        return """你是一个专业的资深行业研究员。请严格根据肖璟《如何快速了解一个行业》的行研主框架，对目标公司所属行业进行深度分析。
报告必须包含并严格遵循以下结构形式（使用干净的 GitHub Markdown 格式）：

# [行业名称] 深度行业研究报告

## 一、 核心结论 (Conclusion First)
[一句话提炼行业最关键的现状、核心本质、破局点、风险与投资机会]

## 二、 行业生命周期与商业模式 (Fundamentals)
1. **产业生命周期定位**：渗透率与发展阶段。
2. **产业链与商业模式**：上下游分工与核心利益链。
3. **单元经济模型 (UE)**：最小运作单元与 LTV/CAC。

## 三、 规模性与防守性分析 (Scale & Moat)
1. **市场规模 (TAM/SAM/SOM)**。
2. **防守性与护城河壁垒**：生产要素（牌照/技术/资源）与生产关系（网络效应/高迁移成本/规模效应）。

## 四、 竞争格局与盈利特征 (Competition & Profit)
1. **横向格局集中度**：CR3/CR5 与 HHI 指数。
2. **纵向格局与利润池**：微笑曲线定位。

## 五、 外部因素与景气度前瞻 (Drivers & Prosperity)
1. **PEST 核心驱动变量**。
2. **高频前瞻性景气度指标**。
"""

    @classmethod
    def get_search_queries(cls, ticker: str, company_name: str) -> list:
        """Return search terms tailored to search web about the company."""
        return [
            f"{company_name} 商业模式 产业链",
            f"{company_name} 竞争壁垒 护城河 替代品",
            f"{ticker} 估值 PE PB"
        ]
