from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

#step 1 - load the pdf
loader = PyPDFLoader("data/nimbuscloud_handbook.pdf")
documents =  loader.load()

#step 2 - chunk it

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n","\n",". "," ",""],
)

chunks = text_splitter.split_documents(documents)

#step 3 - Generate embeddings model
embeddings = OllamaEmbeddings(model="nomic-embed-text")

#step 4 - creating vector store
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db",
    collection_name="nimbuscloud_handbook"
)

print(f"Vector store created with {len(chunks)} chunks")
print("Saved to ./chroma_db")

# Quick test: similarity search karke dekhte hain
query = "how many paid leaves do employees get"
results = vectorstore.similarity_search(query, k=2)


print(f"\n--- Top 2 results for query: '{query}' ---")
for i, doc in enumerate(results):
    print(f"\nResult {i+1} (page {doc.metadata.get('page')}):")
    print(doc.page_content[:300])