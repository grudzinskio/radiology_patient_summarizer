# Radiology Patient Summarizer

An AI-driven system that turns radiology (and biomedical) reports into **plain-language patient summaries**, with automated validation and a **human-in-the-loop** review UI. Built for the Hack 4 Health hackathon (MSOE / Medical College of Wisconsin).

---

## What It Does

- **Input**: Raw radiology or biomedical report text  
- **Output**: Patient-friendly summary at ~6th–8th grade reading level, with:
  - **Accuracy & fidelity**: No invented findings; entities and measurements preserved
  - **Safety**: No medical advice, false reassurance, or alarmist language
  - **Explainability**: Sentence-to-source mapping and confidence cues
  - **Review workflow**: Radiologist can approve, edit, or reject before release

See [docs/system-workflow.md](docs/system-workflow.md) for the full pipeline (entity extraction → RAG → summarization → validation → refinement → HITL UI).

---

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/problem-context.md](docs/problem-context.md) | Hack 4 Health problem statement, judging criteria, presentation rules |
| [docs/hackathon-instructions.md](docs/hackathon-instructions.md) | Hackathon sign-up, rubric link, **LLM API setup** (Gemini, Rosie Llama, OpenAI) |
| [docs/system-workflow.md](docs/system-workflow.md) | End-to-end pipeline and LangGraph orchestration |
| [docs/README.md](docs/README.md) | Index of all docs |

---

## Repository Layout

```
radiology_patient_summarizer-1/
├── backend/                    # FastAPI backend
│   ├── src/
│   │   ├── main.py             # App entry, CORS, lifespan (load NLP model)
│   │   ├── routers/            # health, summaries
│   │   ├── schemas/            # Pydantic models (summaries, provenance, validation)
│   │   ├── services/
│   │   │   └── summaries/      # Entity extraction, RAG, summarizer, validation, refiner, agent
│   │   └── utils/clients/     # LLM clients
│   └── README.md               # Backend setup and run
├── frontend/
│   └── app/                    # Next.js app
│       ├── app/                # layout, page (HITL dashboard)
│       ├── components/         # hitl-dashboard, report-panel, validation-badges, etc.
│       ├── lib/                # api.ts, types.ts
│       └── package.json
├── data/
│   ├── merged_plain_language_dataset.txt   # Biomedical → plain-language pairs (training/RAG)
│   └── DATASET_DESCRIPTIONS.pdf            # Dataset sources and descriptions
├── docs/                       # All project docs (see Documentation above)
├── notebooks/                  # Experiments (RadBERT, extraction, Rosie/Llama)
├── sample_reports.txt          # Example radiology reports for testing
├── requirements.txt            # Python deps (backend)
└── README.md                   # This file
```

---

## Getting Started

### Prerequisites

- **Python 3.12+** (backend)
- **Node.js 18+** (frontend)
- **LLM API**: Set `OPENAI_API_KEY` (or use Gemini / Rosie Llama; see [docs/hackathon-instructions.md](docs/hackathon-instructions.md))

### Backend

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r ../requirements.txt
# Optional: scispaCy model for entity extraction
# pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
```

Run from **project root**:

```bash
python backend/src/main.py
```

- API: **http://127.0.0.1:8000**
- Docs: **http://127.0.0.1:8000/docs**

See [backend/README.md](backend/README.md) for more detail.

### Frontend

```bash
cd frontend/app
npm install
npm run dev
```

- App: **http://localhost:3000**

The UI is the HITL dashboard: submit a report → get a plain-language summary, validation badges, entity list, and sentence mapping; then approve, edit, or reject.

---

## Data

- **`data/merged_plain_language_dataset.txt`**  
  Merged biomedical → plain-language pairs (e.g. CELLS, Cochrane) used for RAG/glossary and training context. See **`data/DATASET_DESCRIPTIONS.pdf`** for sources and descriptions.

- **`sample_reports.txt`**  
  Example radiology reports (chest X-ray, abdominal CT, brain MRI, etc.) for quick testing.

**Note:** If you use Git LFS for large files, run `git lfs install` and `git lfs pull` as in [docs/hackathon-instructions.md](docs/hackathon-instructions.md).

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/summaries` | List summaries (sidebar) |
| GET | `/summaries/{id}` | Get one summary (original + plain-language + entities + validation + provenance) |
| POST | `/summaries/summarize` | Generate summary from `medical_report` (+ optional `patient_id`, `report_id`) |
| POST | `/summaries/{id}/approve` | Approve summary (optional `radiologist_notes`) |
| POST | `/summaries/{id}/improve` | Save edited summary and optional notes |
| GET | `/summaries/{id}/download` | Download approved summary as text |

Request/response shapes are in `backend/src/schemas/summaries.py` and frontend `lib/types.ts`.

---

## Tech Stack

| Layer | Stack |
|-------|--------|
| **Backend** | FastAPI, Python 3.12+, Pydantic |
| **NLP / entities** | scispaCy, medspacy, UMLS linker |
| **Orchestration** | LangGraph (StateGraph), TypedDict state |
| **LLM** | OpenAI API (configurable; see [docs/hackathon-instructions.md](docs/hackathon-instructions.md) for Gemini / Rosie) |
| **Validation** | textstat (readability), rapidfuzz (fidelity), custom safety/provenance checks |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind, Radix UI, shadcn/ui-style components |

---

## Hackathon Context

This project was built for **Hack 4 Health** (MSOE / MCW). Judging is based on the **presentation** (design choices, safeguards, validation pipelines, safety, and real-world readiness), not on code review. For problem statement, rubric, and LLM setup, use:

- [docs/problem-context.md](docs/problem-context.md)
- [docs/hackathon-instructions.md](docs/hackathon-instructions.md)

---

## License & Credits

- Hack 4 Health is run by MSOE AI-Club in collaboration with the Medical College of Wisconsin.
- Plain-language datasets are from public biomedical sources (see `data/DATASET_DESCRIPTIONS.pdf`).
