# System Workflow

## Overview

The system transforms radiology reports into plain-language patient summaries through an automated pipeline with validation and human-in-the-loop review.

## Workflow

```
Input (Report) → Entity Extraction → RAG (Knowledge Retrieval) → Summary Agent → Validation Loop → Radiologist → UI
```

## Components

### 1. Entity Extraction Pipeline
**Purpose**: Extract clinical facts from the raw report to create a "ground truth" list.

**Tool**: `EntityExtractionPipeline` using `SpacyComponent`
- Uses scispaCy with UMLS (Unified Medical Language System) linker
- Extracts technical terms, anatomy, measurements, and findings
- Outputs structured entities with confidence scores and UMLS definitions

**Output**: `EntityExtractionResult` containing:
- Findings (e.g., "5mm nodule", "mild opacification")
- Anatomy (e.g., "right lower lobe", "pleural space")
- Measurements (e.g., "5mm")
- Uncertainty phrases

### 2. RAG Service (Knowledge Retrieval)
**Purpose**: Retrieve trusted, standardized definitions for medical terms.

**Tools**:
- `RAGService` with hybrid retrieval approach
- `SpacyComponent` (reused) for UMLS authoritative definitions
- `GlossaryBuilder` for PLABA/Cochrane dataset lookups

**Process**:
1. Takes extracted entities from Step 1
2. Retrieves definitions from UMLS (primary source)
3. Falls back to PLABA/Cochrane datasets for plain language translations
4. Returns a "Definitions Context" dictionary

**Output**: Dictionary mapping medical terms to their plain language definitions

### 3. Summary Agent
**Purpose**: Generate initial plain-language summary from technical report.

**Tool**: `SummarizerAgent` using LLM (OpenAI client)

**Inputs**:
- Original radiology report
- Extracted entities (from Step 1)
- Retrieved definitions (from Step 2)

**Key Instructions**:
- Use 6th-8th grade reading level
- Include every item from entity list
- Do not invent medical facts
- Use provided definitions for medical terms
- No medical advice or alarmist language

**Output**: Initial draft plain-language summary

### 4. Validation Pipeline
**Purpose**: Automated quality checks to ensure safety, accuracy, and readability.

**Tool**: `ValidationPipeline` orchestrating multiple validation components

**Validation Checks**:

1. **Fidelity Check** (`FidelityComponent`)
   - Ensures all critical entities from original report appear in summary
   - Uses fuzzy string matching to handle variations
   - Flags missing findings, anatomy, or measurements

2. **Hallucination Check** (`HallucinationComponent`)
   - Detects entities in summary not present in original report
   - Uses LLM to extract entities from summary and compares to original
   - Prevents AI from inventing medical facts

3. **Readability Check** (`ReadabilityComponent`)
   - Calculates Flesch-Kincaid Grade Level
   - Ensures summary is at 6th-8th grade reading level
   - Flags summaries that are too complex

4. **Safety Check** (`SafetyComponent`)
   - Scans for banned keywords ("emergency", "call 911", "you must")
   - Prevents alarmist tone or unintended medical advice
   - Ensures appropriate patient communication

5. **Entity Matching** (`EntityMatchingComponent`)
   - Validates entity alignment between original and summary

**Output**: `ValidationReport` with pass/fail status and error messages

### 5. Refinement Loop
**Purpose**: Automatically correct validation failures.

**Tool**: `RefinerAgent` using LLM

**Process**:
1. If validation fails, collects all error messages
2. Sends draft summary + specific errors back to LLM
3. LLM generates revised summary addressing the errors
4. Revised summary goes back through validation pipeline
5. Loop continues until validation passes or max retries reached

**Output**: Refined summary that should pass validation

### 6. Human-in-the-Loop (HITL) UI
**Purpose**: Radiologist review and approval before sending to patient.

**Tool**: Next.js/React frontend (`HITLDashboard`)

**Features**:
- **Side-by-side view**: Original report and AI summary
- **Validation badges**: Visual indicators for each validation check
- **Entity list**: Shows extracted findings, anatomy, measurements
- **Sentence mapping**: Hover over summary sentences to see source in original
- **Actions**:
  - Approve: Send summary to patient
  - Edit: Manually modify summary
  - Reject: Flag for review/reprocessing

**Backend API** (`/summaries`):
- `POST /summarize`: Generate summary
- `POST /{id}/approve`: Approve summary
- `POST /{id}/improve`: Save manual edits
- `GET /{id}/download`: Download approved summary

## Orchestration

The entire workflow is orchestrated by `PlainLanguageReportAgent` using **LangGraph** (a state machine framework for building agent workflows).

### LangGraph Architecture

**State Management**: Uses a `TypedDict` (`PlainLanguageReportAgentState`) to maintain state across nodes:
- `medical_report`: Original report text
- `extracted_entities`: Entity extraction results
- `retrieved_definitions`: RAG-retrieved definitions dictionary
- `plain_language_report`: Generated summary
- `validation_passed`: Boolean validation status
- `validation_reasons`: List of error messages

**Graph Structure** (built with `StateGraph`):

1. **Entity Extraction Node** (`entity_extraction_pipeline`)
   - Extracts entities from report
   - Updates state with `extracted_entities`

2. **RAG Retrieval Node** (`rag_retrieval`)
   - Retrieves medical term definitions
   - Updates state with `retrieved_definitions`

3. **Summarization Node** (`summarization_agent`)
   - Generates initial summary
   - Updates state with `plain_language_report`

4. **Validation Node** (`validation_pipeline`)
   - Runs all validation checks
   - Updates state with `validation_passed` and `validation_reasons`

5. **Conditional Edge** (`_validation_gate`)
   - Routes based on validation result:
     - If `validation_passed == True` → `END` (workflow complete)
     - If `validation_passed == False` → `refiner_agent` (refinement needed)

6. **Refinement Node** (`refiner_agent`)
   - Generates corrected summary based on validation errors
   - Updates state with new `plain_language_report`

7. **Loop Back Edge**
   - Refined summary automatically goes back to `validation_pipeline`
   - Creates a self-correcting loop until validation passes

**Graph Flow**:
```
Entry → entity_extraction_pipeline → rag_retrieval → summarization_agent 
→ validation_pipeline → [conditional] → refiner_agent → validation_pipeline → ...
```

The graph continues iterating until validation passes or max retries are reached. LangGraph handles state persistence and conditional routing automatically.

## Key Technologies

- **NLP**: scispaCy with UMLS linker for entity extraction
- **LLM**: OpenAI API for summarization and refinement
- **Validation**: Custom Python components with fuzzy matching (rapidfuzz)
- **Orchestration**: **LangGraph** (StateGraph) for workflow management and state machine logic
- **State Management**: TypedDict for type-safe state passing between nodes
- **Frontend**: Next.js/React with TypeScript
- **Backend**: FastAPI (Python)
