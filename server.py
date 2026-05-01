#!/usr/bin/env python3
"""
Odoo Email Link - Local CORS Proxy + Gmail API Server
Runs on http://localhost:7842

Gmail API setup:
  1. Drop credentials.json from Google Cloud Console into this folder
  2. Run start.bat — browser opens to authorize on first use
  3. token.json saved automatically for future runs
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qs
import urllib.error, json, threading, os, base64

PORT       = 7842
SCOPES     = ['https://www.googleapis.com/auth/gmail.readonly']
CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token.json')

_inbox_store  = {}
_inbox_lock   = threading.Lock()
_gmail_svc    = None
_gmail_lock   = threading.Lock()


def _libs_ok():
    try:
        import google.oauth2.credentials, google_auth_oauthlib.flow, googleapiclient.discovery
        return True
    except ImportError:
        return False


def _get_svc():
    global _gmail_svc
    with _gmail_lock:
        if _gmail_svc:
            return _gmail_svc
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request as GReq
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GReq())
            else:
                flow  = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            open(TOKEN_FILE, 'w').write(creds.to_json())
        _gmail_svc = build('gmail', 'v1', credentials=creds)
        return _gmail_svc


def _fetch(limit=30, flagged=False, folder='INBOX'):
    import base64
    svc = _get_svc()
    q   = ('is:starred ' if flagged else '') + ('in:inbox' if folder.upper()=='INBOX' else f'in:{folder}')
    res = svc.users().messages().list(userId='me', q=q.strip(), maxResults=limit).execute()
    out = []
    for ref in res.get('messages', []):
        try:
            m  = svc.users().messages().get(userId='me', id=ref['id'], format='full').execute()
            hd = {h['name']:h['value'] for h in m['payload']['headers']}
            fr = hd.get('From','')
            sn, se = ('','')
            if '<' in fr:
                sn = fr.split('<')[0].strip().strip('"')
                se = fr.split('<')[1].rstrip('>')
            else:
                se = fr
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(hd.get('Date',''))
                ds = dt.strftime('%b %-d')
            except Exception:
                ds = hd.get('Date','')[:10]

            # Extract plain text body
            body = ''
            def _get_body(payload):
                if payload.get('mimeType') == 'text/plain' and payload.get('body',{}).get('data'):
                    try: return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8','replace')
                    except: return ''
                for part in payload.get('parts', []):
                    r = _get_body(part)
                    if r: return r
                return ''
            body = _get_body(m['payload'])
            if not body:
                body = m.get('snippet', '')
            # Clean up body — normalize line endings and trim
            body = body.replace('\r\n','\n').replace('\r','\n')
            # Collapse 3+ blank lines to 2
            import re as _re2
            body = _re2.sub(r'\n{3,}', '\n\n', body).strip()
            body = body[:2000]  # cap at 2000 chars for performance

            out.append({
                'uid':         ref['id'],
                'subject':     hd.get('Subject','(no subject)'),
                'sender':      se,
                'sender_name': sn,
                'preview':     m.get('snippet',''),
                'body':        body,
                'date':        ds,
                'flagged':     'STARRED' in m.get('labelIds',[]),
                'to':          hd.get('To',''),
                'reply_to':    hd.get('Reply-To', se),
                'message_id':  hd.get('Message-ID',''),
            })
        except Exception:
            continue
    return out


class ProxyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path   = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)

        if path == '/ping':
            self._j({'ok': True})

        elif path == '/gmail/status':
            auth = False
            if _libs_ok() and (os.path.exists(TOKEN_FILE) or os.path.exists(CREDS_FILE)):
                try: _get_svc(); auth = True
                except Exception: pass
            self._j({'has_creds': os.path.exists(CREDS_FILE),
                     'has_token': os.path.exists(TOKEN_FILE),
                     'has_libs':  _libs_ok(),
                     'authorized': auth})

        elif path == '/gmail/auth':
            if not os.path.exists(CREDS_FILE):
                self._j({'error': 'credentials.json not found — drop it in the OEL folder'}, 400); return
            if not _libs_ok():
                self._j({'error': 'Missing libraries. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'}, 400); return
            try:
                _get_svc()
                self._j({'ok': True})
            except Exception as e:
                self._j({'error': str(e)}, 500)

        elif path == '/gmail/fetch':
            if not _libs_ok():
                self._j({'error': 'Google API libraries not installed'}); return
            try:
                emails = _fetch(
                    limit   = int(params.get('limit', ['30'])[0]),
                    flagged = params.get('flagged', ['0'])[0] == '1',
                    folder  = params.get('folder', ['INBOX'])[0])
                self._j({'ok': True, 'emails': emails, 'count': len(emails)})
            except Exception as e:
                self._j({'error': str(e)}, 500)

        elif path == '/gmail/revoke':
            global _gmail_svc
            if os.path.exists(TOKEN_FILE): os.remove(TOKEN_FILE)
            with _gmail_lock: _gmail_svc = None
            self._j({'ok': True})

        elif path == '/inbox':
            with _inbox_lock: data = dict(_inbox_store)
            self._j(data)

        elif path == '/inbox/push':
            enc = params.get('d', [None])[0]
            if enc:
                try:
                    data = json.loads(base64.b64decode(enc.encode()).decode('utf-8','replace'))
                    with _inbox_lock: _inbox_store.clear(); _inbox_store.update(data)
                    html = b'<html><body style="font-family:sans-serif;padding:30px;background:#1a1a1a;color:#c8f04e"><h2>&#10003; Emails received</h2><p style="color:#888">OEL has your emails. You can close this tab.</p><script>setTimeout(function(){window.close();},1500);</script></body></html>'
                    self.send_response(200); self._cors()
                    self.send_header('Content-Type','text/html'); self.send_header('Content-Length',len(html)); self.end_headers(); self.wfile.write(html); return
                except Exception: pass
            self.send_response(400); self.end_headers()

        else:
            self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_POST(self):
        path   = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)

        if path == '/inbox':
            try:
                data = json.loads(body.decode('utf-8','replace'))
                with _inbox_lock: _inbox_store.clear(); _inbox_store.update(data)
                self._j({'ok': True, 'count': len(data.get('emails',[]))})
            except Exception as e:
                self._j({'error': str(e)}, 400)
        elif path == '/inbox/clear':
            with _inbox_lock: _inbox_store.clear()
            self._j({'ok': True})
        else:
            target = params.get('url', [None])[0]
            if not target: self.send_response(400); self.end_headers(); return
            try:
                req = Request(target, data=body, headers={'Content-Type':'text/xml', 'Connection':'keep-alive'})
                with urlopen(req, timeout=30) as r: data = r.read()
                self.send_response(200); self._cors()
                self.send_header('Content-Type','text/xml'); self.end_headers(); self.wfile.write(data)
            except urllib.error.URLError as e:
                self.send_response(502); self._cors(); self.end_headers(); self.wfile.write(str(e).encode())

    def _j(self, obj, status=200):
        b = json.dumps(obj).encode()
        self.send_response(status); self._cors()
        self.send_header('Content-Type','application/json'); self.send_header('Content-Length',len(b)); self.end_headers(); self.wfile.write(b)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')

    def log_message(self, fmt, *args): pass


if __name__ == '__main__':
    from socketserver import ThreadingMixIn
    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
    ThreadedHTTPServer(('localhost', PORT), ProxyHandler).serve_forever()
