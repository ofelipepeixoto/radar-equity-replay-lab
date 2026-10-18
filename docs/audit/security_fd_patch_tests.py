# Original regression tests, MIT License, Copyright (c) 2026 Carlos Felipe.
"""Focused regression tests for the candidate FD patch; mocks only."""
import json
import unittest
from unittest.mock import patch

import requests
from hedge_fund.data.client import FDClient, FDClientError


def response(body=None, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body or {}).encode()
    return result


class FDGuardTests(unittest.TestCase):
    def test_foreign_pagination_refused_before_second_request(self):
        with FDClient(api_key='synthetic-key') as client:
            with patch.object(client._session, 'request', return_value=response({'rows': [], 'next_page_url': 'https://foreign.invalid/page'})) as transport:
                with self.assertRaises(FDClientError):
                    client._get('/synthetic/', {}, 'rows')
                self.assertEqual(transport.call_count, 1)

    def test_same_origin_pagination_works(self):
        replies = [response({'rows': [1], 'next_page_url': 'https://api.financialdatasets.ai/page2'}), response({'rows': [2]})]
        with FDClient(api_key='synthetic-key') as client:
            with patch.object(client._session, 'request', side_effect=replies) as transport:
                self.assertEqual(client._get('/synthetic/', {}, 'rows'), [1, 2])
                self.assertEqual(transport.call_count, 2)
                self.assertTrue(all(c.kwargs['allow_redirects'] is False for c in transport.call_args_list))

    def test_redirect_refused(self):
        with FDClient(api_key='synthetic-key') as client:
            with patch.object(client._session, 'request', return_value=response(status=302)) as transport:
                with self.assertRaises(FDClientError):
                    client._request('GET', '/synthetic/')
                transport.assert_called_once()
                self.assertFalse(transport.call_args.kwargs['allow_redirects'])

    def test_pagination_cycle_refused(self):
        reply = response({'rows': [], 'next_page_url': 'https://api.financialdatasets.ai/repeat'})
        with FDClient(api_key='synthetic-key') as client:
            with patch.object(client._session, 'request', return_value=reply) as transport:
                with self.assertRaises(FDClientError):
                    client._get('/synthetic/', {}, 'rows')
                self.assertEqual(transport.call_count, 2)

    def test_page_limit_refused(self):
        replies = [response({'rows': [], 'next_page_url': 'https://api.financialdatasets.ai/page2'}), response({'rows': [], 'next_page_url': 'https://api.financialdatasets.ai/page3'})]
        with FDClient(api_key='synthetic-key') as client:
            client.MAX_PAGES = 2
            with patch.object(client._session, 'request', side_effect=replies) as transport:
                with self.assertRaises(FDClientError):
                    client._get('/synthetic/', {}, 'rows')
                self.assertEqual(transport.call_count, 2)

    def test_unsafe_urls_never_reach_transport(self):
        paths = ['http://api.financialdatasets.ai/page', '//foreign.invalid/page', 'https://api.financialdatasets.ai.evil.invalid/page', 'https://api.financialdatasets.ai:444/page', 'https://user:pass@api.financialdatasets.ai/page', 'https://api.financialdatasets.ai/page#fragment', 'https://api.financialdatasets.ai\\@foreign.invalid/page', 'https://api.financialdatasets.ai/page\nX-Test: yes']
        with FDClient(api_key='synthetic-key') as client:
            with patch.object(client._session, 'request') as transport:
                for path in paths:
                    with self.subTest(path=path), self.assertRaises(FDClientError):
                        client._request('GET', path)
                transport.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
