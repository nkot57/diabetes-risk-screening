# DiabetesNet — a from-scratch ML screening tool that learns in the browser

Estimate Type-2 diabetes risk from routine blood-work, see where you stand against a
real cohort, and watch the model improve as confirmed outcomes accumulate. The
classifier is **written from scratch** — gradient descent + binary cross-entropy, no
ML libraries — the same optimization that underlies neural-network and LLM training.

**Live demo:** _add your GitHub Pages URL here_

---

## What it does
- Enter or upload your blood-work (manual, **PDF**, or CSV) and get a calibrated
  Type-2 diabetes risk score.
- See **where you sit** on the distribution of people with confirmed outcomes, with
  the honest diabetes prevalence (and 95% confidence interval) for your risk band.
- Confirm your real outcome → it’s folded back in as training data and the model
  **fine-tunes** on it.

## How it works (the model)
The score is a **logistic regression** — equivalently, a single-neuron neural network
with a sigmoid activation — trained by hand:

1. **Standardize** each marker to a z-score: `x = (value − mean) / std`
2. **Linear combination:** `z = b + Σ wⱼ·xⱼ`
3. **Sigmoid → probability:** `score = 100 · 1/(1 + e^−z)`

Training minimizes **binary cross-entropy** by **gradient descent**, nudging the 9
parameters (8 weights + 1 bias) toward predictions that match reality. It’s the same
machinery used to train networks of every size:

| LLM training | This project |
|---|---|
| Billions of weights | One weight per blood-work marker + a bias |
| Forward pass → softmax probabilities | Blood-work → sigmoid → P(diabetic) |
| **Cross-entropy** loss | **Binary cross-entropy** loss |
| Back-propagation + optimizer step | Hand-written gradient + `w ← w − η·∇` |
| Fine-tuning on new data | “Confirm your result” → a few gradient steps |

A separate [`trainer.html`](trainer.html) exposes the training itself — a live loss
curve, animated weights, a logistic-regression ↔ one-hidden-layer (back-prop) toggle,
and held-out accuracy / ROC-AUC.

## Features
- **From-scratch logistic regression** (and an optional one-hidden-layer net with
  back-propagation) — no ML libraries.
- **Calibrated probability output** — the score is a real `P(diabetic)`, so risk
  bands’ measured prevalence matches their range.
- **Missing-data scoring** — blank markers are mean-imputed and flagged as
  lower-confidence, so partial panels still score.
- **PDF / CSV upload** with a parse-and-confirm step (never auto-trusted).
- **Online fine-tuning** — each confirmed outcome retrains the model live.
- **Persistence** — confirmations survive refresh via `localStorage`, and can flow to
  a private database (Supabase) you periodically retrain from.
- **100% client-side** — training and inference run in the browser; free to host.
- **Privacy by design** — only anonymous numbers + a 0/1 outcome are ever stored.

## Architecture
```
 Visitor's browser ──confirm──▶  Supabase table (private, insert-only)
        ▲                              │
        │ loads weights.json           │ you read it (secret key, local)
        │                              ▼
   GitHub Pages  ◀──commit──  node retrain.js  ──▶ weights.json
```
Data is collected continuously, but **you** decide when to fold it into the model —
the manual retrain is both the publish step and the review gate against bad data.

## Run it locally
The page must be served over HTTP (it fetches the cohort CSV):
```bash
python3 -m http.server 8000
# then open http://localhost:8000/index.html
```

## Collect submissions & retrain (optional)
See [`SETUP.md`](SETUP.md) for the 5-minute Supabase setup. To update the published
model from collected data:
```bash
SUPABASE_URL=... SUPABASE_SERVICE_KEY=... node retrain.js   # writes weights.json
```
Commit `weights.json` to publish the updated model to every visitor.

## Limitations & honest notes
- **Not a medical device.** A personal-project demonstration on a public dataset of
  unverified origin. It does not diagnose anyone.
- **Models inherit their data.** This dataset shows HDL *rising* with diabetes — the
  opposite of the real clinical relationship — and the model dutifully learns that
  “backwards” signal. It’s kept and explained as a lesson in how bias propagates from
  training data, exactly the problem LLMs face with their corpora.
- **PDF import has no unit conversion yet** (e.g. mg/dL vs mmol/L) — which is why the
  parsed values must be confirmed before scoring.
- Histogram/prevalence are computed on the full cohort (a calibration view, not a
  held-out generalization claim — see `trainer.html` for held-out metrics).

## Files
| File | What it is |
|---|---|
| `index.html` | The screening dashboard (the product) |
| `trainer.html` | The from-scratch training visualizer |
| `retrain.js` | Periodic retrain → `weights.json` (zero-dependency Node) |
| `weights.json` | The published, curated model |
| `supabase-schema.sql` | Database table + insert-only security + validation |
| `SETUP.md` | Database setup walkthrough |
| `Diabetes Classification 2.csv` | The reference cohort |

---

_Built as a personal project. Not affiliated with any medical institution and not for
clinical use._
