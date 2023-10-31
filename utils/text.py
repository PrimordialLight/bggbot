from cleantext import clean


def normalize(content: str, to_lower: bool = False) -> str:
    if to_lower:
        return clean(content, normalize_whitespace=True, fix_unicode=True, no_line_breaks=True, lower=True, no_punct=True)
    else:
        return clean(content, normalize_whitespace=True, fix_unicode=True, no_line_breaks=True, lower=False, no_punct=True)
