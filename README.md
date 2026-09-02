# 🚗 Car Helper - 智能汽车推荐Agent

基于 **LangGraph + Neo4j知识图谱** 的智能选车助手，通过自然语言对话帮助用户找到理想车型。

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://github.com/langchain-ai/langgraph)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008CC1.svg)](https://neo4j.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 核心亮点

### 📊 规模与性能
- **40,912** 条车型数据 | **636** 个品牌 | **7,077** 个车系
- **P95响应 <100ms**（所有查询工具，最快1.3ms）
- **34** 条自动化测试，核心工具层覆盖率 **93%**

### 🧠 技术创新
- **参数化Cypher设计** — LLM只填参数不生成查询，零SQL注入风险，零查询幻觉
- **四维贪心采样算法** — 品牌/能源/价格/时间四维度覆盖，能源覆盖率比随机采样高 **97%**
- **DeepSeek Thinking Mode适配** — 首创LangGraph框架下的reasoning内容全生命周期保全方案
- **三级查询复杂度分级** — 简单查询快速响应，复杂查询多步推理，复合查询融合网络搜索

### 🛠️ 架构特性
- 🔍 **知识图谱** — Neo4j存储结构化车型数据，快速多维度查询
- 🌐 **网络搜索** — Tavily集成，补充口碑/评测等非结构化信息
- 💬 **流式输出** — FastAPI + SSE实时推送，支持reasoning过程可视化
- 💾 **会话持久化** — PostgreSQL存储对话历史，支持跨会话恢复
- 🧪 **工程化** — pytest测试 + 异步架构 + 错误降级处理

---

## 🚀 快速开始

### 环境要求
- Python 3.12
- Neo4j 5.x（运行在 `bolt://localhost:7687`）
- PostgreSQL（运行在 `localhost:5432`）

### 安装依赖

```bash
git clone https://github.com/Polar-Region1/car-helper.git
cd car-helper
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
TAVILY_API_KEY=your_tavily_api_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
DB_URI=postgresql://user:password@localhost:5432/car_helper_sessions
```

### 导入数据到Neo4j

```bash
cd src/pipeline/data_import
python store_data_to_neo4j.py
python insert_data_to_neo4j.py
```

### 启动Web服务

```bash
python -m src.api
# 访问 http://localhost:7860
```

### 或使用命令行交互

```bash
python -m src.agent
```

---

## 📐 系统架构

```
┌─────────────────┐
│   用户输入      │
│  "推荐一款     │
│   新能源SUV"   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      LangGraph Agent               │
│  ┌──────────────────────────────┐  │
│  │  三级查询复杂度分级策略      │  │
│  │  简单→复杂→复合              │  │
│  └──────────────────────────────┘  │
└──────┬────────────────────┬─────────┘
       │                    │
       ▼                    ▼
┌──────────────┐    ┌──────────────┐
│ Neo4j查询    │    │ Tavily搜索   │
│ 7个参数化工具│    │ 网络补充     │
│ P95<100ms    │    │ 口碑/评测    │
└──────┬───────┘    └──────┬───────┘
       │                    │
       └──────────┬─────────┘
                  ▼
          ┌──────────────┐
          │ 四维贪心采样 │
          │ 500→20条     │
          │ 能源覆盖+97% │
          └──────┬───────┘
                 ▼
         ┌───────────────┐
         │  流式输出结果  │
         │  FastAPI+SSE  │
         └───────────────┘
```

---

## 🔧 核心组件

### 1. 参数化查询工具（7个）

| 工具 | 功能 | P95响应时间 |
|------|------|------------|
| `query_by_brand` | 品牌查询 | 16.1ms |
| `query_by_price_range` | 价格区间查询 | 53.2ms |
| `query_by_energy_type` | 能源类型查询 | 38.0ms |
| `query_by_conditions` | 多条件组合查询 | 52.4ms |
| `compare_models` | 车型对比 | 10.9ms |
| `query_by_maintenance_cost` | 保养成本查询 | 87.8ms |
| `explore_schema` | 知识图谱探索 | 1.3ms |

**设计原则**：固定Cypher模板 + 参数绑定，LLM只负责选工具和填参数，不生成查询语句。

### 2. 四维贪心采样算法

```python
# 将500条结果压缩至20条，同时保证多样性
def stratified_sample(records, max_count=20):
    """
    维度1: 品牌覆盖（占50%配额）
    维度2: 能源类型覆盖
    维度3: 价格区间覆盖
    维度4: 上市时间填充（倒序）
    """
```

**实测效果**：能源类型覆盖率比随机采样高 **97%**（5.0 vs 2.5）

### 3. 三级查询复杂度分级

- **简单查询**（单维度）→ 直接调工具，简洁回答
- **复杂查询**（多条件/对比）→ 多步推理，结构化分析
- **复合查询**（需网络补充）→ 先查图谱，再搜网络，融合输出

### 4. DeepSeek Thinking Mode适配

