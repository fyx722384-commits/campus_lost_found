import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "campus_lost_found.db")


class DatabaseManager:
    """SQLite 数据库管理类，封装连接、建表和常用 SQL 操作。"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, sql, params=()):
        with self.get_connection() as conn:
            conn.execute(sql, params)
            conn.commit()

    def insert(self, sql, params=()):
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid

    def query(self, sql, params=()):
        with self.get_connection() as conn:
            return conn.execute(sql, params).fetchall()

    def query_one(self, sql, params=()):
        with self.get_connection() as conn:
            return conn.execute(sql, params).fetchone()

    def init_db(self):
        with self.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    phone TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    location TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    description TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    image_path TEXT,
                    status TEXT NOT NULL DEFAULT '待认领',
                    created_at TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    applicant_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT '待审核',
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    FOREIGN KEY (item_id) REFERENCES items(id),
                    FOREIGN KEY (applicant_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS priority_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    fee_amount REAL NOT NULL DEFAULT 0,
                    pay_status TEXT NOT NULL DEFAULT '未支付',
                    status TEXT NOT NULL DEFAULT '待审核',
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    expire_at TEXT,
                    FOREIGN KEY (item_id) REFERENCES items(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    related_type TEXT,
                    related_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS support_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    content TEXT NOT NULL,
                    reply TEXT,
                    status TEXT NOT NULL DEFAULT '待回复',
                    created_at TEXT NOT NULL,
                    replied_at TEXT,
                    admin_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (admin_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                """
            )
            conn.commit()

    def log(self, user_id, action, target_type, target_id=None):
        self.insert(
            """
            INSERT INTO operation_logs (user_id, action, target_type, target_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, action, target_type, target_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


db = DatabaseManager()
