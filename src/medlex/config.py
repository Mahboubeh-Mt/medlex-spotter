from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import yaml

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Defaults:
    dosage_units: str = r"(?:mg|g|iu|units|u)"
    forms: str = r"(?:tab(?:let)?s?|xr|er|sr|inj|inject(?:ion)?|pen|vial)"

    # Allow dict-like access in code that does defaults.get("key", default)
    def get(self, key: str, default=None):
        return getattr(self, key, default)


@dataclass
class Negation:
    patterns: List[str] = field(default_factory=list)

    # Allow dict-like access in code that does negation.get("patterns", [...])
    def get(self, key: str, default=None):
        return getattr(self, key, default)


@dataclass
class Target:
    # required
    canonical: str
    terms: List[str]

    # optional knobs
    fuzzy: Optional[int] = None
    generate_phonetic: bool = False
    short_token_guard: bool = False  # tolerated if it appears in YAML


@dataclass
class Config:
    defaults: Defaults = field(default_factory=Defaults)
    targets: List[Target] = field(default_factory=list)
    negation: Negation = field(default_factory=Negation)


def _as_str_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    # allow single string
    return [str(x)]


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError("Config error: top-level YAML must be a mapping (dict).")

    # ---- defaults ----
    defaults_raw = raw.get("defaults", {}) or {}
    if not isinstance(defaults_raw, dict):
        raise ValueError("Config error: 'defaults' must be a mapping (dict).")

    # Only pass known keys to Defaults to avoid unexpected-kw errors
    defaults_kw: Dict[str, Any] = {}
    if "dosage_units" in defaults_raw:
        defaults_kw["dosage_units"] = str(defaults_raw["dosage_units"])
    if "forms" in defaults_raw:
        defaults_kw["forms"] = str(defaults_raw["forms"])
    defaults = Defaults(**defaults_kw)

    # ---- negation ----
    neg_raw = raw.get("negation", {}) or {}
    patterns: List[str] = []
    if isinstance(neg_raw, dict):
        patterns = _as_str_list(neg_raw.get("patterns", []))
    elif isinstance(neg_raw, list):
        # allow YAML like:  negation: ["no", "not", ...]
        patterns = _as_str_list(neg_raw)
    else:
        raise ValueError("Config error: 'negation' must be a dict or a list.")
    negation = Negation(patterns=patterns)

    # ---- targets ----
    targets_raw = raw.get("targets", [])
    if not isinstance(targets_raw, list):
        raise ValueError("Config error: 'targets' must be a list.")

    targets: List[Target] = []
    for t in targets_raw:
        if not isinstance(t, dict):
            raise ValueError(f"Config error: target entries must be dicts, got {type(t)}.")

        canonical = t.get("canonical") or t.get("canon")
        terms = t.get("terms")

        if not canonical or not terms or not isinstance(terms, list) or len(terms) == 0:
            raise ValueError(
                f"Config error: Each target needs 'canonical' and non-empty 'terms'. "
                f"Problematic entry: {t}"
            )

        # Optional fields (ignore if absent)
        fuzzy = t.get("fuzzy", None)
        if fuzzy is not None:
            try:
                fuzzy = int(fuzzy)
            except Exception as e:
                raise ValueError(f"Config error: 'fuzzy' must be an integer. Entry: {t}") from e

        generate_phonetic = bool(t.get("generate_phonetic", False))
        short_token_guard = bool(t.get("short_token_guard", False))

        targets.append(
            Target(
                canonical=str(canonical),
                terms=[str(x) for x in terms],
                fuzzy=fuzzy,
                generate_phonetic=generate_phonetic,
                short_token_guard=short_token_guard,
            )
        )

    return Config(defaults=defaults, targets=targets, negation=negation)
