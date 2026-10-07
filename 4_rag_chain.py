from langchain_ollama import OllamaEmbeddings,ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

#step 1 - load existing vector store
embeddings = OllamaEmbeddings(model="nomic-embed-text")

vectorstore = Chroma(
    persist_directory="./chroma_db/",
    collection_name="nimbuscloud_handbook",
    embedding_function=embeddings,
)

#step 2 - Retriever

retriever = vectorstore.as_retriever(search_kwargs={"k":3})

llm = ChatOllama(model="llama3.1", temperature=0.2)

prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant answering questions based only on the provided context.
If the answer is not present in the context, say you don't know — do not make up information.

Context:
{context}

Question: {question}

Answer:

"""
)

def answer_question(question: str) -> str:
    # Relevant chunks retrieve karo
    retrieved_docs = retriever.invoke(question)
    context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)

    # Prompt ko fill karo aur LLM ko bhejo
    final_prompt = prompt.format(context=context_text, question=question)
    response = llm.invoke(final_prompt)

    return response.content

# Test
if __name__ == "__main__":
    q = "Employees can reach to whom for hr related queries and what are the timings for that."
    print("Question:", q)
    print("Answer:", answer_question(q))