import asyncio
import os
import time

from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import (
    ProxyConnector,
    ProxyType,
)


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


async def check_socks_proxy(
    proxy: str,
    version: str
):

    host, port = proxy.rsplit(
        ":",
        1
    )

    if version == "socks4":

        proxy_type = ProxyType.SOCKS4

    elif version == "socks5":

        proxy_type = ProxyType.SOCKS5

    else:

        return False, 0

    started = time.perf_counter()

    timeout = ClientTimeout(
        total=TIMEOUT,
        connect=TIMEOUT,
        sock_connect=TIMEOUT,
        sock_read=TIMEOUT
    )

    connector = ProxyConnector(
        proxy_type=proxy_type,
        host=host,
        port=int(port),
        rdns=True,
        limit=1
    )

    try:

        async with ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=False
        ) as session:

            async with session.get(
                TEST_URL,
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
        OSError,
        ConnectionError
    ):

        return False, 0

    except Exception:

        return False, 0
