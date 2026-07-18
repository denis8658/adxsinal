def validate_ssid(value: str) -> str:
    value = value.strip()
    if len(value) < 12:
        raise ValueError("SSID inválido ou muito curto")
    if len(value) > 8192:
        raise ValueError("SSID excede o tamanho permitido")
    return value
