import unittest

from helpdesk_agent.workflow import HelpdeskWorkflow


class TestHelpdeskWorkflow(unittest.TestCase):
    def test_run_completes_without_approval(self) -> None:
        workflow = HelpdeskWorkflow()
        state = workflow.run({"case_id": "case-001", "summary": "Password reset", "service": "identity"})

        self.assertEqual(state.case_id, "case-001")
        self.assertEqual(state.current_step, "closed")
        self.assertEqual(state.history[-1]["step"], "close")

    def test_run_stays_in_approval_when_required(self) -> None:
        workflow = HelpdeskWorkflow()
        state = workflow.run(
            {
                "case_id": "case-002",
                "summary": "Production config change",
                "service": "platform",
                "metadata": {"requires_approval": True},
            }
        )

        self.assertEqual(state.current_step, "approval")
        self.assertTrue(any(entry["status"] == "pending_approval" for entry in state.history))


if __name__ == "__main__":
    unittest.main()
