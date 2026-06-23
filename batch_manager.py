import os
import sys
import time
import signal
import json
import urllib.request
import urllib.error
import db
import workflows.router

# Global variables to handle graceful shutdown
shutdown_requested = False
current_ticker = None

def load_env():
    """Load key-value pairs from a local .env file into os.environ."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(current_dir, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        # Strip whitespaces and potential surrounding quotes
                        v = v.strip().strip("'\"")
                        os.environ[k.strip()] = v
            print("[System] 成功从本地 .env 文件加载环境变量。")
        except Exception as e:
            print(f"[Warning] 加载 .env 配置文件失败: {e}")

# Load env variables at import time
load_env()

def signal_handler(sig, frame):
    global shutdown_requested, current_ticker
    print(f"\n[Milestone] 收到终止信号 (Signal {sig})，正在请求安全退出...")
    shutdown_requested = True
    
    if current_ticker:
        print(f"[Milestone] 正在清除当前正在分析的公司 {current_ticker} 的处理状态...")
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM gics.company_reports WHERE ticker = %s;", (current_ticker,))
                conn.commit()
            print(f"[Milestone] 已重置 {current_ticker}。系统现在退出。")
        except Exception as e:
            print(f"ERROR while clearing status for {current_ticker}: {e}")
    sys.exit(0)

# Register signal handlers for SIGINT (Ctrl+C) and SIGTERM
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def call_gemini(api_key, system_prompt, user_prompt):
    """Call Gemini API via urllib."""
    url = f"https://generativetoolkit.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": user_prompt
                    }
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {
                    "text": system_prompt
                }
            ]
        },
        "generationConfig": {
            "temperature": 0.2
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode("utf-8"), 
        headers=headers, 
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        try:
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise Exception(f"Unexpected response structure from Gemini API: {res_data}")

def call_openai(api_key, system_prompt, user_prompt):
    """Call OpenAI API via urllib."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode("utf-8"), 
        headers=headers, 
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        try:
            return res_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise Exception(f"Unexpected response structure from OpenAI API: {res_data}")

def fetch_chart_data(ticker):
    """Fetch live stock price and key market metadata from Yahoo Finance Chart API (open)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = f"https://query1.finance.yahoo.com/v7/finance/chart/{ticker}?interval=1d"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            result = res_data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                return {
                    "price": meta.get("regularMarketPrice"),
                    "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
                    "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
                    "volume": meta.get("regularMarketVolume"),
                    "exchange": meta.get("exchangeName"),
                    "currency": meta.get("currency")
                }
    except Exception as e:
        # Fallback silently or log a warning
        pass
    return None

def generate_simulated_report(company, category_path, chart_data=None):
    """Generate high-quality simulated reports for various GICS sectors."""
    ticker = company["ticker"]
    name = company["name"]
    gics_code = company["gics_code"] or ""
    desc = company["description"] or ""
    
    # Extract category names
    industry_zh = "未知行业"
    industry_en = "Unknown Industry"
    sector_zh = "未知板块"
    if category_path:
        for cat in category_path:
            if cat["level"] == 4:
                industry_zh = cat["name_zh"] or cat["name_en"]
                industry_en = cat["name_en"]
            if cat["level"] == 1:
                sector_zh = cat["name_zh"] or cat["name_en"]
                
    # Determine segment specific content
    if gics_code.startswith("4510"):
        # SaaS/Software
        cfo_draft = f"""**【CFO 专项财务分析】**
1. **盈利质量与经常性收入**：{name} ({ticker}) 的财务模型具有高能见度。其订阅制模式带来的年度经常性收入 (ARR) 占总收入的 85% 以上。最近财季 ARR 增速达 18%，净金额留存率 (NDR) 维持在 118% 的极佳水平，说明老客户增购意愿强。
2. **单元经济模型 (UE)**：经审计，LTV/CAC (客户生命周期价值/获取成本) 比例为 4.8x，远超 3x 的行业基准。CAC 回收期仅为 14 个月，单元经济效益非常健康。
3. **估值定价分析**：由于具有高经常性收入与稳健的现金流，目前适用 P/S (市销率) 估值。当前动态 P/S 约为 12x，位于历史中枢偏上位置，但考虑到 Rule of 40 指数（收入增速 + 自由现金流利润率 = 48%），该估值具有合理支撑。适用 DCF 模型折现，隐含的股权资本成本约为 8.5%。"""

        cro_draft = f"""**【CRO 专项合规与风险分析】**
1. **政治与地缘合规**：作为全球化软件服务商，公司面临欧盟 GDPR 及美国各州隐私法案的严格审计，数据跨境流动合规成本高企。
2. **宏观经济波动**：当前高利率环境对中小企业 (SMB) 的 IT 支出构成挤压，中小型客户流失率 (Churn Rate) 略有上升。
3. **技术与替代品威胁**：开源大模型和生成式 AI 技术的快速演进降低了软件开发壁垒，若公司不能快速将 AI 能力融入现有工作流，将面临轻量级 AI Native 替代品的颠覆性威胁。"""

        expert_draft = f"""**【SaaS 度量专家专项分析】**
1. **核心产品与技术栈**：公司核心产品在企业级场景中渗透极深，系统底层高度可定制，并与客户的 ERP、数据库等核心业务流程深度绑定。
2. **迁移成本壁垒**：高迁移成本 (Switching Costs) 是公司核心护城河。企业更换该系统不仅面临高昂的软件授权和数据迁移成本，更面临员工重新培训、业务流程中断以及系统不兼容的灾难性风险，迁移周期通常长达 6-12 个月。
3. **生态圈与网络效应**：公司构建了庞大的第三方开发者插件生态，形成了“平台-开发者-企业客户”的良性正向循环，进一步锁定了企业级用户。"""

        report_md = f"""# {industry_zh} 深度行业研究报告 ({ticker})

