import sqlite3

DB_NAME = "homebites.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone_number INTEGER UNIQUE NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    address TEXT,
    city TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    price INTEGER NOT NULL,
    weight TEXT NOT NULL,
    photos TEXT,
    videos TEXT,
    description TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,

    order_status TEXT NOT NULL CHECK(order_status IN ('pending','confirmed','delivered','cancelled')),
    payment_status TEXT NOT NULL CHECK(payment_status IN ('pending','paid','failed')),
    payment_mode TEXT NOT NULL CHECK(payment_mode IN ('cash','upi','card')),

    order_date TEXT NOT NULL,
    delivery_date TEXT,
    address TEXT NOT NULL,
    city TEXT NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS order_details (
    order_detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,

    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price INTEGER NOT NULL CHECK (price >= 0),

    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
)
""")


    cursor.close()
    conn.commit()
    conn.close()

def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()