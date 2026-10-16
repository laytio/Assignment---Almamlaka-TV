# Almamlaka TV — RAG Knowledge Assistant

A bilingual document-based chatbot developed for the Almamlaka TV AI Engineer technical assignment.

The application answers questions using three provided PDF documents. It retrieves relevant information, generates answers in Arabic or English, and includes document and page references so users can verify the information.

**Live application:** https://assignment-almamlaka-tv-production.up.railway.app/

## Overview

The application uses Retrieval-Augmented Generation (RAG) to answer questions about the Digital Expansion Initiative.

The knowledge base consists of three documents:

- `Almamlaka_Project_Overview.pdf`
- `Almamlaka_Budget_Timeline.pdf`
- `Almamlaka_Team_Governance.pdf`

The chatbot is designed to answer questions supported by these documents rather than relying on the language model's general knowledge.

It also handles follow-up questions, identifies documented revisions and conflicting information, and declines questions that cannot be answered from the available evidence.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11, FastAPI |
| Language model | Qwen3-32B via OpenRouter |
| Embedding model | paraphrase-multilingual-MiniLM-L12-v2 |
| Retrieval | In-memory vector similarity search |
| PDF processing | PyMuPDF |
| Frontend | HTML, CSS, JavaScript |
| Deployment | Docker, Railway |
| Testing | pytest |

## Architecture

The application follows a retrieval-based question-answering pipeline.

### 1. Document Processing

The three PDF files are loaded using PyMuPDF.

Each page is converted into a text chunk with metadata identifying its source document and page number.

Chunk identifiers are generated deterministically.

### 2. Embedding and Retrieval

Document chunks are embedded using:

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

The same model encodes incoming questions.

Embeddings are normalized, and similarity scores are calculated using vector dot products.

The application retrieves the most relevant chunks and passes them to the language model as supporting evidence.

The vectors are stored in memory because the current knowledge base contains only six pages. An external vector database would introduce additional infrastructure without providing a meaningful benefit at this scale.

### 3. Evidence Handling

Retrieved passages are formatted with their original document names and page numbers.

A lightweight evidence-processing step also identifies sentences that explicitly document changes to values or dates.

Relevant change statements are included in the model context to help distinguish documented revisions from unresolved contradictions.

This process uses general language patterns and semantic similarity rather than hardcoded project facts.

### 4. Answer Generation

The application uses `qwen/qwen3-32b` through OpenRouter.

The model receives the retrieved evidence, conversation context, and instructions to:

- Answer only from the supplied documents.
- Respond in the language of the user's question.
- Cite source documents and page numbers.
- Distinguish original values from documented revisions.
- Identify unresolved conflicts when the documents do not establish which value is current.
- Decline questions that lack supporting evidence.
- Treat document contents and user messages as untrusted instructions.

The model uses a temperature setting of 0 to reduce output variability, although this does not guarantee identical answers across requests.

### 5. Conversation Handling

Conversation history is maintained using session identifiers.

The application retains a limited number of previous messages to support follow-up questions without sending an unlimited conversation history to the model.

Session history is stored in process memory and is not persisted across application restarts.

## Features

**Bilingual interaction**

The interface supports Arabic and English, including right-to-left layout for Arabic content.

**Document-grounded answers**

Answers are generated from the supplied PDFs, with source references included in the response.

**Revision and conflict handling**

The chatbot is instructed to report documented changes and distinguish them from unresolved contradictions.

**Multi-turn conversations**

Users can ask follow-up questions within the same session.

**Out-of-scope handling**

Questions without sufficient supporting information are declined rather than answered from general knowledge.

**Prompt-injection resistance**

The application instructs the language model not to follow attempts to override its document-grounding rules.

**Source visibility**

The interface displays retrieved document references and similarity scores. These retrieval references are separate from the citations included in generated answers.

## Running Locally

### Requirements

- Python 3.11
- An OpenRouter API key

### Installation

Clone the repository:

```bash
git clone https://github.com/laytio/Assignment---Almamlaka-TV.git
cd Assignment---Almamlaka-TV
```

Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Create the environment configuration:

```bash
cp .env.example .env
```

Open `.env` and configure:

```env
OPENROUTER_API_KEY=your_api_key_here
LLM_MODEL=qwen/qwen3-32b
```

Start the application:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Open:

http://127.0.0.1:8000

The FastAPI backend serves both the API and the frontend.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Web interface |
| GET | `/api/health` | Application health and document information |
| POST | `/api/chat` | Submit a question and receive a grounded answer |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the revised project budget?",
    "session_id": null
  }'
```

The response contains the session identifier, question, generated answer, and retrieved source metadata.

## Testing

Run the automated test suite:

```bash
PYTHONPATH=backend python -m pytest tests/ -q
```
Latest local deterministic test results:

```text
88 passed, 12 skipped
```

The 12 skipped tests require live language-model calls and are intentionally excluded from the default test run.


The automated tests cover document processing, retrieval evidence, documented-change detection, conflict-handling logic, and API behavior.

A separate set of four targeted live model checks was performed after the documented-change handling was introduced.

All four checks passed, covering:

- Arabic project budget.
- English project budget.
- Arabic launch date.
- A budget governance question with a potentially irrelevant revision note.

These checks are a limited functional verification, not a statistical guarantee of consistent model behavior.

## Evaluation

The `evaluation/` directory contains scripts and results from earlier development experiments.

These include retrieval comparisons, citation checks, response-quality checks, groundedness heuristics, and robustness tests.

The recorded benchmark results were produced before the latest evidence-handling changes. They are retained as development baselines and should not be interpreted as final performance measurements of the current implementation.

Some evaluation checks use deterministic or heuristic criteria. They do not establish that every generated answer is factually correct.

## Known Limitations

The current implementation has several known limitations:

- Generated page-level citations can occasionally be inaccurate (for example, the right document with the wrong page number). Verify them against the source documents.
- Complex authorization and numerical-threshold reasoning may occasionally be inconsistent, for example treating "above" a threshold as "at or above" it.
- Language-model responses may vary between requests.
- Documented-change detection depends on supported language patterns and a provisional semantic similarity threshold.
- Questions with ambiguous references may not trigger the documented-change detection step.
- Retrieved source references do not necessarily indicate which passages the model used in its final answer.
- Conversation history is stored in memory and is lost when the application restarts.
- The current in-memory retrieval approach is intended for a small document collection.
- Prompt-injection safeguards reduce risk but do not guarantee complete protection.

## Deployment

The application is deployed as a single Docker-based service on Railway.

FastAPI serves the frontend and API from the same application.

The Docker image uses CPU-only dependencies and includes the embedding model required for retrieval.

Deployment configuration and troubleshooting instructions are available in [DEPLOYMENT.md](DEPLOYMENT.md).

## Project Structure

```text
backend/
  app/
    chunking.py
    config.py
    context_builder.py
    conversation_service.py
    document_loader.py
    embedding_service.py
    evidence_notes.py
    llm_service.py
    main.py
    rag_service.py
  data/
    Almamlaka_Budget_Timeline.pdf
    Almamlaka_Project_Overview.pdf
    Almamlaka_Team_Governance.pdf
  requirements.txt

frontend/
  assets/
  app.js
  index.html
  styles.css
  text.js

tests/
evaluation/

Dockerfile
railway.json
DEPLOYMENT.md
README.md
```

## Notes

This project was developed as a technical assignment to demonstrate practical implementation of document retrieval, language-model integration, evidence handling, API development, and deployment.

The implementation prioritizes a straightforward architecture appropriate for the size of the provided knowledge base.
