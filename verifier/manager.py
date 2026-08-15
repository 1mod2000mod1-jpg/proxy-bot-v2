import asyncio
from dataclasses import dataclass

from database.db import Database
from verifier.http_proxy import check_http_proxy
from verifier.socks_proxy import check_socks_proxy


@dataclass
class ScanResult:

    total: int
    alive: int
    dead: int

    http_alive: int
    socks4_alive: int
    socks5_alive: int

    avg_latency: float


class VerifierManager:

    def __init__(
        self,
        db: Database
    ):

        self.db = db

        self.running = False

    async def scan_one(
        self,
        row
    ):

        proxy = row["proxy"]

        original_protocol = (
            row["protocol"]
            or "unknown"
        )

        # ----------------------------------------------------
        # إذا كان المصدر محدد النوع نجرب نوعه أولاً.
        # إذا كان unknown نجرب الأنواع المختلفة.
        # ----------------------------------------------------

        protocols = []

        if original_protocol in (
            "http",
            "https"
        ):

            protocols = [
                "http"
            ]

        elif original_protocol == "socks4":

            protocols = [
                "socks4"
            ]

        elif original_protocol == "socks5":

            protocols = [
                "socks5"
            ]

        else:

            protocols = [
                "http",
                "socks4",
                "socks5"
            ]

        for protocol in protocols:

            if protocol == "http":

                alive, latency = (
                    await check_http_proxy(
                        proxy
                    )
                )

            elif protocol == "socks4":

                alive, latency = (
                    await check_socks_proxy(
                        proxy,
                        "socks4"
                    )
                )

            else:

                alive, latency = (
                    await check_socks_proxy(
                        proxy,
                        "socks5"
                    )
                )

            if alive:

                self.db.update_check(
                    proxy=proxy,
                    alive=True,
                    latency=latency,
                    protocol=protocol
                )

                return (
                    proxy,
                    True,
                    latency,
                    protocol
                )

        # لم ينجح أي اختبار
        self.db.update_check(
            proxy=proxy,
            alive=False,
            latency=0,
            protocol=original_protocol
            if original_protocol != "unknown"
            else "unknown"
        )

        return (
            proxy,
            False,
            0,
            original_protocol
        )

    async def scan_all(self):

        if self.running:

            raise RuntimeError(
                "A scan is already running."
            )

        self.running = True

        try:

            rows = self.db.all_proxies()

            if not rows:

                return ScanResult(
                    total=0,
                    alive=0,
                    dead=0,
                    http_alive=0,
                    socks4_alive=0,
                    socks5_alive=0,
                    avg_latency=0
                )

            semaphore = asyncio.Semaphore(
                50
            )

            async def worker(row):

                async with semaphore:

                    try:

                        return await self.scan_one(
                            row
                        )

                    except Exception:

                        return (
                            row["proxy"],
                            False,
                            0,
                            row["protocol"]
                            or "unknown"
                        )

            results = await asyncio.gather(
                *[
                    worker(row)
                    for row in rows
                ]
            )

            alive = 0

            http_alive = 0
            socks4_alive = 0
            socks5_alive = 0

            latencies = []

            for (
                proxy,
                is_alive,
                latency,
                protocol
            ) in results:

                if not is_alive:
                    continue

                alive += 1

                if protocol == "http":
                    http_alive += 1

                elif protocol == "socks4":
                    socks4_alive += 1

                elif protocol == "socks5":
                    socks5_alive += 1

                if latency > 0:
                    latencies.append(
                        latency
                    )

            average = (
                sum(latencies)
                / len(latencies)
                if latencies
                else 0
            )

            return ScanResult(
                total=len(rows),
                alive=alive,
                dead=len(rows) - alive,
                http_alive=http_alive,
                socks4_alive=socks4_alive,
                socks5_alive=socks5_alive,
                avg_latency=average
            )

        finally:

            self.running = False
