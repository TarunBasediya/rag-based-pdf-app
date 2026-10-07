from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="nimbuscloud_handbook",
)

retriever = vectorstore.as_retriever(search_kwargs={"k":3})

def search_nimbuscloud_handbook(query: str) -> str:
    """Search the NimbusCloud employee handbook for information about company
    policies, leave policy, remote work, performance reviews, internal tools,
    security compliance, or any other company-related question.
    Use this tool whenever the user asks anything about NimbusCloud company details."""
    retrieved_docs = retriever.invoke(query)
    if not retrieved_docs:
        return "No relevant information found in the handbook."
    formatted_results = []
    for doc in retrieved_docs:
        page_num = doc.metadata.get("page", "unknown")
        formatted_results.append(f"[Page {page_num}]: {doc.page_content}")
    return "\n\n".join(formatted_results)

def get_current_date() -> str:
    """Returns today's date. Use this when the user asks about today's date,
    or needs to calculate something relative to today (like deadlines)."""
    from datetime import date
    return str(date.today())

model = ChatOllama(model="llama3.1", temperature=0.2, timeout=300)

# --- Naya: Checkpointer banaya, memory ke liye ---
checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=[search_nimbuscloud_handbook, get_current_date],
    system_prompt=(
        "You are a helpful assistant for NimbusCloud employees. "
        "Use the search_nimbuscloud_handbook tool to answer questions about "
        "company policies. If the tool doesn't return relevant information, "
        "say you don't know rather than guessing."
    ),
    checkpointer=checkpointer,   # yahan attach kiya
)


if __name__ == "__main__":
    # thread_id ek unique conversation identify karta hai
    config = {"configurable": {"thread_id": "user-tarun-session-1"}}

    # Pehla question
    result1 = agent.invoke(
        {"messages": [{"role": "user", "content": "How many paid leaves do employees get?"}]},
        config=config,
    )
    print("Q1 Answer:", result1["messages"][-1].content)

    # Follow-up question - "it" ka reference maternity leave se hai, but humne "maternity" bola context mein
    result2 = agent.invoke(
        {"messages": [{"role": "user", "content": "And how many weeks of maternity leave is that?"}]},
        config=config,
    )
    print("Q2 Answer:", result2["messages"][-1].content)