"""Manual-only diagnostics. No publishing, secret printing, secret writes, or third-party requests."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

EXPECTED = 'md_ibrahim07_official'
# Account's Instagram Graph node observed in its authenticated account insights.
FACEBOOK_IG_NODE = '17841430484113368'
VERSION = 'v25.0'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

opener = build_opener(NoRedirect())

def classify(message):
    text = str(message).lower()
    if 'expired' in text or 'session has been invalidated' in text:
        return 'expired_or_invalidated_session'
    if 'cannot parse' in text or 'malformed' in text:
        return 'token_not_parsed_by_this_api'
    if 'permission' in text or 'scope' in text:
        return 'permission_or_scope_requirement'
    if 'version' in text:
        return 'api_version_requirement'
    if 'unsupported get request' in text or 'does not exist' in text:
        return 'node_not_visible_or_wrong_api_login'
    if 'access token' in text or 'oauth' in text:
        return 'oauth_authorization_rejected'
    return 'request_rejected'

def get(host, path, token, fields=None):
    if host not in ('https://graph.instagram.com', 'https://graph.facebook.com'):
        raise RuntimeError('Unapproved host')
    url = host + '/' + VERSION + path
    if fields:
        url += '?' + urlencode({'fields': fields})
    assert urlparse(url).hostname in ('graph.instagram.com', 'graph.facebook.com')
    request = Request(url, headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'User-Agent': 'Instagram-Read-Only-Diagnostic'}, method='GET')
    try:
        with opener.open(request, timeout=25) as response:
            body = json.loads(response.read(65536))
            return body, {'http_status': response.status, 'accepted': True}
    except HTTPError as exc:
        summary = {'http_status': exc.code, 'accepted': False}
        try:
            error = json.loads(exc.read(65536)).get('error', {})
            for key in ('code', 'error_subcode'):
                if isinstance(error.get(key), int):
                    summary[key] = error[key]
            error_type = error.get('type', '')
            if isinstance(error_type, str) and re.fullmatch(r'[A-Za-z_]{1,60}', error_type):
                summary['error_type'] = error_type
            summary['classification'] = classify(error.get('message', ''))
        except (ValueError, TypeError, AttributeError):
            summary['classification'] = 'non_json_error'
        return None, summary
    except (URLError, TimeoutError):
        return None, {'accepted': False, 'classification': 'network_error'}
    except (ValueError, TypeError):
        return None, {'accepted': False, 'classification': 'invalid_response'}

def inspect_family(host, node_path, token):
    body, result = get(host, node_path, token, 'id,username')
    if body is None:
        return result
    matches = str(body.get('username', '')).lower() == EXPECTED
    result['expected_instagram_account'] = matches
    if matches and str(body.get('id', '')).isdigit():
        _, quota = get(host, '/' + str(body['id']) + '/content_publishing_limit', token)
        result['publishing_limit_check'] = quota
    return result

def main():
    raw = os.environ.get('INSTAGRAM_ACCESS_TOKEN', '')
    if not raw:
        print(json.dumps({'secret_present': False, 'result': 'missing_secret'}))
        return
    token = raw.strip()
    flags = {'outer_whitespace': token != raw, 'bearer_prefix': False, 'wrapping_quotes': False, 'assignment_prefix': False}
    if token.startswith('INSTAGRAM_ACCESS_TOKEN='):
        flags['assignment_prefix'] = True
        token = token.split('=', 1)[1].strip()
    if len(token) > 1 and token[0] == token[-1] and token[0] in ('\"', "'"):
        flags['wrapping_quotes'] = True
        token = token[1:-1].strip()
    if token.lower().startswith('bearer '):
        flags['bearer_prefix'] = True
        token = token[7:].strip()
    report = {'secret_present': True, 'format_flags': flags, 'publishing_performed': False}
    if token.startswith(('ghp_', 'github_pat_', 'gho_', 'ghu_', 'ghs_', 'ghr_')):
        report['result'] = 'github_credential_not_instagram_token'
        print(json.dumps(report, indent=2))
        return
    if not token or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in token):
        report['result'] = 'credential_contains_internal_whitespace_or_invalid_characters'
        print(json.dumps(report, indent=2))
        return
    report['instagram_login'] = inspect_family('https://graph.instagram.com', '/me', token)
    first = report['instagram_login']
    if first.get('expected_instagram_account') and first.get('publishing_limit_check', {}).get('accepted'):
        report['result'] = 'instagram_login_account_and_publishing_check_passed'
    else:
        # Read only the already-known Instagram node through Meta's alternative login family.
        # Do not enumerate Facebook profiles/pages, print IDs, or retrieve a page access token.
        report['facebook_login_for_same_instagram_account'] = inspect_family('https://graph.facebook.com', '/' + FACEBOOK_IG_NODE, token)
        second = report['facebook_login_for_same_instagram_account']
        report['result'] = 'facebook_login_configuration_needed' if second.get('expected_instagram_account') and second.get('publishing_limit_check', {}).get('accepted') else 'authorization_not_ready'
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
