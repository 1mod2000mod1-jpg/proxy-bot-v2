import asyncio
import os
import time


TIMEOUT = float(os.getenv("CHECK_TIMEOUT", "5"))


async def check_tcp(host: str, port: int):
    """
    فحص TCP فقط.
    يستخدم كمرحلة أولية سريعة قبل فحص HTTP Proxy.
    """

    writer = None
    started = time.perf_counter()

    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=TIMEOUT
        )

        latency = round(
            (time.perf_counter() - started) * 1000
        )

        return True, latency

    except Exception:
        return False, 0

    finally:
        if writer:
            writer.close()

            try:
                await writer.wait_closed()
            except Exception:
                pass
