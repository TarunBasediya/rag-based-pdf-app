from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
import sys

def build_agent():
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings,
        collection_name="nimbuscloud_handbook",
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    def search_nimbuscloud_handbook(query: str) -> str:
        """Search the NimbusCloud employee handbook for information about company
        policies, leave policy, remote work, performance reviews, internal tools,
        security compliance, or any other company-related question."""
        retrieved_docs = retriever.invoke(query)
        if not retrieved_docs:
            return "No relevant information found in the handbook."
        formatted_results = []
        for doc in retrieved_docs:
            page_num = doc.metadata.get("page", "unknown")
            formatted_results.append(f"[Page {page_num}]: {doc.page_content}")
        return "\n\n".join(formatted_results)

    model = ChatOllama(model="llama3.1", temperature=0.2, timeout=300)
    checkpointer = InMemorySaver()

    agent = create_agent(
        model=model,
        tools=[search_nimbuscloud_handbook],
        system_prompt=(
            "You are a helpful assistant for NimbusCloud employees. "
            "Use the search_nimbuscloud_handbook tool to answer questions about "
            "company policies. If the tool doesn't return relevant information, "
            "say you don't know rather than guessing."
        ),
        checkpointer=checkpointer,
    )
    return agent


def main():
    print("=" * 60)
    print("NimbusCloud Handbook Assistant (type 'exit' to quit)")
    print("=" * 60)

    agent = build_agent()
    config = {"configurable": {"thread_id": "cli-session"}}

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            sys.exit(0)

        if user_input.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )
            answer = result["messages"][-1].content
            print(f"\nAssistant: {answer}")
        except Exception as e:
            print(f"\n[Error occurred: {e}]")


if __name__ == "__main__":
    main()