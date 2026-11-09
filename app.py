#!/usr/bin/env python3
"""StudyBuddy — AI-powered study companion from PDFs/notes."""

import os, re, tempfile, json, time, asyncio, httpx
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
LLM_BASE = os.environ.get("LLM_BASE", "http://localhost:3001/v1")
LLM_KEY  = os.environ.get("LLM_KEY",  "freellmapi-658cd66399606328ed1c4158055a64909ee449bc388fa661")
PORT     = int(os.environ.get("PORT", "8000"))

CLIENT = OpenAI(base_url=LLM_BASE, api_key=LLM_KEY)

# Use "auto" — the router picks the best available model automatically
# Falls back to explicit models if auto fails
MODEL_CHAIN = ["auto", "glm-5.3-flash", "gemini-flash", "qwen3.8-flash-next"]
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="StudyBuddy")

def call_llm(messages: list[dict], max_tokens: int = 2000) -> str:
    """Call LLM with exponential-backoff retry across multiple models."""
    for attempt in range(MAX_RETRIES):
        for model in MODEL_CHAIN:
            try:
                r = CLIENT.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.3,
                )
                return r.choices[0].message.content or ""
            except Exception:
                continue
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))
    raise RuntimeError("All models exhausted after retries")


@app.get("/", response_class=HTMLResponse)
async def index():
    here = Path(__file__).parent
    html = (here / "index.html").read_text()
    return html


@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"error": "Only PDF files are accepted"}, status_code=400)

    raw = await file.read()
    text = ""
    try:
        reader = PdfReader(raw)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n\n"
    except Exception as e:
        return JSONResponse({"error": f"PDF parse error: {e}"}, status_code=422)

    if len(text) < 100:
        return JSONResponse({"error": "PDF too short or no readable text"}, status_code=400)

    return JSONResponse({"text_length": len(text), "page_count": len(reader.pages)})


@app.post("/api/study-notes")
async def generate_study_notes(request: Request):
    data = await request.json()
    text = data.get("text", "").strip()
    if len(text) < 200:
        return JSONResponse({"error": "Text too short"}, status_code=400)

    prompt = f"""You are StudyBuddy, an expert tutor. Analyze this study material and produce a comprehensive study guide in markdown.

Material ({len(text)} chars):
{text[:8000]}

Produce exactly these sections (use markdown headers ##):
## 📋 Key Concepts
- Bullet list of the most important concepts (5-8 items) with brief explanations

## 🧠 Summary
- A concise paragraph summarizing the core ideas

## 🔑 Important Definitions
- Key terms and their definitions in bullet form

## ❓ Practice Questions
- 5-7 questions to test understanding (do NOT include answers yet — user will request them)

## 📝 Quick Reference
- A small table or list of facts to memorize

Keep it focused and educational. Use markdown formatting throughout."""

    result = call_llm([{"role": "user", "content": prompt}])
    return JSONResponse({"notes": result})


@app.post("/api/generate-quizzes")
async def generate_quizzes(request: Request):
    data = await request.json()
    notes = data.get("notes") or data.get("text", "")
    count = data.get("count", 5)

    prompt = f"""Generate {count} multiple-choice quiz questions based on this study material.
Return ONLY valid JSON array (no explanation text outside the array):

{notes[:6000]}

Output format (JSON array only, no other text):
[{{"question":"...","options":["A)","B)","C)","D)","correct":0}}]
The correct field is the zero-based index of the correct answer."""

    raw = call_llm([{"role": "user", "content": prompt}], max_tokens=2000)
    # Extract JSON array from possibly-wrapped response
    m = re.search(r"\[[\s\S]*\]", raw)
    if m:
        try:
            quizzes = json.loads(m.group())
            return JSONResponse({"quizzes": quizzes})
        except json.JSONDecodeError:
            pass
    # Fallback: return raw text
    return JSONResponse({"quizzes": [{"question": raw, "options": [], "correct": 0}]})


@app.post("/api/explain")
async def explain_topic(request: Request):
    data = await request.json()
    topic = data.get("topic", "").strip()
    context = data.get("context", "")
    if not topic:
        return JSONResponse({"error": "Topic required"}, status_code=400)

    ctx_hint = f"\nRelevant context:\n{context[:2000]}" if context else ""

    prompt = f"""You are StudyBuddy, a patient and clear tutor. Explain this topic simply but thoroughly.

Topic: {topic}{ctx_hint}

Use analogies when helpful. Break complex ideas into digestible steps. End with a one-sentence takeaway."""

    result = call_llm([{"role": "user", "content": prompt}])
    return JSONResponse({"explanation": result})


@app.post("/api/memorize")
async def memorize_flashcards(request: Request):
    data = await request.json()
    text = data.get("text") or data.get("notes", "").strip()
    if len(text) < 100:
        return JSONResponse({"error": "Text too short"}, status_code=400)

    prompt = f"""Create flashcards from this study material. Return ONLY a JSON array:

{text[:5000]}

Format (JSON array only):
[{{"front":"term/concept","back":"clear definition or explanation"}}]
Create 8-12 high-quality flashcards covering key ideas."""

    raw = call_llm([{"role": "user", "content": prompt}], max_tokens=2000)
    m = re.search(r"\[[\s\S]*\]", raw)
    if m:
        try:
            cards = json.loads(m.group())
            return JSONResponse({"flashcards": cards})
        except json.JSONDecodeError:
            pass
    return JSONResponse({"flashcards": []})


if __name__ == "__main__":
    print(f"StudyBuddy starting on http://0.0.0.0:{PORT}")
    print(f"LLM endpoint: {LLM_BASE}")
    print(f"LAN URL:      http://192.168.100.32:{PORT}")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
