import re


IP_PORT_PATTERN = re.compile(
    r"(?<![\d.])"
    r"((?:\d{1,3}\.){3}\d{1,3})"
    r":"
    r"(\d{1,5})"
    r"(?!\d)"
)


def valid_port(value: str) -> bool:

    try:

        port = int(value)

        return 1 <= port <= 65535

    except ValueError:

        return False


def valid_ip(ip: str) -> bool:

    parts = ip.split(".")

    if len(parts) != 4:
        return False

    for part in parts:

        try:
            value = int(part)
        except ValueError:
            return False

        if not 0 <= value <= 255:
            return False

    return True


def source_protocol(url: str) -> str:

    lower = url.lower()

    if "socks5" in lower:
        return "socks5"

    if "socks4" in lower:
        return "socks4"

    if "https" in lower:
        return "https"

    if "http" in lower:
        return "http"

    return "unknown"


def extract_proxies(
    text: str,
    source_url: str
):

    protocol = source_protocol(
        source_url
    )

    results = set()

    for ip, port in IP_PORT_PATTERN.findall(text):

        if not valid_ip(ip):
            continue

        if not valid_port(port):
            continue

        # طلبك الحالي هو 34.*
        if not ip.startswith("34."):
            continue

        results.add(
            (
                f"{ip}:{int(port)}",
                protocol
            )
        )

    return results
