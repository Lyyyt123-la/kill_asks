# 问数 AskData · 对话式数据分析平台

> 上传 CSV / Excel / PDF / Word / 图片，用一句自然语言完成 **查询 → 自动 SQL → 图表 → 业务洞察 / 文档问答**。
> 赛题方向：AI 数据分析与可视化（自然语言交互降低数据分析门槛）。

| 作品信息 | 内容 |
|---|---|
| 参赛赛道 | AI WEB 网页开发挑战赛 · 赛道二 |
| 学校 | 广东科贸职业学院 |
| 指导老师 | 林龙键 |
| 团队成员 | 罗勇添、辛嘉炜、林俊宁 |
| 技术文档 | [技术文档 PDF](docs/技术文档_问数AskData.pdf) · [Word 版](docs/技术文档_问数AskData.docx) |
| 演示视频素材 | [视频脚本与分镜](docs/演示视频脚本.md) · [字幕 SRT](docs/演示视频字幕.srt) |

![欢迎页](docs/screenshots/01-welcome.png)

## 已实现功能

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据接入 | ✅ | CSV / Excel 上传，自动识别编码、表头、时间/数值/布尔字段，自动建 DuckDB 表 |
| 文档接入 | ✅ | PDF / Word 提取正文与表格，表格自动变成可分析数据集 |
| 图片识别 | ✅ | 截图经视觉大模型（qwen3-vl-plus）识别表格 → CSV → 数据集 |
| 文档问答 | ✅ | RAG：切片 + 向量/关键词混合检索 + 带引用片段回答 |
| 数据预览 | ✅ | 网页端查看前 100 行 + 字段列表（类型 / 样例 / 枚举 / 空值率） |
| 对话式交互 | ✅ | ChatGPT 风格多轮对话，自动携带上一轮 SQL 与结果列，支持追问下钻 |
| 自然语言转 SQL | ✅ | LLM 生成 DuckDB SQL；未配置 Key 时自动进入规则版演示模式 |
| SQL 安全校验 | ✅ | 只读、单语句、仅 SELECT/WITH、表字段白名单、强制 LIMIT、超时中断 |
| 失败自动修复 | ✅ | 校验/执行失败时把报错回喂模型重写 SQL，最多重试 2 次 |
| 自动可视化 | ✅ | ECharts 折线 / 柱状 / 环形 / 表格，支持手动切换、导出图片与 CSV |
| 智能洞察 | ✅ | 二次调用模型生成「结论 + 2~4 条带数字的洞察 + 追问建议」，失败时本地统计兜底 |
| 检查器 | ✅ | 右侧抽屉查看结果表、可展开 SQL、执行耗时、生成次数与字段结构 |
| 演示保底 | ✅ | 内置双11示例数据；无 Key / 断网 / 模型超时也可完整演示 |

![问答与图表](docs/screenshots/03-answer-region.png)
![检查器](docs/screenshots/04-inspector.png)

## 技术架构

```
Vue 3 + Vite + ECharts + 原生 CSS
        │  REST / SSE（预留）        http://127.0.0.1:5173
        ▼
FastAPI（Python 3.11+）
   ├─ routers/       datasets · chat · llm 健康检查
   ├─ services/
   │   ├─ dataset_service.py   CSV/Excel → pandas → DuckDB + 元数据(SQLite)
   │   ├─ nl2sql.py            理解 → 生成 SQL → 校验 → 执行 → 重试 → 图表 → 洞察
   │   ├─ sql_guard.py         sqlglot 静态校验 + 强制 LIMIT + 只读白名单
   │   ├─ executor.py          只读 DuckDB 连接 + 超时中断 + 行数上限
   │   ├─ mock_planner.py      无 Key 时的规则版 NL2SQL（比赛演示兜底）
   │   ├─ insight.py           洞察生成（LLM / 本地统计）
   │   └─ llm.py               OpenAI 兼容协议客户端（强制 JSON + 解析重试）
   ├─ prompts.py       NL2SQL / SQL 修复 / 洞察 三套 Prompt（技术文档可直接引用）
   └─ store.py         SQLite 存数据集元数据
```

## 快速开始（Windows，已验证）

环境要求：Python 3.11+、Node.js 20+。

```powershell
# 0. 克隆
git clone https://github.com/Lyyyt123-la/kill_asks.git
cd kill_asks

# 1. 一键安装依赖 + 生成演示数据（首次执行）
pwsh -ExecutionPolicy Bypass -File scripts\setup.ps1

# 2. 配置大模型（可选：不配置也能以「演示模式」完整运行）
#    编辑 backend\.env，填入 LLM_API_KEY（智谱 GLM-4-Flash 等 OpenAI 兼容接口）
#    修改后重启后端即可生效；可用 GET /api/llm/test 验证连通性

# 3. 启动前后端
pwsh -ExecutionPolicy Bypass -File scripts\dev.ps1
# 打开 http://127.0.0.1:5173
```

**生产模式（单端口，方便部署）**：

```powershell
pwsh -ExecutionPolicy Bypass -File scripts\build.ps1   # 构建前端到 frontend/dist
pwsh -ExecutionPolicy Bypass -File scripts\dev.ps1     # 或手动启动 uvicorn
# 访问 http://127.0.0.1:8000（FastAPI 直接托管前端）
```

