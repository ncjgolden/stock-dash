import copy
import json
import unittest
from pathlib import Path

import pandas as pd

from chat_research import parse_bundle, validate, growth, trends, request_text


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.bundle=json.loads((Path(__file__).parents[1]/'research/initial-examples.json').read_text())

    def test_initial_reports_have_real_source_financials(self):
        result=parse_bundle(json.dumps(self.bundle))
        self.assertEqual(len(result),2)
        self.assertEqual(growth(120,100),'+20.0%')
        self.assertEqual(growth(5,-10),'흑자 전환')

    def test_mismatched_cumulative_period_rejected(self):
        r=copy.deepcopy(self.bundle['reports'][0]);r['financial']['prior_period']='2024-06'
        with self.assertRaises(ValueError):validate(r)

    def test_peer_currency_mismatch_rejected(self):
        r=copy.deepcopy(self.bundle['reports'][0]);r['peers']['rows'][0]['currency']='USD'
        with self.assertRaises(ValueError):validate(r)

    def test_request_excludes_private_positions(self):
        text=request_text([{'name':'삼성전자','code':'005930','quantity':982734,'account':'private-account'}])
        self.assertNotIn('982734',text);self.assertNotIn('private-account',text)

    def test_daily_and_completed_weekly(self):
        dates=pd.bdate_range('2025-01-01', periods=160)
        prices={'adjusted': True, 'rows':[{'date':str(d.date()),'close':i+100} for i,d in enumerate(dates)]}
        t,_=trends(prices,'2025-09-01')
        self.assertEqual(t['daily'],'상승 정렬');self.assertEqual(t['weekly'],'상승 정렬')
        t,_=trends({'adjusted': True, 'rows':prices['rows'][:30]},'2025-09-01')
        self.assertEqual(t['daily'],'기간 부족')
