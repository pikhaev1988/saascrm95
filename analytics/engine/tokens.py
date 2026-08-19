"""Единая интерпретация токенов ответов по заданиям."""


def is_success_token(token_value) -> bool:
    token = str(token_value or "").strip()
    if not token:
        return False
    if token == "+":
        return True
    if token in {"-", "0"}:
        return False
    if token.isdigit():
        return int(token) > 0
    return False


def is_blank_token(token_value) -> bool:
    token = str(token_value or "").strip()
    return not token


def is_error_token(token_value) -> bool:
    token = str(token_value or "").strip()
    if not token:
        return False
    if token in {"-", "0"}:
        return True
    if token.isdigit():
        return int(token) == 0
    return False
