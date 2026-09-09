import os
import re
from pathlib import Path
from typing import List

import numpy as np
import uvicorn
from dotenv import load_dotenv
from docx import Document
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from openai import OpenAI
from sentence_transformers import SentenceTransformer


load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
RAW_DOCS_DIR = PROJECT_DIR / "raw_docs"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

app = FastAPI(title="WISOL 문서 챗봇")

EMBED_MODEL = None
DOCUMENT_CHUNKS: List[str] = []
DOCUMENT_EMBEDDINGS: np.ndarray | None = None
GROQ_CLIENT: OpenAI | None = None
GROQ_MODEL: str | None = None


def read_docx_to_markdown(path: Path) -> str:
    doc = Document(path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    body = "\n".join(paragraphs)
    return f"## {path.stem}\n\n{body}"


def split_markdown_to_chunks(markdown_text: str, chunk_size: int = 800) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", markdown_text) if p.strip()]
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n{paragraph}" if current else paragraph
        else:
            if current:
                chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())

    return chunks


def load_documents() -> List[str]:
    if not RAW_DOCS_DIR.exists():
        return []

    docs: List[str] = []
    for doc_path in sorted(RAW_DOCS_DIR.glob("*.docx")):
        docs.append(read_docx_to_markdown(doc_path))
    return docs


def initialize_index():
    global EMBED_MODEL, DOCUMENT_CHUNKS, DOCUMENT_EMBEDDINGS

    markdown_docs = load_documents()
    chunks: List[str] = []
    for doc in markdown_docs:
        chunks.extend(split_markdown_to_chunks(doc))

    DOCUMENT_CHUNKS = chunks
    if not chunks:
        DOCUMENT_EMBEDDINGS = np.empty((0, 1), dtype=np.float32)
        return

    EMBED_MODEL = SentenceTransformer(EMBEDDING_MODEL)
    passages = [f"passage: {chunk}" for chunk in chunks]
    vectors = EMBED_MODEL.encode(passages, normalize_embeddings=True, show_progress_bar=False)
    DOCUMENT_EMBEDDINGS = np.asarray(vectors, dtype=np.float32)


def get_groq_client() -> OpenAI:
    global GROQ_CLIENT, GROQ_MODEL
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY가 설정되지 않았습니다.")

    if GROQ_CLIENT is None:
        GROQ_CLIENT = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    if GROQ_MODEL is None:
        try:
            models = GROQ_CLIENT.models.list()
            available = [m.id for m in models.data]
            preferred_order = [
                "openai/gpt-oss-20b",
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ]
            for preferred in preferred_order:
                if preferred in available:
                    GROQ_MODEL = preferred
                    break
            if GROQ_MODEL is None:
                GROQ_MODEL = available[0]
        except Exception:
            GROQ_MODEL = "llama-3.3-70b-versatile"

    return GROQ_CLIENT


def find_relevant_chunks(question: str, top_k: int = 4) -> List[str]:
    if EMBED_MODEL is None or DOCUMENT_EMBEDDINGS is None or len(DOCUMENT_CHUNKS) == 0:
        return []

    query_vector = EMBED_MODEL.encode([f"query: {question}"], normalize_embeddings=True, show_progress_bar=False)
    query_vector = np.asarray(query_vector, dtype=np.float32)[0]
    similarities = DOCUMENT_EMBEDDINGS @ query_vector

    if similarities.size == 0:
        return []

    ranked = np.argsort(similarities)[::-1][:top_k]
    top_chunks = [DOCUMENT_CHUNKS[int(i)] for i in ranked]

    if not top_chunks:
        return []

    if float(similarities[ranked[0]]) < 0.15:
        return []

    return top_chunks


def clean_answer(answer: str) -> str:
    cleaned = re.sub(r"\s+", " ", answer or "").strip()
    cleaned = cleaned.replace("\n", " ")
    if not cleaned:
        return "문서에서 확인할 수 없습니다"
    if cleaned.startswith("문서에서 확인할 수 없습니다"):
        return "문서에서 확인할 수 없습니다"

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return cleaned[:200].strip()

    filtered = []
    for sentence in sentences:
        if len(sentence) < 3:
            continue
        filtered.append(sentence)

    if not filtered:
        return cleaned[:200].strip()

    final_sentences = filtered[:4]
    final = " ".join(final_sentences)

    if len(final) > 300:
        words = final.split()
        if len(words) > 35:
            final = " ".join(words[:35]).rstrip(".,!?:;") + "..."

    if final.count(".") == 0 and final.count("!") == 0 and final.count("?") == 0:
        if len(final) > 200:
            return final[:200].rsplit(" ", 1)[0] + "..."
    return final


def answer_question(question: str) -> str:
    if not question:
        return "문서에서 확인할 수 없습니다"

    relevant = find_relevant_chunks(question)
    if not relevant:
        return "문서에서 확인할 수 없습니다"

    try:
        client = get_groq_client()
    except Exception:
        return "문서에서 확인할 수 없습니다"

    context = "\n\n".join(relevant)
    system_prompt = (
        "당신은 문서 기반 QA 어시스턴트입니다. "
        "주어진 문서 내용만 근거로 답하고, 문서에 없는 내용은 절대 추측하지 마세요. "
        "답변은 2~4문장으로 간결하게 작성하세요. "
        "문서에 해당 내용이 없으면 반드시 '문서에서 확인할 수 없습니다'라고만 답하세요."
    )
    user_prompt = f"질문: {question}\n\n문서 내용:\n{context}"

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=180,
        )
        answer = response.choices[0].message.content
        return clean_answer(answer)
    except Exception:
        return "문서에서 확인할 수 없습니다"


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!doctype html>
    <html lang="ko">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>WISOL 문서 챗봇</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f5f7fb; margin: 0; padding: 32px; color: #1f2937; }
        .box { max-width: 900px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 12px 30px rgba(0,0,0,0.08); }
        h1 { margin-top: 0; }
        textarea { width: 100%; min-height: 110px; padding: 12px; border: 1px solid #d1d5db; border-radius: 10px; font-size: 16px; }
        button { background: #2563eb; color: white; border: none; border-radius: 10px; padding: 12px 18px; font-size: 16px; cursor: pointer; }
        .answer { margin-top: 20px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 12px; padding: 18px; line-height: 1.7; }
      </style>
    </head>
    <body>
      <div class="box">
        <h1>WISOL 문서 챗봇</h1>
        <textarea id="question" placeholder="예: 해외출장 프로세스"></textarea>
        <div style="margin-top: 16px;">
          <button onclick="ask()">질문하기</button>
        </div>
        <div class="answer" id="answer">질문을 입력하고 답변을 받아보세요.</div>
      </div>

      <script>
        async function ask() {
          const q = document.getElementById('question').value.trim();
          if (!q) {
            document.getElementById('answer').textContent = '질문을 입력해주세요.';
            return;
          }
          document.getElementById('answer').textContent = '답변을 생성 중입니다...';
          const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ question: q })
          });
          const data = await response.json();
          document.getElementById('answer').textContent = data.answer || '문서에서 확인할 수 없습니다';
        }
      </script>
    </body>
    </html>
    """


@app.post("/api/chat")
def chat(payload: dict):
    question = str(payload.get("question", "")).strip()
    return {"answer": answer_question(question)}


initialize_index()


if __name__ == "__main__":
    uvicorn.run("chatbot:app", host="0.0.0.0", port=8000, reload=False)
