import unittest
from unittest.mock import patch
import publisher as base
import publisher_facebook as adapter

class FacebookLoginTests(unittest.TestCase):
    def test_same_expected_instagram_account_and_quota_are_verified(self):
        me = {'id': adapter.INSTAGRAM_ID, 'username': adapter.EXPECTED_USERNAME}
        with patch.object(adapter, 'facebook_request', side_effect=[me, {}]) as request:
            client = adapter.FacebookInstagram('fake-token', 'v25.0')
            client.verify(adapter.EXPECTED_USERNAME)
            self.assertEqual(client.user, adapter.INSTAGRAM_ID)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args_list[0].args[0], '/v25.0/' + adapter.INSTAGRAM_ID)
            self.assertEqual(request.call_args_list[1].args[0], '/v25.0/' + adapter.INSTAGRAM_ID + '/content_publishing_limit')
    def test_wrong_username_stops_before_quota_or_publication(self):
        with patch.object(adapter, 'facebook_request', return_value={'id': adapter.INSTAGRAM_ID, 'username': 'different_account'}) as request:
            with self.assertRaises(base.SafetyError):
                adapter.FacebookInstagram('fake-token', 'v25.0').verify(adapter.EXPECTED_USERNAME)
            self.assertEqual(request.call_count, 1)
    def test_wrong_node_id_stops(self):
        with patch.object(adapter, 'facebook_request', return_value={'id': '123', 'username': adapter.EXPECTED_USERNAME}):
            with self.assertRaises(base.SafetyError):
                adapter.FacebookInstagram('fake-token', 'v25.0').verify(adapter.EXPECTED_USERNAME)
    def test_unapproved_account_configuration_makes_no_request(self):
        with patch.object(adapter, 'facebook_request') as request:
            with self.assertRaises(base.SafetyError):
                adapter.FacebookInstagram('fake-token', 'v25.0').verify('another_account')
            request.assert_not_called()

if __name__ == '__main__':
    unittest.main()