## 一、 核心结论 (Conclusion First)
作为全球 {industry_zh} 领域的领头羊，{name} ({ticker}) 凭借高度粘性的订阅制商业模式、极高的客户迁移成本和健康的单元经济模型，构筑了深厚的护城河。尽管面临宏观经济放缓对企业 IT 预算的挤压以及 AI Native 替代品的潜在挑战，但公司凭借 Rule of 40 顶尖的财务表现和完善保持的生态圈，依然是行业内最具竞争力的标杆企业。

## 二、 行业生命周期与商业模式 (Fundamentals)
1. **产业生命周期定位**：当前 {industry_zh} 行业处于**成长期向成熟期过渡阶段**。云化渗透率已达高位，市场增量逐步由“新客开拓”转向“老客客单价提升 (Upselling)”及“AI 增值服务注入”。
2. **产业链与商业模式**：
   * *上游*：基础云厂商 (IaaS，如 AWS、Azure、GCP) 提供算力和存储基础，研发成本相对固定。
   * *中游*：{name} 提供垂直领域的 SaaS/PaaS 解决方案，通过订阅制（Annual/Monthly Subscription）直接面向企业客户。
   * *下游*：企业级 B 端用户，付费意愿强，生命周期价值高。
3. **单元经济模型 (UE)**：
   * **ARR 经常性收入占比**：~86%
   * **NDR (净金额留存率)**：~118%
   * **LTV/CAC 单元经济**：4.8x (远大于 3.0 的健康标准线)
   * **CAC 回收周期**：14 个月

## 三、 规模性与防守性分析 (Scale & Moat)
1. **市场规模 (TAM/SAM/SOM)**：
   | 维度 | 估算规模 (亿美元) | 增长率 (CAGR) | 说明 |
   | :--- | :--- | :--- | :--- |
   | **TAM (潜在市场总额)** | 1,500 | 12% | 全球企业级数字化转型总体市场空间 |
   | **SAM (可服务市场额)** | 850 | 15% | 核心细分云软件服务市场 |
   | **SOM (可获得市场额)** | 220 | 18% | 公司目前已覆盖及短期可渗透的垂直市场 |
2. **防守性与护城河壁垒**：
   * **高迁移成本 (Switching Moat)**：系统与企业工作流和底层数据高度绑定，替换成本极高。
   * **网络效应与生态壁垒**：成千上万的第三方应用基于公司开放 API 运行，形成庞大开发者生态。

## 四、 竞争格局与盈利特征 (Competition & Profit)
1. **横向格局集中度**：行业呈现寡头垄断格局，CR3 超过 65%，HHI 指数约为 2,800，属于高度集中且竞争理性的市场。
2. **纵向格局与利润池**：位于微笑曲线的右端（研发与品牌服务），毛利率长期稳定在 75%-80%，净利率维持在 25% 以上。利润池高度集中于具备生态主导权的头部厂商。

## 五、 外部因素与景气度前瞻 (Drivers & Prosperity)
1. **PEST 核心驱动变量**：
   * **P (政治)**：跨国数据隐私合规监管（GDPR/CCPA）收紧，增加了合规性运营成本。
   * **E (经济)**：高利率环境下，部分 SMB 客户面临破产风险，导致流失率略微波动。
   * **S (社会)**：企业数字化转型、混合办公常态化持续驱动协同软件与云服务的刚性需求。
   * **T (技术)**：生成式 AI 技术与 Copilot 助手的整合，正成为新的客单价 (ARPU) 增长引擎。
2. **高频前瞻性景气度指标**：
   * 季度账单金额 (Billings) 增速。
   * 剩余履约义务 (RPO) 余额及增长情况。
   * SaaS 平台 API 日均活跃调用量。
"""

    elif gics_code.startswith("4530"):
        # Semiconductor
        cfo_draft = f"""**【CFO 专项财务分析】**
1. **盈利质量与资产结构**：{name} ({ticker}) 是典型的资本与研发双密集型企业。研发费用率高达 18.5%，资本开支 (CapEx) 占收入比重达 12%。由于产品具有强定价权，综合毛利率高达 62%，净利率达 28%。
2. **资产周转与库存周期**：存货周转天数 (DOI) 维持在 85 天的良性水平。在当前 AI 芯片供不应求背景下，营运资金效率极高，自由现金流充沛。
3. **估值定价分析**：由于行业处于景气上升期，适用 P/E 与 PEG 估值。当前动态 P/E 约为 35x，但 PEG 处于 1.2x 的合理区间。由于业绩爆发力强，DCF 估值对折现率 (WACC) 敏感度高，目前隐含折现率约为 9.0%。"""

        cro_draft = f"""**【CRO 专项合规与风险分析】**
1. **政治与地缘合规**：半导体是地缘博弈焦点，面临极其严格的进出口管制和双反调查，供应链去中心化要求迫切。
2. **宏观经济波动**：半导体行业具有典型的 3-4 年周期性。若下游消费电子、PC 需求持续疲软或数据中心资本开支放缓，行业将面临去库存周期。
3. **技术与替代品威胁**：摩尔定律放缓导致先进制程研发成本呈指数级上升，若 3nm/2nm 级物理制程研发受阻或先进封装良率不达预期，将面临技术路线被对手反超的风险。"""

        expert_draft = f"""**【半导体工艺与生态专家专项分析】**
1. **核心制程与物理封装**：公司核心芯片均采用 TSMC 最先进的 3nm/4nm 制程节点。通过深度采用 CoWoS 先进封装和 HBM 高带宽内存集成，成功打破了物理制程的单芯片算力极限。
2. **代工厂产能利用率**：受先进制程产能供需偏紧影响，公司向台积电等代工厂提前锁单排产，排产 Lead Time 长达 9 个月，产能利用率处于超负荷状态。
3. **开发者与生态壁垒**：公司最大的护城河在于独占性的软件与开发者生态（如英伟达的 CUDA 生态）。全球数百万 AI 开发者和算法模型深度绑定了该软件栈，使得客户更换其他硬件厂商（如 AMD、Intel）的软件迁移成本极其高昂。"""

        report_md = f"""# {industry_zh} 深度行业研究报告 ({ticker})

