import unittest

from fastapi.testclient import TestClient

from helpdesk_agent.main import create_app


class TestMainApp(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_hello_world(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "helpdesk agent is running"})

    def test_healthz(self) -> None:
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})
