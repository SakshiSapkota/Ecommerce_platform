#!/usr/bin/env python3
"""
SajhaMart E-Commerce Backend Server
Pure Python HTTP server — image uploads, full admin panel
"""

import http.server, socketserver, json, os, sys, urllib.parse, io, uuid, base64
from datetime import datetime
from http.cookies import SimpleCookie

sys.path.insert(0, os.path.dirname(__file__))
from db import init_db
from handlers import (
    handle_register, handle_login, handle_logout, handle_get_session,
    handle_get_products, handle_get_product, handle_get_categories,
    handle_place_order, handle_get_orders, handle_cancel_order,
    handle_get_wishlist, handle_add_wishlist, handle_remove_wishlist,
    handle_analytics,
    handle_delete_account, handle_forgot_password, handle_reset_password, handle_verify_reset_token,
    handle_admin_check, handle_admin_dashboard,
    handle_admin_get_categories, handle_admin_add_category,
    handle_admin_update_category, handle_admin_delete_category,
    handle_admin_get_products, handle_admin_add_product,
    handle_admin_update_product, handle_admin_delete_product,
    handle_admin_get_orders, handle_admin_get_order,
    handle_admin_update_order_status, handle_admin_delete_order,
    handle_admin_get_users, handle_admin_delete_user,
)

