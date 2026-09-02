# Car Helper — 智能选车助手

## 项目简介
基于 Neo4j 知识图谱（4 万+车型）+ DeepSeek LLM + Tavily 搜索的汽车推荐 Agent。用户通过自然语言提问，Agent 调用参数化 Cypher 工具查询结构化数据，或通过网络搜索补充口碑/评测等非结构化信息。

## 技术栈
- Agent 框架：LangGraph（create_agent）
- LLM：DeepSeek（via OpenAI-compatible API，thinking 模式已适配）
- 知识图谱：Neo4j（40,912 车型 / 636 品牌 / 7,077 车系）
- 会话持久化：PostgreSQL（AsyncPostgresSaver）
- 网络搜索：Tavily Search
- 测试：pytest（23 条工具级 + 2 条搜索 + 9 条 E2E）

## 运行方式

```bash
# 启动 Web 服务（FastAPI + SSE + 前端）
cd Agent_design/car_helper
E:/Anaconda_envs/envs/langchain_v1/python.exe -m src.api
# 访问 http://localhost:7860

# 启动 Agent（交互式命令行，异步流式输出）
cd Agent_design/car_helper
python -m src.agent

# 运行测试
cd Agent_design/car_helper
E:/Anaconda_envs/envs/langchain_v1/python.exe -m pytest tests/ -v

# 数据导入到 Neo4j（分两步，按顺序执行）
cd Agent_design/car_helper/src/pipeline/data_import
python store_data_to_neo4j.py
python insert_data_to_neo4j.py
```

**前提条件**：
- Neo4j 数据库运行在 `bolt://localhost`，默认用户 `neo4j` / 密码 `12345678`
- PostgreSQL 运行在 `localhost:5432`，数据库 `car_helper_sessions`
- `.env` 文件配置了 `DEEPSEEK_API_KEY`、`TAVILY_API_KEY` 等
- Python 3.12，运行环境：`E:/Anaconda_envs/envs/langchain_v1`

## 目录结构

```
car_helper/
├── CLAUDE.md                  # 项目文档（本文件）
├── task.md                    # 任务清单
├── design.md                  # 设计规格
├── .env                       # API Keys（不入库）
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── agent.py               # Agent 主入口（LLM + 工具注册 + CLI 交互）
│   ├── api.py                 # FastAPI + SSE Web 后端
│   ├── config.py              # 全局配置（API Keys、DB URI）
│   ├── deepseek_patched.py    # DeepSeek thinking mode monkey-patch
│   ├── session.py             # 会话管理（PostgreSQL 持久化 + 历史恢复）
│   ├── db/
│   │   ├── __init__.py
│   │   └── neo4j_conn.py      # Neo4j 线程安全单例连接
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── neo4j_tools.py     # 7 个参数化 Cypher 查询工具 + 分层采样 + 结果校验
│   │   └── web_search.py      # Tavily 搜索工具封装
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── system_prompt.py   # 系统提示词（含查询复杂度分级策略）
│   │   └── compress_prompt.py # 消息压缩提示词
│   ├── pipeline/
│   │   ├── data_import/       # Neo4j 数据导入脚本
│   │   ├── entities/          # 实体数据文件
│   │   └── relationships/     # 关系数据文件
│   └── web/                   # 前端界面（引擎室风格）
│       ├── index.html
│       ├── style.css
│       └── app.js
├── tests/
│   ├── conftest.py
│   ├── test_neo4j_tools.py    # 23 条工具级测试
│   ├── test_web_search.py     # 2 条搜索测试
│   └── test_e2e.py            # 9 条端到端测试
└── scripts/
    └── crawl.py               # 懂车帝数据爬虫
```

## 核心架构

### 参数化 Cypher（非 LLM 生成）
所有查询工具使用硬编码 Cypher 模板 + `$param` 绑定，LLM 只负责选工具和填参数。这彻底消除了 Cypher 注入风险和查询幻觉。

### 四维分层采样
查询结果最多返回 500 条，通过四维贪心覆盖算法压缩到 20 条：品牌覆盖 → 能源类型覆盖 → 价格区间覆盖 → 上市时间填充。

### 查询复杂度分级
- **简单查询**（单维度）：直接调工具，简洁回答
- **复杂查询**（多条件/对比/推荐）：多步推理，结构化分析
- **复合查询**（结构化+非结构化）：先查知识图谱，再搜网络补充

### DeepSeek Thinking Mode
通过 monkey-patch 4 个 langchain-openai 内部函数，实现 reasoning_content 的全生命周期保全（反序列化、序列化、内容格式化、流式输出）。

### 会话持久化
PostgreSQL（AsyncPostgresSaver）存储完整对话状态，支持 `/resume` 恢复历史会话、`/exit` 时持久化最后提问。

## Web 接口
- `POST /api/chat` — SSE 流式对话（message, session_id）
- `GET /api/sessions` — 获取会话历史列表
- `GET /` — 前端页面

## CLI 命令
- `/exit` — 保存会话并退出
- `/resume` — 恢复历史会话
