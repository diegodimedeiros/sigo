import re


NON_DIGIT_RE = re.compile(r"\D+")


def normalize_text(value):
    return str(value or "").strip()


def normalize_upper(value):
    text = normalize_text(value)
    return text.upper() if text else ""


def normalize_digits(value):
    return NON_DIGIT_RE.sub("", normalize_text(value))
