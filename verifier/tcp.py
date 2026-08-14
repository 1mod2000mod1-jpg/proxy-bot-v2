import asyncio


TIMEOUT = float(
    __import__("os").getenv(
        "CHECK_TIMEOUT",
        "5"
    )
)


async def check_tcp(
    host: str,
    port: int
) -> bool:

    writer = None

    try:

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                host,
                port
            ),
            timeout=TIMEOUT
        )

        return True

    except Exception:
        return False

    finally:

        if writer is not None:

            writer.close()

            try:
                await writer.wait_closed()
            except Exception:
                pass
