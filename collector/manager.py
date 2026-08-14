import asyncio
from dataclasses import dataclass

from collector.sources import fetch_source
from collector.parser import extract_proxies

from database.db import Database


@dataclass
class CollectResult:
    discovered: int
    new: int
    duplicates: int
    failed_sources: int


class CollectorManager:

    def __init__(self, db: Database):
        self.db = db

    async def collect(self) -> CollectResult:

        sources = self.db.sources()

        if not sources:
            return CollectResult(
                discovered=0,
                new=0,
                duplicates=0,
                failed_sources=0
            )

        semaphore = asyncio.Semaphore(10)

        async def worker(url):
            async with semaphore:
                return await asyncio.to_thread(
                    fetch_source,
                    url
                )

        results = await asyncio.gather(
            *(worker(url) for url in sources),
            return_exceptions=True
        )

        all_proxies = set()
        failed = 0

        for result in results:

            if isinstance(result, Exception):
                failed += 1
                continue

            if not result:
                failed += 1
                continue

            all_proxies.update(
                extract_proxies(result)
            )

        before = self.db.count()

        self.db.add_many(
            sorted(all_proxies)
        )

        after = self.db.count()

        new = max(
            0,
            after - before
        )

        duplicates = max(
            0,
            len(all_proxies) - new
        )

        return CollectResult(
            discovered=len(all_proxies),
            new=new,
            duplicates=duplicates,
            failed_sources=failed
        )
