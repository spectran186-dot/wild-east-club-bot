import asyncpg
from datetime import datetime

from config import config


class Database:
    def __init__(self):
        if not config.database_url:
            raise RuntimeError("DATABASE_URL is not configured")

    async def _connect(self):
        return await asyncpg.connect(config.database_url)

    async def create_tables(self):
        connection = await self._connect()
        try:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE,
                    first_name TEXT,
                    username TEXT,
                    phone TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS admins (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE,
                    role TEXT
                );

                CREATE TABLE IF NOT EXISTS routes (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    start_point TEXT,
                    finish_point TEXT,
                    description TEXT,
                    duration TEXT,
                    default_price INTEGER,
                    status TEXT DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS events (
                    id BIGSERIAL PRIMARY KEY,
                    route_id BIGINT,
                    event_date TEXT,
                    event_time TEXT,
                    price INTEGER,
                    max_places INTEGER DEFAULT 30,
                    free_places INTEGER DEFAULT 10,
                    meeting_point TEXT,
                    status TEXT DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS bookings (
                    id BIGSERIAL PRIMARY KEY,
                    event_id BIGINT,
                    telegram_id BIGINT,
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

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_events_status_date
                    ON events (status, event_date, event_time);

                CREATE INDEX IF NOT EXISTS idx_bookings_event_id
                    ON bookings (event_id);
            """)
        finally:
            await connection.close()

    async def add_user(self, telegram_id, first_name, username):
        connection = await self._connect()
        try:
            await connection.execute(
                """
                INSERT INTO users (telegram_id, first_name, username, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (telegram_id) DO NOTHING
                """,
                telegram_id,
                first_name,
                username,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        finally:
            await connection.close()

    async def get_routes(self):
        connection = await self._connect()
        try:
            rows = await connection.fetch(
                """
                SELECT id, title, start_point, finish_point, default_price
                FROM routes
                WHERE status = 'active'
                ORDER BY id
                """
            )
            return [tuple(row) for row in rows]
        finally:
            await connection.close()

    async def add_event(self, route_id, event_date, event_time, price, meeting_point):
        connection = await self._connect()
        try:
            event_id = await connection.fetchval(
                """
                INSERT INTO events
                    (route_id, event_date, event_time, price, max_places, free_places, meeting_point)
                VALUES ($1, $2, $3, $4, 30, 30, $5)
                RETURNING id
                """,
                route_id,
                event_date,
                event_time,
                price,
                meeting_point,
            )
            return event_id
        finally:
            await connection.close()

    async def get_events(self):
        connection = await self._connect()
        try:
            rows = await connection.fetch(
                """
                SELECT
                    events.id,
                    events.route_id,
                    events.event_date,
                    events.event_time,
                    events.price,
                    routes.title,
                    routes.start_point,
                    routes.finish_point,
                    events.meeting_point
                FROM events
                LEFT JOIN routes ON routes.id = events.route_id
                WHERE events.status = 'active'
                ORDER BY events.event_date, events.event_time
                """
            )
            return [tuple(row) for row in rows]
        finally:
            await connection.close()

    async def update_event(self, event_id, route_id, event_date, event_time, price, meeting_point):
        connection = await self._connect()
        try:
            await connection.execute(
                """
                UPDATE events
                SET route_id = $1,
                    event_date = $2,
                    event_time = $3,
                    price = $4,
                    meeting_point = $5
                WHERE id = $6
                """,
                route_id,
                event_date,
                event_time,
                price,
                meeting_point,
                event_id,
            )
        finally:
            await connection.close()

    async def delete_event(self, event_id):
        connection = await self._connect()
        try:
            await connection.execute(
                "UPDATE events SET status = 'deleted' WHERE id = $1",
                event_id,
            )
        finally:
            await connection.close()

    async def has_booking(self, event_id, full_name, phone):
        def normalize_phone(value):
            digits = "".join(ch for ch in str(value or "") if ch.isdigit())
            if digits.startswith("8") and len(digits) == 11:
                digits = "7" + digits[1:]
            elif len(digits) == 10:
                digits = "7" + digits
            elif not (digits.startswith("7") and len(digits) == 11):
                return None
            return digits

        target_phone = normalize_phone(phone)
        if not target_phone:
            return False

        connection = await self._connect()
        try:
            rows = await connection.fetch(
                """
                SELECT full_name, phone
                FROM bookings
                WHERE event_id = $1
                  AND LOWER(TRIM(full_name)) = LOWER(TRIM($2))
                  AND status NOT IN ('cancelled', 'canceled')
                """,
                event_id,
                full_name,
            )
            return any(normalize_phone(row["phone"]) == target_phone for row in rows)
        finally:
            await connection.close()

    async def add_booking(
        self,
        telegram_id,
        event_id,
        full_name,
        phone,
        children=0,
        comment="",
        status="new",
    ):
        def normalize_phone(value):
            digits = "".join(ch for ch in str(value or "") if ch.isdigit())
            if digits.startswith("8") and len(digits) == 11:
                digits = "7" + digits[1:]
            elif len(digits) == 10:
                digits = "7" + digits
            elif not (digits.startswith("7") and len(digits) == 11):
                return None
            return f"+{digits}"

        phone = normalize_phone(phone) or phone

        connection = await self._connect()
        try:
            await connection.execute(
                """
                INSERT INTO bookings
                    (telegram_id, event_id, full_name, phone, children, comment, status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                telegram_id,
                event_id,
                full_name,
                phone,
                children,
                comment,
                status,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
        finally:
            await connection.close()

    async def get_event_full(self, event_id):
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                """
                SELECT
                    events.id,
                    events.route_id,
                    events.event_date,
                    events.event_time,
                    events.price,
                    routes.title,
                    routes.start_point,
                    routes.finish_point,
                    events.meeting_point
                FROM events
                LEFT JOIN routes ON routes.id = events.route_id
                WHERE events.id = $1
                  AND events.status = 'active'
                """,
                event_id,
            )
            return tuple(row) if row else None
        finally:
            await connection.close()

    async def get_event(self, event_id):
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "SELECT id, event_date, event_time, price FROM events WHERE id = $1",
                event_id,
            )
            return tuple(row) if row else None
        finally:
            await connection.close()

    async def get_event_info(self, event_id):
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                """
                SELECT
                    events.id,
                    events.event_date,
                    events.event_time,
                    events.price,
                    routes.title,
                    routes.start_point,
                    routes.finish_point,
                    events.meeting_point
                FROM events
                LEFT JOIN routes ON routes.id = events.route_id
                WHERE events.id = $1
                """,
                event_id,
            )
            return tuple(row) if row else None
        finally:
            await connection.close()

    async def get_bookings(self):
        connection = await self._connect()
        try:
            rows = await connection.fetch(
                """
                SELECT
                    bookings.id,
                    bookings.event_id,
                    bookings.telegram_id,
                    bookings.full_name,
                    bookings.phone,
                    bookings.created_at,
                    events.event_date,
                    events.event_time,
                    routes.title,
                    bookings.children,
                    bookings.comment,
                    bookings.status,
                    events.max_places
                FROM bookings
                LEFT JOIN events ON events.id = bookings.event_id
                LEFT JOIN routes ON routes.id = events.route_id
                ORDER BY bookings.id DESC
                """
            )
            return [tuple(row) for row in rows]
        finally:
            await connection.close()

    async def update_booking_status(self, booking_id, status):
        connection = await self._connect()
        try:
            await connection.execute(
                "UPDATE bookings SET status = $1 WHERE id = $2",
                status,
                booking_id,
            )
        finally:
            await connection.close()

    async def delete_booking(self, booking_id):
        connection = await self._connect()
        try:
            await connection.execute(
                "DELETE FROM bookings WHERE id = $1",
                booking_id,
            )
        finally:
            await connection.close()

    async def get_event_booking_stats(self, event_id):
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE bookings.status NOT IN ('cancelled', 'canceled')
                    ),
                    COALESCE(MAX(events.max_places), 10)
                FROM bookings
                LEFT JOIN events ON events.id = bookings.event_id
                WHERE bookings.event_id = $1
                """,
                event_id,
            )
            return row[0], row[1]
        finally:
            await connection.close()
