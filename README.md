# Car Helper

Car Helper 是一个本地优先的汽车知识图谱问答 Agent。用户用自然语言描述预算、能源类型、车型级别或品牌，DeepSeek 选择受约束的查询工具，从 Neo4j 获取结构化车型数据，并可通过 Tavily 补充口碑、新闻和优惠等时效信息。

这个项目当前是知识图谱增强的问答系统，不包含用户画像、学习排序或独立推荐评分模型。

## 架构

```text
React / CLI
    │
    ├─ FastAPI + SSE
    │       │
    │       └─ LangChain Agent + DeepSeek
    │               ├─ 参数化 Neo4j 查询工具
    │               └─ Tavily 网络搜索
    │
    ├─ PostgreSQL：LangGraph 短期会话 checkpoint
    └─ SQLite：本地用户身份、会话目录和可控长期记忆
```

后端只创建一个 Agent、一个 PostgreSQL 连接池和一个 checkpointer。不同会话通过 LangGraph `thread_id` 隔离，同一会话的并发请求会串行处理。网页端在同一 `thread_id` 下保留完整消息列表，每轮回答仍通过 SSE 增量显示。

系统首次启动会在 `var/car_helper.db` 创建一个本地用户 UUID。SQLite 只保存本地身份、会话目录和用户明确要求记住的稳定偏好；短期对话正文仍由 PostgreSQL checkpoint 保存。网页右上角的“记忆”面板可查看、修改和逐条删除长期记忆。当前预算、给他人选车、本轮候选等临时条件不会自动写入长期记忆。

## 环境

- Python 3.12
- Node.js 20+
- Neo4j 5+
- PostgreSQL
- DeepSeek API Key
- Tavily API Key（仅网络搜索需要）

本项目开发环境使用 `E:\Anaconda_envs\envs\langchain_v1\python.exe`。

安装依赖：

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m pip install -r requirements.txt
cd frontend
npm install
```

在项目根目录创建 `.env`，至少配置：

```env
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
TAVILY_API_KEY=...
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
DB_URI=postgresql://user:password@localhost:5432/car_helper_sessions
LOCAL_DB_PATH=var/car_helper.db
```

`.env` 已被 Git 忽略。不要提交密钥或数据库密码。

## 启动

开发模式需要两个进程：Vite 在 3000 端口提供热更新页面，并将 `/api` 代理到 7860 端口的 FastAPI。

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m src.api
cd frontend
npm run dev
```

访问 `http://localhost:3000`。

生产模式只需要 FastAPI 一个进程。React 构建产物由 FastAPI 托管，3000 端口不再使用：

```powershell
cd frontend
npm run build
cd ..
E:\Anaconda_envs\envs\langchain_v1\python.exe -m src.api
```

访问 `http://127.0.0.1:7860`。未加入用户认证前，后端默认只监听本机地址，不应直接暴露到公网。

命令行入口：

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m src.agent
```

CLI 支持 `/resume` 恢复会话和 `/exit` 退出。

## 数据导入

车型原始数据不随代码仓库发布，并已被 Git 忽略。运行导入器前，需要在本地准备 `src/pipeline/entities/` 和 `src/pipeline/relationships/`；所需文件名、字段和校验规则以 `src/pipeline/data_import/import_data.py` 为准。

导入器默认只校验本地数据，不连接或修改数据库：

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m src.pipeline.data_import.import_data
```

校验通过后执行幂等导入：

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m src.pipeline.data_import.import_data --apply
```

旧数据库没有新版 `_source_id`，首次迁移需要明确替换全部图数据：

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m src.pipeline.data_import.import_data --apply --replace --confirm-replace
```

最后一条命令会删除现有 Neo4j 图数据。执行前必须自行完成备份和确认；应用启动和测试都不会自动创建索引或修改 Neo4j schema。

## 测试

确定性单元测试不访问网络或真实数据库：

```powershell
E:\Anaconda_envs\envs\langchain_v1\python.exe -m pytest tests/unit -v
```

显式运行只读集成测试：

```powershell
$env:RUN_INTEGRATION = "1"
E:\Anaconda_envs\envs\langchain_v1\python.exe -m pytest tests/integration -v
```

前端验证：

```powershell
cd frontend
npm run lint
npm run build
```

仓库不保存静态性能报告。性能数据必须由当前版本重新运行 `scripts/load_test.py` 和 `scripts/sampling_comparison.py` 后得出。

## 主要目录

```text
src/
├─ agent.py                 CLI 入口
├─ agent_factory.py         Agent、LLM 和工具注册
├─ api.py                   FastAPI、SSE、会话接口、前端托管
├─ config.py                环境配置
├─ session.py               PostgreSQL checkpointer 与 CLI 会话恢复入口
├─ storage/                 SQLite 本地身份、会话目录和长期记忆
├─ memory/                  记忆上下文、提示词注入和受约束工具
├─ db/                      Neo4j 连接
├─ tools/                   车型查询和网络搜索工具
├─ prompts/                 Agent 系统提示词
└─ pipeline/data_import/    安全数据校验与导入

frontend/                   React + TypeScript 前端
tests/unit/                 隔离单元测试
tests/integration/          显式外部服务测试
scripts/                    压测与采样评估
```

开发约束和安全规则见 `AGENTS.md`。
