from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

#step 1 - load the pdf to the text splitting
loader = PyPDFLoader("data/nimbuscloud_handbook.pdf")
documents = loader.load()

#step 2 - Splitting the text
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n","\n",". "," ",""]
)

#step 3 - converting document into chunks
chunks = text_splitter.split_documents(documents)

print(f"Total chunks created - {len(chunks)}")
print("--- Sample chunk 1---")
print(chunks[0].page_content)
print("\n--- Sample chunk 1 metadata ----")
print(chunks[0].metadata)
