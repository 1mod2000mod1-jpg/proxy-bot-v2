import urllib.request


USER_AGENT = (
    "Mozilla/5.0 "
    "PROXPMOY/3.0"
)


def fetch_source(url: str) -> str:

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        data = response.read(
            5 * 1024 * 1024
        )

        return data.decode(
            "utf-8",
            errors="ignore"
        )
