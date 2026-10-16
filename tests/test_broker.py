import os
import unittest
from unittest.mock import Mock, patch
from broker_kis import KIS, BrokerError


class BalanceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'KIS_APP_KEY':'test-key', 'KIS_APP_SECRET':'test-secret', 'KIS_CANO':'12345678', 'KIS_ACNT_PRDT_CD':'01', 'KIS_ENV':'demo'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def row(self, code, qty, value):
        return {'pdno':code, 'prdt_name':'fixture', 'hldg_qty':str(qty), 'pchs_avg_pric':'100', 'prpr':'120', 'evlu_amt':str(value), 'evlu_pfls_amt':'20'}

    def response(self, rows, continuation='', nk=''):
        return Mock(headers={'tr_cont':continuation}), {'rt_cd':'0', 'output1':rows, 'output2':[{'dnca_tot_amt':'1000'}], 'ctx_area_fk100':'f', 'ctx_area_nk100':nk}

    def test_complete_pages_and_zero_positions(self):
        client = KIS(key='test-key', secret='test-secret', cano='12345678', product='01')
        with patch.object(client, 'authorize'), patch.object(client, 'request', side_effect=[self.response([self.row('005930',1,100)],'M','next'),self.response([self.row('000660',2,300),self.row('035420',0,0)])]) as request, patch('broker_kis.time.sleep'):
            client.token='test-token'
            snapshot=client.balance()
        self.assertEqual(len(snapshot['positions']),2)
        self.assertEqual(snapshot['positions'][1]['weight'],75)
        self.assertEqual(snapshot['value'],400)
        self.assertEqual(request.call_args.kwargs['headers']['tr_cont'],'N')
        self.assertEqual(request.call_args.kwargs['headers']['tr_id'],'VTTC8434R')

    def test_incomplete_page_is_not_success(self):
        client=KIS(key='test-key', secret='test-secret', cano='12345678', product='01');client.token='test-token'
        with patch.object(client,'authorize'),patch.object(client,'request',return_value=self.response([self.row('005930',1,100)],'M','')):
            with self.assertRaises(BrokerError):client.balance()

    def test_broker_error_does_not_echo_response(self):
        client=KIS(key='test-key', secret='test-secret', cano='12345678', product='01');client.token='test-token'
        with patch.object(client,'authorize'),patch.object(client,'request',return_value=(Mock(),{'rt_cd':'1','msg1':'test-secret 12345678'})):
            with self.assertRaises(BrokerError) as error:client.balance()
        self.assertNotIn('test-secret',str(error.exception))
        self.assertNotIn('12345678',str(error.exception))

    def test_empty_account(self):
        client=KIS(key='test-key', secret='test-secret', cano='12345678', product='01');client.token='test-token'
        with patch.object(client,'authorize'),patch.object(client,'request',return_value=self.response([])):
            result=client.balance()
        self.assertEqual(result['positions'],[])
        self.assertEqual(result['value'],0)


    def test_explicit_clients_are_isolated_from_environment(self):
        first = KIS(key='first', secret='first-secret', cano='11111111', product='01')
        second = KIS(key='second', secret='second-secret', cano='22222222', product='01')
        first.token = 'first-token'
        self.assertEqual(second.cano, '22222222')
        self.assertEqual(second.key, 'second')
        self.assertIsNone(second.token)
        self.assertEqual(os.environ['KIS_APP_KEY'], 'test-key')

    def test_missing_credentials_cannot_fall_back_to_environment(self):
        with self.assertRaises(BrokerError):
            KIS(key='', secret='', cano='', product='')
