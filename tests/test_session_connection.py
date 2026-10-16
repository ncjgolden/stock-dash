import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

SOURCE = """
from portfolio_ui import render_portfolio
render_portfolio(None, False)
"""

class ConnectionTests(unittest.TestCase):
    def test_invalid_input_and_disconnect_clear_session(self):
        app = AppTest.from_string(SOURCE).run()
        self.assertFalse(app.exception)
        app.button[0].click().run()
        self.assertTrue(app.error)
        self.assertNotIn('kis_client', app.session_state)
        with patch('broker_kis.KIS.balance', return_value={'positions':[], 'value':0, 'pnl':0, 'cash':0, 'mode':'demo', 'fetched':'test'}):
            for widget, value in zip(app.text_input, ['fixture-key','fixture-secret','12345678','01']):
                widget.set_value(value)
            app.button[0].click().run()
        self.assertFalse(app.exception)
        state = app.session_state
        self.assertIn('kis_client', state)
        self.assertNotIn('kis_input_secret', state)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        state = app.session_state
        for key in ['kis_client','account_snapshot','account_results']:
            self.assertNotIn(key,state)
        self.assertEqual(len(app.text_input),4)

if __name__ == '__main__': unittest.main()
