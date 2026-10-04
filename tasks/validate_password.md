Implement `validate_password(password: str) -> list[str]`.

Return the names of the rules the password fails, always in this order:

1. `"length"` - at least 8 characters
2. `"uppercase"` - at least one uppercase letter
3. `"lowercase"` - at least one lowercase letter
4. `"digit"` - at least one digit
5. `"special"` - at least one character that is neither alphanumeric nor whitespace
6. `"whitespace"` - must not contain any whitespace

An empty list means the password is valid.
