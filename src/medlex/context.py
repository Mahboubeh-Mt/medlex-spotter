import regex as re
from dataclasses import dataclass


@dataclass
class ContextCfg:
    dosage_units: str
    forms: str
    negation_patterns: list[str]


def context_score(text: str, start: int, end: int, cfg: ContextCfg) -> int:
    window = text[max(0, start - 30) : min(len(text), end + 30)]
    pos = 0
    if cfg.dosage_units:
        pos += len(re.findall(rf"\b\d+(?:\.\d+)?\s*({cfg.dosage_units})\b", window))
    if cfg.forms:
        pos += len(re.findall(rf"\b{cfg.forms}\b", window))
    return pos


def is_negated(text: str, start: int, end: int, cfg: ContextCfg) -> bool:
    window = text[max(0, start - 30) : min(len(text), end + 30)]
    for pat in cfg.negation_patterns:
        if re.search(pat, window):
            return True
    return False
