# app/streamlit_app.py
import io
import os
import json
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

from medlex.pipeline import build_variant_bank, process_text

st.set_page_config(page_title="MedLex Spotter", page_icon="🩺", layout="wide")
st.title("🩺 MedLex Spotter")
st.caption(
    "Extract medication mentions (fuzzy + phonetic) from free-text notes with negation handling."
)

# --- Sidebar: inputs ---------------------------------------------------------
st.sidebar.header("Inputs")

notes_file = st.sidebar.file_uploader(
    "Upload notes file (CSV or TSV with columns: note_id, text)",
    type=["csv", "tsv"],
)

cfg_file = st.sidebar.file_uploader(
    "Optional: upload custom targets YAML",
    type=["yaml", "yml"],
    help="If omitted, uses configs/example_targets.yaml from the repo.",
)

run_btn = st.sidebar.button("Run extraction", type="primary")


# --- Helpers -----------------------------------------------------------------
def _read_notes(upload) -> pd.DataFrame:
    """Read CSV/TSV with columns note_id,text."""
    if upload is None:
        raise ValueError("No file uploaded.")
    name = upload.name.lower()
    sep = "\t" if name.endswith(".tsv") else ","
    try:
        df = pd.read_csv(upload, sep=sep)
    except Exception:
        # Fallback: sniff delimiter
        upload.seek(0)
        txt = upload.read()
        upload.seek(0)
        df = pd.read_csv(io.BytesIO(txt), sep=None, engine="python")

    # Normalize columns
    cols = {c.strip().lower(): c for c in df.columns}
    if "note_id" not in cols or "text" not in cols:
        raise ValueError("File must contain columns: note_id, text")
    df = df.rename(columns={cols["note_id"]: "note_id", cols["text"]: "text"})
    return df


def _resolve_cfg_path(upload) -> str:
    """Return a filesystem path for the YAML: uploaded temp file or repo default."""
    if upload is None:
        default_path = os.path.join("configs", "example_targets.yaml")
        if not os.path.exists(default_path):
            raise FileNotFoundError(
                "Default config 'configs/example_targets.yaml' not found. Upload a YAML in the sidebar."
            )
        return default_path

    # Persist upload to a temp file on disk for the pipeline
    tmp_dir = ".streamlit_tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, upload.name)
    with open(path, "wb") as f:
        f.write(upload.getbuffer())
    return path


# --- UI: preview --------------------------------------------------------------
with st.expander("Preview data (first 20 rows)", expanded=True):
    if notes_file is not None:
        try:
            df_preview = _read_notes(notes_file).head(20)
            st.dataframe(df_preview, width="stretch")
        except Exception as e:
            st.error(f"Could not read notes file: {e}")
    else:
        st.info("Upload a CSV/TSV in the sidebar to preview it here.")

st.divider()

# --- Run ----------------------------------------------------------------------
if run_btn:
    if notes_file is None:
        st.error("Please upload a notes file first.")
        st.stop()

    # Load config / build banks
    try:
        cfg_path = _resolve_cfg_path(cfg_file)
        ctx, bank, ph_bank, fz = build_variant_bank(cfg_path)
    except Exception as e:
        st.error(f"Config error: {e}")
        st.stop()

    # Read notes
    try:
        df = _read_notes(notes_file)
    except Exception as e:
        st.error(f"Could not read notes file: {e}")
        st.stop()

    # First pass: run the pipeline, collect raw results
    items: List[Dict[str, Any]] = []
    flag_keys = set()

    with st.status("Processing notes…", expanded=False) as status:
        for _, r in df.iterrows():
            note_id = int(r["note_id"])
            text = str(r["text"])

            res = process_text(text, ctx, bank, ph_bank, fz)
            items.append({"note_id": note_id, "res": res})

            # Discover has_* keys from actual output (robust to any config variations)
            for k in res.keys():
                if k.startswith("has_"):
                    flag_keys.add(k)

        status.update(label="Done ✅", state="complete")

    # Stable, sorted list of flag columns
    flag_cols = sorted(flag_keys)

    # Second pass: build uniform rows with all flags + JSON spans
    out_rows: List[Dict[str, Any]] = []
    for it in items:
        res = it["res"]
        row = {"note_id": it["note_id"]}
        for col in flag_cols:
            row[col] = int(res.get(col, 0))
        row["spans"] = json.dumps(res.get("spans", []), ensure_ascii=False)
        out_rows.append(row)

    df_out = pd.DataFrame(out_rows).sort_values("note_id").reset_index(drop=True)

    st.subheader("Results")
    if flag_cols:
        st.dataframe(df_out, width="stretch")
    else:
        st.warning(
            "No `has_*` flags were produced by the pipeline. "
            "Check your YAML targets and a sample note to ensure matches are possible."
        )
        st.dataframe(df_out[["note_id", "spans"]], width="stretch")

    # Expanded spans (optional)
    with st.expander("Show extracted spans (expanded table)"):
        expanded = []
        for r in out_rows:
            try:
                spans = json.loads(r.get("spans", "[]"))
                for s in spans:
                    expanded.append(
                        {
                            "note_id": r["note_id"],
                            "matched": s.get("matched"),
                            "span": s.get("span"),
                            "context": s.get("context"),
                            "source": s.get("source"),
                            "is_negated": s.get("is_negated"),
                        }
                    )
            except Exception:
                pass
        if expanded:
            st.dataframe(pd.DataFrame(expanded), width="stretch")
        else:
            st.info("No spans to display.")

    # Download
    csv_bytes = df_out.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download results CSV",
        data=csv_bytes,
        file_name="medlex_spotter_results.csv",
        mime="text/csv",
    )
