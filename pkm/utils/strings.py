def without_suffix(s: str, suffix: str) -> str:
    if s.endswith(suffix):
        return s[:-len(suffix)]

    return s


def without_prefix(s: str, prefix: str) -> str:
    if s.startswith(prefix):
        return s[len(prefix):]

    return s
