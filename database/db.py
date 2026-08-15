import os
import sqlite3


class Database:

    def __init__(
        self,
        path: str
    ):

        self.path = path

        parent = os.path.dirname(
            path
        )

        if parent:

            os.makedirs(
                parent,
                exist_ok=True
            )

    def connection(self):

        conn = sqlite3.connect(
            self.path,
            timeout=30
        )

        conn.row_factory = sqlite3.Row

        return conn

    def init(self):

        with self.connection() as conn:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS proxies (
                    proxy TEXT PRIMARY KEY,
                    protocol TEXT DEFAULT 'unknown',
                    alive INTEGER DEFAULT 0,
                    latency INTEGER DEFAULT 0,
                    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_checked TEXT
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    url TEXT PRIMARY KEY
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_proxies_alive
                ON proxies(alive)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_proxies_protocol
                ON proxies(protocol)
                """
            )

    def sources(self):

        with self.connection() as conn:

            rows = conn.execute(
                """
                SELECT url
                FROM sources
                ORDER BY rowid ASC
                """
            ).fetchall()

        return [
            row["url"]
            for row in rows
        ]

    def count(self):

        with self.connection() as conn:

            return conn.execute(
                """
                SELECT COUNT(*)
                FROM proxies
                """
            ).fetchone()[0]

    def add_many(
        self,
        items
    ):

        if not items:
            return

        with self.connection() as conn:

            for proxy, protocol in items:

                existing = conn.execute(
                    """
                    SELECT protocol
                    FROM proxies
                    WHERE proxy=?
                    """,
                    (proxy,)
                ).fetchone()

                if existing is None:

                    conn.execute(
                        """
                        INSERT INTO proxies(
                            proxy,
                            protocol,
                            last_seen
                        )
                        VALUES(
                            ?,
                            ?,
                            CURRENT_TIMESTAMP
                        )
                        """,
                        (
                            proxy,
                            protocol
                        )
                    )

                else:

                    old_protocol = (
                        existing["protocol"]
                        or "unknown"
                    )

                    new_protocol = protocol

                    if (
                        old_protocol == "unknown"
                        and new_protocol != "unknown"
                    ):
                        final_protocol = new_protocol
                    else:
                        final_protocol = old_protocol

                    conn.execute(
                        """
                        UPDATE proxies
                        SET
                            protocol=?,
                            last_seen=CURRENT_TIMESTAMP
                        WHERE proxy=?
                        """,
                        (
                            final_protocol,
                            proxy
                        )
                    )

    def update_check(
        self,
        proxy: str,
        alive: bool,
        latency: int,
        protocol: str
    ):

        with self.connection() as conn:

            conn.execute(
                """
                UPDATE proxies

                SET
                    alive=?,
                    latency=?,
                    protocol=?,
                    last_checked=CURRENT_TIMESTAMP

                WHERE proxy=?
                """,
                (
                    int(alive),
                    int(latency),
                    protocol,
                    proxy
                )
            )

    def all_proxies(self):

        with self.connection() as conn:

            return conn.execute(
                """
                SELECT *
                FROM proxies
                ORDER BY alive DESC, latency ASC
                """
            ).fetchall()

    def page(
        self,
        offset: int,
        limit: int
    ):

        with self.connection() as conn:

            return conn.execute(
                """
                SELECT *
                FROM proxies

                ORDER BY
                    alive DESC,
                    CASE
                        WHEN latency <= 0 THEN 999999
                        ELSE latency
                    END ASC,
                    last_seen DESC

                LIMIT ? OFFSET ?
                """,
                (
                    limit,
                    offset
                )
            ).fetchall()

    def stats(self):

        with self.connection() as conn:

            total = conn.execute(
                """
                SELECT COUNT(*)
                FROM proxies
                """
            ).fetchone()[0]

            alive = conn.execute(
                """
                SELECT COUNT(*)
                FROM proxies
                WHERE alive=1
                """
            ).fetchone()[0]

            dead = (
                total - alive
            )

            filtered = conn.execute(
                """
                SELECT COUNT(*)
                FROM proxies
                WHERE proxy LIKE '34.%'
                """
            ).fetchone()[0]

            last_update = conn.execute(
                """
                SELECT MAX(last_seen)
                FROM proxies
                """
            ).fetchone()[0]

        return {
            "total": total,
            "alive": alive,
            "dead": dead,
            "filtered": filtered,
            "last_update": last_update
        }

    def clear(self):

        with self.connection() as conn:

            conn.execute(
                "DELETE FROM proxies"
            )

    def export_txt(
        self,
        path: str
    ):

        rows = self.all_proxies()

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            for row in rows:

                if row["alive"]:

                    file.write(
                        row["proxy"]
                        + "\n"
                    )

        return path
