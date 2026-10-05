"""豫宿巡后端服务层。

模块划分：
- store   数据读写（mock_data.json 只读 + runtime.json 读写 + 内存缓存 + 趋势生成）
- rules   贷后风控规则引擎（R001-R004）
- rag     RAG 检索（ChromaDB 可选 + 纯 Python 兜底，多租户 collection 隔离）
- llm     大模型接入（OpenAI 兼容；无 Key 时离线兜底）
- report  AI 巡检报告生成
- creative AI 文创生图 + 图片矢量化
"""
