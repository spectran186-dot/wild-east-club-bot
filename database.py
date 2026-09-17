import aiosqlite
from datetime import datetime
from pathlib import Path

from config import config


class Database:
    def __init__(self):
        Path(config.database_name).parent.mkdir(parents=True, exist_ok=True)

    async def _connect(self):
        # Не меняем journal_mode при каждом запросе: PRAGMA journal_mode=WAL
        # может ждать блокировку файла БД и создавать фризы в Telegram-обработчиках.
        connection = await aiosqlite.connect(config.database_name, timeout=10)
        await connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    async def create_tables(self):
        connection = await self._connect()
        try:
            # WAL включаем один раз при инициализации БД, а не перед каждым запросом.
            await connection.execute("PRAGMA journal_mode = WAL")
            await connection.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                first_name TEXT,
                username TEXT,
                phone TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                role TEXT
            );

            CREATE TABLE IF NOT EXISTS routes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_point TEXT,
                finish_point TEXT,
                description TEXT,
                duration TEXT,
                default_price INTEGER,
                status TEXT DEFAULT 'active'
            );

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
            );

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
            );

            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """)
            await connection.commit()
        finally:
            await connection.close()

    async def add_user(self, telegram_id, first_name, username):
        connection = await self._connect()
        try:
            await connection.execute(
                """
                INSERT OR IGNORE INTO users
                (telegram_id, first_name, username, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    first_name,
                    username,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            await connection.commit()
        finally:
            await connection.close()

    async def get_events(self):
        connection = await self._connect()
        try:
            cursor = await connection.execute(
                """
                SELECT
                    events.id,
                    events.route_id,
                    events.event_date,
                    events.event_time,
                    events.price,
                    routes.title,
                    routes.start_point,
                    routes.finish_point
                FROM events
                LEFT JOIN routes ON routes.id = events.route_id
                WHERE events.status = 'active'
                ORDER BY events.event_date, events.event_time
                """
            )
            return await cursor.fetchall()
        finally:
            await connection.close()

    async def add_booking(self, telegram_id, event_id, full_name, phone):
        connection = await self._connect()
        try:
            await connection.execute(
                """
                INSERT INTO bookings
                (telegram_id, event_id, full_name, phone, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    event_id,
                    full_name,
                    phone,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                ),
            )
            await connection.commit()
        finally:
            await connection.close()

    async def get_event(self, event_id):
        connection = await self._connect()
        try:
            cursor = await connection.execute(
                """
                SELECT id, event_date, event_time, price
                FROM events
                WHERE id = ?
                """,
                (event_id,),
            )
            return await cursor.fetchone()
        finally:
            await connection.close()

    async def get_event_info(self, event_id):
        connection = await self._connect()
        try:
            cursor = await connection.execute(
                """
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
                """,
                (event_id,),
            )
            return await cursor.fetchone()
        finally:
            await connection.close()

    async def get_bookings(self):
        connection = await self._connect()
        try:
            cursor = await connection.execute(
                """
                SELECT
                    bookings.id,
                    bookings.full_name,
                    bookings.phone,
                    bookings.created_at,
                    events.event_date,
                    events.event_time,
                    routes.title
                FROM bookings
                LEFT JOIN events ON events.id = bookings.event_id
                LEFT JOIN routes ON routes.id = events.route_id
                ORDER BY bookings.id DESC
                """
            )
            return await cursor.fetchall()
        finally:
            await connection.close()

    async def create_demo_routes(self):
        connection = await self._connect()
        try:
            cursor = await connection.execute("SELECT COUNT(*) FROM routes")
            count = (await cursor.fetchone())[0]
            if count:
                return

            routes = [
                (
                    "Переяславка → Гродеково",
                    "Переяславка",
                    "Гродеково",
                    "Самый популярный маршрут",
                    "3 часа",
                    2500,
                ),
                (
                    "Гродеково → Могилёвка",
                    "Гродеково",
                    "Могилёвка",
                    "Длинный маршрут",
                    "4 часа",
                    2500,
                ),
                (
                    "Амуркабель → Ерофей",
                    "Амуркабель",
                    "Арена Ерофей",
                    "Закатный маршрут",
                    "2 часа",
                    1500,
                ),
            ]

            await connection.executemany(
                """
                INSERT INTO routes
                (title, start_point, finish_point, description, duration, default_price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                routes,
            )
            await connection.commit()
        finally:
            await connection.close()

    async def create_demo_events(self):
        demo_date = "2026-09-20"
        demo_time = "10:00-13:00"
        demo_price = 2500

        connection = await self._connect()
        try:
            cursor = await connection.execute("SELECT COUNT(*) FROM events")
            count = (await cursor.fetchone())[0]

            if count == 0:
                await connection.execute(
                    """
                    INSERT INTO events
                    (route_id, event_date, event_time, price, max_places, free_places, meeting_point)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (1, demo_date, demo_time, demo_price, 10, 10, "Переяславка"),
                )
                await connection.commit()
                return

            cursor = await connection.execute(
                """
                SELECT id
                FROM events
                WHERE route_id = 1
                  AND event_date = '2026-08-30'
                  AND event_time = '10:00-13:00'
                LIMIT 1
                """
            )
            old_demo = await cursor.fetchone()

            if old_demo:
                cursor = await connection.execute(
                    "SELECT COUNT(*) FROM bookings WHERE event_id = ?",
                    (old_demo[0],),
                )
                booking_count = (await cursor.fetchone())[0]

                if booking_count == 0:
                    await connection.execute(
                        """
                        UPDATE events
                        SET event_date = ?,
                            event_time = ?,
                            price = ?,
                            max_places = 10,
                            free_places = 10,
                            meeting_point = 'Переяславка',
                            status = 'active'
                        WHERE id = ?
                        """,
                        (demo_date, demo_time, demo_price, old_demo[0]),
                    )
                    await connection.commit()
                    return

            cursor = await connection.execute(
                """
                SELECT id
                FROM events
                WHERE route_id = 1
                  AND event_date = ?
                  AND event_time = ?
                LIMIT 1
                """,
                (demo_date, demo_time),
            )
            current_demo = await cursor.fetchone()

            if not current_demo:
                await connection.execute(
                    """
                    INSERT INTO events
                    (route_id, event_date, event_time, price, max_places, free_places, meeting_point)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (1, demo_date, demo_time, demo_price, 10, 10, "Переяславка"),
                )
                await connection.commit()
        finally:
            await connection.close()
