#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GraphQL Schema定义。

使用Graphene库实现GraphQL接口，提供灵活的数据查询能力。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 检查graphene是否可用
try:
    import graphene
    from graphene import ObjectType, String, Int, Float, Boolean, List, Field, Schema
    GRAPHENE_AVAILABLE = True
except ImportError:
    GRAPHENE_AVAILABLE = False
    logger.warning("Graphene not installed. GraphQL API will not be available.")

if GRAPHENE_AVAILABLE:
    # ==================== 类型定义 ====================

    class WaterQualityType(ObjectType):
        """水质数据类型。"""
        turbidity = Float(description="浊度 (NTU)")
        dissolved_oxygen = Float(description="溶解氧 (mg/L)")
        ph = Float(description="pH值")
        temperature = Float(description="温度 (°C)")
        timestamp = String(description="时间戳")

    class ControlStatusType(ObjectType):
        """控制状态类型。"""
        pump_status = String(description="泵状态")
        valve_position = Int(description="阀门位置 (%)")
        coagulant_dose = Float(description="混凝剂投加量")
        aeration_rate = Float(description="曝气速率")
        controller_type = String(description="控制器类型")

    class SimulationResultType(ObjectType):
        """仿真结果类型。"""
        step = Int(description="步数")
        timestamp = String(description="时间戳")
        turbidity = Float(description="浊度")
        dissolved_oxygen = Float(description="溶解氧")
        ph = Float(description="pH值")
        coagulant_dose = Float(description="混凝剂投加量")
        aeration_rate = Float(description="曝气速率")

    class SimulationType(ObjectType):
        """仿真类型。"""
        simulation_id = String(description="仿真ID")
        status = String(description="状态")
        current_step = Int(description="当前步数")
        total_steps = Int(description="总步数")
        progress = Float(description="进度 (%)")
        start_time = String(description="开始时间")
        end_time = String(description="结束时间")
        results = List(SimulationResultType, description="仿真结果")

    class SessionType(ObjectType):
        """会话类型。"""
        session_id = String(description="会话ID")
        user_id = String(description="用户ID")
        created_at = String(description="创建时间")
        last_active = String(description="最后活动时间")
        total_tool_calls = Int(description="工具调用总数")
        simulations = List(SimulationType, description="仿真列表")

    class ToolType(ObjectType):
        """工具类型。"""
        name = String(description="工具名称")
        description = String(description="工具描述")
        category = String(description="工具分类")
        version = String(description="版本号")
        call_count = Int(description="调用次数")
        success_count = Int(description="成功次数")
        error_count = Int(description="错误次数")
        avg_execution_time = Float(description="平均执行时间")

    class PerformanceMetricsType(ObjectType):
        """性能指标类型。"""
        IAE = Float(description="积分绝对误差")
        ISE = Float(description="积分平方误差")
        settling_time = Float(description="调节时间")
        overshoot = Float(description="超调量 (%)")
        rise_time = Float(description="上升时间")
        steady_state_error = Float(description="稳态误差")

    # ==================== 查询 ====================

    class Query(ObjectType):
        """GraphQL查询根。"""

        # 会话查询
        session = Field(
            SessionType,
            session_id=String(required=True),
            description="获取会话信息"
        )

        sessions = List(
            SessionType,
            user_id=String(),
            description="列出所有会话"
        )

        # 仿真查询
        simulation = Field(
            SimulationType,
            session_id=String(required=True),
            simulation_id=String(required=True),
            description="获取仿真信息"
        )

        simulations = List(
            SimulationType,
            session_id=String(required=True),
            status=String(),
            description="列出会话的所有仿真"
        )

        # 工具查询
        tool = Field(
            ToolType,
            name=String(required=True),
            description="获取工具信息"
        )

        tools = List(
            ToolType,
            category=String(),
            description="列出所有工具"
        )

        # 水质数据查询
        water_quality = Field(
            WaterQualityType,
            session_id=String(required=True),
            simulation_id=String(required=True),
            description="获取当前水质数据"
        )

        # 控制状态查询
        control_status = Field(
            ControlStatusType,
            session_id=String(required=True),
            simulation_id=String(required=True),
            description="获取控制状态"
        )

        # Resolver实现
        def resolve_session(self, info, session_id):
            """解析会话查询。"""
            from ..session import get_session_manager

            session_manager = get_session_manager()
            session = session_manager.get_session(session_id)

            if not session:
                return None

            return SessionType(
                session_id=session.session_id,
                user_id=session.user_id,
                created_at=session.created_at.isoformat(),
                last_active=session.last_active.isoformat(),
                total_tool_calls=session.total_tool_calls,
                simulations=[
                    SimulationType(
                        simulation_id=sim_id,
                        status=sim.status,
                        current_step=sim.current_step,
                        total_steps=sim.total_steps,
                        start_time=sim.start_time.isoformat() if sim.start_time else None,
                        end_time=sim.end_time.isoformat() if sim.end_time else None,
                        progress=(sim.current_step / sim.total_steps * 100) if sim.total_steps > 0 else 0
                    )
                    for sim_id, sim in session.simulations.items()
                ]
            )

        def resolve_sessions(self, info, user_id=None):
            """解析会话列表查询。"""
            from ..session import get_session_manager

            session_manager = get_session_manager()
            sessions_info = session_manager.list_sessions(user_id)

            return [
                SessionType(
                    session_id=s.session_id,
                    user_id=s.user_id,
                    created_at=s.created_at.isoformat(),
                    last_active=s.last_active.isoformat()
                )
                for s in sessions_info
            ]

        def resolve_simulation(self, info, session_id, simulation_id):
            """解析仿真查询。"""
            from ..session import get_session_manager

            session_manager = get_session_manager()
            session = session_manager.get_session(session_id)

            if not session:
                return None

            simulation = session.simulations.get(simulation_id)
            if not simulation:
                return None

            return SimulationType(
                simulation_id=simulation_id,
                status=simulation.status,
                current_step=simulation.current_step,
                total_steps=simulation.total_steps,
                progress=(simulation.current_step / simulation.total_steps * 100) if simulation.total_steps > 0 else 0,
                start_time=simulation.start_time.isoformat() if simulation.start_time else None,
                end_time=simulation.end_time.isoformat() if simulation.end_time else None,
                results=[
                    SimulationResultType(**result)
                    for result in simulation.results[:100]  # 限制返回数量
                ]
            )

        def resolve_tool(self, info, name):
            """解析工具查询。"""
            from ..registry import get_registry

            registry = get_registry()
            tool = registry.get_tool(name)

            if not tool:
                return None

            stats = registry.get_stats(name)

            return ToolType(
                name=tool.name,
                description=tool.description,
                category=tool.category,
                version=tool.version,
                call_count=stats.get('call_count', 0),
                success_count=stats.get('success_count', 0),
                error_count=stats.get('error_count', 0),
                avg_execution_time=stats.get('avg_execution_time', 0.0)
            )

        def resolve_tools(self, info, category=None):
            """解析工具列表查询。"""
            from ..registry import get_registry

            registry = get_registry()
            tools = registry.list_tools(category)

            return [
                ToolType(
                    name=tool.name,
                    description=tool.description,
                    category=tool.category,
                    version=tool.version,
                    call_count=registry.get_stats(tool.name).get('call_count', 0),
                    success_count=registry.get_stats(tool.name).get('success_count', 0),
                    error_count=registry.get_stats(tool.name).get('error_count', 0),
                    avg_execution_time=registry.get_stats(tool.name).get('avg_execution_time', 0.0)
                )
                for tool in tools
            ]

    # ==================== 变更 ====================

    class StartSimulation(graphene.Mutation):
        """启动仿真变更。"""
        class Arguments:
            session_id = String(required=True)
            steps = Int(default_value=100)
            turbidity_setpoint = Float(default_value=2.0)
            do_setpoint = Float(default_value=8.0)
            controller_type = String(default_value="pid")

        simulation_id = String()
        status = String()
        message = String()

        async def mutate(self, info, session_id, steps, turbidity_setpoint, do_setpoint, controller_type):
            """执行启动仿真变更。"""
            from ..tools.simulation_tools import start_simulation_handler

            try:
                result = await start_simulation_handler(
                    {
                        "steps": steps,
                        "turbidity_setpoint": turbidity_setpoint,
                        "do_setpoint": do_setpoint,
                        "controller_type": controller_type
                    },
                    session_id=session_id
                )

                return StartSimulation(
                    simulation_id=result.get("simulation_id"),
                    status=result.get("status"),
                    message=result.get("message")
                )
            except Exception as e:
                return StartSimulation(
                    simulation_id=None,
                    status="error",
                    message=str(e)
                )

    class Mutation(ObjectType):
        """GraphQL变更根。"""
        start_simulation = StartSimulation.Field()

    # 创建Schema
    schema = Schema(query=Query, mutation=Mutation)

    def create_graphql_app():
        """创建GraphQL应用。"""
        try:
            from aiohttp import web
            from graphql.execution.executors.asyncio import AsyncioExecutor

            async def graphql_handler(request):
                """GraphQL请求处理器。"""
                try:
                    data = await request.json()
                    result = await schema.execute_async(
                        data.get('query'),
                        variable_values=data.get('variables'),
                        operation_name=data.get('operationName'),
                        executor=AsyncioExecutor()
                    )

                    response_data = {}
                    if result.data:
                        response_data['data'] = result.data
                    if result.errors:
                        response_data['errors'] = [str(e) for e in result.errors]

                    return web.json_response(response_data)

                except Exception as e:
                    logger.error(f"GraphQL error: {e}", exc_info=True)
                    return web.json_response(
                        {"errors": [str(e)]},
                        status=500
                    )

            async def graphiql_handler(request):
                """GraphiQL IDE处理器。"""
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>GraphiQL</title>
                    <link href="https://unpkg.com/graphiql/graphiql.min.css" rel="stylesheet" />
                </head>
                <body style="margin: 0;">
                    <div id="graphiql" style="height: 100vh;"></div>
                    <script crossorigin src="https://unpkg.com/react/umd/react.production.min.js"></script>
                    <script crossorigin src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"></script>
                    <script crossorigin src="https://unpkg.com/graphiql/graphiql.min.js"></script>
                    <script>
                        const fetcher = GraphiQL.createFetcher({ url: '/graphql' });
                        ReactDOM.render(
                            React.createElement(GraphiQL, { fetcher: fetcher }),
                            document.getElementById('graphiql'),
                        );
                    </script>
                </body>
                </html>
                """
                return web.Response(text=html, content_type='text/html')

            return graphql_handler, graphiql_handler

        except ImportError:
            logger.error("aiohttp is required for GraphQL app")
            return None, None

else:
    # Graphene不可用时的占位符
    schema = None

    def create_graphql_app():
        """创建GraphQL应用（Graphene不可用）。"""
        logger.error("Graphene is not installed. Install with: pip install graphene")
        return None, None