手动启动方式：

```powershell
# 后端
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd frontend
npm run dev
```

## 大模型配置

复制 `backend/.env.example` 为 `backend/.env`，填入任意 OpenAI 兼容服务的 Key。

**推荐：阿里云百炼 DashScope（一个 Key 可调用 Qwen / DeepSeek / GLM / Kimi 等）**

```ini
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
LLM_API_KEY=你的Key
```

经过实测（本项目演示数据 + 6 类问题）：`qwen-plus` 约 8–12 秒/问，SQL 与洞察质量稳定；
`qwen3.8-max-0902` 质量更高但单问 30–90 秒，不建议现场演示使用。

备选：智谱 GLM、DeepSeek、Kimi、OpenAI，`.env.example` 中已给出配置示例。
**Key 只在后端环境变量中读取，不会进入前端代码，也不提交到 Git。**

- 未配置 Key：`/api/health` 返回 `mock_mode: true`，系统自动使用规则版 NL2SQL；
- 配置 Key 后：自动调用真实模型，失败时仍会降级到演示模式，保证演示不中断；
- 可用 `GET /api/llm/status`、`POST /api/llm/test` 检查模型配置与连通性。

## 演示数据与推荐问题

`demo_data/double11_sales.csv`：双11大促销售数据（36,000 行，10 列，含空值等脏数据）；
`demo_data/双11大促销售数据.xlsx`：中文表头版本（8,000 行），用于演示 Excel 上传。

推荐提问（点击欢迎页/数据集卡片可直接发送）：

1. 各区域的销售额对比
2. 双11当天各小时销售额趋势
3. 销售额最高的 5 个品类
4. 各渠道的退款率排名

## 主要 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 服务状态、模型是否启用、演示模式标记 |
| POST | `/api/datasets/upload` | 上传 CSV/Excel（multipart） |
| POST | `/api/datasets/demo` | 载入内置示例数据集 |
| GET | `/api/datasets` | 数据集列表 |
| GET | `/api/datasets/{id}` | 数据集详情（字段、样例、枚举） |
| GET | `/api/datasets/{id}/preview?limit=100` | 数据预览 |
| DELETE | `/api/datasets/{id}` | 删除数据集 |
| POST | `/api/chat` | 自然语言分析（返回 SQL、结果、图表配置、洞察、步骤耗时） |
| POST | `/api/query` | 检查器手动执行 SQL（经同样安全校验） |
| GET | `/api/llm/status` | 模型配置状态 |
| POST | `/api/llm/test` | 模型连通性测试 |

启动后访问 <http://127.0.0.1:8000/docs> 可查看 Swagger 交互文档。

## 目录结构

```
kill_asks/
├─ backend/
│  ├─ app/             FastAPI 应用（routers / services / prompts）
│  ├─ requirements.txt
│  ├─ .env.example     模型配置模板（真实 .env 已被 gitignore）
│  └─ data/            运行时数据（上传文件 / DuckDB / SQLite，已忽略）
├─ frontend/
│  ├─ src/             Vue3 应用（components / api / styles）
│  ├─ scripts/         e2e-screenshots.mjs 真实浏览器点击截图脚本
│  └─ vite.config.js   dev 代理 /api → 127.0.0.1:8000
├─ demo_data/          示例数据（CSV + 中文表头 Excel）
├─ docs/screenshots/   真实运行截图（E2E 自动生成）
├─ scripts/            setup / dev / build / 数据生成 / API 冒烟测试
└─ README.md
```

## 测试与自查

```powershell
# 后端 API 冒烟测试（健康检查 / 演示数据 / 4 类问题 / 危险 SQL 拦截）
backend\.venv\Scripts\python.exe scripts\test_api.py

# 真实浏览器 E2E：自动走完「载入示例 → 提问 → 出图 → 检查器 → 上传中文 Excel → 再提问」并截图
cd frontend
node scripts\e2e-screenshots.mjs
```

## 在线演示

- 本地演示：`http://127.0.0.1:8000`（后端同时托管前端）
- 临时公网演示：`https://wicked-stars-care.loca.lt`（隧道，兼容机开机时有效；首次访问如出现 Tunnel Password 提示，密码见 <https://loca.lt/mytunnelpassword>）
- 长期部署：仓库已提供 `Dockerfile` / `docker-compose.yml` / `render.yaml`，见 [Docker 部署说明](docs/部署指南.md)

## 演示素材

`demo_data/documents/` 内置三份演示文件：

| 文件 | 用途 |
|---|---|
| `2025年Q3经营情况报告.pdf` | 演示 PDF 表格提取 + 文档问答（带引用） |
| `双11大促复盘摘要.docx` | 演示 Word 表格提取 |
| `各渠道退款率截图.png` | 演示视觉大模型识别截图表格 |

## 下一步（省赛迭代方向）

- SSE 流式输出「思考步骤」，体验更接近 ChatGPT；
- 多表关联与 SQL JOIN 支持、语义层口径配置；
- 看板收藏与分享、导出 PPT / 长图；
- 用户体系与数据集权限、查询审计面板；
- 部署到云服务器（Docker Compose，单端口 8000 同时托管前端与 API）。

---

如有问题或建议，欢迎提 Issue。
