from langchain_ollama import OllamaEmbeddings,ChatOllama
from langchain_chroma import Chroma
from langchain.agents import create_agent

embeddings = OllamaEmbeddings(model="nomic-embed-text")

vectorestore = Chroma(
    persist_directory="./chroma_db/",
    embedding_function=embeddings,
    collection_name="nimbuscloud_handbook"
)

retriever = vectorestore.as_retriever(search_kwargs={"k":3})

#creating tool

def search_nimbuscloud_handbook(query:str)->str:
    """Search the NimbusCloud employee handbook for information about company
    policies, leave policy, remote work, performance reviews, internal tools,
    security compliance, or any other company-related question.
    Use this tool whenever the user asks anything about NimbusCloud company details."""

    retrieved_docs = retriever.invoke(query)
    if not retrieved_docs:
        return "No relevant information found"
    formatted_results=[]
    for doc in retrieved_docs:
        page_num = doc.metadata.get("page","unknown")
        formatted_results.append(f"[Page {page_num}]:{doc.page_content}")

    return "\n\n".join(formatted_results)

#model info

model = ChatOllama(
    model="llama3.1",
    temperature=0.2,
    timeout=300,
)

agent = create_agent(
    model=model,
    tools=[search_nimbuscloud_handbook],
    system_prompt=(
         "You are a helpful assistant for NimbusCloud employees. "
        "Use the search_nimbuscloud_handbook tool to answer questions about "
        "company policies. If the tool doesn't return relevant information, "
        "say you don't know rather than guessing."
    ),
)

if __name__ == "__main__":
    result= agent.invoke(
        {"messages":[
            {"role":"user","content":"How many paid leaves do I get per year?"}
        ]}

    )
    print(result["messages"][-1].content)


