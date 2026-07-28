#!/usr/bin/env python3
"""
All API request handlers — shop + admin
"""

import sqlite3, hashlib, json, re, secrets
from datetime import datetime
from db import get_db

# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_pw(pw):  return hashlib.sha256(pw.encode()).hexdigest()
def valid_email(e): return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e))
def row(r):  return dict(r) if r else None
def rows(rs): return [dict(r) for r in rs]

def product_row(r):
    p = dict(r) if r else None
    if not p:
        return None
    discount = max(0, min(95, int(p.get('discount_percent') or 0)))
    price = float(p.get('price') or 0)
    p['discount_percent'] = discount
    p['final_price'] = round(price * (100 - discount) / 100, 2)
    return p

def product_rows(rs):
    return [product_row(r) for r in rs]

def get_user_by_session(sid):
    if not sid: return None
    db = get_db()
    try:
        r = db.execute(
            "SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.id=?", (sid,)
        ).fetchone()
        return row(r)
    finally: db.close()

def require_admin(sid):
    u = get_user_by_session(sid)
    return u if (u and u.get('is_admin')) else None

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════════════

def handle_register(body):
    name  = (body.get('name') or '').strip()
    email = (body.get('email') or '').strip().lower()
    pw    = body.get('password') or ''
    errs  = {}
    if len(name) < 2:       errs['name']     = 'Min 2 characters'
    if not valid_email(email): errs['email']  = 'Invalid email'
    if len(pw) < 6:         errs['password'] = 'Min 6 characters'
    if errs: return {'success':False,'errors':errs}, 400, None

    db = get_db()
    try:
        if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            return {'success':False,'errors':{'email':'Already registered'}}, 409, None
        cur = db.execute("INSERT INTO users (name,email,password_hash) VALUES (?,?,?)",
                         (name, email, hash_pw(pw)))
        uid = cur.lastrowid
        sid = secrets.token_hex(32)
        db.execute("INSERT INTO sessions (id,user_id) VALUES (?,?)", (sid, uid))
        db.execute("INSERT INTO analytics (event_type,data) VALUES (?,?)",
                   ('register', json.dumps({'user_id':uid})))
        db.commit()
        return {'success':True,'user':{'id':uid,'name':name,'email':email}}, 200, sid
    finally: db.close()

def handle_login(body):
    email = (body.get('email') or '').strip().lower()
    pw    = body.get('password') or ''
    if not email or not pw:
        return {'success':False,'errors':{'general':'Email and password required'}}, 400, None
    db = get_db()
    try:
        u = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not u or u['password_hash'] != hash_pw(pw):
            return {'success':False,'errors':{'general':'Invalid email or password'}}, 401, None
        sid = secrets.token_hex(32)
        db.execute("INSERT INTO sessions (id,user_id) VALUES (?,?)", (sid, u['id']))
        db.execute("INSERT INTO analytics (event_type,data) VALUES (?,?)",
                   ('login', json.dumps({'user_id':u['id']})))
        db.commit()
        return {'success':True,'user':{'id':u['id'],'name':u['name'],'email':u['email'],'is_admin':u['is_admin']}}, 200, sid
    finally: db.close()

def handle_logout(sid):
    if sid:
        db = get_db()
        try: db.execute("DELETE FROM sessions WHERE id=?", (sid,)); db.commit()
        finally: db.close()
    return {'success':True}

def handle_get_session(sid):
    u = get_user_by_session(sid)
    if u: return {'loggedIn':True,'user':{'id':u['id'],'name':u['name'],'email':u['email'],'is_admin':u.get('is_admin',0)}}
    return {'loggedIn':False}

