import asyncio
from dataclasses import dataclass

from database.db import Database
from verifier.http_proxy import check_http_proxy


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

        # لا نفتح آلاف الاتصالات دفعة واحدة.
        semaphore = asyncio.Semaphore(50)

        async def worker(row):

            proxy = row["proxy"]

            async with semaphore:

                alive, latency = (
                    await check_http_proxy(proxy)
                )

                return (
                    proxy,
                    alive,
                    latency
                )

        results = await asyncio.gather(
            *[
                worker(row)
                for row in rows
            ],
            return_exceptions=True
        )

        alive_count = 0
        latencies = []

        for result in results:

            if isinstance(result, Exception):
                continue

            proxy, alive, latency = result

            self.db.update_check(
                proxy,
                alive,
                latency
            )

            if alive:
                alive_count += 1

                if latency > 0:
                    latencies.append(latency)

        average = (
            sum(latencies) / len(latencies)
            if latencies
            else 0
        )

        return ScanResult(
            total=len(rows),
            alive=alive_count,
            dead=len(rows) - alive_count,
            avg_latency=average
        )
