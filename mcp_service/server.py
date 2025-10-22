#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP服务器主入口。

启动和管理MCP服务，支持多种连接模式：
- stdio: 标准输入输出模式（用于Claude Desktop等）
- http: HTTP/SSE模式（用于Web客户端）
"""

import asyncio
import json
import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path

from .config import get_config, get_service_info
from .protocol import MCPProtocolHandler
from .registry import get_registry
from .session import get_session_manager
from .tools import register_all_tools

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP服务器。

    管理MCP服务的生命周期，包括：
    - 工具注册
    - 会话管理
    - 协议处理
    - 连接管理
    """

    def __init__(self):
        """初始化MCP服务器。"""
        self.config = get_config()
        self.service_info = get_service_info()
        self.protocol_handler = MCPProtocolHandler()
        self.session_manager = get_session_manager()
        self.tool_registry = get_registry()

        self._setup_logging()
        self._initialized = False

    def _setup_logging(self):
        """配置日志系统。"""
        log_level = getattr(logging, self.config.log_level.upper())
        logging.basicConfig(
            level=log_level,
            format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            handlers=[
                logging.FileHandler(self.config.log_file),
                logging.StreamHandler(sys.stderr)  # STDIO模式下输出到stderr
            ]
        )

    def initialize(self):
        """初始化服务器。"""
        if self._initialized:
            logger.warning("Server already initialized")
            return

        logger.info(f"Initializing {self.service_info.name} v{self.service_info.version}")

        # 注册所有工具
        register_all_tools()
        logger.info(f"Registered {len(self.tool_registry.list_tools())} tools")

        # 启动会话清理任务
        # 注意：在异步环境中启动
        logger.info("Session cleanup task will be started in async context")

        self._initialized = True
        logger.info("MCP Server initialized successfully")

    async def start_stdio_mode(self):
        """启动STDIO模式。

        此模式通过标准输入输出与客户端通信，适用于：
        - Claude Desktop
        - CLI工具
        - 进程间通信
        """
        logger.info("Starting MCP Server in STDIO mode")

        # 启动会话清理任务
        await self.session_manager.start_cleanup_task()

        # 创建默认会话（STDIO模式通常是单会话）
        default_session = self.session_manager.create_session(
            user_id="stdio_user",
            metadata={"mode": "stdio"}
        )
        session_id = default_session.session_id

        logger.info(f"Created default session: {session_id}")

        # 从stdin读取JSON-RPC请求
        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    logger.info("STDIN closed, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # 解析请求
                    request_data = json.loads(line)

                    # 处理请求
                    response = await self.protocol_handler.handle_request(
                        request_data,
                        session_id=session_id
                    )

                    # 发送响应到stdout
                    response_json = json.dumps(response.to_dict(), ensure_ascii=False)
                    print(response_json, flush=True)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)

                except Exception as e:
                    logger.error(f"Error processing request: {e}", exc_info=True)
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.session_manager.stop_cleanup_task()
            logger.info("MCP Server stopped")

    async def start_http_mode(self):
        """启动HTTP模式。

        此模式提供HTTP/SSE接口，适用于：
        - Web应用
        - REST API客户端
        - 浏览器
        """
        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp is required for HTTP mode. Install with: pip install aiohttp")
            raise

        logger.info(f"Starting MCP Server in HTTP mode on {self.config.host}:{self.config.port}")

        # 启动会话清理任务
        await self.session_manager.start_cleanup_task()

        app = web.Application()

        # 健康检查端点
        async def health_check(request):
            return web.json_response({
                "status": "healthy",
                "service": self.service_info.name,
                "version": self.service_info.version
            })

        # Prometheus指标端点
        async def metrics_endpoint(request):
            """Prometheus指标导出端点。"""
            try:
                from .monitoring import get_metrics, record_session_metrics

                # 更新会话指标
                stats = self.session_manager.get_stats()
                record_session_metrics(
                    stats.get("total_sessions", 0),
                    stats.get("total_simulations", 0)
                )

                # 导出指标
                metrics = get_metrics()
                prometheus_text = metrics.export_prometheus_format()

                return web.Response(
                    text=prometheus_text,
                    content_type="text/plain; version=0.0.4"
                )
            except ImportError:
                return web.json_response(
                    {"error": "Monitoring not available"},
                    status=503
                )

        # MCP端点
        async def mcp_endpoint(request):
            try:
                # 获取或创建会话
                session_id = request.headers.get("X-Session-ID")
                if not session_id:
                    # 创建新会话
                    user_id = request.headers.get("X-User-ID", "anonymous")
                    session = self.session_manager.create_session(
                        user_id=user_id,
                        metadata={"mode": "http"}
                    )
                    session_id = session.session_id

                # 解析请求
                request_data = await request.json()

                # 处理请求
                response = await self.protocol_handler.handle_request(
                    request_data,
                    session_id=session_id
                )

                # 返回响应（添加会话ID到响应头）
                return web.json_response(
                    response.to_dict(),
                    headers={"X-Session-ID": session_id}
                )

            except Exception as e:
                logger.error(f"Error in MCP endpoint: {e}", exc_info=True)
                return web.json_response(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    },
                    status=500
                )

        # 会话管理端点
        async def create_session_endpoint(request):
            try:
                data = await request.json()
                user_id = data.get("user_id", "anonymous")
                metadata = data.get("metadata", {})

                session = self.session_manager.create_session(user_id, metadata)

                return web.json_response({
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "created_at": session.created_at.isoformat()
                })

            except Exception as e:
                logger.error(f"Error creating session: {e}", exc_info=True)
                return web.json_response({"error": str(e)}, status=500)

        # 注册路由
        app.router.add_get("/health", health_check)
        app.router.add_get("/metrics", metrics_endpoint)
        app.router.add_post("/mcp", mcp_endpoint)
        app.router.add_post("/sessions", create_session_endpoint)

        # 启动服务器
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.config.host, self.config.port)
        await site.start()

        logger.info(f"MCP Server running at http://{self.config.host}:{self.config.port}")

        # 保持运行
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await runner.cleanup()
            self.session_manager.stop_cleanup_task()
            logger.info("MCP Server stopped")

    async def start(self, mode: str = "stdio"):
        """启动服务器。

        Args:
            mode: 运行模式，可选 'stdio' 或 'http'
        """
        self.initialize()

        if mode == "stdio":
            await self.start_stdio_mode()
        elif mode == "http":
            await self.start_http_mode()
        else:
            raise ValueError(f"Unknown mode: {mode}")


async def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="Smart Water Factory MCP Service")
    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        default="stdio",
        help="Server mode (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP server port (default: 8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    # 创建并启动服务器
    server = MCPServer()

    # 更新配置
    from .config import config_manager
    if args.mode == "http":
        config_manager.update_config(
            host=args.host,
            port=args.port,
            debug=args.debug
        )

    # 启动服务器
    await server.start(mode=args.mode)


if __name__ == "__main__":
    asyncio.run(main())