通过monkey-patch 4个 `langchain-openai` 内部函数，实现reasoning_content的：
- ✅ 反序列化（from API response）
- ✅ 序列化（to checkpoint）
- ✅ 内容格式化（to UI）
- ✅ 流式输出（SSE events）

---

## 📊 性能基准

### 查询性能（100次迭代测试）

| 工具 | 平均耗时 | P50 | P95 | P99 |
|------|---------|-----|-----|-----|
| query_by_brand | 32.1ms | 10.8ms | 16.1ms | 2111.0ms |
| query_by_price_range | 44.2ms | 42.5ms | 53.2ms | 77.3ms |
| query_by_energy_type | 28.8ms | 28.5ms | 38.0ms | 56.7ms |
| query_by_conditions | 46.3ms | 39.6ms | 52.4ms | 661.4ms |
| compare_models | 8.6ms | 8.7ms | 10.9ms | 15.0ms |
| query_by_maintenance_cost | 69.2ms | 69.8ms | 87.8ms | 92.2ms |
| explore_schema | 0.8ms | 0.7ms | 1.3ms | 2.2ms |

### 采样质量对比（50次迭代）

| 维度 | 四维贪心 | 随机采样 | 提升 |
|------|---------|---------|------|
| 能源类型覆盖 | 5.0 | 2.5 | **+97%** |
| 品牌覆盖 | 2.0 | 2.0 | - |

---

## 🧪 测试

### 运行全部测试

```bash
pytest tests/ -v
# 32 passed (23工具级 + 2搜索 + 9 E2E)
```

### 测试覆盖率

```bash
pytest --cov=src tests/
# 核心工具层覆盖率: 93%
```

### 性能测试

```bash
pytest tests/test_performance.py -v -s
```

### 采样算法对比

```bash
python scripts/sampling_comparison.py
```

---

## 📁 项目结构

```
car_helper/
├── src/
│   ├── agent.py              # Agent主入口（LLM + 工具注册）
│   ├── api.py                # FastAPI + SSE Web后端
│   ├── config.py             # 全局配置
│   ├── session.py            # 会话管理（PostgreSQL持久化）
│   ├── deepseek_patched.py   # DeepSeek thinking mode适配
│   ├── db/
│   │   └── neo4j_conn.py     # Neo4j线程安全单例连接
│   ├── tools/
│   │   ├── neo4j_tools.py    # 7个参数化Cypher工具 + 采样算法
│   │   └── web_search.py     # Tavily搜索工具
│   ├── prompts/
│   │   ├── system_prompt.py  # 系统提示词（含分级策略）
│   │   └── compress_prompt.py# 消息压缩提示词
│   └── pipeline/
│       └── data_import/       # Neo4j数据导入脚本
├── tests/
│   ├── test_neo4j_tools.py   # 23条工具级测试
│   ├── test_web_search.py    # 2条搜索测试
│   ├── test_e2e.py           # 9条端到端测试
│   └── test_performance.py   # 性能基准测试
├── scripts/
│   ├── crawl.py              # 懂车帝数据爬虫
│   ├── load_test.py          # FastAPI并发压测
│   └── sampling_comparison.py # 采样算法对比
└── benchmark_report.md       # 性能测试报告
```

---

## 🎯 使用示例

### 品牌查询
```
用户: 比亚迪有哪些纯电动车？
Agent: [调用query_by_brand] 为您找到20款比亚迪车型...
```

### 多条件筛选
```
用户: 推荐一款10-20万的新能源SUV
Agent: [调用query_by_conditions] 符合条件的车型有...
```

### 车型对比
```
用户: 对比几款热门SUV
Agent: [调用compare_models] 为您对比以下车型...
```

### 网络搜索补充
```
用户: 汉EV的口碑怎么样？
Agent: [调用web_search] 根据网络评测...
```

---

## 🛣️ 技术演进

### V1.0（2026-04）
- ✅ 基础Agent框架
- ✅ Neo4j知识图谱构建
- ✅ 7个参数化查询工具

### V2.0（2026-05）
- ✅ 四维贪心采样算法
- ✅ 异步架构改造
- ✅ 34条自动化测试
- ✅ DeepSeek Thinking Mode适配
- ✅ PostgreSQL会话持久化

### V3.0（2026-05）
- ✅ FastAPI + SSE Web服务
- ✅ 引擎室风格前端界面
- ✅ 性能基准测试

### 未来规划
- ⏳ 用户画像与个性化推荐
- ⏳ 车型图片识别
- ⏳ 多轮对话上下文优化
- ⏳ 分布式部署与横向扩展

---

## 📝 License

MIT License

---

## 👨‍💻 作者

**lyl** - AI Agent开发者 / 算法研究者

如有问题或建议，欢迎提Issue或PR！

---

## 🙏 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent编排框架
- [Neo4j](https://neo4j.com/) - 图数据库
- [DeepSeek](https://www.deepseek.com/) - 大语言模型
- [Tavily](https://tavily.com/) - 搜索引擎API
