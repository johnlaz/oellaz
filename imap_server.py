#!/usr/bin/env python3
"""
Odoo Email Link - Lead Capture Server
Runs on http://localhost:7843
Start with: python imap_server.py

Also auto-starts server.py (CORS proxy on port 7842) if not already running.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json, imaplib, email, ssl, sys, os, subprocess, time, threading, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request as _req
import urllib.error   as _err
from email.header import decode_header
from datetime import datetime, timedelta

PORT       = 7843
PROXY_PORT = 7842
GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL    = 'llama-3.3-70b-versatile'

# ─── Scan progress (polled via GET /status) ───────────────────────────────────

_lock     = threading.Lock()
_progress = {'running': False, 'stage': 'idle', 'total': 0,
             'scanned': 0, 'matched': 0, 'message': '', 'ts': 0}
_cancel_requested = False

def sp(**kw):
    with _lock:
        kw['ts'] = time.time()
        _progress.update(kw)

def gp():
    with _lock:
        return dict(_progress)

# ─── Email helpers ────────────────────────────────────────────────────────────

def decode_mime(value):
    if not value:
        return ''
    parts = decode_header(value)
    out = []
    for raw, enc in parts:
        if isinstance(raw, bytes):
            out.append(raw.decode(enc or 'utf-8', errors='replace'))
        else:
            out.append(str(raw))
    return ' '.join(out)

def strip_html(text):
    text = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<(br|p|div|tr|li|h[1-6])\b[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|tr|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    for ent, ch in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&nbsp;',' '),
                    ('&quot;','"'),('&#39;',"'"),('&ndash;','–'),('&mdash;','—')]:
        text = text.replace(ent, ch)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def get_text_body(msg):
    """Extract plain text, preferring text/plain but stripping HTML if needed."""
    plain = html = None
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if 'attachment' in cd:
                continue
            if ct == 'text/plain' and plain is None:
                charset = part.get_content_charset() or 'utf-8'
                plain = part.get_payload(decode=True).decode(charset, errors='replace')
            elif ct == 'text/html' and html is None:
                charset = part.get_content_charset() or 'utf-8'
                html = part.get_payload(decode=True).decode(charset, errors='replace')
    else:
        charset = msg.get_content_charset() or 'utf-8'
        raw = msg.get_payload(decode=True).decode(charset, errors='replace')
        if msg.get_content_type() == 'text/html':
            html = raw
        else:
            plain = raw
    if plain and plain.strip():
        return plain
    if html:
        return strip_html(html)
    return ''

# ─── IMAP ─────────────────────────────────────────────────────────────────────

def connect_imap(config):
    ctx  = ssl.create_default_context()
    conn = imaplib.IMAP4_SSL(config['host'], int(config.get('port', 993)), ssl_context=ctx)
    conn.login(config['email'], config['password'])
    return conn

def imap_test(config):
    try:
        conn = connect_imap(config)
        status, data = conn.select('INBOX', readonly=True)
        count = int(data[0]) if status == 'OK' else 0
        conn.logout()
        return {'ok': True, 'message': f'Connected. {count} messages in INBOX.'}
    except imaplib.IMAP4.error as e:
        return {'ok': False, 'message': f'IMAP auth error: {e}'}
    except Exception as e:
        return {'ok': False, 'message': str(e)}

# ─── Groq extraction ──────────────────────────────────────────────────────────

def groq_extract(body_text, ai_hint='', groq_key=''):
    """Call Groq to extract lead fields from email body. Returns dict."""
    if not groq_key:
        return {'customer_name':'', 'phone':'', 'email':'', 'notes':'',
                'error': 'No Groq key — add it in Step 1 credentials'}

    hint = f'\n\nNote: {ai_hint}' if ai_hint else ''
    system_msg = (
        'You are a lead data extractor. Read the email and return ONLY a JSON object '
        'with exactly these keys: "customer_name", "phone", "email", "notes". '
        'customer_name: full name of the caller or customer (often in ALL CAPS in call alerts). '
        'phone: phone number exactly as shown. '
        'email: email address if present, else empty string. '
        'notes: 1-3 sentence summary of why they called or what they need. '
        'If a field is not found use an empty string. '
        'Return ONLY the raw JSON — no markdown, no backticks, no explanation.' + hint
    )

    payload = json.dumps({
        'model': GROQ_MODEL,
        'max_tokens': 400,
        'temperature': 0,
        'messages': [
            {'role': 'system', 'content': system_msg},
            {'role': 'user',   'content': body_text[:6000]},
        ]
    }).encode()

    request = _req.Request(GROQ_ENDPOINT, data=payload, headers={
        'Content-Type':  'application/json',
        'Authorization': f'Bearer {groq_key}',
        'User-Agent':    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept':        'application/json',
    })
    try:
        with _req.urlopen(request, timeout=25) as resp:
            data = json.loads(resp.read())
        raw = data['choices'][0]['message']['content'].strip()
        # Strip accidental markdown fences
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw.strip())
        result.setdefault('customer_name', '')
        result.setdefault('phone', '')
        result.setdefault('email', '')
        result.setdefault('notes', '')
        return result
    except _err.HTTPError as e:
        body = e.read().decode(errors='replace')
        return {'customer_name':'','phone':'','email':'','notes':'',
                'error': f'Groq HTTP {e.code}: {body[:200]}'}
    except Exception as e:
        return {'customer_name':'','phone':'','email':'','notes':'',
                'error': str(e)}

# ─── Main scan ────────────────────────────────────────────────────────────────

def imap_fetch(config, specs, days=14):
    """
    Two-pass IMAP scan. Returns matched emails with full body text.
    Groq extraction happens in the browser after this returns.
    """
    sp(running=True, stage='connecting', total=0, scanned=0, matched=0,
       message='Connecting to mailbox…')
    results       = []
    seen_subjects = []
    total         = 0
    candidates    = []

    try:
        conn = connect_imap(config)
        conn.select('INBOX', readonly=True)

        since_date = (datetime.now() - timedelta(days=int(days))).strftime('%d-%b-%Y')
        sp(stage='searching', message=f'Searching inbox since {since_date}…')
        status, uids = conn.uid('search', None, f'SINCE {since_date}')
        if status != 'OK' or not uids[0]:
            conn.logout()
            sp(running=False, stage='done', message='No messages in date window.')
            return {'leads': [], 'debug': {'total': 0, 'candidates': 0, 'seen_subjects': []}}

        uid_list = uids[0].split()
        total_raw = len(uid_list)

        # Yahoo IMAP sometimes ignores SINCE — apply a Python-side date cutoff too
        cutoff_dt = datetime.now() - timedelta(days=int(days))
        sp(stage='headers', total=total_raw, scanned=0,
           message=f'Found {total_raw} messages — applying {days}-day date filter…')

        # Validate specs have at least one filter
        for spec in specs:
            if not any([spec.get('subject_contains','').strip(), spec.get('subject_exact','').strip(),
                        spec.get('from_contains','').strip(),    spec.get('from_domain','').strip(),
                        spec.get('from_exact','').strip()]):
                err = f'Spec "{spec.get("name","?")}" has no Subject or Sender filter. Add one and save.'
                sp(running=False, stage='error', message=err)
                return {'leads': [{'error': err}], 'debug': {}}

        # ── Pass 1: headers only ────────────────────────────────────────────
        candidates   = []
        filtered_out = 0
        from email.utils import parsedate_to_datetime as _parse_dt
        import datetime as _dt

        for i, uid in enumerate(uid_list):
            global _cancel_requested
            if _cancel_requested:
                _cancel_requested = False
                conn.logout()
                sp(running=False, stage='done', message='Scan cancelled by user.')
                return {'leads': [], 'debug': {'total': total_raw, 'candidates': 0, 'seen_subjects': seen_subjects}}
            sp(scanned=i+1, message=f'Scanning headers… {i+1} / {total_raw}')
            status, data = conn.uid('fetch', uid, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
            if status != 'OK' or not data or data[0] is None:
                continue
            raw_hdr  = data[0][1] if isinstance(data[0], tuple) else b''
            hdr      = email.message_from_bytes(raw_hdr)
            subject  = decode_mime(hdr.get('Subject', ''))
            sender   = decode_mime(hdr.get('From', ''))
            date_str = hdr.get('Date', '')

            # Python-side date check — Yahoo IMAP SINCE is unreliable
            try:
                email_dt = _parse_dt(date_str)
                if email_dt.tzinfo is not None:
                    cutoff_aware = cutoff_dt.replace(tzinfo=_dt.timezone.utc)
                    if email_dt < cutoff_aware:
                        filtered_out += 1
                        continue
                elif email_dt.replace(tzinfo=None) < cutoff_dt:
                    filtered_out += 1
                    continue
            except Exception:
                pass  # unparseable date — include the email

            if len(seen_subjects) < 10:
                em = re.search(r'<([^>]+)>', sender)
                seen_subjects.append({
                    'subject':      subject,
                    'sender':       sender,
                    'sender_email': em.group(1) if em else sender,
                    'date':         date_str,
                })

            matched = []
            for spec in specs:
                subj_norm  = ' '.join(subject.split()).lower()
                subj_clean = re.sub(r'^(re|fwd|fw|aw):\s*', '', subj_norm, flags=re.IGNORECASE)
                sender_norm = sender.lower().strip()
                em2 = re.search(r'<([^>]+)>', sender)
                sender_email = em2.group(1).lower() if em2 else sender_norm

                subj_ok = True
                if spec.get('subject_exact'):
                    n = spec['subject_exact'].lower().strip()
                    subj_ok = n == subj_norm or n == subj_clean
                elif spec.get('subject_contains'):
                    n = spec['subject_contains'].lower().strip()
                    subj_ok = n in subj_norm or n in subj_clean

                from_ok = True
                if spec.get('from_exact'):
                    n = spec['from_exact'].lower().strip()
                    from_ok = n in sender_norm or n in sender_email
                elif spec.get('from_domain'):
                    d = spec['from_domain'].lstrip('@').lower().strip()
                    from_ok = f'@{d}' in sender_norm or f'@{d}' in sender_email
                elif spec.get('from_contains'):
                    n = spec['from_contains'].lower().strip()
                    from_ok = n in sender_norm or n in sender_email

                if subj_ok and from_ok:
                    matched.append(spec)

            if matched:
                candidates.append((uid, subject, sender, date_str, matched))
                sp(matched=len(candidates))  # update counter immediately as each match is found

        total = total_raw - filtered_out  # emails actually within date window
        n = len(candidates)
        sp(stage='bodies', matched=n,
           message=f'{n} match{"es" if n!=1 else ""} — fetching bodies…')

        # ── Pass 2: fetch body, return for browser to send to Groq ──────────
        for i, (uid, subject, sender, date_str, matched_specs) in enumerate(candidates):
            sp(message=f'Fetching body {i+1} of {n}…')
            status, data = conn.uid('fetch', uid, '(RFC822)')
            if status != 'OK' or not data or data[0] is None:
                continue
            msg  = email.message_from_bytes(data[0][1])
            body = get_text_body(msg)

            # One result per email — use first spec that passes body_contains filter
            spec = next(
                (s for s in matched_specs
                 if not s.get('body_contains') or s['body_contains'].lower() in body.lower()),
                matched_specs[0]
            )
            results.append({
                'uid':          uid.decode(),
                'spec_id':      spec.get('id', ''),
                'spec_name':    spec.get('name', ''),
                'spec_tag':     spec.get('tag', ''),
                'user_id':      spec.get('user_id'),
                'ai_hint':      spec.get('ai_hint', ''),
                'subject':      subject,
                'sender':       sender,
                'date':         date_str,
                'body':         body[:6000],
                'body_snippet': body[:400].strip(),
                'fields':       {},
            })
            # Update matched count in real time so progress bar reflects it
            sp(matched=len(results))

        conn.logout()
        sp(running=False, stage='done',
           message=f'Done — {len(results)} match{"es" if len(results)!=1 else ""} fetched. Running AI extraction…')

    except Exception as e:
        sp(running=False, stage='error', message=str(e))
        return {'leads': [{'error': str(e)}], 'debug': {}}

    return {
        'leads': results,
        'debug': {'total': total, 'candidates': len(candidates), 'seen_subjects': seen_subjects},
    }

# ─── HTTP handler ─────────────────────────────────────────────────────────────

class IMAPHandler(BaseHTTPRequestHandler):

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type',  'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/ping':
            self._json({'ok': True, 'service': 'imap_server', 'port': PORT})
        elif path == '/status':
            self._json(gp())
        else:
            self._json({'error': 'Not found'}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_body()

        if path == '/test':
            self._json(imap_test(data.get('config', data)))

        elif path == '/cancel':
            global _cancel_requested
            _cancel_requested = True
            sp(message='Cancelling…')
            self._json({'ok': True})

        elif path == '/test-groq':
            key    = data.get('groq_key', '')
            result = groq_extract('Test email body: Name is John Smith, phone (305) 555-1234.', groq_key=key)
            self._json(result)

        elif path == '/browse':
            config = data.get('config', {})
            limit  = int(data.get('limit', 30))
            flagged = data.get('flagged', False)
            folder  = data.get('folder', 'INBOX')
            if not config.get('email') or not config.get('password'):
                self._json({'error': 'Missing IMAP credentials'}, 400)
                return
            try:
                emails = _fetch(limit=limit, flagged=flagged, folder=folder)
                self._json({'ok': True, 'emails': emails, 'count': len(emails)})
            except Exception as e:
                self._json({'error': str(e)}, 500)

        elif path == '/headers':
            config  = data.get('config', {})
            limit   = int(data.get('limit', 50))
            folder  = data.get('folder', 'INBOX')
            if not config.get('email') or not config.get('password'):
                self._json({'error': 'Missing credentials'}, 400)
                return
            try:
                emails = _fetch(limit=limit, folder=folder)
                self._json({'ok': True, 'emails': emails})
            except Exception as e:
                self._json({'error': str(e)}, 500)

        elif path == '/body':
            config = data.get('config', {})
            uid    = data.get('uid')
            folder = data.get('folder', 'INBOX')
            if not config.get('email') or not config.get('password'):
                self._json({'error': 'Missing credentials'}, 400)
                return
            try:
                emails = _fetch(limit=200, folder=folder)
                match  = next((e for e in emails if str(e.get('uid')) == str(uid)), None)
                if match:
                    self._json({'ok': True, 'body': match.get('body',''), 'email': match})
                else:
                    self._json({'error': 'Message not found'}, 404)
            except Exception as e:
                self._json({'error': str(e)}, 500)

        elif path == '/folders':
            config = data.get('config', {})
            if not config.get('email') or not config.get('password'):
                self._json({'error': 'Missing credentials'}, 400)
                return
            try:
                import imaplib as _imap
                M = _imap.IMAP4_SSL(config['host'], int(config.get('port', 993)))
                M.login(config['email'], config['password'])
                typ, lst = M.list()
                M.logout()
                folders = [l.decode().split('"."')[-1].strip().strip('"') for l in lst if l]
                self._json({'ok': True, 'folders': folders})
            except Exception as e:
                self._json({'error': str(e)}, 500)

        elif path == '/scrape':
            url = data.get('url', '')
            if not url:
                self._json({'error': 'No URL'}, 400)
                return
            try:
                req = _req.Request(url, headers={'User-Agent':'Mozilla/5.0'})
                with _req.urlopen(req, timeout=15) as r:
                    raw = r.read().decode('utf-8','replace')
                # Strip tags
                text = re.sub(r'<[^>]+>', ' ', raw)
                text = re.sub(r'\s+', ' ', text).strip()[:8000]
                self._json({'ok': True, 'text': text})
            except Exception as e:
                self._json({'error': str(e)}, 500)

        elif path == '/send':
            # Send email via SMTP using the same credentials as IMAP
            config  = data.get('config', {})
            to      = data.get('to', '')
            subject = data.get('subject', '')
            body    = data.get('body', '')

            if not config.get('email') or not config.get('password'):
                self._json({'error': 'No email credentials configured — check Settings > Mail Account'}, 400)
                return
            if not to:
                self._json({'error': 'No recipient specified'}, 400)
                return
            try:
                imap_host = config.get('host', '')
                # Derive SMTP host from IMAP host
                smtp_host = imap_host.replace('imap.', 'smtp.', 1)
                if not smtp_host or smtp_host == imap_host:
                    if 'gmail' in imap_host:
                        smtp_host = 'smtp.gmail.com'
                    elif 'yahoo' in imap_host:
                        smtp_host = 'smtp.mail.yahoo.com'
                    elif 'outlook' in imap_host or 'hotmail' in imap_host or 'office365' in imap_host:
                        smtp_host = 'smtp.office365.com'
                    else:
                        smtp_host = imap_host.replace('imap', 'smtp')

                smtp_port = int(config.get('smtp_port', 587))
                sender    = config.get('email', '')
                password  = config.get('password', '')

                msg = MIMEMultipart('alternative')
                msg['From']    = sender
                msg['To']      = to
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                html_body = '<p>' + body.replace('\n', '</p><p>') + '</p>'
                msg.attach(MIMEText(html_body, 'html'))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as srv:
                    srv.ehlo()
                    srv.starttls()
                    srv.login(sender, password)
                    srv.sendmail(sender, [to], msg.as_string())

                self._json({'ok': True, 'smtp_host': smtp_host})
            except Exception as e:
                self._json({'error': str(e)}, 500)

        elif path == '/fetch':
            config = data.get('config', {})
            specs  = data.get('specs', [])
            days   = data.get('days', 14)
            if not config.get('email') or not config.get('password'):
                self._json({'error': 'Missing IMAP credentials'}, 400)
                return
            result_box = [None]
            def run(): result_box[0] = imap_fetch(config, specs, days)
            t = threading.Thread(target=run, daemon=True)
            t.start()
            t.join(timeout=480)
            if t.is_alive():
                sp(running=False, stage='error', message='Scan timed out (8 min limit).')
                self._json({'leads': [{'error': 'Timed out. Try a shorter date range.'}], 'debug': {}})
            else:
                self._json(result_box[0] or {'leads': [], 'debug': {}})

        else:
            self._json({'error': 'Not found'}, 404)


    def log_message(self, fmt, *args):
        print(f'  [{args[1]}] {args[0]}')

# ─── Auto-launch server.py ────────────────────────────────────────────────────

def is_port_open(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('localhost', port)) == 0

def start_proxy_server():
    if is_port_open(PROXY_PORT):
        print(f'  CORS proxy already running on port {PROXY_PORT}.')
        return
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.py')
    if not os.path.exists(script):
        print('  WARNING: server.py not found — CORS proxy not started.')
        return
    python  = sys.executable
    pythonw = python.replace('python.exe', 'pythonw.exe')
    exe     = pythonw if os.path.exists(pythonw) else python
    kwargs  = {}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen([exe, script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    for _ in range(6):
        time.sleep(0.5)
        if is_port_open(PROXY_PORT):
            print(f'  CORS proxy started on port {PROXY_PORT}.')
            return
    print(f'  WARNING: CORS proxy did not respond on port {PROXY_PORT}.')

# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('Odoo Email Link - Lead Capture Server')
    start_proxy_server()
    server = ThreadingHTTPServer(('localhost', PORT), IMAPHandler)
    print(f'Ready on http://localhost:{PORT}  |  Press Ctrl+C to stop.\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
