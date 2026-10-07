from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Yeh define karta hai ki request body mein kya aana chahiye
class ChatRequest(BaseModel):
    message: str

# Yeh define karta hai ki response mein kya jayega
class ChatResponse(BaseModel):
    answer: str

@app.get("/")
def read_root():
    return {"message": "Hello, this is my first API!"}

@app.get("/greet/{name}")
def greet(name: str):
    return {"greeting": f"Hello, {name}!"}

@app.post("/chat")
def chat(request: ChatRequest):
    # request.message se hum bheja gaya text access kar sakte hain
    return ChatResponse(answer=f"You said: {request.message}")