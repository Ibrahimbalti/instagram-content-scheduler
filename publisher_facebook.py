"""Compatibility adapter for the authorized Instagram account's Facebook Login token.
Retains publisher.py's campaign approvals, account guard, duplicate checks and ledger.
No Facebook feed posting, token printing, credential changes, or paid services.
"""
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request
import publisher as base

HOST = 'https://graph.facebook.com'
INSTAGRAM_ID = '17841430484113368'
EXPECTED_USERNAME = 'md_ibrahim07_official'


def facebook_request(path, token, method='GET', params=None, body=None):
    if not path.startswith('/v') or '\n' in path or '\r' in path:
        raise base.SafetyError('Unsafe Instagram API path.')
    url = HOST + path
    if params:
        url += '?' + urlencode(params)
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'User-Agent': 'Ibrahim-Instagram-Scheduler'}
    data = None
    if body is not None:
        data = urlencode(body).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    attempts = 3 if method == 'GET' else 1
    for attempt in range(attempts):
        try:
            with base.OPENER.open(Request(url, data=data, headers=headers, method=method), timeout=45) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            if method == 'GET' and exc.code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            code = None
            try:
                error = json.loads(exc.read(65536)).get('error', {})
                if isinstance(error.get('code'), int):
                    code = error['code']
            except (ValueError, TypeError, AttributeError):
                pass
            detail = ('; Meta code ' + str(code)) if code is not None else ''
            raise base.SafetyError('Instagram Facebook Login endpoint returned HTTP ' + str(exc.code) + detail + '; stopped safely.') from None
        except (URLError, TimeoutError):
            if method == 'GET' and attempt < attempts - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise base.SafetyError('Network outcome uncertain; no publishing mutation was retried.') from None
        except (ValueError, TypeError):
            raise base.SafetyError('Unexpected Meta response format; stopped safely.') from None


class FacebookInstagram(base.Instagram):
    def call(self, path, method='GET', params=None, body=None):
        return facebook_request(self.prefix + path, self.token, method, params, body)

    def verify(self, expected):
        if expected.lower() != EXPECTED_USERNAME:
            raise base.SafetyError('Unexpected configured Instagram account.')
        me = self.call('/' + INSTAGRAM_ID, params={'fields': 'id,username'})
        if str(me.get('id', '')) != INSTAGRAM_ID or me.get('username', '').lower() != expected.lower():
            raise base.SafetyError('Token does not authorize the expected Instagram account.')
        self.user = INSTAGRAM_ID
        self.call('/' + self.user + '/content_publishing_limit')


def main():
    original_client = base.Instagram
    base.Instagram = FacebookInstagram
    try:
        base.main()
    finally:
        base.Instagram = original_client


if __name__ == '__main__':
    try:
        main()
    except base.SafetyError as exc:
        print('SAFE STOP: ' + str(exc), file=sys.stderr)
        sys.exit(1)
