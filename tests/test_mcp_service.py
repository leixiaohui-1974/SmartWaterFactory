#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP服务测试用例。"""

import unittest
import asyncio
import json
from datetime import datetime

# 测试前需要先注册工具
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_service.models.schemas import (
    Tool, ToolParameter, ToolParameterType,
    MCPRequest, MCPResponse
)
from mcp_service.registry import get_registry
from mcp_service.session import get_session_manager
from mcp_service.protocol import MCPProtocolHandler
from mcp_service.tools import register_all_tools


class TestMCPModels(unittest.TestCase):
    """测试MCP数据模型。"""

    def test_tool_parameter(self):
        """测试工具参数。"""
        param = ToolParameter(
            name="test_param",
            type=ToolParameterType.STRING,
            description="Test parameter",
            required=True
        )
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.type, ToolParameterType.STRING)
        self.assertTrue(param.required)

    def test_mcp_request(self):
        """测试MCP请求。"""
        request = MCPRequest(
            id="test-1",
            method="test_method",
            params={"key": "value"}
        )
        self.assertEqual(request.jsonrpc, "2.0")
        self.assertEqual(request.method, "test_method")

    def test_mcp_response(self):
        """测试MCP响应。"""
        response = MCPResponse(
            id="test-1",
            result={"status": "success"}
        )
        response_dict = response.to_dict()
        self.assertEqual(response_dict["jsonrpc"], "2.0")
        self.assertIn("result", response_dict)


class TestToolRegistry(unittest.TestCase):
    """测试工具注册表。"""

    def setUp(self):
        """设置测试环境。"""
        self.registry = get_registry()

        # 清空注册表
        for tool_name in list(self.registry._tools.keys()):
            self.registry.unregister(tool_name)

    def test_register_tool(self):
        """测试注册工具。"""
        def test_handler(args, session_id=None):
            return {"result": "test"}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            parameters=[],
            handler=test_handler
        )

        self.registry.register(tool)
        self.assertIsNotNone(self.registry.get_tool("test_tool"))

    def test_list_tools(self):
        """测试列出工具。"""
        def handler1(args, session_id=None):
            return {}

        def handler2(args, session_id=None):
            return {}

        tool1 = Tool(name="tool1", description="Tool 1", parameters=[], handler=handler1, category="cat1")
        tool2 = Tool(name="tool2", description="Tool 2", parameters=[], handler=handler2, category="cat2")

        self.registry.register(tool1)
        self.registry.register(tool2)

        all_tools = self.registry.list_tools()
        self.assertEqual(len(all_tools), 2)

        cat1_tools = self.registry.list_tools(category="cat1")
        self.assertEqual(len(cat1_tools), 1)


class TestSessionManager(unittest.TestCase):
    """测试会话管理器。"""

    def setUp(self):
        """设置测试环境。"""
        self.manager = get_session_manager()

        # 清空所有会话
        for session_id in list(self.manager._sessions.keys()):
            self.manager.delete_session(session_id)

    def test_create_session(self):
        """测试创建会话。"""
        session = self.manager.create_session(
            user_id="test_user",
            metadata={"test": "data"}
        )

        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, "test_user")
        self.assertEqual(session.metadata["test"], "data")

    def test_get_session(self):
        """测试获取会话。"""
        session = self.manager.create_session("test_user")
        retrieved = self.manager.get_session(session.session_id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.session_id, session.session_id)

    def test_delete_session(self):
        """测试删除会话。"""
        session = self.manager.create_session("test_user")
        session_id = session.session_id

        success = self.manager.delete_session(session_id)
        self.assertTrue(success)

        retrieved = self.manager.get_session(session_id)
        self.assertIsNone(retrieved)


class TestMCPProtocolHandler(unittest.IsolatedAsyncioTestCase):
    """测试MCP协议处理器。"""

    async def asyncSetUp(self):
        """异步设置测试环境。"""
        # 注册工具
        register_all_tools()

        self.handler = MCPProtocolHandler()
        self.manager = get_session_manager()

        # 创建测试会话
        self.session = self.manager.create_session("test_user")
        self.session_id = self.session.session_id

    async def asyncTearDown(self):
        """异步清理测试环境。"""
        # 删除测试会话
        self.manager.delete_session(self.session_id)

    async def test_initialize(self):
        """测试初始化请求。"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test_client"}
            }
        }

        response = await self.handler.handle_request(request_data, self.session_id)

        self.assertIsNotNone(response.result)
        self.assertIn("serverInfo", response.result)

    async def test_tools_list(self):
        """测试工具列表请求。"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/list",
            "params": {}
        }

        response = await self.handler.handle_request(request_data, self.session_id)

        self.assertIsNotNone(response.result)
        self.assertIn("tools", response.result)
        self.assertGreater(len(response.result["tools"]), 0)

    async def test_resources_list(self):
        """测试资源列表请求。"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "resources/list",
            "params": {}
        }

        response = await self.handler.handle_request(request_data, self.session_id)

        self.assertIsNotNone(response.result)
        self.assertIn("resources", response.result)


class TestMCPIntegration(unittest.IsolatedAsyncioTestCase):
    """MCP服务集成测试。"""

    async def asyncSetUp(self):
        """异步设置测试环境。"""
        # 注册所有工具
        register_all_tools()

        self.handler = MCPProtocolHandler()
        self.manager = get_session_manager()

        # 创建测试会话
        self.session = self.manager.create_session("integration_test_user")
        self.session_id = self.session.session_id

    async def asyncTearDown(self):
        """异步清理测试环境。"""
        self.manager.delete_session(self.session_id)

    async def test_complete_workflow(self):
        """测试完整的工作流程。"""
        # 1. 初始化
        init_request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }
        init_response = await self.handler.handle_request(init_request, self.session_id)
        self.assertIsNotNone(init_response.result)

        # 2. 列出工具
        tools_request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/list",
            "params": {}
        }
        tools_response = await self.handler.handle_request(tools_request, self.session_id)
        self.assertIn("tools", tools_response.result)

        # 3. 启动仿真（示例）
        # 注意：这会启动一个真实的仿真，可能需要较长时间
        # sim_request = {
        #     "jsonrpc": "2.0",
        #     "id": "3",
        #     "method": "tools/call",
        #     "params": {
        #         "name": "start_simulation",
        #         "arguments": {
        #             "steps": 10,
        #             "turbidity_setpoint": 2.0,
        #             "do_setpoint": 8.0
        #         }
        #     }
        #     }
        # sim_response = await self.handler.handle_request(sim_request, self.session_id)
        # self.assertFalse(sim_response.result.get("isError", True))


def run_tests():
    """运行所有测试。"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMCPModels))
    suite.addTests(loader.loadTestsFromTestCase(TestToolRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPProtocolHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
