import asyncio
import os
import time

import aiohttp


TIMEOUT = float(os.getenv("CHECK_TIMEOUT", "5"))

TEST_URL = os.getenv(
    "PROXY_TEST_URL",
    "http://example.com/"
)


async def check_http_proxy(proxy: str):
    """
    فحص HTTP Proxy فعلي.

    proxy:
        34.x.x.x:PORT

    النتيجة:
        (alive, latency)
    """

    proxy_url = f"http://{proxy}"

    started = time.perf_counter()

    timeout = aiohttp.ClientTimeout(
        total=TIMEOUT,
        connect=TIMEOUT,
        sock_connect=TIMEOUT,
        sock_read=TIMEOUT
    )

    try:

        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=1
        )

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
                    "User-Agent": "PROXPMOY-Checker/3.0"
                }
            ) as response:

                # نحتاج فقط إلى استجابة HTTP حقيقية
                # من خلال البروكسي.
                await response.read(1024)

                latency = round(
                    (time.perf_counter() - started)
                    * 1000
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
