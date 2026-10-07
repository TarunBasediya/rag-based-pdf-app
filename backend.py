from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import shutil
import os

from langchain_core.messages import AIMessageChunk
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

    def search_pdf(query: str) -> str:
        """Search the uploaded PDF document for relevant information to answer
        the user's question. Always use this tool for any question about the
        document's content."""
        retrieved_docs = retriever.invoke(query)
        if not retrieved_docs:
            return "No relevant information found in the document."
        results = []
        for doc in retrieved_docs:
            page_num = doc.metadata.get("page", "unknown")
            results.append(f"[Page {page_num}]: {doc.page_content}")
        return "\n\n".join(results)

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

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="uploaded_doc",
    )

    # Naya agent banao is vectorstore ke saath, aur global state update karo
    state["vectorstore"] = vectorstore
    state["agent"] = build_agent_from_vectorstore(vectorstore)

    return UploadResponse(
        message=f"'{file.filename}' processed successfully.",
        chunks_created=len(chunks),
    )


# --- Endpoint 2: Chat (streaming) ---
@app.post("/chat")
def chat(request: ChatRequest):
    if state["agent"] is None:
        raise HTTPException(
            status_code=400,
            detail="No PDF uploaded yet. Please upload a PDF first.",
        )

    config = {"configurable": {"thread_id": request.thread_id}}

    def generate_chunks():
        for message_chunk, _metadata in state["agent"].stream(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
            stream_mode="messages",
        ):
            if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                yield message_chunk.content

    return StreamingResponse(generate_chunks(), media_type="text/plain")