# ═══════════════════════════════════════════════════════════════════════════════
#  PRODUCTS (shop)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_get_products(query):
    db = get_db()
    try:
        search   = (query.get('search',[''])[0] or '').strip().lower()
        category = (query.get('category',[''])[0] or '').strip()
        sort     = (query.get('sort',[''])[0] or '').strip()
        min_p    = query.get('min_price',[None])[0]
        max_p    = query.get('max_price',[None])[0]

        sql, params = "SELECT * FROM products WHERE 1=1", []
        if search:
            sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)"
            params += [f'%{search}%']*3
        if category and category != 'All':
            sql += " AND category=?"; params.append(category)
        if min_p: sql += " AND price>=?"; params.append(float(min_p))
        if max_p: sql += " AND price<=?"; params.append(float(max_p))

        order = {'price_asc':'price ASC','price_desc':'price DESC',
                 'rating':'rating DESC','name':'name ASC'}.get(sort,'id ASC')
        sql += f" ORDER BY {order}"

        prods = product_rows(db.execute(sql, params).fetchall())
        cats  = ['All'] + [r['name'] for r in db.execute("SELECT name FROM categories ORDER BY name").fetchall()]
        return {'success':True,'products':prods,'categories':cats,'total':len(prods)}
    finally: db.close()

def handle_get_product(pid):
    db = get_db()
    try:
        r = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if not r: return {'success':False,'error':'Not found'}
        return {'success':True,'product':product_row(r)}
    finally: db.close()

