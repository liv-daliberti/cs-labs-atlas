"""Shared transport configuration; credentials never enter publication receipts."""
import json
import os
import sys
import termios
from urllib.parse import urlsplit


def origin(value):
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or
            parts.path not in ('', '/') or parts.query or parts.fragment):
        raise ValueError('Publication origin must be an HTTPS origin without credentials, path, query or fragment')
    return value.rstrip('/')


def credentials(update=False):
    """CI uses secret environment variables; interactive tools can supply one JSON line."""
    if os.environ.get('ATLAS_UPDATE_TOKEN') or os.environ.get('SITES_BYPASS_TOKEN'):
        result = {'update_token': os.environ.get('ATLAS_UPDATE_TOKEN', ''),
                  'bypass_token': os.environ.get('SITES_BYPASS_TOKEN', '')}
    else:
        settings = termios.tcgetattr(sys.stdin.fileno()) if sys.stdin.isatty() else None
        if settings:
            hidden = settings.copy()
            hidden[3] &= ~termios.ECHO
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, hidden)
        print('Ready for publication credentials on stdin (input is hidden; {} for anonymous verification).', flush=True)
        try:
            try:
                result = json.loads(sys.stdin.readline())
            except (ValueError, TypeError):
                raise ValueError('Expected one JSON credentials object on stdin') from None
        finally:
            if settings:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, settings)
    if not isinstance(result, dict) or any(not isinstance(v, str) for v in result.values()):
        raise ValueError('Credentials must be a JSON object of strings')
    if update and len(result.get('update_token', '')) < 32:
        raise ValueError('An existing maintenance token of at least 32 characters is required; no upload attempted')
    return result


def headers(values, update=False):
    result = {}
    if values.get('bypass_token'):
        result['OAI-Sites-Authorization'] = 'Bearer ' + values['bypass_token']
    if update:
        result['X-Atlas-Update-Token'] = values['update_token']
    return result


def scoped_receipts(value, site_origin):
    # Older bare-hash receipts do not establish which bucket was verified.
    if value.get('schema') == 2 and value.get('origin') == site_origin:
        return value.get('objects', {})
    return {}
