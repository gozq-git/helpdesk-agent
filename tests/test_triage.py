import unittest

from helpdesk_agent.triage import TriageParser


class TestTriageParser(unittest.TestCase):
    def test_email_parses_access_issue(self) -> None:
        parser = TriageParser()
        payload = parser.parse("Hi, my password reset request is urgent.", "email", sender="alice@example.com")
        self.assertEqual(payload["source"], "email")
        self.assertEqual(payload["service"], "identity")
        self.assertEqual(payload["issue_type"], "access")
        self.assertEqual(payload["priority"], "high")

    def test_slack_parses_incident(self) -> None:
        parser = TriageParser()
        payload = parser.parse("Production outage on the platform, please help.", "slack", sender="ops")
        self.assertEqual(payload["service"], "platform")
        self.assertEqual(payload["issue_type"], "incident")
        self.assertEqual(payload["priority"], "critical")


if __name__ == "__main__":
    unittest.main()