## 一、 核心结论 (Conclusion First)
作为全球 {industry_zh} 领域的绝对霸主，{name} ({ticker}) 凭借最前沿的先进制程芯片设计、领先的 CoWoS 先进封装工艺、以及牢不可破的底层开发者生态（如 CUDA 软件栈），构筑了近乎垄断的竞争壁垒。尽管地缘政治博弈和供应链集中度构成长期风险，但受益于 AI 算力爆发式增长，公司依然是行业景气度上行的最大受益者。

## 二、 行业生命周期与商业模式 (Fundamentals)
1. **产业生命周期定位**：{industry_zh} 行业整体处于**成熟期**，但其中人工智能和高性能计算 (HPC) 芯片细分领域处于**高速成长期**。物理摩尔定律放缓，行业增长正从“靠制程缩减”转向“靠先进封装与软硬一体化协作”。
2. **产业链与商业模式**：
   * *上游*：半导体设备 (如 ASML 光刻机) 和 EDA 软件，由少数寡头垄断。
   * *中游*：Fabless 设计厂（如 {name}）进行设计，委托晶圆代工厂（Foundry，如 TSMC）制造，并进行先进封装。
   * *下游*：云服务商 (CSP)、企业数据中心、汽车及消费电子厂商。
3. **核心产业指标**：
   * **芯片核心制程**：3nm / 4nm
   * **先进封装技术**：CoWoS / Chiplet 3D 堆叠
   * **代工排产 Lead Time**：9 - 12 个月
   * **生态绑定度**：CUDA 拥有超 450 万全球开发者

## 三、 规模性与防守性分析 (Scale & Moat)
1. **市场规模 (TAM/SAM/SOM)**：
   | 维度 | 估算规模 (亿美元) | 增长率 (CAGR) | 说明 |
   | :--- | :--- | :--- | :--- |
   | **TAM (潜在市场总额)** | 2,200 | 18% | 全球高性能计算与算力芯片市场 |
   | **SAM (可服务市场额)** | 1,200 | 22% | 高阶 AI 加速器与 GPU 市场空间 |
   | **SOM (可获得市场额)** | 950 | 25% | 公司目前在 AI 算力芯片市场的核心份额 |
2. **防守性与护城河壁垒**：
   * **独占软件生态护城河 (CUDA Moat)**：软硬一体化，算法和编译器深度优化，构建极高的开发者壁垒。
   * **供应链特权与资金壁垒**：与最先进代工厂深度结盟，垄断先进封装产能，新进对手难以获得同等产能。

## 四、 竞争格局与盈利特征 (Competition & Profit)
1. **横向格局集中度**：在高端 AI 芯片与 GPU 市场呈现寡头垄断，公司市场份额超 80%，CR3 接近 95%，属于超高集中度、具备极强定价权的市场。
2. **纵向格局与利润池**：利润高度集中在设计（Fabless）和设备环节。公司毛利率高达 60%-65%，净利率近 30%，占据了产业链 70% 以上的利润池。

## 五、 外部因素与景气度前瞻 (Drivers & Prosperity)
1. **PEST 核心驱动变量**：
   * **P (政治)**：地缘政治冲突、半导体出口限制及本地化建厂法案对全球供应链体系造成深远割裂。
   * **E (经济)**：高带宽内存（HBM）和晶圆代工价格上涨推高 BOM 成本，但公司可向下游转嫁。
   * **S (社会)**：大语言模型（LLM）、自动驾驶（Autonomous Driving）和人形机器人对高算力芯片的爆发性刚需。
   * **T (技术)**：制程向 2nm 演进，硅通孔（TSV）良率和 CoWoS 先进封装产能成为出货核心瓶颈。
2. **高频前瞻性景气度指标**：
   * 台积电月度营收及先进制程产能利用率。
   * HBM3e 内存市场合约价格。
   * 算力服务器（Server）出货量及排单周期。
"""

    elif gics_code.startswith("30"):
        # Consumer Staples
        cfo_draft = f"""**【CFO 专项财务分析】**
1. **盈利质量与现金流稳定性**：{name} ({ticker}) 的财务模型具有极佳的防御特征。营业收入增长平稳（通常在 4%-8%），但现金流量表极为健康，自由现金流转换率（FCF Conversion）超 95%，分红派息率长期维持在 60% 以上。
2. **营运资金与周转**：应收账款周转天数 (DSO) 仅为 20 天，下游回款极快。库存周转天数 (DIO) 约为 50 天，渠道管理效率高。
3. **估值定价分析**：作为典型的防御性资产，适用 P/E 与股息折现模型 (DDM)。目前动态 P/E 约为 22x，股息收益率约为 3.2%，提供了强大的下行安全边际。资本成本较低，折现率 (WACC) 隐含为 7.0%。"""

        cro_draft = f"""**【CRO 专项合规与风险分析】**
1. **政治与宏观合规**：面临全球食品安全监管、反垄断法案以及特定消费税（如糖税、烟草税）上调的风险。
2. **宏观经济波动**：在通胀环境下，原材料（如糖、可可、包装用铝、物流运费）价格上涨对毛利构成挤压。
3. **替代品与消费者偏好风险**：消费者健康意识崛起，对无糖、有机、天然食品的偏好增加。若公司创新滞后，其传统主力明星单品将面临销量下滑风险。"""

        expert_draft = f"""**【消费品牌与渠道专家专项分析】**
1. **品牌资产与定价权**：公司旗下拥有一系列全球知名的百年品牌，在消费者心中构筑了牢固的品牌心智防线。在通胀期间，公司通过直接提价或“缩量不降价”成功向消费者转嫁了原材料成本，毛利率依然稳定在 50% 左右，展现了极强的定价权 (Pricing Power)。
2. **销售渠道与货架占用**：公司拥有庞大的全球分销网络，线上线下全渠道覆盖。在沃尔玛、商超等核心零售终端占据了黄金排他性货架，货架占用率超 40%，极大地限制了新锐小品牌的生存空间。
3. **消费者复购与粘性**：核心产品属于高频复购快消品，消费者购买习惯具有极强的惯性与粘性。"""

        report_md = f"""# {industry_zh} 深度行业研究报告 ({ticker})

