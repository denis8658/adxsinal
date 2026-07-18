import re


def mask_secret(value: str) -> str:
    if len(value) <= 10:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def mask_sensitive_text(text: str) -> str:
    text = re.sub(r'42\["auth"[^\n\r]*', "[SSID_REDACTED]", text)
    text = re.sub(r'(?i)(x-engine-key|engine_master_key|ssid)(["\s:=]+)([^\s,}]+)', r"\1\2[REDACTED]", text)
    return text
