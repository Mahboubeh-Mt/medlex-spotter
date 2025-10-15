# medlex-spotter 🩺🔎
![tests](https://img.shields.io/github/actions/workflow/status/Mahboubeh-Mt/medlex-spotter/ci.yml?branch=main)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.12+-blue)

> Fast, reproducible medication spotting in noisy clinical/free-text (misspellings, abbreviations, and phonetic variants) with context & negation awareness.

---

### TL;DR

```bash
# Install in a fresh venv
python -m pip install --upgrade pip
pip install -e .

# Run the app (recommended for a quick demo)
streamlit run app/streamlit_app.py
```
---
## Why this pipeline? (The problem it solves)

In many real-world datasets (e.g., doctors’ notes, prescription histories), **medications are recorded as free text**.
For Type 2 Diabetes (T2D) meds like **Metformin** and **Insulin**, notes might include:

- **Misspellings**: `metfornin`, `metforim`, `insuline`
- **Abbreviations**: `met`, `metf.`
- **Noisy context**: “met with family”, “no insulin”, “stopped metformin”

When we need to know, per participant/text, whether a specific medication was **actually prescribed/used**, naïve keyword matching creates **false positives** and **misses**. This hurts downstream analyses (e.g., brain atrophy associations, RBA, risk modeling) and forces us to call “medication history not available” as a study limitation.

**medlex-spotter** fixes this by combining:
- **Exact + fuzzy + phonetic** matching,
- **Context scoring** (dose units & forms nearby),
- **Negation handling** (e.g., “no insulin”, “stopped metformin”),
- **Guardrails** to avoid short-token traps (e.g., *“met with family”* won’t trigger Metformin).

The result: a small, **reproducible** pipeline you can run locally, in CI, and extend to **other medications** or **any custom term list**.

---

## Features

- **Robust matching**: exact, fuzzy (RapidFuzz), phonetic (Double Metaphone via `Metaphone`)
-  **Context-aware**: boosts matches near **dosage units** (mg, units) and **forms** (tablet, injection)
- **Negation-aware**: filters “no/deny/stop” contexts
-  **Short/phonetic guardrails**: avoids “met”/“ins” collisions unless context proves it’s a med
- **YAML-configurable** targets (easy to add meds/terms & thresholds)
- **Tests included** (end-to-end, sample data)
- **CLI + (optional) Streamlit app**
- **CI-ready**: GitHub Actions workflow provided
- **Installable**: `pip install -e .`

---

## Quickstart

```bash
# 1) Install (in a virtualenv)
python -m pip install --upgrade pip
pip install -e .

# 2) Run on the example notes
python -m medlex.cli --in data/examples/notes.tsv --targets configs/example_targets.yaml > outputs.csv

# 3) Check results
cat outputs.csv
```
### Expected behavior:

Correctly flags METFORMIN and INSULIN mentions.

Avoids false positives on phrases like “met with family”.

### How it works (high level)

1. Preprocess: normalize text (casing, punctuation, spacing)

2. Generate variant banks per canonical label
   - literal terms (exact + fuzzy thresholds from YAML)

   - phonetic codes (for longer variants to reduce noise)
3. Scan: exact → fuzzy → phonetic
4. Score context around hits (dosage units, forms)
5. Apply rules:
- drop negated mentions
- require context for short tokens and phonetic matches
- denylist ultra-ambiguous pieces (e.g., a bare met)

6. Aggregate: keep best span per canonical; emit has_<med> flags + spans

### Configuration (YAML)
Define meds/terms, thresholds, and context in configs/example_targets.yaml:
```bash
defaults:
  dosage_units: ["mg", "g", "units", "iu"]
  forms: ["tablet", "tab", "capsule", "cap", "injection", "inj", "pen"]
negation:
  patterns:
    - "\\bno\\b"
    - "\\bstop(ped|s|ping)?\\b"
    - "\\bdiscontinue(d)?\\b"
    - "\\ballergic to\\b"

targets:
  - canonical: "METFORMIN"
    terms: ["metformin", "metforman", "metfornin", "metforim", "metf", "metf."]
    fuzzy: 90             # Levenshtein similarity threshold (0–100)
    generate_phonetic: true

  - canonical: "INSULIN"
    terms: ["insulin", "insuline", "ins."]
    fuzzy: 88
    generate_phonetic: true
```
**You can add any medication: set canonical, list terms, adjust fuzzy, and choose whether to generate_phonetic.**

### CLI
```python
python -m medlex.cli \
  --in data/examples/notes.tsv \
  --targets configs/example_targets.yaml > outputs.csv
```
Input (notes.tsv): a tab-separated file with at least:
```bash
note_id   text
1         Started metformin 500 mg tablet daily
2         No insulin since last visit
...
```
Output (outputs.csv):

- columns: has_metformin, has_insulin, plus per-span JSON in spans (if desired)
### Extend to other medications / keywords
1. Open your YAML (e.g., configs/my_targets.yaml)
2. Add a new block:
```
- canonical: "GLP1"
  terms: ["semaglutide", "ozempic", "wegovy", "liraglutide", "victoza"]
  fuzzy: 90
  generate_phonetic: true
 ```
3. Run the CLI with your config:
```
python -m medlex.cli --in path/to/your/notes.tsv --targets configs/my_targets.yaml > outputs.csv
```
Tip: keep abbreviations (≤3 chars) to a minimum unless you’re confident they appear near dosage/form cues.
### Tests
```python
pytest -q
```
The test suite checks:
- End-to-end behavior on example notes
- Negation + context guardrails for short/phonetic spans

### Streamlit app
A simple UI can let users upload a file and pick meds to search.

### Reproducibility & CI

Pre-commit hooks: lint/format on commit
```python
pre-commit install
pre-commit run -a
```
- GitHub Actions (.github/workflows/ci.yml): runs tests on push/PR

### Limitations

This is a rule-assisted string matcher, not a full clinical NER model.
It prioritizes precision (avoiding spurious hits) over recall when ambiguous.

Complex narratives (e.g., historical vs. current meds, conditional statements) may need richer context rules.

Always validate on your domain data; tweak fuzzy, terms, and context lists.

Roadmap

- Add a YAML denylist per target (e.g., block met generically)

- Export audit traces (note_id, span, context score, reason kept/dropped)

- Add more negation & temporality patterns

- Optional spaCy model for richer context windows

- Expand example configs for common T2D/neurology meds

### Contributing

PRs and issues welcome! Please run:
```python
pre-commit run -a
pytest -q
```
### 👤 Author & Contact

**Mahboubeh Motaghi**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mahboubeh-motaghi-phd-58033759)
[![Google Scholar](https://img.shields.io/badge/Google%20Scholar-Profile-4285F4?logo=google-scholar&logoColor=white)](https://scholar.google.com/citations?user=CkXNH2MAAAAJ&hl=en)
[![Email](https://img.shields.io/badge/Email-Contact-informational?logo=gmail&logoColor=white)](mailto:mahboubeh.motaghi@gmail.com)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Please cite](https://img.shields.io/badge/Attribution-appreciated-blue)](./CITATION.cff)

⭐️ *If you found this project interesting, feel free to fork, star, or reach out for collaboration.*
