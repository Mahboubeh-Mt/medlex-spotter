import argparse
import sys
import json
from typing import Optional

import pandas as pd

from .pipeline import build_variant_bank, process_text


def _detect_sep(path: str) -> str:
    """
    Heuristic: prefer tab if tabs appear in the header; otherwise comma.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(2048).decode("utf-8", errors="ignore")
        header = head.splitlines()[0] if head else ""
        return "\t" if "\t" in header else ","
    except Exception:
        # If detection fails, default to comma
        return ","


def _read_table(path_in: str, sep_arg: str) -> pd.DataFrame:
    if sep_arg == "csv":
        sep = ","
    elif sep_arg == "tsv":
        sep = "\t"
    else:  # auto
        sep = _detect_sep(path_in)
    return pd.read_csv(path_in, sep=sep)


def main(path_in: str, cfg_path: str, out_path: Optional[str] = "-", sep_arg: str = "auto"):
    # Build matching context/banks
    ctx, bank, ph_bank, fz = build_variant_bank(cfg_path)

    # Precompute the full set of flag columns we expect from the YAML
    flag_keys = [f"has_{t.canonical.lower()}" for t in ctx.targets]

    # Load notes
    df = _read_table(path_in, sep_arg)

    # Validate columns
    required = ("note_id", "text")
    for col in required:
        if col not in df.columns:
            raise SystemExit(f"Input must contain columns: {', '.join(required)} (missing: {col})")

    # Process rows
    rows = []
    for _, r in df.iterrows():
        note_id = int(r["note_id"])
        text = str(r["text"])

        res = process_text(text, ctx, bank, ph_bank, fz)

        # Ensure every flag column exists; default to 0 if missing
        flags = {k: int(res.get(k, 0)) for k in flag_keys}

        # Spans as JSON string for safe CSV embedding
        spans_json = json.dumps(res.get("spans", []), ensure_ascii=False)

        rows.append({"note_id": note_id, **flags, "spans": spans_json})

    out_df = pd.DataFrame(rows).sort_values("note_id")

    # Write output
    if out_path in (None, "-"):
        out_df.to_csv(sys.stdout, index=False)
    else:
        out_df.to_csv(out_path, index=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="medlex-spotter CLI")
    p.add_argument(
        "--in", dest="path_in", required=True, help="Input CSV/TSV with columns: note_id,text"
    )
    p.add_argument("--targets", required=True, help="YAML targets config")
    p.add_argument(
        "--out", dest="out_path", default="-", help="Output CSV path (use '-' for stdout)"
    )
    p.add_argument(
        "--sep", dest="sep", default="auto", choices=["auto", "csv", "tsv"], help="Input delimiter"
    )
    a = p.parse_args()
    main(a.path_in, a.targets, a.out_path, a.sep)
