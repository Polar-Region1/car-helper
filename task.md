# Car Helper 重构任务清单

## 阶段〇：项目整理

- [x] **T0: 项目文件清理** — 删除 7 个无用/重复 Python 文件: test.py(旧system prompt)、test-2.py(垃圾代码)、src/test.py+src/test-2.py(一次性生成脚本)、src/store_data_to_neo4j.py+src/insert_data_to_neo4j.py(重构前旧版)、demo/demo3.py(旧agent架构)。清理后 20→13 个 .py 文件。2026-05-02

## 阶段一：基础设施重构

- [x] **T1: 项目目录重组** — 新目录已创建: src/tools/, src/db/, src/prompts/, src/data_import/
- [x] **T2: Neo4j 连接管理抽取** — db/neo4j_conn.py 单例模式（含线程安全双重检查锁），agent.py + 两个导入脚本均已使用

## 阶段二：工具层重构（核心）

- [x] **T3: 品牌查询工具 `query_by_brand`** — 参数: brand, limit；固定 Cypher 模板
- [x] **T4: 价格区间查询工具 `query_by_price_range`** — 参数: price_range, limit
- [x] **T5: 能源类型查询工具 `query_by_energy_type`** — 参数: energy_type, limit
- [x] **T6: 多条件组合查询工具 `query_by_conditions`** — 参数: price_range?, energy_type?, level?, brand?；动态拼 WHERE，参数化传入
- [x] **T7: 车型对比工具 `compare_models`** — 参数: brand, limit
- [x] **T8: 保养成本查询工具 `query_by_maintenance_cost`** — 参数: price_ranges, limit
- [x] **T9: Schema 探索工具 `explore_schema`** — 参数: node_type(白名单校验), limit

## 阶段三：采样与校验层

- [x] **T10: 分层采样函数 `stratified_sample`** — 四维度采样（品牌/能源/价格/上市时间），默认 20 条
- [x] **T11: 采样统计函数 `sample_stats`** — 原始/采样条数、品牌覆盖率、能源覆盖率
- [x] **T12: 查询结果校验函数 `validate_result`** — 空结果拦截 + 关键字段缺失告警

## 阶段四：Agent 重组

- [x] **T13: System Prompt 瘦身** — 从 396 行裁剪到 ~30 行，删除全部 Cypher 示例
- [x] **T14: Agent 注册新工具** — 7 个参数化工具 + web_search 替换原 neo4j_query
- [x] **T15: Web Search 工具迁移** — 抽到 tools/web_search.py

## 阶段五：验证

- [x] **T16: 工具级测试** — 23 条测试全通过，覆盖所有 7 个工具 + web_search（正常/异常/边界场景）。tests/test_neo4j_tools.py + tests/test_web_search.py
- [x] **T17: 端到端测试** — 9 条 E2E 测试全通过，覆盖品牌/价格/能源/对比/保养/多条件/搜索/模糊提问/不存在的品牌。tests/test_e2e.py

## 阶段六：生产级加固

- [x] **T18: 单例线程安全** — Neo4jConnection 加双重检查锁（threading.Lock）
- [x] **T19: 异步化改造** — 全部工具改为 async def，同步 Neo4j/Tavily 调用通过 asyncio.to_thread 避免阻塞；agent.py 改为 astream_events 流式输出
- [x] **T20: Neo4j 索引** — 品牌.name、价格区间.name、能源类型.name 三个字段建索引，ensure_indexes() 启动时自动执行
- [x] **T21: 错误处理** — Neo4jConnection 连接失败/会话不可用抛 Neo4jConnectionError；查询层捕获连接异常和通用异常返回中文降级提示；Tavily 超时/网络错误返回友好提示；ensure_indexes 失败不阻塞启动；close() 防 close 本身抛异常

## 阶段七：项目重构与技术迁移（2026-05-14）

- [x] **T22: 文件结构重构** — config.py 迁入 src/；data_import/entities/relationships 迁入 src/pipeline/；main.py 迁入 scripts/crawl.py；删除 agent-v1.py、demo/、car_data/、middleware/（未接入的中间件）
- [x] **T23: DeepSeek Thinking Mode 适配** — 从高考志愿助手迁移 deepseek_patched.py（4 个 monkey-patch 函数），agent.py 启用 thinking 模式 + reasoning_content 双通道流式渲染
- [x] **T24: PostgreSQL 会话持久化** — InMemorySaver 替换为 AsyncPostgresSaver；新增 session.py（会话 ID 管理、/resume 恢复、/exit 持久化最后提问）；config.py 增加 DB_URI
- [x] **T25: 查询复杂度分级策略** — system_prompt.py 增加三级路由：简单查询（单维度，简洁回答）→ 复杂查询（多条件/对比，多步推理）→ 复合查询（结构化+非结构化组合）

## 阶段八：Web 界面部署（2026-05-15）

- [x] **T26: FastAPI SSE 后端** — 新增 api.py，复用现有 agent 逻辑，SSE 流输出 connected/tool_start/tool_end/reasoning/content/done/error 事件；GET /api/sessions 会话列表
- [x] **T27: 引擎室风格前端** — 新增 src/web/（index.html + style.css + app.js），深色工业美学，衬线体正文，打字机流式输出，工具调用仪表盘动画，reasoning 折叠，会话管理
- [x] **T28: 项目文档更新** — CLAUDE.md 更新目录结构、运行方式、Web 接口说明
