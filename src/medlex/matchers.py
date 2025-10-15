from dataclasses import dataclass
import regex as re
from rapidfuzz import fuzz
from .preprocess import metaphone_encode_window


@dataclass
class Hit:
    canonical: str
    variant: str
    score: int
    start: int
    end: int


def scan_exact(text: str, variant: str, canonical: str) -> list[Hit]:
    hits = []
    for m in re.finditer(re.escape(variant), text):
        hits.append(Hit(canonical, variant, 100, m.start(), m.end()))
    return hits


def scan_fuzzy(text: str, variant: str, canonical: str, thresh: int) -> list[Hit]:
    # heuristic: look for substrings starting with first 3 chars
    hits = []
    stub = re.escape(variant[:3])
    for m in re.finditer(rf"{stub}\w{{0,12}}", text):
        cand = text[m.start() : m.end()]
        score = fuzz.ratio(cand, variant)
        if score >= thresh:
            hits.append(Hit(canonical, variant, score, m.start(), m.end()))
    return hits


def scan_phonetic(text: str, ph_variant: str, canonical: str) -> list[Hit]:
    # ph_variant is like ph_<code>
    hits = []
    # compare metaphone code of window with variant code
    code = ph_variant
    for m in re.finditer(r"\w{3,15}", text):
        phs = metaphone_encode_window(text, m.start(), m.end())
        if code in phs:
            hits.append(Hit(canonical, ph_variant, 80, m.start(), m.end()))
    return hits
