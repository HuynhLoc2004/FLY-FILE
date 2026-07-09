# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmartPDF is a Vietnamese PDF tools web app. It has a FastAPI backend (`backend/`) and a React + Vite frontend (`frontend/`). The primary feature is translating Vietnamese legal documents (birth certificates, marriage certificates, school transcripts, etc.) to English using AI.

## Running the Project

**Backend** (from `backend/`):
```
uvicorn main:app --reload --port 8000
```

**Frontend** (from `frontend/`):
```
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # production build
npm run lint      # ESLint
npm run preview   # preview production build
```

The frontend proxies API calls to `http://localhost:8000` — both must run simultaneously.

## Environment Variables

The backend reads these at startup:
- `GEMINI_API_KEY` — Gemini API key (has a hardcoded fallback key in `engine.py` and `html_translator.py`)
- `DEEPL_API_KEY` — optional; enables DeepL as translation backend instead of Google Translate

## Architecture

### Backend API (`backend/main.py`)

FastAPI app with one file per endpoint group. All endpoints return `StreamingResponse` with binary files or JSON. Key API routes:
- `POST /api/merge` — merge PDFs
- `POST /api/merge-pages` — merge specific pages by manifest JSON
- `POST /api/compress` — compress PDF (level: low/medium/high)
- `POST /api/split` — split PDF by page ranges, returns ZIP
- `POST /api/translate-pdf` — structured bilingual JSON (block-by-block)
- `POST /api/translate-pdf/html` — HTML-based translation (better layout fidelity)
- `POST /api/translate-pdf/download-docx` — direct DOCX download
- `POST /api/translate-pdf/download-pdf` — HTML→PDF via WeasyPrint
- `POST /api/pdf-to-word` — PDF to DOCX conversion
- `POST /api/pdf-to-images` — render PDF pages as base64 images
- `POST /api/images-to-pdf`, `POST /api/word-to-pdf`, `POST /api/convert-image`

### Translation Pipeline (`backend/services/translation/`)

Two parallel translation pipelines:

**1. Structured/block pipeline** (`extractor.py` → `engine.py` → `docx_builder.py`):
- `extractor.py`: Uses PyMuPDF (`fitz`) to extract text blocks and tables per page with layout metadata (bbox, font size, bold, alignment, heading detection)
- `engine.py`: Orchestrates translation — detects doc type, loads glossary, translates blocks concurrently (up to 8 workers). Primary translator: Gemini (`gemini-3.5-flash`). Fallbacks: DeepL → Google Translate. Birth certificates get special template-based translation via `template_translator.py`.
- `docx_builder.py`: Builds `.docx` from translated blocks, preserving formatting

**2. HTML pipeline** (`html_extractor.py` → `html_translator.py`):
- `html_extractor.py`: Converts PDF pages to structured HTML preserving visual layout
- `html_translator.py`: Sends HTML to Gemini with instructions to translate text while preserving all tags/styles. Handles scanned (image) PDFs via OCR path. Scanned pages are paired together (2 at a time) for better form reconstruction. Translation runs 4 pages in parallel.

**Document type detection** (`document_detector.py`): Classifies PDFs into types (`birth_cert`, `marriage_cert`, `school_transcript`, `employment`, `consular`, `general_legal`) based on keyword matching.

**Glossaries** (`glossaries/`): Each doc type has a glossary of Vietnamese→English term mappings. `engine.py` passes these as context to Gemini or uses placeholder substitution for DeepL/Google.

### Frontend (`frontend/src/`)

React SPA with React Router. Routes:
- `/` → `Home` page (tool grid)
- `/tool/:toolId` → `ToolPage` (dispatches to the appropriate Workspace component)

**Workspace components** each handle one tool's full UI lifecycle: file upload → API call → result display/download. `TranslateWorkspace` has a two-mode UI (HTML pipeline preferred, bilingual side-by-side view).

`ToolPage` owns the initial file drop/select state and passes `initialFiles` to the active Workspace. The `translate` tool bypasses this — `TranslateWorkspace` manages its own file input.

### PDF processing libraries
- `PyMuPDF` (`fitz`) — PDF parsing, rendering, splitting, merging
- `pypdf` / `pikepdf` — used in compressor and merger services
- `python-docx` — DOCX building
- `WeasyPrint` — HTML→PDF rendering
- `docx2pdf` — Word→PDF conversion (requires LibreOffice or MS Word on host)
- `deep-translator` — Google Translate free fallback
- `deepl` — optional DeepL API client
