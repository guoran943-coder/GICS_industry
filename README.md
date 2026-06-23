# GICS 行业分类同步 MCP 服务 (industry_ai_agent)

这是一个基于 MCP (Model Context Protocol) 的本地智能体服务，用于在 PostgreSQL 中初始化 GICS 行业分类结构，提供个股的行业映射登记、按行业前缀模糊检索个股以及获取公司四级行业分类链条的功能。

## 目录结构
*   `pyproject.toml`：使用 `uv` 工具链管理项目依赖。
*   `db.py`：数据库操作层（封装了 PostgreSQL 架构初始化、数据增删改查）。
*   `gics_seed.json`：内置的标准 GICS 2023 行业架构数据种子文件。
*   `mcp_server.py`：使用 Python `FastMCP` 实现的 MCP 服务器。
*   `mcp_client.py`：测试客户端，支持交互式命令行及单命令调用。

---

## 快速上手与验证

### 1. 安装项目环境与依赖
确保本地安装了 `uv` 工具链，在当前目录下运行以下命令安装虚拟环境及所有依赖：
```bash
uv sync
```

### 2. 数据库配置
本系统默认连接本地 PostgreSQL 的 `industry` 数据库：
*   **默认连接串**：`postgresql://guoying@localhost:5432/industry`
*   如需使用自定义凭证，可在运行前配置 `DATABASE_URL` 环境变量：
    ```bash
    export DATABASE_URL="postgresql://username:password@localhost:5432/your_database"
    ```

### 3. 一键初始化与数据同步
通过 MCP 客户端运行以下命令，初始化 `gics` 命名空间及表结构，并导入种子数据：
```bash
# 1. 创建表结构 (调用 init_database 接口)
uv run python mcp_client.py init_database

# 2. 同步 GICS 行业树分类 (调用 sync_gics_categories 接口)
uv run python mcp_client.py sync_gics_categories
```

### 4. 登记与检索测试

#### A. 登记个股映射 (update_company_gics)
```bash
# 登记苹果公司映射到 GICS 45202030 (技术硬件、存储与外设)
uv run python mcp_client.py update_company_gics ticker=AAPL name="Apple Inc." gics_code=45202030 description="智能手机及消费电子巨头"

# 登记英伟达公司映射到 GICS 45301020 (半导体)
uv run python mcp_client.py update_company_gics ticker=NVDA name="NVIDIA Corporation" gics_code=45301020 description="GPU 与 AI 芯片霸主"
```

#### B. 检索个股完整的行业分类链条 (get_company_classification)
```bash
uv run python mcp_client.py get_company_classification ticker=AAPL
```
*输出样例：*
> - **Sector (一级板块)** [45]: Information Technology / 信息技术
> - **Industry Group (二级行业组)** [4520]: Technology Hardware & Equipment / 技术硬件与设备
> - **Industry (三级行业)** [452020]: Computers & Peripherals / 计算机与外设
> - **Sub-Industry (四级子行业)** [45202030]: Technology Hardware, Storage & Peripherals / 技术硬件、存储与外设

#### C. 按行业前缀检索个股列表 (get_companies_by_gics)
```bash
# 检索信息技术大类 (45) 下的所有上市公司
uv run python mcp_client.py get_companies_by_gics gics_code=45
```

---

## 如何在 Claude Desktop 等 IDE 中集成该 MCP

在 Claude Desktop 或您的开发 IDE 配置文件（如 `claude_desktop_config.json`）中添加以下配置：

```json
{
  "mcpServers": {
    "gics-industry-server": {
      "command": "/Users/guoying/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/guoying/weixindushu/industry_ai_agent",
        "run",
        "mcp_server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://guoying@localhost:5432/industry"
      }
    }
  }
}
```
配置完成后重启大模型客户端，智能体即可获得主动查询与更新您本地 GICS 行业分类的能力！

---

## ThroatScan HTTP API（Phase 2）

`api_server.py` 现提供 ThroatScan 兼容端点：

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 健康检查（PostgreSQL + 静态 SP500 缓存） |
| `GET /api/companies/{ticker}/classification` | 单 ticker GICS |
| `POST /api/companies/classifications` | 批量 `{ "tickers": ["NVDA", "AMD"] }` |

静态模式无需数据库，依赖 `data/throatscan-gics-cache.json`（503 条 S&P 500 映射）。

### 本地启动

```bash
uv sync
uv run uvicorn api_server:app --host 0.0.0.0 --port 8001
curl http://127.0.0.1:8001/api/companies/NVDA/classification
```

### 刷新静态缓存

```bash
uv run python export_for_throatscan.py
```

### 部署到 Vercel（推荐，与 ThroatScan 同账号）

```bash
npx vercel deploy --prod --yes
```

部署后在 ThroatScan 项目设置：

```bash
GICS_API_URL=https://<your-gics-api>.vercel.app
```

### 部署到 Railway / Render（Docker，可接 PostgreSQL）

- **Railway**：连接 GitHub 仓库，使用根目录 `Dockerfile` + `railway.toml`
- **Render**：Blueprint `render.yaml`，可选配置 `DATABASE_URL`

Fork 仓库：[guoran943-coder/GICS_industry](https://github.com/guoran943-coder/GICS_industry)
