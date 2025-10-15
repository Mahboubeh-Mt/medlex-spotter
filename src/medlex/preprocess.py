import regex as re


def clean_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def metaphone_encode_window(s: str, start: int, end: int):
    # encode the matched window to compare with phonetic variants
    from metaphone import doublemetaphone

    window = s[max(0, start - 3) : min(len(s), end + 3)]
    a, b = doublemetaphone(window)
    outs = set()
    if a:
        outs.add(f"ph_{a.lower()}")
    if b:
        outs.add(f"ph_{b.lower()}")
    return outs