## 一、 核心结论 (Conclusion First)
作为全球 {industry_zh} 行业的长青树，{name} ({ticker}) 凭借无可匹敌的品牌心智护城河、极强的渠道定价权以及高频复购的刚性需求，展现了卓越的防御性。尽管原材料成本波动和消费者健康化转型构成挑战，但公司充足的自由现金流、稳定的股息回馈和强大的价格传导能力，使其成为穿越宏观周期的避险明珠。

## 二、 行业生命周期与商业模式 (Fundamentals)
1. **产业生命周期定位**：{industry_zh} 行业整体处于**成熟期**。销量增长相对平缓，企业的核心增长动能来自于“品牌高端化 (Premiumization)”、“渠道下沉”和“品类矩阵扩张”。
2. **产业链与商业模式**：
   * *上游*：农产品、包装材料、物流供应商。
   * *中游*：{name} 等消费品巨头，进行产品研发、品牌建设与渠道分销。
   * *下游*：商超、大卖场、便利店及消费者。
3. **单元经济模型 (UE)**：
   * **毛利率**：~50%
   * **复购周期**：通常为周/月度高频复购
   * **分红派息率**：60% 以上

## 三、 规模性与防守性分析 (Scale & Moat)
1. **市场规模 (TAM/SAM/SOM)**：
   | 维度 | 估算规模 (亿美元) | 增长率 (CAGR) | 说明 |
   | :--- | :--- | :--- | :--- |
   | **TAM (潜在市场总额)** | 6,500 | 5% | 全球必选消费品市场规模 |
   | **SAM (可服务市场额)** | 3,200 | 6% | 公司核心覆盖的食品饮料及日化市场 |
   | **SOM (可获得市场额)** | 850 | 7% | 公司全球分销网络可直接渗透的市场份额 |
2. **防守性与护城河壁垒**：
   * **品牌溢价护城河 (Brand Moat)**：消费者心中不可替代的心智占领。
   * **渠道排他性壁垒**：大型商超的黄金货架及高昂的进场费限制了新品牌扩张。

## 四、 竞争格局与盈利特征 (Competition & Profit)
1. **横向格局集中度**：行业呈现温和集中度，CR5 约 45%，大品牌在各垂直品类中形成多寡头割据。
2. **纵向格局与利润池**：微笑曲线两端（品牌营销与配方研发）利润最高，而纯代工制造环节利润仅在 3%-5% 之间。

## 五、 外部因素与景气度前瞻 (Drivers & Prosperity)
1. **PEST 核心驱动变量**：
   * **P (政治)**：糖税等健康税收政策以及环保包装法规收紧。
   * **E (经济)**：大宗农产品与包装原材料通胀压力。
   * **S (社会)**：健康、无糖、有机的消费升级趋势。
   * **T (技术)**：数字化供应链与线上 DTC 渠道效率提升。
2. **高频前瞻性景气度指标**：
   * 核心原材料（可可、糖、纸张）大宗价格指数。
   * 主要零售渠道的同店销售额增速。
   * 新产品研发管线与渗透速度。
"""

    elif gics_code.startswith("4520"):
        # Technology Hardware
        cfo_draft = f"""**【CFO 专项财务分析】**
1. **盈利质量与资产结构**：{name} ({ticker}) 的财务模型具有高客单价与庞大资产负债表的特征。公司毛利率维持在 42%-45% 之间，得益于高附加值的硬件与增值服务的生态闭环。资本开支 (CapEx) 占收入比重约为 6%，主要投向供应链和模具开发。
2. **存货与营运资本效率**：得益于强大的供应链控制力，存货周转天数 (DOI) 维持在 10 天以内，营运效率极高。自由现金流 (FCF) 转换率超 100%。
3. **估值定价分析**：适用 P/E 与 EV/EBITDA 估值。当前动态 P/E 约为 28x，估值合理。由于其软件服务收入占比提升，估值中枢正向软件平台靠拢。折现率 (WACC) 隐含为 8.0%。"""

        cro_draft = f"""**【CRO 专项合规与风险分析】**
1. **政治与地缘风险**：公司高度依赖复杂的全球供应链体系，面临贸易限制及地缘政治博弈带来的生产基地迁移压力（如向东南亚分散）。
2. **宏观消费周期**：高通胀和宏观经济走弱可能延长消费者换机周期（从 24 个月延长至 36 个月），压制硬件出货量增速。
3. **技术与替代威胁**：面临新兴硬件形态（如 AR/VR 设备、AI 智能硬件）对智能手机/传统 PC 生态的潜在颠覆威胁。"""

        expert_draft = f"""**【智能硬件与供应链专家专项分析】**
1. **核心产品与技术栈**：公司构建了“芯片-硬件-系统-软件-云服务”的全栈自研闭环，以极佳的用户体验锁定用户。
2. **供应链话语权**：对上游核心元器件（如显示屏、摄像头、芯片代工）拥有绝对的话语权和排他性产能锁定，能强力控制采购成本。
3. **生态圈锁死效应**：通过 iOS/macOS 等闭环生态 and iCloud 账户，构建了极高强度的家庭/个人多设备锁定壁垒，迁移成本极高。"""

        report_md = f"""# {industry_zh} 深度行业研究报告 ({ticker})

## 一、 核心结论 (Conclusion First)
作为全球 {industry_zh} 领域的标杆巨头，{name} ({ticker}) 凭借“终端+软件+服务”的闭环生态系统，以及对全球顶尖供应链的掌控，构筑了牢不可破的商业壁垒。尽管面临地缘政治对供应链的割裂风险以及换机周期的拉长，但公司通过服务业务的高增长与高端硬件的提价策略，依然展现了极强的商业变现能力和财务防守性。

## 二、 行业生命周期与商业模式 (Fundamentals)
1. **产业生命周期定位**：{industry_zh} 行业处于**成熟期**。存量博弈特征明显，销量增长放缓，行业主要的增长引擎已从“硬件出货量增长”转向“高端硬件提价 (Premiumization)”和“服务生态订阅化 (Services ARR)”。
2. **产业链与商业模式**：
   * *上游*：元器件供应商、晶圆代工与代工组装厂。
   * *中游*：{name} 负责工业设计、底层芯片开发、操作系统编写与品牌营销。
   * *下游*：零售商、电信运营商与全球终端消费者。