PORT = 8080
BASE_DIR     = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')
UPLOADS_DIR  = os.path.join(FRONTEND_DIR, 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_IMG_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
MAX_IMG_SIZE = 5 * 1024 * 1024  # 5 MB

MIME = {
    '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8',
    '.js':'application/javascript; charset=utf-8',
    '.json':'application/json; charset=utf-8', '.png':'image/png', '.jpg':'image/jpeg',
    '.jpeg':'image/jpeg', '.gif':'image/gif', '.svg':'image/svg+xml',
    '.ico':'image/x-icon', '.webp':'image/webp',
}

def _send(wfile, send_response, send_header, end_headers, status, data, extra_headers=None):
    body = json.dumps(data).encode('utf-8')
    send_response(status)
    send_header('Content-Type', 'application/json; charset=utf-8')
    send_header('Content-Length', str(len(body)))
    send_header('Access-Control-Allow-Origin', '*')
    send_header('Access-Control-Allow-Headers', 'Content-Type')
    if extra_headers:
        for k, v in extra_headers.items():
            send_header(k, v)
    end_headers()
    wfile.write(body)


class EcomHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *a):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % a}")

    def sid(self):
        c = SimpleCookie(self.headers.get('Cookie', ''))
        return c['session_id'].value if 'session_id' in c else None

    # ── Response helpers ────────────────────────────────────────────────────

    def json_resp(self, data, status=200, cookie=None):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def file_resp(self, path):
        ext  = os.path.splitext(path)[1].lower()
        mime = MIME.get(ext, 'application/octet-stream')
        try:
            with open(path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, 'Not found')

    def read_json(self):
        l = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(l).decode()) if l else {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # ── GET ─────────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        qs     = urllib.parse.parse_qs(parsed.query)
        sid    = self.sid()

        # Shop API
        if   path == '/api/session':   return self.json_resp(handle_get_session(sid))
        elif path == '/api/products':  return self.json_resp(handle_get_products(qs))
        elif path == '/api/categories': return self.json_resp(handle_get_categories())
        elif path == '/api/analytics': return self.json_resp(handle_analytics())
        elif path == '/api/orders':    return self.json_resp(handle_get_orders(sid))
        elif path == '/api/wishlist':  return self.json_resp(handle_get_wishlist(sid))
        elif path.startswith('/api/products/'):
            return self.json_resp(handle_get_product(path.split('/')[-1]))
        elif path.startswith('/api/verify-reset/'):
            r, s = handle_verify_reset_token(path.split('/')[-1])
            return self.json_resp(r, s)

        # Admin API
        elif path == '/api/admin/check':
            r, s = handle_admin_check(sid); return self.json_resp(r, s)
        elif path == '/api/admin/dashboard':
            r, s = handle_admin_dashboard(sid); return self.json_resp(r, s)
        elif path == '/api/admin/categories':
            r, s = handle_admin_get_categories(sid); return self.json_resp(r, s)
        elif path == '/api/admin/products':
            r, s = handle_admin_get_products(sid); return self.json_resp(r, s)
        elif path == '/api/admin/orders':
            r, s = handle_admin_get_orders(sid); return self.json_resp(r, s)
        elif path.startswith('/api/admin/orders/'):
            r, s = handle_admin_get_order(sid, path.split('/')[-1])
            return self.json_resp(r, s)
        elif path == '/api/admin/users':
            r, s = handle_admin_get_users(sid); return self.json_resp(r, s)

        # Static files
        else:
            fp = '/index.html' if path == '/' else path
            full = os.path.normpath(os.path.join(FRONTEND_DIR, fp.lstrip('/')))
            # Security: stay within frontend dir
            if not full.startswith(os.path.abspath(FRONTEND_DIR)):
                return self.send_error(403)
            if os.path.isfile(full):
                return self.file_resp(full)
            return self.file_resp(os.path.join(FRONTEND_DIR, 'index.html'))

    # ── POST ────────────────────────────────────────────────────────────────

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        sid  = self.sid()
        ct   = self.headers.get('Content-Type', '')

        # ── Image upload (multipart) ──────────────────────────────────────
        if path == '/api/admin/upload-image':
            return self._handle_image_upload(sid)

        # ── JSON endpoints ────────────────────────────────────────────────
        body = self.read_json()

        # Auth
        if path == '/api/register':
            r, s, c = handle_register(body)
            cookie = f'session_id={c}; Path=/; HttpOnly' if c else None
            return self.json_resp(r, s, cookie)

        elif path == '/api/login':
            r, s, c = handle_login(body)
            cookie = f'session_id={c}; Path=/; HttpOnly' if c else None
            return self.json_resp(r, s, cookie)

        elif path == '/api/logout':
            r = handle_logout(sid)
            return self.json_resp(r, 200,
                'session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')

        elif path == '/api/account/delete':
            r, s = handle_delete_account(sid, body); return self.json_resp(r, s)

        elif path == '/api/forgot-password':
            r, s = handle_forgot_password(body); return self.json_resp(r, s)

        elif path == '/api/reset-password':
            r, s = handle_reset_password(body); return self.json_resp(r, s)

        # Shop
        elif path == '/api/orders':
            r, s = handle_place_order(sid, body); return self.json_resp(r, s)

        elif path == '/api/wishlist':
            r, s = handle_add_wishlist(sid, body); return self.json_resp(r, s)

        # Admin
        elif path == '/api/admin/categories':
            r, s = handle_admin_add_category(sid, body); return self.json_resp(r, s)

        elif path.startswith('/api/admin/categories/'):
            cid = path.split('/')[-1]
            r, s = handle_admin_update_category(sid, cid, body)
            return self.json_resp(r, s)

        elif path == '/api/admin/products':
            r, s = handle_admin_add_product(sid, body); return self.json_resp(r, s)

        elif path.startswith('/api/admin/products/') and not path.endswith('/status'):
            pid = path.split('/')[-1]
            r, s = handle_admin_update_product(sid, pid, body)
            return self.json_resp(r, s)

        elif path.startswith('/api/admin/orders/') and path.endswith('/status'):
            oid = path.split('/')[-2]
            r, s = handle_admin_update_order_status(sid, oid, body)
            return self.json_resp(r, s)

        else:
            self.json_resp({'error': 'Not found'}, 404)

    # ── DELETE ───────────────────────────────────────────────────────────────

    def do_DELETE(self):
        path  = urllib.parse.urlparse(self.path).path
        sid   = self.sid()
        parts = path.split('/')

        if path.startswith('/api/wishlist/'):
            r, s = handle_remove_wishlist(sid, parts[-1])
        elif path.startswith('/api/orders/') and path.endswith('/cancel'):
            oid = parts[-2]
            r, s = handle_cancel_order(sid, oid)
        elif path.startswith('/api/admin/categories/'):
            r, s = handle_admin_delete_category(sid, parts[-1])
        elif path.startswith('/api/admin/products/'):
            r, s = handle_admin_delete_product(sid, parts[-1])
        elif path.startswith('/api/admin/orders/'):
            r, s = handle_admin_delete_order(sid, parts[-1])
        elif path.startswith('/api/admin/users/'):
            r, s = handle_admin_delete_user(sid, parts[-1])
        else:
            return self.json_resp({'error': 'Not found'}, 404)

        self.json_resp(r, s)

    # ── Image Upload Handler ─────────────────────────────────────────────────

    def _handle_image_upload(self, sid):
        from handlers import require_admin
        if not require_admin(sid):
            return self.json_resp({'success': False, 'error': 'Unauthorized'}, 403)

        ct = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in ct:
            return self.json_resp({'success': False, 'error': 'Multipart form required'}, 400)

        try:
            length  = int(self.headers.get('Content-Length', 0))
            raw     = self.rfile.read(length)

            # Parse boundary
            boundary = None
            for part in ct.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part[9:].strip().encode()
                    break

            if not boundary:
                return self.json_resp({'success': False, 'error': 'No boundary'}, 400)

            # Simple multipart parser
            file_data, mime_type, original_name = self._parse_multipart(raw, boundary)

            if not file_data:
                return self.json_resp({'success': False, 'error': 'No file received'}, 400)

            if mime_type not in ALLOWED_IMG_TYPES:
                return self.json_resp({'success': False,
                    'error': f'Invalid type: {mime_type}. Use JPG, PNG, GIF or WebP'}, 400)

            if len(file_data) > MAX_IMG_SIZE:
                return self.json_resp({'success': False, 'error': 'File too large (max 5 MB)'}, 400)

            ext_map = {
                'image/jpeg': '.jpg', 'image/png': '.png',
                'image/gif': '.gif',  'image/webp': '.webp'
            }
            ext      = ext_map.get(mime_type, '.jpg')
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(UPLOADS_DIR, filename)

            with open(filepath, 'wb') as f:
                f.write(file_data)

            url = f'/uploads/{filename}'
            return self.json_resp({'success': True, 'url': url, 'filename': filename})

        except Exception as e:
            return self.json_resp({'success': False, 'error': str(e)}, 500)

    def _parse_multipart(self, raw, boundary):
        """Simple multipart/form-data parser — extracts the first file part."""
        delim = b'--' + boundary
        parts = raw.split(delim)
        for part in parts:
            if b'filename=' not in part:
                continue
            # Split headers from body
            if b'\r\n\r\n' in part:
                header_raw, body = part.split(b'\r\n\r\n', 1)
            elif b'\n\n' in part:
                header_raw, body = part.split(b'\n\n', 1)
            else:
                continue

            # Strip trailing boundary marker
            if body.endswith(b'\r\n'):
                body = body[:-2]

            # Parse Content-Type from headers
            mime = 'image/jpeg'
            for line in header_raw.split(b'\n'):
                line = line.strip()
                if line.lower().startswith(b'content-type:'):
                    mime = line.split(b':', 1)[1].strip().decode('utf-8', errors='replace')

            # Get original filename
            fname = ''
            for line in header_raw.split(b'\n'):
                if b'filename=' in line:
                    try:
                        fname = line.split(b'filename=')[1].strip().strip(b'"').decode()
                    except: pass

            return body, mime.strip(), fname

        return None, None, None


def run():
    init_db()
    print(f"\n{'='*52}")
    print(f"  SajhaMart E-Commerce Server")
    print(f"  Store:  http://localhost:{PORT}")
    print(f"  Admin:  http://localhost:{PORT}/admin.html")
    print(f"  Uploads folder: frontend/uploads/")
    print(f"{'='*52}\n")
    with socketserver.ThreadingTCPServer(('', PORT), EcomHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == '__main__':
    run()
