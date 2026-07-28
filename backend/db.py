#!/usr/bin/env python3
import sqlite3, os, hashlib, json
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
PRIMARY_DB_PATH = os.path.join(DATA_DIR, 'sajhamart.db')
LEGACY_DB_PATH = os.path.join(DATA_DIR, 'labshop.db')

# Keep existing installs on their current database instead of creating a fresh
# one with a different filename.
DB_PATH = LEGACY_DB_PATH if os.path.exists(LEGACY_DB_PATH) and not os.path.exists(PRIMARY_DB_PATH) else PRIMARY_DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_db(); c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, is_admin INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL, token TEXT NOT NULL UNIQUE,
            used INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL, description TEXT DEFAULT '',
            cover_image TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, description TEXT DEFAULT '',
            price REAL NOT NULL, category TEXT NOT NULL,
            image TEXT DEFAULT '', stock INTEGER DEFAULT 100,
            rating REAL DEFAULT 4.0, reviews INTEGER DEFAULT 0,
            badge TEXT DEFAULT '', offer_label TEXT DEFAULT '',
            discount_percent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, items TEXT NOT NULL, total REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            shipping_name TEXT, shipping_email TEXT, shipping_address TEXT,
            shipping_city TEXT, shipping_zip TEXT, payment_method TEXT DEFAULT 'card',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, product_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL, data TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # Migration: Add cover_image to categories if not exists
    try:
        c.execute("SELECT cover_image FROM categories LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE categories ADD COLUMN cover_image TEXT DEFAULT ''")
        print("[DB] Added cover_image column to categories.")
    # Migration: Add offer/discount fields to products if not exists
    for col, ddl in (
        ("offer_label", "ALTER TABLE products ADD COLUMN offer_label TEXT DEFAULT ''"),
        ("discount_percent", "ALTER TABLE products ADD COLUMN discount_percent INTEGER DEFAULT 0"),
    ):
        try:
            c.execute(f"SELECT {col} FROM products LIMIT 1")
        except sqlite3.OperationalError:
            c.execute(ddl)
            print(f"[DB] Added {col} column to products.")
    # Categories
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT OR IGNORE INTO categories (name,description) VALUES (?,?)", [
            ('Electronics','Gadgets, devices and tech accessories'),
            ('Books','Programming, science and technical books'),
            ('Clothing','Apparel, footwear and accessories'),
            ('Home','Home office and lifestyle products'),
        ])
        print("[DB] Categories seeded.")
    # Products
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        seed_products(c)
    # Admin
    c.execute("SELECT COUNT(*) FROM users WHERE email='admin@sajhamart.com'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (name,email,password_hash,is_admin) VALUES (?,?,?,1)",
                  ('Admin','admin@sajhamart.com', hashlib.sha256(b'admin123').hexdigest()))
        print("[DB] Admin: admin@sajhamart.com / admin123")
    conn.commit(); conn.close()
    print("[DB] Database ready.")

def seed_products(c):
    data = [
        ("Wireless Noise-Cancelling Headphones","Premium over-ear headphones with 30hr battery and active noise cancellation.",149.99,"Electronics","headphones.svg",85,4.8,342,"Best Seller"),
        ("Mechanical Gaming Keyboard","RGB backlit keyboard with Cherry MX switches and aluminium frame.",89.99,"Electronics","keyboard.svg",60,4.6,218,""),
        ("4K Webcam Pro","Ultra HD webcam with autofocus, ring light and dual stereo microphones.",129.99,"Electronics","webcam.svg",45,4.5,176,"New"),
        ("Portable SSD 1TB","USB-C SSD with 1050MB/s read speeds and shock-resistant casing.",109.99,"Electronics","ssd.svg",120,4.9,512,"Top Rated"),
        ("Premium Cotton Hoodie","Ultra-soft heavyweight cotton hoodie with kangaroo pocket.",59.99,"Clothing","hoodie.svg",200,4.7,289,""),
        ("Slim Fit Chinos","Modern stretch-cotton chinos. Wrinkle-resistant, multiple colours.",49.99,"Clothing","chinos.svg",150,4.4,134,""),
        ("Running Sneakers X3","Lightweight performance sneakers with responsive cushioning.",79.99,"Clothing","sneakers.svg",90,4.6,401,"Best Seller"),
        ("Leather Bifold Wallet","Genuine leather slim wallet with RFID blocking and 6 card slots.",34.99,"Clothing","wallet.svg",300,4.5,223,""),
        ("Clean Code: A Handbook","Agile software craftsmanship by Robert C. Martin — essential reading.",39.99,"Books","book1.svg",500,4.9,890,"Classic"),
        ("The Pragmatic Programmer","From journeyman to master. Updated 20th anniversary edition.",44.99,"Books","book2.svg",450,4.8,720,""),
        ("Designing Data-Intensive Apps","Big ideas behind reliable, scalable, maintainable systems.",49.99,"Books","book3.svg",380,4.9,654,"Top Rated"),
        ("Python Crash Course 3rd Ed","Hands-on project-based introduction to Python for all levels.",35.99,"Books","book4.svg",600,4.7,1102,""),
        ("Smart LED Desk Lamp","Touch LED lamp with wireless charging and adjustable colour temp.",69.99,"Home","lamp.svg",75,4.6,298,"New"),
        ("Ergonomic Chair Cushion","Memory foam cushion with coccyx cutout. Reduces back pain.",45.99,"Home","cushion.svg",180,4.5,467,"Best Seller"),
        ("Bamboo Desk Organiser","Eco-friendly bamboo organiser with 5 compartments and phone stand.",29.99,"Home","organizer.svg",250,4.3,189,""),
        ("Pour-Over Coffee Set","Complete set with borosilicate carafe, stainless filter, bamboo stand.",55.99,"Home","coffee.svg",110,4.7,342,""),
    ]
    c.executemany("INSERT INTO products (name,description,price,category,image,stock,rating,reviews,badge) VALUES (?,?,?,?,?,?,?,?,?)", data)
    print(f"[DB] {len(data)} products seeded.")
