import re


IP_PORT = re.compile(
    r"(?<![\d.])"
    r"(34\."
    r"(?:\d{1,3}\.){2}"
    r"\d{1,3})"
    r":"
    r"(\d{1,5})"
    r"(?!\d)"
)


def valid_port(port: str) -> bool:
    try:
        value = int(port)
        return 1 <= value <= 65535
    except ValueError:
        return False


def valid_octet(value: str) -> bool:
    try:
        return 0 <= int(value) <= 255
    except ValueError:
        return False


def valid_ip(ip: str) -> bool:

    parts = ip.split(".")

    if len(parts) != 4:
        return False

    return all(
        valid_octet(part)
        for part in parts
    )


def extract_proxies(text: str):

    result = set()

    for ip, port in IP_PORT.findall(text):

        if not valid_ip(ip):
            continue

        if not valid_port(port):
            continue

        result.add(
            f"{ip}:{int(port)}"
        )

    return result
