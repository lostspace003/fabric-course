# Microsoft Fabric Project Course: Brightcart Delivery Promise

A 147-minute project course for complete beginners. A learner who has never opened Fabric creates an account, tours the
platform, watches each component solve one small problem for Brightcart (a fictional online retailer), then builds one
connected solution: a medallion lakehouse, an MLflow experiment and registered model, a real-time endpoint feeding a
checkout app, a stream into an Eventhouse with a live dashboard and an alert, nightly batch scoring into Power BI, and a
model v2 swap with no app change.

Trainer: Jalal. Published on the Gennoor Learning Studio. The kit that specifies the course is in `kit/` (unchanged).

## Layout
| Folder | What |
|---|---|
| `course/RUN_OF_SHOW.md` | every lesson, its duration and the running total (cap 150 min) |
| `course/part-1-tour`, `part-2-components` | demo scripts 1.1–2.11 (narration + on-screen action) |
| `course/part-3-project` | 3.0 brief, Labs 1–7: `lab-guide.md` (for learners) + `script.md` (recording) |
| `course/optional` | 3.8 AI layer (paid capacity), 3.9 Azure ML alternative |
| `course/ML_CARDS.md` | "In one minute" cards for ML ideas the course uses but does not teach |
| `slides/` | S1–S5, chapter cards, lower-thirds, end card; `animations/A01…A12.html` + `render.py` → `out/*.mp4` |
| `assets/icons/` | official Microsoft Fabric icons, byte-identical to `kit/icons` (never edit) |
| `data/` | seeded synthetic data (`generator/generate.py`, seed 42), `manifest.json`, `DATA_DICTIONARY.md` |
| `fabric/` | notebooks nb_00…nb_04, SQL, KQL, DAX + report spec, pipeline and Activator build specs |
| `app/checkout-simulator` | Streamlit consumer of the model endpoint (mock mode needs no Fabric) |
| `ops/` | cost guardrails and cleanup |
| `OPEN_QUESTIONS.md`, `QA_REPORT.md` | what must be verified at the dry run; definition-of-done results |

## Run the labs
1. Get a Fabric trial (lesson 1.2). Parts 1–3 run on the trial; only 3.8 / 3.9 need paid capacity or an Azure subscription.
2. Do Part 2 in `ws-fabric-tour` (it creates `lh_reference` and `sqldb_brightcart_ops`), or run the fallback in Lab 1 step 0.
3. Follow `course/part-3-project/lab-01…lab-07` in order. Each lab ends with a ✅ checkpoint and an "If this fails" box.
4. The app: `cd app/checkout-simulator`, `pip install -r requirements.txt`, `streamlit run app.py` (mock mode by default; live
   mode needs the `.env` from Lab 4). Never commit `.env`.

## Regenerate the data and run the checks
```
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python data/generator/generate.py --check
.venv/Scripts/python -m pytest data/generator/tests app/checkout-simulator/tests -q
.venv/Scripts/python slides/lint_icons.py
```
The generator targets (kit 02 §4.4) are asserted by the tests: late rate 18–22 %, carrier-3 remote ≥ 35 %, peak ≥ 1.5× off-peak,
LightGBM holdout ROC-AUC 0.80–0.87 and ≥ 0.03 above the logistic baseline.

## Rules kept everywhere
- Trial first; paid-only features are optional and labelled. Costs are said out loud; endpoints and schedules are turned off after use.
- Synthetic data only. No secrets in the repo (`.env.example` shows the keys).
- Icons: official files only, unchanged, labelled; motion = opacity, position, uniform scale.
- Every UI-dependent step carries `⟲ verify at recording`; unknowns go to `OPEN_QUESTIONS.md`, never guessed.
