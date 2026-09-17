import sqlite3
from datetime import datetime
from pathlib import Path
from config import config


class Database:

    def __init__(self):

        Path("data").mkdir(exist_ok=True)

        self.connection = sqlite3.connect(config.database_name)

        self.cursor = self.connection.cursor()

    def create_tables(self):
        

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            first_name TEXT,
            username TEXT,
            phone TEXT,
            created_at TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            role TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_point TEXT,
            finish_point TEXT,
            description TEXT,
            duration TEXT,
            default_price INTEGER,
            status TEXT DEFAULT 'active'
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER,
            event_date TEXT,
            event_time TEXT,
            price INTEGER,
            max_places INTEGER DEFAULT 10,
            free_places INTEGER DEFAULT 10,
            meeting_point TEXT,
            status TEXT DEFAULT 'active'
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            telegram_id INTEGER,
            full_name TEXT,
            phone TEXT,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            own_sup INTEGER DEFAULT 0,
            source TEXT,
            status TEXT DEFAULT 'new',
            comment TEXT,
            created_at TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        self.connection.commit()

    def add_user(self, telegram_id, first_name, username):

        self.cursor.execute(
             "SELECT id FROM users WHERE telegram_id = ?",
             (telegram_id,)
        )

        if self.cursor.fetchone():
            return

        self.cursor.execute(
        """
        INSERT INTO users
        (
            telegram_id,
            first_name,
            username,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            telegram_id,
            first_name,
            username,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

        self.connection.commit()

    def get_events(self):
        self.cursor.execute("""
            SELECT id, route_id, event_date, event_time, price
            FROM events
            WHERE status = ?
            ORDER BY event_date, event_time
        """, ("active",))

        return self.cursor.fetchall()

    def add_booking(self, telegram_id, event_id, full_name, phone):
        self.cursor.execute("""
            INSERT INTO bookings
            (
                telegram_id,
                event_id,
                full_name,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            telegram_id,
            event_id,
            full_name,
            phone,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        self.connection.commit()

    def get_event(self, event_id):
        self.cursor.execute("""
            SELECT id,event_date,event_time,price
            FROM events
            WHERE id=?
        """, (event_id,))
        return self.cursor.fetchone()

    def create_demo_routes(self):

        self.cursor.execute("SELECT COUNT(*) FROM routes")

        if self.cursor.fetchone()[0] > 0:
            return

        routes = [
            (
            "Переяславка → Гродеково",
            "Переяславка",
            "Гродеково",
            "Самый популярный маршрут",
            "3 часа",
            2500
            ),
            (
            "Гродеково → Могилёвка",
            "Гродеково",
            "Могилёвка",
            "Длинный маршрут",
            "4 часа",
            2500
            ),
            (
            "Амуркабель → Ерофей",
            "Амуркабель",
            "Арена Ерофей",
            "Закатный маршрут",
            "2 часа",
            1500
            )
        ]

        self.cursor.executemany("""
            INSERT INTO routes
            (
            title,
            start_point,
            finish_point,
            description,
            duration,
            default_price
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, routes)

        self.connection.commit()

    def create_demo_events(self):

        self.cursor.execute("SELECT COUNT(*) FROM events")

        if self.cursor.fetchone()[0] > 0:
            return

        self.cursor.execute("""
            INSERT INTO events
            (
                route_id,
                event_date,
                event_time,
                price,
                max_places,
                free_places,
                meeting_point
            )
            VALUES
            (
                1,
                '2026-08-30',
                '10:00-13:00',
                2500,
                10,
                10,
                'Переяславка'
            )
        """)

        self.connection.commit()

    def add_booking(self, telegram_id, event_id, full_name, phone):
        self.cursor.execute("""
            INSERT INTO bookings
            (
                telegram_id,
                event_id,
                full_name,
                phone,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            telegram_id,
            event_id,
            full_name,
            phone,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        self.connection.commit()

    def get_event_info(self, event_id):
        self.cursor.execute("""
            SELECT
                events.id,
                events.event_date,
                events.event_time,
                events.price,
                routes.title,
                routes.start_point,
                routes.finish_point
            FROM events
            LEFT JOIN routes ON routes.id = events.route_id
            WHERE events.id = ?
        """, (event_id,))

        return self.cursor.fetchone()

    def get_bookings(self):
        self.cursor.execute("""
            SELECT
                bookings.id,
                bookings.full_name,
                bookings.phone,
                bookings.created_at,
                events.event_date,
                events.event_time,
                routes.title
            FROM bookings
            LEFT JOIN events
                ON events.id = bookings.event_id
            LEFT JOIN routes
                ON routes.id = events.route_id
            ORDER BY bookings.id DESC
        """)
        return self.cursor.fetchall()

    def get_events(self):
        self.cursor.execute("""
            SELECT
                id,
                route_id,
                event_date,
                event_time,
                price
            FROM events
            WHERE status = 'active'
            ORDER BY event_date, event_time
        """)

        return self.cursor.fetchall()