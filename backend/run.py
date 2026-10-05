"""豫宿巡后端启动入口。

用法：
    python run.py            # 默认 0.0.0.0:8000
    python run.py 9000       # 指定端口

启动后：
    Swagger 文档  http://localhost:8000/docs
    健康检查      http://localhost:8000/api/health
"""
import os
import sys

import uvicorn

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            port = 8000

    # 关闭 ChromaDB 匿名遥测，保证离线环境干净启动
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_TELEMETRY_ENABLED", "False")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
