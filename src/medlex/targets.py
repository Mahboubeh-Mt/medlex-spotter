from typing import Iterable
from rapidfuzz.utils import default_process
from metaphone import doublemetaphone


def normalize_term(t: str) -> str:
    return default_process(t or "")


def expand_phonetic(terms: Iterable[str]) -> set[str]:
    out = set()
    for t in terms:
        a, b = doublemetaphone(t)
        # include both metaphone codes as synthetic variants (prefixed)
        if a:
            out.add(f"ph_{a.lower()}")
        if b:
            out.add(f"ph_{b.lower()}")
    return out
