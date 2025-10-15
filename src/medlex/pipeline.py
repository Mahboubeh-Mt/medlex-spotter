# src/medlex/pipeline.py
from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from typing import Dict, List, Tuple, Any

from .config import load_config  # existing loader


# ---------- small helpers ----------


def _as_plain(obj: Any) -> Any:
    """Best-effort convert dataclass-like / pydantic-like objects to plain dicts."""
    try:
        if is_dataclass(obj):
            return asdict(obj)
    except Exception:
        pass
    # pydantic v1/v2 models expose .dict()/model_dump()
    for m in ("model_dump", "dict"):
        fn = getattr(obj, m, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    return obj  # fall back


def _get(obj: Any, key: str, default=None):
    """Get obj[key] or obj.key if present."""
    if obj is None:
        return default
    # try mapping
    if isinstance(obj, dict) and key in obj:
        return obj[key]
    # try attribute
    if hasattr(obj, key):
        return getattr(obj, key)
    return default


# ---------- core compile logic ----------


class Ctx:
    def __init__(self, negation_re: re.Pattern, window: int = 40):
        self.negation_re = negation_re
        self.window = window


def _compile_term_regex(terms: List[str]) -> re.Pattern:
    safe = [re.escape(t) for t in terms if t and str(t).strip()]
    if not safe:
        return re.compile(r"(?!x)x")  # never matches
    return re.compile(r"(?i)\b(?:%s)\b" % "|".join(safe))


def build_variant_bank(cfg_path: str):
    """
    Accepts dict-like OR object-like configs.

    Returns:
      ctx, bank, ph_bank, fz
    """
    raw = load_config(cfg_path)
    cfg = _as_plain(raw)  # normalize

    # ---- negation ----
    neg = _get(cfg, "negation", {}) if cfg is not None else {}
    neg = _as_plain(neg)
    neg_patterns = _get(neg, "patterns", None)
    if not neg_patterns:
        neg_patterns = [r"\b(no|not|without|stop|stopped|discontinued|allergic to|avoid|denies)\b"]
    negation_re = re.compile("|".join(neg_patterns), flags=re.IGNORECASE)
    ctx = Ctx(negation_re=negation_re, window=40)

    # ---- targets ----
    targets = _get(cfg, "targets", None)
    if targets is None:
        # Sometimes nested under cfg.config or similar; try a plain dict conversion
        cfg_plain = _as_plain(cfg)
        targets = _get(cfg_plain, "targets", None)

    if not targets or not isinstance(targets, (list, tuple)):
        raise ValueError("Config must have a 'targets' list.")

    bank: Dict[str, re.Pattern] = {}
    for t in targets:
        t_plain = _as_plain(t)
        canon = _get(t_plain, "canonical", None) or _get(t_plain, "canon", None)
        terms = _get(t_plain, "terms", None)
        if not canon or not terms or not isinstance(terms, (list, tuple)):
            raise ValueError(
                f"Each target needs 'canonical' (or 'canon') and a non-empty list of 'terms'. Problematic entry: {t_plain}"
            )
        bank[str(canon).upper()] = _compile_term_regex(list(terms))

    # ph_bank/fz kept for signature compatibility (unused in this simplified flow)
    ph_bank: Dict[str, Any] = {}
    fz: Dict[str, Any] = {}
    return ctx, bank, ph_bank, fz


def _is_negated(text: str, span: Tuple[int, int], ctx: Ctx) -> bool:
    L, R = span
    lo = max(0, L - ctx.window)
    hi = min(len(text), R + ctx.window)
    return bool(ctx.negation_re.search(text[lo:hi]))


def process_text(
    text: str, ctx: Ctx, bank: Dict[str, re.Pattern], ph_bank: Dict[str, Any], fz: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Emits:
      - has_<lowercanonical> flags (0/1)
      - spans: [{matched, span, context, source, is_negated}]
    Flag = 1 iff any NON-NEGATED match exists for that canonical.
    """
    spans: List[Dict[str, Any]] = []
    flags: Dict[str, int] = {f"has_{canon.lower()}": 0 for canon in bank.keys()}

    for canon, cre in bank.items():
        found_non_neg = False
        for m in cre.finditer(text or ""):
            span = (m.start(), m.end())
            neg = _is_negated(text, span, ctx)
            lo = max(0, span[0] - 30)
            hi = min(len(text), span[1] + 30)
            spans.append(
                {
                    "matched": m.group(0),
                    "span": span,
                    "context": text[lo:hi],
                    "source": canon,
                    "is_negated": bool(neg),
                }
            )
            if not neg:
                found_non_neg = True
        if found_non_neg:
            flags[f"has_{canon.lower()}"] = 1

    return {**flags, "spans": spans}