def handle_get_categories():
    db = get_db()
    try:
        cats = rows(db.execute("SELECT * FROM categories ORDER BY name").fetchall())
        for c in cats:
            c['product_count'] = db.execute(
                "SELECT COUNT(*) FROM products WHERE category=?", (c['name'],)).fetchone()[0]
        return {'success':True,'categories':cats}
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  ORDERS (shop)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_place_order(sid, body):
    items = body.get('items', [])
    if not items: return {'success':False,'error':'Cart is empty'}, 400

    errs = {}
    sh = body.get('shipping', {})
    if not sh.get('name','').strip():          errs['name']    = 'Required'
    if not valid_email(sh.get('email','')):    errs['email']   = 'Valid email required'
    if not sh.get('address','').strip():       errs['address'] = 'Required'
    if not sh.get('city','').strip():          errs['city']    = 'Required'
    if not sh.get('zip','').strip():           errs['zip']     = 'Required'
    if errs: return {'success':False,'errors':errs}, 400

    db = get_db()
    try:
        total, validated = 0, []
        for item in items:
            r = db.execute("SELECT * FROM products WHERE id=?", (item['id'],)).fetchone()
            if not r: return {'success':False,'error':f"Product {item['id']} not found"}, 400
            qty = max(1, int(item.get('quantity',1)))
            p = product_row(r)
            total += p['final_price'] * qty
            validated.append({'id':r['id'],'name':r['name'],'price':p['final_price'],'quantity':qty,'image':r['image']})

        u = get_user_by_session(sid)
        cur = db.execute("""
            INSERT INTO orders (user_id,items,total,status,shipping_name,shipping_email,
                                shipping_address,shipping_city,shipping_zip,payment_method)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (u['id'] if u else None, json.dumps(validated), round(total,2), 'Pending',
              sh.get('name','').strip(), sh.get('email','').strip(),
              sh.get('address','').strip(), sh.get('city','').strip(), sh.get('zip','').strip(),
              body.get('payment_method','card')))
        oid = cur.lastrowid
        db.execute("INSERT INTO analytics (event_type,data) VALUES (?,?)",
                   ('order', json.dumps({'order_id':oid,'total':total})))
        db.commit()
        return {'success':True,'order_id':oid,'total':round(total,2),'message':'Order placed!'}, 200
    finally: db.close()

def handle_cancel_order(sid, oid):
    u = get_user_by_session(sid)
    if not u: return {'success': False, 'error': 'Not authenticated'}, 401
    db = get_db()
    try:
        r = db.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, u['id'])).fetchone()
        if not r: return {'success': False, 'error': 'Order not found'}, 404
        o = dict(r)
        if o['status'] == 'Cancelled':
            return {'success': False, 'error': 'Order is already cancelled'}, 400
        if o['status'] in ('Shipped', 'Delivered'):
            return {'success': False, 'error': f'Cannot cancel an order that has been {o["status"].lower()}'}, 400
        # Allow cancellation only within 24 hours
        from datetime import datetime, timedelta
        created = datetime.fromisoformat(o['created_at'])
        if datetime.utcnow() - created > timedelta(hours=24):
            return {'success': False, 'error': 'Orders can only be cancelled within 24 hours of placing them'}, 400
        db.execute("UPDATE orders SET status='Cancelled' WHERE id=?", (oid,))
        db.commit()
        return {'success': True, 'message': f'Order #{oid} has been cancelled'}, 200
    finally: db.close()

def handle_get_orders(sid):
    u = get_user_by_session(sid)
    if not u: return {'success':False,'error':'Not authenticated','orders':[]}
    db = get_db()
    try:
        rs = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (u['id'],)).fetchall()
        result = []
        for r in rs:
            o = dict(r); o['items'] = json.loads(o['items']); result.append(o)
        return {'success':True,'orders':result}
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  WISHLIST (shop)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_get_wishlist(sid):
    u = get_user_by_session(sid)
    if not u: return {'success':False,'error':'Not authenticated','items':[]}
    db = get_db()
    try:
        rs = db.execute("""SELECT p.* FROM products p JOIN wishlist w ON p.id=w.product_id
                           WHERE w.user_id=? ORDER BY w.created_at DESC""", (u['id'],)).fetchall()
        return {'success':True,'items':rows(rs)}
    finally: db.close()

def handle_add_wishlist(sid, body):
    u = get_user_by_session(sid)
    if not u: return {'success':False,'error':'Login required'}, 401
    pid = body.get('product_id')
    if not pid: return {'success':False,'error':'product_id required'}, 400
    db = get_db()
    try:
        db.execute("INSERT OR IGNORE INTO wishlist (user_id,product_id) VALUES (?,?)", (u['id'],pid))
        db.commit()
        return {'success':True}, 200
    finally: db.close()

def handle_remove_wishlist(sid, pid):
    u = get_user_by_session(sid)
    if not u: return {'success':False,'error':'Login required'}, 401
    db = get_db()
    try:
        db.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?", (u['id'], pid))
        db.commit()
        return {'success':True}, 200
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS (shop)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_analytics():
    db = get_db()
    try:
        tu = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        to = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        rev= db.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0]
        tp = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        cats = rows(db.execute("SELECT category,COUNT(*) as count FROM products GROUP BY category ORDER BY count DESC").fetchall())
        return {'success':True,'stats':{'total_users':tu,'total_orders':to,'revenue':round(float(rev),2),'total_products':tp},'top_categories':cats}
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN — AUTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def handle_admin_check(sid):
    u = require_admin(sid)
    if not u: return {'success':False,'error':'Unauthorized'}, 403
    return {'success':True,'user':{'id':u['id'],'name':u['name'],'email':u['email']}}, 200

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN — DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════════════

def handle_admin_dashboard(sid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        tp  = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        tu  = db.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0]
        to  = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        tc  = db.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        rev = db.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0]
        pend= db.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'").fetchone()[0]
        ship= db.execute("SELECT COUNT(*) FROM orders WHERE status='Shipped'").fetchone()[0]
        delv= db.execute("SELECT COUNT(*) FROM orders WHERE status='Delivered'").fetchone()[0]

        recent_orders = rows(db.execute("""
            SELECT id,shipping_name,shipping_email,total,status,created_at
            FROM orders ORDER BY created_at DESC LIMIT 8""").fetchall())

        recent_users = rows(db.execute("""
            SELECT id,name,email,created_at FROM users WHERE is_admin=0
            ORDER BY created_at DESC LIMIT 8""").fetchall())

        cat_stats = rows(db.execute("""
            SELECT c.name, COUNT(p.id) as product_count
            FROM categories c LEFT JOIN products p ON p.category=c.name
            GROUP BY c.name ORDER BY product_count DESC""").fetchall())

        return {'success':True,'stats':{
            'total_products':tp,'total_users':tu,'total_orders':to,
            'total_categories':tc,'revenue':round(float(rev),2),
            'pending':pend,'shipped':ship,'delivered':delv
        },'recent_orders':recent_orders,'recent_users':recent_users,'cat_stats':cat_stats}, 200
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN — CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

def handle_admin_get_categories(sid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        cats = rows(db.execute("SELECT * FROM categories ORDER BY name").fetchall())
        # Attach product count
        for c in cats:
            c['product_count'] = db.execute(
                "SELECT COUNT(*) FROM products WHERE category=?", (c['name'],)).fetchone()[0]
        return {'success':True,'categories':cats}, 200
    finally: db.close()

def handle_admin_add_category(sid, body):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    name = (body.get('name') or '').strip()
    desc = (body.get('description') or '').strip()
    cover_image = (body.get('cover_image') or '').strip()
    if not name: return {'success':False,'errors':{'name':'Category name is required'}}, 400
    db = get_db()
    try:
        if db.execute("SELECT id FROM categories WHERE name=?", (name,)).fetchone():
            return {'success':False,'errors':{'name':'Category already exists'}}, 409
        cur = db.execute("INSERT INTO categories (name,description,cover_image) VALUES (?,?,?)", (name, desc, cover_image))
        db.commit()
        return {'success':True,'id':cur.lastrowid,'message':'Category added'}, 200
    finally: db.close()

def handle_admin_update_category(sid, cid, body):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
        if not existing: return {'success':False,'error':'Not found'}, 404
        old_name = existing['name']
        name = (body.get('name') or old_name).strip()
        desc = (body.get('description') or existing['description']).strip()
        cover_image = (body.get('cover_image') or (existing['cover_image'] if 'cover_image' in existing.keys() else '')).strip()
        if name != old_name and db.execute("SELECT id FROM categories WHERE name=? AND id!=?", (name,cid)).fetchone():
            return {'success':False,'errors':{'name':'Name already taken'}}, 409
        db.execute("UPDATE categories SET name=?,description=?,cover_image=? WHERE id=?", (name, desc, cover_image, cid))
        if name != old_name:
            db.execute("UPDATE products SET category=? WHERE category=?", (name, old_name))
        db.commit()
        return {'success':True,'message':'Category updated'}, 200
    finally: db.close()

def handle_admin_delete_category(sid, cid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
        if not existing: return {'success':False,'error':'Not found'}, 404
        count = db.execute("SELECT COUNT(*) FROM products WHERE category=?", (existing['name'],)).fetchone()[0]
        if count > 0:
            return {'success':False,'error':f'Cannot delete: {count} product(s) use this category. Reassign them first.'}, 400
        db.execute("DELETE FROM categories WHERE id=?", (cid,))
        db.commit()
        return {'success':True,'message':'Category deleted'}, 200
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN — PRODUCTS
# ═══════════════════════════════════════════════════════════════════════════════

def handle_admin_get_products(sid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        ps = product_rows(db.execute("SELECT * FROM products ORDER BY id DESC").fetchall())
        return {'success':True,'products':ps}, 200
    finally: db.close()

def handle_admin_add_product(sid, body):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    name  = (body.get('name') or '').strip()
    price = body.get('price')
    cat   = (body.get('category') or '').strip()
    desc  = (body.get('description') or '').strip()
    stock = int(body.get('stock', 100))
    badge = (body.get('badge') or '').strip()
    image = (body.get('image') or '').strip()
    offer_label = (body.get('offer_label') or '').strip()
    try:
        discount_percent = int(body.get('discount_percent') or 0)
    except:
        discount_percent = -1

    errs = {}
    if not name:   errs['name']     = 'Required'
    if not price:  errs['price']    = 'Required'
    if not cat:    errs['category'] = 'Required'
    try:
        if float(price) < 0: errs['price'] = 'Must be positive'
    except: errs['price'] = 'Must be a number'
    if discount_percent < 0 or discount_percent > 95:
        errs['discount_percent'] = 'Use 0 to 95'
    if errs: return {'success':False,'errors':errs}, 400

    db = get_db()
    try:
        cur = db.execute("""INSERT INTO products
            (name,description,price,category,image,stock,rating,reviews,badge,offer_label,discount_percent)
            VALUES (?,?,?,?,?,?,4.0,0,?,?,?)""",
            (name, desc, float(price), cat, image, stock, badge, offer_label, discount_percent))
        db.commit()
        return {'success':True,'product_id':cur.lastrowid,'message':'Product added'}, 200
    finally: db.close()

def handle_admin_update_product(sid, pid, body):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        ex = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if not ex: return {'success':False,'error':'Not found'}, 404
        name  = (body.get('name')  or ex['name']).strip()
        price = body.get('price',  ex['price'])
        cat   = (body.get('category') or ex['category']).strip()
        desc  = (body.get('description') or ex['description'] or '').strip()
        stock = int(body.get('stock', ex['stock']))
        badge = (body.get('badge') or ex['badge'] or '').strip()
        image = (body.get('image') or ex['image'] or '').strip()
        offer_label = ((body.get('offer_label') if 'offer_label' in body else ex['offer_label']) or '').strip()
        try:
            discount_percent = int(body.get('discount_percent') if 'discount_percent' in body else (ex['discount_percent'] or 0))
        except:
            discount_percent = -1

        errs = {}
        if not name: errs['name'] = 'Required'
        if not cat:  errs['category'] = 'Required'
        try:
            if float(price) < 0: errs['price'] = 'Must be positive'
        except: errs['price'] = 'Must be a number'
        if discount_percent < 0 or discount_percent > 95:
            errs['discount_percent'] = 'Use 0 to 95'
        if errs: return {'success':False,'errors':errs}, 400

        db.execute("""UPDATE products SET
            name=?,description=?,price=?,category=?,image=?,stock=?,badge=?,offer_label=?,discount_percent=?
            WHERE id=?""", (name, desc, float(price), cat, image, stock, badge, offer_label, discount_percent, pid))
        db.commit()
        return {'success':True,'message':'Product updated'}, 200
    finally: db.close()

def handle_admin_delete_product(sid, pid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        if not db.execute("SELECT id FROM products WHERE id=?", (pid,)).fetchone():
            return {'success':False,'error':'Not found'}, 404
        db.execute("DELETE FROM products WHERE id=?", (pid,))
        db.commit()
        return {'success':True,'message':'Product deleted'}, 200
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN — ORDERS
# ═══════════════════════════════════════════════════════════════════════════════

def handle_admin_get_orders(sid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        rs = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
        result = []
        for r in rs:
            o = dict(r); o['items'] = json.loads(o['items']); result.append(o)
        return {'success':True,'orders':result}, 200
    finally: db.close()

def handle_admin_get_order(sid, oid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        r = db.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if not r: return {'success':False,'error':'Not found'}, 404
        o = dict(r); o['items'] = json.loads(o['items'])
        return {'success':True,'order':o}, 200
    finally: db.close()

def handle_admin_update_order_status(sid, oid, body):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    status = (body.get('status') or '').strip()
    allowed = ['Pending','Shipped','Delivered','Cancelled']
    if status not in allowed:
        return {'success':False,'error':f'Status must be one of: {", ".join(allowed)}'}, 400
    db = get_db()
    try:
        if not db.execute("SELECT id FROM orders WHERE id=?", (oid,)).fetchone():
            return {'success':False,'error':'Not found'}, 404
        db.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
        db.commit()
        return {'success':True,'message':f'Order #{oid} → {status}'}, 200
    finally: db.close()

def handle_admin_delete_order(sid, oid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        if not db.execute("SELECT id FROM orders WHERE id=?", (oid,)).fetchone():
            return {'success':False,'error':'Not found'}, 404
        db.execute("DELETE FROM orders WHERE id=?", (oid,))
        db.commit()
        return {'success':True,'message':f'Order #{oid} deleted'}, 200
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN — USERS
# ═══════════════════════════════════════════════════════════════════════════════

def handle_admin_get_users(sid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        us = rows(db.execute(
            "SELECT id,name,email,is_admin,created_at FROM users ORDER BY created_at DESC"
        ).fetchall())
        for u in us:
            u['order_count'] = db.execute(
                "SELECT COUNT(*) FROM orders WHERE user_id=?", (u['id'],)).fetchone()[0]
        return {'success':True,'users':us}, 200
    finally: db.close()

def handle_admin_delete_user(sid, uid):
    if not require_admin(sid): return {'success':False,'error':'Unauthorized'}, 403
    db = get_db()
    try:
        u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not u: return {'success':False,'error':'Not found'}, 404
        if u['is_admin']: return {'success':False,'error':'Cannot delete admin account'}, 400
        db.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        db.execute("DELETE FROM wishlist  WHERE user_id=?", (uid,))
        db.execute("DELETE FROM users     WHERE id=?",      (uid,))
        db.commit()
        return {'success':True,'message':f'User #{uid} deleted'}, 200
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  USER — DELETE ACCOUNT
# ═══════════════════════════════════════════════════════════════════════════════

def handle_delete_account(sid, body):
    u = get_user_by_session(sid)
    if not u: return {'success':False,'error':'Not authenticated'}, 401
    if u.get('is_admin'): return {'success':False,'error':'Cannot delete admin account'}, 400

    password = (body.get('password') or '')
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id=?", (u['id'],)).fetchone()
        if not user or user['password_hash'] != hash_pw(password):
            return {'success':False,'error':'Incorrect password. Account not deleted.'}, 401
        db.execute("DELETE FROM sessions WHERE user_id=?", (u['id'],))
        db.execute("DELETE FROM wishlist  WHERE user_id=?", (u['id'],))
        db.execute("DELETE FROM users     WHERE id=?",      (u['id'],))
        db.commit()
        return {'success':True,'message':'Account deleted successfully'}, 200
    finally: db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  FORGOT PASSWORD (file-based token simulation)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_forgot_password(body):
    email = (body.get('email') or '').strip().lower()
    if not valid_email(email):
        return {'success':False,'errors':{'email':'Enter a valid email'}}, 400
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        # Always return success to prevent email enumeration
        if not user:
            return {'success':True,'message':'If that email exists, a reset link has been sent.'}, 200
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO password_resets (email,token) VALUES (?,?)", (email, token))
        db.commit()
        # In a real app this would send an email — for lab we return the token directly
        return {
            'success': True,
            'message': 'Reset token generated (lab simulation — no email sent).',
            'reset_token': token,   # Only returned for lab/demo purposes
            'reset_url': f'http://localhost:8080/reset-password.html?token={token}'
        }, 200
    finally: db.close()

def handle_reset_password(body):
    token    = (body.get('token') or '').strip()
    password = (body.get('password') or '')
    confirm  = (body.get('confirm') or '')

    if not token: return {'success':False,'error':'Token is required'}, 400
    if len(password) < 6:
        return {'success':False,'errors':{'password':'Minimum 6 characters'}}, 400
    if password != confirm:
        return {'success':False,'errors':{'confirm':'Passwords do not match'}}, 400

    db = get_db()
    try:
        reset = db.execute(
            "SELECT * FROM password_resets WHERE token=? AND used=0", (token,)
        ).fetchone()
        if not reset:
            return {'success':False,'error':'Invalid or expired reset token'}, 400

        user = db.execute("SELECT * FROM users WHERE email=?", (reset['email'],)).fetchone()
        if not user:
            return {'success':False,'error':'User not found'}, 404

        db.execute("UPDATE users SET password_hash=? WHERE email=?",
                   (hash_pw(password), reset['email']))
        db.execute("UPDATE password_resets SET used=1 WHERE token=?", (token,))
        db.execute("DELETE FROM sessions WHERE user_id=?", (user['id'],))
        db.commit()
        return {'success':True,'message':'Password reset successfully. Please log in.'}, 200
    finally: db.close()

def handle_verify_reset_token(token):
    db = get_db()
    try:
        r = db.execute(
            "SELECT email FROM password_resets WHERE token=? AND used=0", (token,)
        ).fetchone()
        if not r: return {'valid':False,'error':'Invalid or expired token'}, 400
        return {'valid':True,'email':r['email']}, 200
    finally: db.close()