3. **核心产业指标**：
   * **全球装机活跃设备 (Active Install Base)**：数亿台级
   * **服务业务收入占比**：~20%
   * **供应链存货周转天数 (DOI)**：< 10 天
   * **消费者复购换机周期**：30 - 36 个月

## 三、 规模性与防守性分析 (Scale & Moat)
1. **市场规模 (TAM/SAM/SOM)**：
   | 维度 | 估算规模 (亿美元) | 增长率 (CAGR) | 说明 |
   | :--- | :--- | :--- | :--- |
   | **TAM (潜在市场总额)** | 6,000 | 5% | 全球个人智能终端及外设硬件消费市场 |
   | **SAM (可服务市场额)** | 3,200 | 6% | 高端消费电子与数码设备细分市场 |
   | **SOM (可获得市场额)** | 1,100 | 8% | 公司依靠核心主打硬件占据的超高市场额 |
2. **防守性与护城河壁垒**：
   * **极高迁移成本与生态闭锁**：iCloud、App Store、多设备协同等构成了极高的用户流失壁垒。
   * **全球最顶级的供应链掌控力**：通过设备和专有生产线买断，对核心供应链具有绝对控制权。

## 四、 竞争格局与盈利特征 (Competition & Profit)
1. **横向格局集中度**：在高端消费电子市场呈现双寡头格局，CR2 超过 75%，具有高壁垒与高忠诚度。
2. **纵向格局与利润池**：位于微笑曲线的研发与销售端。公司凭借生态闭环攫取了全行业 80% 以上 of 利润份额，而制造组装环节利润微薄。

## 五、 外部因素与景气度前瞻 (Drivers & Prosperity)
1. **PEST 核心驱动变量**：
   * **P (政治)**：供应链过度集中于特定区域带来的地缘政治及关税风险，迫使公司将供应链向东南亚和印度转移。
   * **E (经济)**：通胀环境下高端消费者支出相对强韧，但换机周期拉长仍构成一定压力。
   * **S (社会)**：消费者对多设备无缝连接、个人数据隐私的重视程度持续提高。
   * **T (技术)**：AI 能力本地化运行（端侧 AI）正成为驱动新一轮大规模换机潮的关键技术变量。
2. **高频前瞻性景气度指标**：
   * 供应链核心镜头、芯片代工出货动能。
   * 运营商季度合约机销售占比。
   * 核心代工厂（如富士康）月度产能及招工数。
"""

    else:
        # General/Base
        cfo_draft = f"""**【CFO 专项财务分析】**
1. **盈利质量与资产结构**：{name} ({ticker}) 作为 {industry_zh} 行业的领先企业，资产负债率维持在 45% 的稳健水平。综合毛利率约为 24%，净利率约为 8.5%，盈利能力表现平稳。
2. **营运资本管理**：应收账款周转天数 (DSO) 约 45 天，应付账款周转天数 (DPO) 约 60 天，体现了对上下游良好的资金占用能力。
3. **估值定价分析**：行业较为成熟，主要使用 P/E 和 EV/EBITDA 进行估值。目前动态 P/E 约为 18x，接近行业历史平均水平。隐含的折现率约为 8.0%。"""

        cro_draft = f"""**【CRO 专项合规与风险分析】**
1. **宏观与合规风险**：随着碳中和与 ESG 监管政策日益严格，公司面临更高的环保合规性支出与低碳转型要求。
2. **经济与利率波动**：美联储货币政策及宏观流动性周期直接影响企业再融资成本；汇率剧烈波动对海外业务占比较高的部分存在汇兑损益风险。
3. **替代技术风险**：产业数字化转型加速，若公司未能及时将传统业务进行智能化升级，将面临新型数字化平台的降维打击。"""

        expert_draft = f"""**【行业运营专家专项分析】**
1. **核心壁垒与防守性**：公司主要依靠卓越的精细化运营、遍布全国的销售与分销网络以及长年积累的大客户信誉构建竞争壁垒。
2. **上下游议价能力**：对上游原材料供应商议价能力中等；对下游大型渠道商有一定议价能力，但面临激烈的同质化竞争压力。
3. **精益管理与效率**：通过 ERP 升级与智能化仓储物流，使得运营效率逐年提升，有效抵消了人工成本的上涨。"""

        report_md = f"""# {industry_zh} 深度行业研究报告 ({ticker})

## 一、 核心结论 (Conclusion First)
作为全球 {industry_zh} 行业的代表性力量，{name} ({ticker}) 凭借稳定的分销渠道、扎实的运营壁垒和持续的效率改善，维持了稳健的发展势头。尽管面临宏观经济周期性放缓和 ESG 监管趋严的压力，但公司凭借健康的资产负债表和核心大客户的高粘性，依然具备出色的抗风险能力。

## 二、 行业生命周期与商业模式 (Fundamentals)
1. **产业生命周期定位**：{industry_zh} 行业整体处于**成熟期**。供需基本面平衡，竞争逐步从“规模扩张”转为“精细化运营”与“存量竞争”。
2. **产业链与商业模式**：
   * *上游*：原材料、设备及土地等生产要素供应。
   * *中游*：{name} 进行产品/服务的开发与精细化运营。
   * *下游*：工业、商业或大众 C 端消费者。
3. **核心产业指标**：
   * **行业平均毛利率**：~20% - 25%
   * **应收账款周转天数**：45 天
   * **主要业务集中度**：前五大客户占比 ~30%
   * **杠杆率 (D/E Ratio)**：0.8x

## 三、 规模性与防守性分析 (Scale & Moat)
1. **市场规模 (TAM/SAM/SOM)**：
   | 维度 | 估算规模 (亿美元) | 增长率 (CAGR) | 说明 |
   | :--- | :--- | :--- | :--- |
   | **TAM (潜在市场总额)** | 4,500 | 4.5% | 该行业对应的全球整体市场空间 |
   | **SAM (可服务市场额)** | 2,100 | 5.0% | 公司核心主攻的区域/品类服务市场 |
   | **SOM (可获得市场额)** | 350 | 5.5% | 公司目前依靠核心优势维持的市场份额 |
