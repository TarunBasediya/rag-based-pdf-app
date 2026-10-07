from langchain_community.document_loaders import PyPDFLoader

#step 1: loading the pdf

loader = PyPDFLoader("data/nimbuscloud_handbook.pdf")
documents = loader.load();

print(f"Total pages loaded : {documents}")
print("--- Page 1 content preview ---")

print(documents[0].page_content[:500])

print("Page 1 meta data")
print(documents[0].metadata)