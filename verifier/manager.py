import asyncio
import time
from dataclasses import dataclass

from verifier.tcp import check_tcp
from database.db import Database


@dataclass
class ScanResult:
    total: int
    alive: int
    dead: int
    avg_latency: float


class VerifierManager:

    def __init__(self, db: Database):
        self.db = db

    async def scan_all(self):

        rows = self.db.all_proxies()

        if not rows:
            return ScanResult(
                total=0,
                alive=0,
                dead=0,
                avg_latency=0
            )

        semaphore = asyncio.Semaphore(100)

        async def worker(row):

            async with semaphore:

                host, port = row["proxy"].rsplit(
                    ":",
                    1
                )

                start = time.perf_counter()

                alive = await check_tcp(
                    host,
                    int(port)
                )

                latency = (
                    (time.perf_counter() - start)
                    * 1000
                )

                return (
                    row["proxy"],
                    alive,
                    round(latency)
                )

        results = await asyncio.gather(
            *(worker(row) for row in rows)
        )

        alive_count = 0
        latencies = []

        for proxy, alive, latency in results:

            self.db.update_check(
                proxy,
                alive,
                latency
            )

            if alive:
                alive_count += 1
                latencies.append(latency)

        average = (
            sum(latencies) / len(latencies)
            if latencies
            else 0
        )

        return ScanResult(
            total=len(results),
            alive=alive_count,
            dead=len(results) - alive_count,
            avg_latency=average
        )
