import unittest
from unittest.mock import MagicMock, patch
import json
from flask import Flask
from control.app.routes.session_routes import session_bp

class TestSessionStrategy(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(session_bp)
        self.client = self.app.test_client()

    @patch('control.app.routes.session_routes.get_db_connection')
    def test_change_session_strategy(self, mock_get_db_conn):
        # Mock DB connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock Session Existence Check
        # First query: SELECT id FROM session...
        mock_cursor.fetchone.side_effect = [
            {'id': 1},  # Session exists
            None # For subsequent fetches if any
        ]

        # Call the endpoint
        response = self.client.post('/sessions/1/change_strategy', json={
            'strategy_id': 'strategy_123'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("Strategy changed and session restarted!", response.json['success'])

        # Verify DB calls
        # 1. Check session exists
        mock_cursor.execute.assert_any_call("SELECT id FROM session WHERE id = %s", (1,))

        # 2. Delete old strategies
        mock_cursor.execute.assert_any_call("DELETE FROM session_strategies WHERE session_id = %s", (1,))

        # 3. Insert new strategy
        mock_cursor.execute.assert_any_call("INSERT INTO session_strategies (session_id, strategy_id) VALUES (%s, %s)", (1, 'strategy_123'))

        # 4. Clear verified answers
        mock_cursor.execute.assert_any_call("DELETE FROM verified_answers WHERE session_id = %s", (1,))

        # 5. Reset session
        # We can't easily check the exact SQL string for UPDATE due to multiline, but we can check if it was called.
        # Let's inspect call args list
        update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE session" in call[0][0]]
        self.assertTrue(len(update_calls) > 0)

        # Check commit
        mock_conn.commit.assert_called()

    @patch('control.app.routes.session_routes.get_db_connection')
    def test_change_session_strategy_no_session(self, mock_get_db_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None # Session not found

        response = self.client.post('/sessions/999/change_strategy', json={
            'strategy_id': 'strategy_123'
        })

        self.assertEqual(response.status_code, 404)
        self.assertIn("Session not found", response.json['error'])

if __name__ == '__main__':
    unittest.main()
