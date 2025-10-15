import pandas as pd
from medlex.pipeline import build_variant_bank, process_text


def test_example_cfg_and_data():
    ctx, bank, ph_bank, fz = build_variant_bank("configs/example_targets.yaml")
    df = pd.read_csv("data/examples/notes.tsv", sep="\t")
    gold = pd.read_csv("eval/labels.tsv", sep="\t").set_index("note_id")
    for _, r in df.iterrows():
        out = process_text(str(r["text"]), ctx, bank, ph_bank, fz)
        g = gold.loc[int(r["note_id"])]
        for canon in ["METFORMIN", "INSULIN"]:
            k = f"has_{canon.lower()}"
            assert int(out[k]) == int(g[canon])
