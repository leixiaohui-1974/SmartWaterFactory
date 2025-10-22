#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP服务启动脚本。

快速启动Smart Water Factory MCP服务的便捷脚本。
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_service.server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMCP Service stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting MCP Service: {e}", file=sys.stderr)
        sys.exit(1)