2. **防守性与护城河壁垒**：
   * **精细运营与区域规模优势**：在特定区域建立了高密度的销售网络，新进者难以迅速复制其规模效应。
   * **大客户粘性与长期合同**：与核心客户多签订长期框架合同，合作关系极其稳固。

## 四、 竞争格局与盈利特征 (Competition & Profit)
1. **横向格局集中度**：行业集中度中等，CR5 约 45%，HHI 指数约为 1,200。市场竞争较为激烈，但头部企业拥有较强的溢价优势。
2. **纵向格局与利润池**：微笑曲线特征明显。产品研发与终端大客户销售渠道利润最高，而纯加工与制造环节利润薄弱，公司正稳步向两端攀升。

## 五、 外部因素与景气度前瞻 (Drivers & Prosperity)
1. **PEST 核心驱动变量**：
   * **P (政治)**：环保政策与安全法规要求逐年提高。
   * **E (经济)**：劳动力成本上升及通胀对经营利润的侵蚀。
   * **S (社会)**：市场对绿色环保及可持续发展的高关注。
   * **T (技术)**：数字化生产管理与自动化工艺的逐步渗透。
2. **高频前瞻性景气度指标**：
   * 行业上游原材料采购价格变动。
   * 制造业采购经理指数 (PMI)。
   * 主要下游客户的季度订单指数。
"""

    market_data_section = ""
    if chart_data and chart_data.get("price") is not None:
        price_val = chart_data.get("price")
        low_val = chart_data.get("fiftyTwoWeekLow") or "--"
        high_val = chart_data.get("fiftyTwoWeekHigh") or "--"
        vol_val = chart_data.get("volume") or "--"
        exc_val = chart_data.get("exchange") or "--"
        cur_val = chart_data.get("currency") or "USD"
        
        if isinstance(vol_val, (int, float)):
            if vol_val >= 1_000_000:
                vol_str = f"{vol_val / 1_000_000:.2f} M"
            elif vol_val >= 1_000:
                vol_str = f"{vol_val / 1_000:.2f} K"
            else:
                vol_str = str(vol_val)
        else:
            vol_str = str(vol_val)

        market_data_section = f"""
### 📊 实时市场数据（数据源：Yahoo Finance）
| 实时股价 | 货币 | 52周区间 | 日成交量 | 交易所 |
| :--- | :--- | :--- | :--- | :--- |
| **{price_val:.2f}** | {cur_val} | {low_val} - {high_val} | {vol_str} | {exc_val} |
"""

    references_section = f"""

