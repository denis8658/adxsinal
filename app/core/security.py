import hashlib


def ssid_fingerprint(ssid: str) -> str:
    return hashlib.sha256(ssid.encode()).hexdigest()
