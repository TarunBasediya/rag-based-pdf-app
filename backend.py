import json
import os
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

app = FastAPI(title="RAG PDF Assistant API")

# --- CORS setup: React (localhost:5173) ko backend call karne dega ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global setup (ek hi baar hoga, app start hote waqt) ---
UPLOAD_DIR = "uploaded_pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

embeddings = OllamaEmbeddings(model="nomic-embed-text")
llm = ChatOllama(model="gpt-oss:120b-cloud", temperature=0.2, timeout=300)
checkpointer = InMemorySaver()

# Yeh dictionary current active agent aur vectorstore hold karega
state = {"agent": None, "vectorstore": None}


def build_agent_from_vectorstore(vectorstore):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # content  -> LLM ko jata hai (answer banane ke liye)
    # artifact -> sirf hamari application ke paas rehta hai (citations ke liye)
    @tool(response_format="content_and_artifact")
    def search_pdf(query: str):
        """Search the uploaded PDF document for relevant information to answer
        the user's question. Always use this tool for any question about the
        document's content."""
        retrieved_docs = retriever.invoke(query)
        if not retrieved_docs:
            return "No relevant information found in the document.", []

        content_parts = []
        sources = []
        for doc in retrieved_docs:
            # PyPDFLoader page numbers 0-indexed hote hain, user ko 1-indexed dikhao
            page = doc.metadata.get("page", 0) + 1
            content_parts.append(f"[Page {page}]: {doc.page_content}")
            sources.append({"page": page, "snippet": doc.page_content[:200]})

        return "\n\n".join(content_parts), sources

    return create_agent(
        model=llm,
        tools=[search_pdf],
        system_prompt=(
            "You are a helpful assistant answering questions about an uploaded "
            "PDF document. Use the search_pdf tool to find answers. If the "
            "information isn't in the document, say you don't know."
        ),
        checkpointer=checkpointer,
    )


# --- Pydantic Schemas ---
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default-session"

class ChatResponse(BaseModel):
    answer: str

class UploadResponse(BaseModel):
    message: str
    chunks_created: int


# --- Streaming helpers ---
def sse_line(payload: dict) -> str:
    """Ek NDJSON event: ek JSON object, ek line."""
    return json.dumps(payload, ensure_ascii=False) + "\n"


def collect_sources(agent, config) -> list:
    """Sirf current question ke tool calls ke sources nikalta hai."""
    messages = agent.get_state(config).values["messages"]
    sources = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break  # yahan se purane questions shuru ho jate hain
        if isinstance(msg, ToolMessage) and msg.artifact:
            sources.extend(msg.artifact)

    # Same page dobara aaye toh ek hi baar rakho, page order mein
    unique = {}
    for s in sources:
        unique.setdefault(s["page"], s)
    return sorted(unique.values(), key=lambda s: s["page"])


# --- Endpoint 1: PDF Upload ---
@app.post("/upload-pdf", response_model=UploadResponse)
def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # File ko disk pe save karo
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Ingestion pipeline: load -> chunk -> embed -> store
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_documents(documents)

    # Har upload ka apna unique collection, taaki purane PDF ke chunks mix na hon
    # (warna citations mein galat document ke pages aa sakte hain)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=f"doc_{uuid.uuid4().hex}",
    )

    # Naya agent banao is vectorstore ke saath, aur global state update karo
    state["vectorstore"] = vectorstore
    state["agent"] = build_agent_from_vectorstore(vectorstore)

    return UploadResponse(
        message=f"'{file.filename}' processed successfully.",
        chunks_created=len(chunks),
    )


# --- Endpoint 2: Chat (streaming NDJSON: token / sources / error events) ---
@app.post("/chat")
def chat(request: ChatRequest):
    if state["agent"] is None:
        raise HTTPException(
            status_code=400,
            detail="No PDF uploaded yet. Please upload a PDF first.",
        )

    # Local variable: stream ke beech mein naya PDF upload ho jaye toh bhi
    # is request ke liye same agent use hota rahe
    agent = state["agent"]
    config = {"configurable": {"thread_id": request.thread_id}}

    def generate():
        try:
            for chunk, _metadata in agent.stream(
                {"messages": [{"role": "user", "content": request.message}]},
                config=config,
                stream_mode="messages",
            ):
                if (
                    isinstance(chunk, AIMessageChunk)
                    and isinstance(chunk.content, str)
                    and chunk.content
                ):
                    yield sse_line({"type": "token", "content": chunk.content})

            # Answer khatam hone ke baad sources bhejo
            sources = collect_sources(agent, config)
            if sources:
                yield sse_line({"type": "sources", "sources": sources})
        except Exception as e:
            yield sse_line({"type": "error", "message": str(e)})

    return StreamingResponse(generate(), media_type="application/x-ndjson")