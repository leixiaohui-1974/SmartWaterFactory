import unittest

from mcp_service.registry import get_registry
from mcp_service.session import get_session_manager
from mcp_service.tools.simulation_tools import (
    clear_hil_fault_handler,
    get_hil_simulation_status_handler,
    register_simulation_tools,
    set_hil_control_handler,
    set_hil_scenario_handler,
    start_hil_simulation_handler,
    step_hil_simulation_handler,
    inject_hil_fault_handler,
)


class TestHILMCPTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry = get_registry()
        self.registry.clear()
        register_simulation_tools()

        self.session_manager = get_session_manager()
        self.session = self.session_manager.create_session("hil_test_user")
        self.session_id = self.session.session_id

    async def asyncTearDown(self):
        self.session_manager.delete_session(self.session_id)

    async def test_hil_tool_registration(self):
        tool_names = {tool.name for tool in self.registry.list_tools(category="simulation")}
        self.assertIn("start_hil_simulation", tool_names)
        self.assertIn("step_hil_simulation", tool_names)
        self.assertIn("get_hil_simulation_status", tool_names)

    async def test_hil_workflow_handlers(self):
        started = await start_hil_simulation_handler({"scenario": "steady", "random_seed": 5}, session_id=self.session_id)
        simulation_id = started["simulation_id"]

        await set_hil_control_handler(
            {
                "simulation_id": simulation_id,
                "coagulant_dose": 6.0,
                "aeration_rate_ma": 12.0,
            },
            session_id=self.session_id,
        )

        stepped = await step_hil_simulation_handler(
            {"simulation_id": simulation_id, "steps": 2},
            session_id=self.session_id,
        )
        self.assertEqual(stepped["steps_executed"], 2)
        self.assertEqual(stepped["current_step"], 2)
        self.assertIn("latest_snapshot", stepped)

        status = await get_hil_simulation_status_handler(
            {"simulation_id": simulation_id},
            session_id=self.session_id,
        )
        self.assertEqual(status["scenario"], "steady")
        self.assertEqual(status["results_count"], 2)

        await set_hil_scenario_handler(
            {"simulation_id": simulation_id, "scenario_name": "turbidity_spike"},
            session_id=self.session_id,
        )
        changed = await get_hil_simulation_status_handler(
            {"simulation_id": simulation_id},
            session_id=self.session_id,
        )
        self.assertEqual(changed["scenario"], "turbidity_spike")

    async def test_hil_fault_injection_handlers(self):
        started = await start_hil_simulation_handler({"random_seed": 9}, session_id=self.session_id)
        simulation_id = started["simulation_id"]

        await inject_hil_fault_handler(
            {
                "simulation_id": simulation_id,
                "sensor_name": "turbidity",
                "mode": "stuck",
                "value": 42.0,
            },
            session_id=self.session_id,
        )
        stepped = await step_hil_simulation_handler(
            {"simulation_id": simulation_id},
            session_id=self.session_id,
        )
        self.assertEqual(stepped["latest_snapshot"]["measured_quality"]["turbidity"], 42.0)

        await clear_hil_fault_handler(
            {
                "simulation_id": simulation_id,
                "sensor_name": "turbidity",
            },
            session_id=self.session_id,
        )
        recovered = await step_hil_simulation_handler(
            {"simulation_id": simulation_id},
            session_id=self.session_id,
        )
        self.assertNotEqual(recovered["latest_snapshot"]["measured_quality"]["turbidity"], 42.0)