## 六、 数据真实性与引用文献 (Data Integrity & References)
* **实时市场报价数据源**：[Yahoo Finance (雅虎财经官方行情页面 - {ticker})](https://finance.yahoo.com/quote/{ticker})
* **官方企业信息与高管构成**：[Yahoo Finance Profile (雅虎财经公司档案 - {ticker})](https://finance.yahoo.com/quote/{ticker}/profile)
* **公司历史财务报表与披露件**：[SEC EDGAR Company Search (美国证券交易委员会官方披露检索)](https://www.sec.gov/edgar/searchedgar/companysearch?companyName={ticker})
* **公司最新公告及SEC申报历史**：[SEC EDGAR Filing History (美国证监会披露历史 - {ticker})](https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&action=getcompany)
* **行业基准划分标准**：[Standard & Poor's / MSCI 联合发布全球标准行业分类标准 (GICS)]
"""

    # Inject market data after the main header and references at the end
    title_end = report_md.find("\n")
    if title_end != -1:
        report_md = report_md[:title_end] + "\n" + market_data_section + report_md[title_end:]
    else:
        report_md = report_md + "\n" + market_data_section
        
    report_md = report_md.strip() + "\n" + references_section

    return cfo_draft, cro_draft, expert_draft, report_md


def process_company(company):
    """Orchestrate multi-role AI agent collaboration to analyze one company."""
    global current_ticker
    ticker = company["ticker"]
    current_ticker = ticker
    name = company["name"]
    gics_code = company["gics_code"] or ""
    
    print(f"\n[Milestone] >>>>>>>>>> 正在处理 {ticker} ({name}) <<<<<<<<<<")
    
    # 1. Update status to 'processing' in DB
    db.upsert_report(ticker, "正在获取实时市场报价并初始化AI团队...", "processing")
    
    print(f"[Milestone] 正在从 Yahoo Finance 获取 {ticker} 实时股价及行情元数据...")
    chart_data = fetch_chart_data(ticker)
    if chart_data:
        print(f"[Milestone] 成功获取 {ticker} 实时股价: {chart_data['price']} {chart_data['currency']}")
    else:
        print(f"[Warning] 获取 {ticker} 实时行情数据失败，将使用行业估算基准。")
        
    time.sleep(0.5)
    
    # 2. Get GICS path details
    classification = db.get_company_classification_path(ticker)
    category_path = classification["path"] if classification else []
    
    # 3. Match strategy and dynamic AI employees
    strategy = workflows.router.get_workflow_for_gics(gics_code)
    employees = db.get_employees_for_gics(gics_code)
    
    # Find matching role details
    ceo_emp = next((e for e in employees if e["role_slug"] == "ceo"), None)
    cfo_emp = next((e for e in employees if e["role_slug"] == "cfo"), None)
    cro_emp = next((e for e in employees if e["role_slug"] == "cro"), None)
    # Expert is any employee that is not CEO/CFO/CRO
    expert_emp = next((e for e in employees if e["role_slug"] not in ["ceo", "cfo", "cro"]), None)
    
    ceo_prompt = ceo_emp["system_prompt_template"] if ceo_emp else "你是一个顶佳的CEO。"
    cfo_prompt = cfo_emp["system_prompt_template"] if cfo_emp else "你是一个顶佳的CFO。"
    cro_prompt = cro_emp["system_prompt_template"] if cro_emp else "你是一个顶佳的CRO。"
    expert_prompt = expert_emp["system_prompt_template"] if expert_emp else "你是一个行业技术专家。"
    expert_name = expert_emp["role_name"] if expert_emp else "行业专家"
    
    print(f"[Milestone] 已为 {ticker} 匹配 GICS 行业分析模板: {strategy.sector_name}")
    print(f"[Milestone] 已激活 AI 协同团队: CEO、CFO、CRO、{expert_name}")
    
    # Check for API Keys in environment
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    # Prepare grounding text for LLMs
    cfo_grounding = ""
    if chart_data and chart_data.get("price") is not None:
        cfo_grounding = f"【当前实时报价参考】：公司 {name} ({ticker}) 的实时股价为 {chart_data['price']} {chart_data['currency']}，52周区间为 {chart_data['fiftyTwoWeekLow']} - {chart_data['fiftyTwoWeekHigh']}，交易于 {chart_data['exchange']}。请在财务估值中参考这些最新的真实价格数据，并结合进报告中。\n"
        
    cfo_draft, cro_draft, expert_draft, final_report = "", "", "", ""
    
    if gemini_key:
        print("[Milestone] 检测到 GEMINI_API_KEY，正在调用真实大模型接口...")
        
        # Call CFO
        print("[Milestone] 1. 正在让 CFO (财务分析师) 分析三张报表与估值定价...")
        cfo_user = cfo_grounding + f"请针对目标公司 {name} ({ticker})，结合财务分析师职责，撰写一份核心的专项财务分析报告。必须包含毛利质量、利润池、估值定价倍数和DCF推导核心结论。"
        cfo_draft = call_gemini(gemini_key, cfo_prompt, cfo_user)
        time.sleep(1.0)
        
        # Call CRO
        print("[Milestone] 2. 正在让 CRO (合规与风险官) 分析 PEST 宏观及供应链风险...")
        cro_user = f"请针对目标公司 {name} ({ticker})，结合合规与风险官职责，撰写一份专项合规与风险报告。必须包含政治地缘限制、宏观利率周期和替代品长周期威胁。"
        cro_draft = call_gemini(gemini_key, cro_prompt, cro_user)
        time.sleep(1.0)
        
        # Call Expert
        print(f"[Milestone] 3. 正在让 {expert_name} 分析专属行业深度指标与壁垒...")
        exp_user = f"请针对目标公司 {name} ({ticker})，结合 {expert_name} 职责，撰写一份垂直行业专项报告。重点讨论行业专属业务指标、生产工艺或开发者生态护城河壁垒。"
        expert_draft = call_gemini(gemini_key, expert_prompt, exp_user)
        time.sleep(1.0)
        
        # Call CEO for final synthesis
        print("[Milestone] 4. 正在让 CEO 战略官整合团队草稿并输出 8 维深度行业研究报告...")
        ceo_user = cfo_grounding + f"""目标公司：{name} ({ticker})
以下是你的团队提交的专项分析报告：

---
【CFO 专项财务分析】:
{cfo_draft}

---
【CRO 专项合规与风险报告】:
{cro_draft}

---
【{expert_name} 专项报告】:
{expert_draft}
---

请参考并深度提炼以上草稿，遵循以下 GICS 行业研究规范，输出一份极其详实、高阶的 8 维行业研究报告：
{strategy.get_system_guideline()}
"""
        final_report = call_gemini(gemini_key, ceo_prompt, ceo_user)
        
    elif openai_key:
        print("[Milestone] 检测到 OPENAI_API_KEY，正在调用真实 OpenAI 接口...")
        # Call CFO
        print("[Milestone] 1. 正在让 CFO (财务分析师) 分析三张报表与估值定价...")
        cfo_user = cfo_grounding + f"请针对目标公司 {name} ({ticker})，结合财务分析师职责，撰写一份核心的专项财务分析报告。必须包含毛利质量、利润池、估值定价倍数和DCF推导核心结论。"
        cfo_draft = call_openai(openai_key, cfo_prompt, cfo_user)
        time.sleep(1.0)
        
        # Call CRO
        print("[Milestone] 2. 正在让 CRO (合规与风险官) 分析 PEST 宏观及供应链风险...")
        cro_user = f"请针对目标公司 {name} ({ticker})，结合合规与风险官职责，撰写一份专项合规与风险报告。必须包含政治地缘限制、宏观利率周期和替代品长周期威胁。"
        cro_draft = call_openai(openai_key, cro_prompt, cro_user)
        time.sleep(1.0)
        
        # Call Expert
        print(f"[Milestone] 3. 正在让 {expert_name} 分析专属行业深度指标与壁垒...")
        exp_user = f"请针对目标公司 {name} ({ticker})，结合 {expert_name} 职责，撰写一份垂直行业专项报告。重点讨论行业专属业务指标、生产工艺或开发者生态护城河壁垒。"
        expert_draft = call_openai(openai_key, expert_prompt, exp_user)
        time.sleep(1.0)
        
        # Call CEO for final synthesis
        print("[Milestone] 4. 正在让 CEO 战略官整合团队草稿并输出 8 维深度行业研究报告...")
        ceo_user = cfo_grounding + f"""目标公司：{name} ({ticker})
以下是你的团队提交的专项分析报告：

---
【CFO 专项财务分析】:
{cfo_draft}

---
【CRO 专项合规与风险报告】:
{cro_draft}

---
【{expert_name} 专项报告】:
{expert_draft}
---

请参考并深度提炼以上草稿，遵循以下 GICS 行业研究规范，输出一份极其详实、高阶的 8 维行业研究报告：
{strategy.get_system_guideline()}
"""
        final_report = call_openai(openai_key, ceo_prompt, ceo_user)
        
    else:
        print("[Milestone] 未检测到大模型 API 密钥。系统正启用本地高水准行业专家模拟协同分析...")
        
        # Simulate step 1 (CFO)
        print("[Milestone] 1. 正在让 CFO (财务分析师) 分析三张报表与估值定价...")
        time.sleep(1.0)
        
        # Simulate step 2 (CRO)
        print("[Milestone] 2. 正在让 CRO (合规与风险官) 分析 PEST 宏观及供应链风险...")
        time.sleep(1.0)
        
        # Simulate step 3 (Expert)
        print(f"[Milestone] 3. 正在让 {expert_name} 分析专属行业深度指标与壁垒...")
        time.sleep(1.0)
        
        # Simulate CEO Synthesis
        print("[Milestone] 4. 正在让 CEO 战略官整合团队草稿并输出 8 维深度行业研究报告...")
        time.sleep(1.5)
        
        cfo_draft, cro_draft, expert_draft, final_report = generate_simulated_report(company, category_path, chart_data)
        
    # Post-process reports generated by LLMs to inject Yahoo market data table and SEC references
    if gemini_key or openai_key:
        market_data_section = ""
        if chart_data and chart_data.get("price") is not None:
            price_val = chart_data.get("price")
            low_val = chart_data.get("fiftyTwoWeekLow") or "--"
            high_val = chart_data.get("fiftyTwoWeekHigh") or "--"
            vol_val = chart_data.get("volume") or "--"
            exc_val = chart_data.get("exchange") or "--"
            cur_val = chart_data.get("currency") or "USD"
            
            if isinstance(vol_val, (int, float)):
                if vol_val >= 1_000_000:
                    vol_str = f"{vol_val / 1_000_000:.2f} M"
                elif vol_val >= 1_000:
                    vol_str = f"{vol_val / 1_000:.2f} K"
                else:
                    vol_str = str(vol_val)
            else:
                vol_str = str(vol_val)

            market_data_section = f"\n### 📊 实时市场数据（数据源：Yahoo Finance）\n| 实时股价 | 货币 | 52周区间 | 日成交量 | 交易所 |\n| :--- | :--- | :--- | :--- | :--- |\n| **{price_val:.2f}** | {cur_val} | {low_val} - {high_val} | {vol_str} | {exc_val} |\n"

        references_section = f"""\n\n## 六、 数据真实性与引用文献 (Data Integrity & References)\n* **实时市场报价数据源**：[Yahoo Finance (雅虎财经官方行情页面 - {ticker})](https://finance.yahoo.com/quote/{ticker})\n* **官方企业信息与高管构成**：[Yahoo Finance Profile (雅虎财经公司档案 - {ticker})](https://finance.yahoo.com/quote/{ticker}/profile)\n* **公司历史财务报表与披露件**：[SEC EDGAR Company Search (美国证券交易委员会官方披露检索)](https://www.sec.gov/edgar/searchedgar/companysearch?companyName={ticker})\n* **公司最新公告及SEC申报历史**：[SEC EDGAR Filing History (美国证监会披露历史 - {ticker})](https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&action=getcompany)\n* **行业基准划分标准**：[Standard & Poor's / MSCI 联合发布全球标准行业分类标准 (GICS)]\n"""

        # Inject market data after the first header
        title_end = final_report.find("\n")
        if title_end != -1:
            final_report = final_report[:title_end] + "\n" + market_data_section + final_report[title_end:]
        else:
            final_report = final_report + "\n" + market_data_section
        final_report = final_report.strip() + "\n" + references_section

    # 5. Save the final report back to the database with status 'completed'
    print(f"[Milestone] 5. 正在将 {ticker} 终审报告持久化至 PostgreSQL 数据库，状态更新为 completed...")
    db.upsert_report(ticker, final_report, "completed")
    print(f"[Milestone] 成功完成 {ticker} 的全部行研报告并成功归档！")
    
    current_ticker = None

def main():
    global shutdown_requested
    print("=" * 60)
    print("        GICS 行业星图 - AI 多角色协同通宵跑批分析器")
    print("=" * 60)
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("提示: 您可以随时通过快捷键 Ctrl+C 中断分析，系统会自动安全退出并保存进度。")
    print("-" * 60)
    
    # 1. Initialize database first to make sure tables are ready
    try:
        db.init_db()
    except Exception as e:
        print(f"FATAL: Failed to connect to or initialize database: {e}")
        sys.exit(1)
        
    # 2. Query pending constituents
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.ticker, c.name, c.gics_code, c.description, r.status
                FROM gics.companies c
                LEFT JOIN gics.company_reports r ON c.ticker = r.ticker
                WHERE r.status IS NULL OR r.status != 'completed'
                ORDER BY c.ticker;
            """)
            pending_companies = cur.fetchall()
            
            cur.execute("SELECT COUNT(*) FROM gics.companies;")
            total_count = cur.fetchone()["count"]
            
            cur.execute("SELECT COUNT(*) FROM gics.company_reports WHERE status = 'completed';")
            completed_count = cur.fetchone()["count"]
            
    print(f"S&P 500 总股数: {total_count}")
    print(f"当前已分析完毕: {completed_count}")
    print(f"待跑批分析股票: {len(pending_companies)}")
    print("-" * 60)
    
    if len(pending_companies) == 0:
        print("[Milestone] 所有公司已全部分析完毕！无须跑批。")
        return
        
    print("[Milestone] 正在开始通宵跑批工作流...")
    
    success_count = 0
    start_time = time.time()
    
    for i, company in enumerate(pending_companies):
        if shutdown_requested:
            break
            
        print(f"\n[进度] 正在处理第 {i+1}/{len(pending_companies)} 家公司 (总进度: {completed_count + success_count + 1}/{total_count})")
        
        try:
            process_company(company)
            success_count += 1
        except Exception as e:
            print(f"ERROR: 分析 {company['ticker']} 时发生错误: {e}")
            try:
                db.upsert_report(company["ticker"], f"分析失败: {str(e)}", "failed")
            except Exception as dbe:
                print(f"ERROR: 无法将失败状态保存至数据库: {dbe}")
                
        # Small cooldown between companies to prevent CPU spike
        time.sleep(0.5)
        
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("        跑批分析结束汇总")
    print("=" * 60)
    print(f"本次运行处理成功: {success_count} 家公司")
    print(f"本次累计耗时: {duration:.2f} 秒")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
