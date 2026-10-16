from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.conversation_service import ConversationService
from app.rag_service import RAGService


settings = get_settings()

# Conversation memory
conversation_service = ConversationService(max_messages=6)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the RAG service once when the API starts.
    """
    print("Initializing Almamlaka RAG Service...")

    app.state.rag = RAGService(
        data_dir=str(settings.data_dir)
    )

    print("RAG Service ready!")

    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    sources: list[dict]


@app.get("/api/health")
def health() -> dict:
    pdfs = sorted(
        p.name for p in settings.data_dir.glob("*.pdf")
    )

    return {
        "status": "ok",
        "env": settings.app_env,
        "documents": pdfs
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Answer questions using document-grounded RAG.
    Supports multi-turn conversations.
    """

    session_id = request.session_id or str(uuid4())

    try:
        # Retrieve previous conversation messages
        history = conversation_service.get_history(
            session_id
        )

        # Generate RAG answer
        result = app.state.rag.ask(
            question=request.question,
            conversation_history=history,
            top_k=6
        )

        # Save conversation history
        conversation_service.add_message(
            session_id,
            "user",
            request.question
        )

        conversation_service.add_message(
            session_id,
            "assistant",
            result["answer"]
        )

        return ChatResponse(
            session_id=session_id,
            question=request.question,
            answer=result["answer"],
            sources=result["sources"]
        )

    except Exception as exc:
        print(f"Chat API error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question."
        ) from exc


# Serve the frontend from the same origin. Mounted last so /api/* routes match first.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

if FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend"
    )