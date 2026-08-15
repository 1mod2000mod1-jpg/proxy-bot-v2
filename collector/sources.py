import urllib.request


USER_AGENT = (
    "Mozilla/5.0 "
    "PROXPMOY/4.0"
)


def fetch_source(url: str):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/plain,text/*,*/*;q=0.8",
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        data = response.read(
            10 * 1024 * 1024
        )

        return data.decode(
            "utf-8",
            errors="ignore"
        )
