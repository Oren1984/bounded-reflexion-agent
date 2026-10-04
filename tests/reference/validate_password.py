def validate_password(password: str) -> list[str]:
    checks = [
        ("length", len(password) >= 8),
        ("uppercase", any(c.isupper() for c in password)),
        ("lowercase", any(c.islower() for c in password)),
        ("digit", any(c.isdigit() for c in password)),
        ("special", any(not c.isalnum() and not c.isspace() for c in password)),
        ("whitespace", not any(c.isspace() for c in password)),
    ]
    return [name for name, ok in checks if not ok]
