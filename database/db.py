import csv
import os
import sqlite3


class Database:

    def __init__(self, path):

        self.path = path

        parent = os.path.dirname(path)

        if parent:
            os.makedirs(
                parent,
                exist_ok=True
            )

    def connection(self):
        conn = sqlite3.connect(
            self.path
        )

        conn.row_factory = sqlite3.Row

        return conn

    def init(self):

        with self.connection() as conn:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS proxies (
                    proxy TEXT PRIMARY KEY,
                    protocol TEXT,
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

    def add_many(self, proxies):

        if not proxies:
            return

        with self.connection() as conn:

            conn.executemany(
                """
                INSERT INTO proxies(proxy)
                VALUES(?)
                ON CONFLICT(proxy)
                DO UPDATE SET
                    last_seen=CURRENT_TIMESTAMP
                """,
                [
                    (proxy,)
                    for proxy in proxies
                ]
            )

    def update_check(
        self,
        proxy,
        alive,
        latency
    ):

        with self.connection() as conn:

            conn.execute(
                """
                UPDATE proxies
                SET
                    alive=?,
                    latency=?,
                    last_checked=CURRENT_TIMESTAMP
                WHERE proxy=?
                """,
                (
                    int(alive),
                    latency,
                    proxy
                )
            )

    def count(self):

        with self.connection() as conn:

            return conn.execute(
                "SELECT COUNT(*) FROM proxies"
            ).fetchone()[0]

    def all_proxies(self):

        with self.connection() as conn:

            return conn.execute(
                """
                SELECT *
                FROM proxies
                ORDER BY last_seen DESC
                """
            ).fetchall()

    def page(
        self,
        offset,
        limit
    ):

        with self.connection() as conn:

            return conn.execute(
                """
                SELECT *
                FROM proxies
                ORDER BY alive DESC, latency ASC
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
                "SELECT COUNT(*) FROM proxies"
            ).fetchone()[0]

            alive = conn.execute(
                """
                SELECT COUNT(*)
                FROM proxies
                WHERE alive=1
                """
            ).fetchone()[0]

            dead = total - alive

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

    def sources(self):

        with self.connection() as conn:

            return [
                row[0]
                for row in conn.execute(
                    "SELECT url FROM sources"
                )
            ]

    def load_sources_from_env(self):

        raw = os.getenv(
            "PROXY_SOURCE_URLS",
            ""
        )

        urls = [
            x.strip()
            for x in raw.splitlines()
            if x.strip()
        ]

        with self.connection() as conn:

            conn.executemany(
                """
                INSERT OR IGNORE INTO sources(url)
                VALUES(?)
                """,
                [
                    (url,)
                    for url in urls
                ]
            )

    def clear(self):

        with self.connection() as conn:

            conn.execute(
                "DELETE FROM proxies"
            )

    def export_txt(self, path):

        rows = self.all_proxies()

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            for row in rows:

                file.write(
                    row["proxy"] + "\n"
                )

        return path

    def export_csv(self, path):

        rows = self.all_proxies()

        with open(
            path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "proxy",
                    "protocol",
                    "alive",
                    "latency",
                    "first_seen",
                    "last_seen",
                    "last_checked"
                ]
            )

            for row in rows:

                writer.writerow(
                    [
                        row["proxy"],
                        row["protocol"],
                        row["alive"],
                        row["latency"],
                        row["first_seen"],
                        row["last_seen"],
                        row["last_checked"]
                    ]
                )

        return path
