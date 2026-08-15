import asyncio
import os
import time

import aiohttp


TIMEOUT = float(
    os.getenv(
        "CHECK_TIMEOUT",
        "5"
    )
)

TEST_URL = os.getenv(
    "PROXY_TEST_URL",
    "http://example.com/"
)


async def check_http_proxy(
    proxy: str
):

    proxy_url = (
        f"http://{proxy}"
    )

    started = time.perf_counter()

    timeout = aiohttp.ClientTimeout(
        total=TIMEOUT,
        connect=TIMEOUT,
        sock_connect=TIMEOUT,
        sock_read=TIMEOUT
    )

    connector = aiohttp.TCPConnector(
        ssl=False,
        limit=1
    )

    try:

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=False
        ) as session:

            async with session.get(
                TEST_URL,
                proxy=proxy_url,
                allow_redirects=False,
                headers={
                    "User-Agent": "PROXPMOY/4.0"
                }
            ) as response:

                await response.read(
                    2048
                )

                latency = round(
                    (
                        time.perf_counter()
                        - started
                    ) * 1000
                )

                if 100 <= response.status < 600:

                    return True, latency

                return False, latency

    except (
        asyncio.TimeoutError,
        aiohttp.ClientError,
        OSError,
        ConnectionError
    ):

        return False, 0

    except Exception:

        return False, 0
