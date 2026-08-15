import asyncio
from dataclasses import dataclass

from collector.parser import extract_proxies
from collector.sources import fetch_source
from database.db import Database


@dataclass
class CollectResult:

    discovered: int
    new: int
    duplicates: int
    failed_sources: int


class CollectorManager:

    def __init__(
        self,
        db: Database
    ):

        self.db = db

    async def collect(
        self
    ):

        sources = self.db.sources()

        if not sources:

            return CollectResult(
                discovered=0,
                new=0,
                duplicates=0,
                failed_sources=0
            )

        semaphore = asyncio.Semaphore(
            15
        )

        async def fetch(url):

            async with semaphore:

                try:

                    text = await asyncio.to_thread(
                        fetch_source,
                        url
                    )

                    return (
                        url,
                        text,
                        None
                    )

                except Exception as exc:

                    return (
                        url,
                        None,
                        exc
                    )

        results = await asyncio.gather(
            *[
                fetch(url)
                for url in sources
            ]
        )

        all_items = set()

        failed = 0

        for url, text, error in results:

            if error or text is None:

                failed += 1
                continue

            try:

                items = extract_proxies(
                    text,
                    url
                )

                all_items.update(
                    items
                )

            except Exception:

                failed += 1

        before = self.db.count()

        self.db.add_many(
            sorted(all_items)
        )

        after = self.db.count()

        inserted = max(
            0,
            after - before
        )

        duplicates = max(
            0,
            len(all_items) - inserted
        )

        return CollectResult(
            discovered=len(all_items),
            new=inserted,
            duplicates=duplicates,
            failed_sources=failed
        )
