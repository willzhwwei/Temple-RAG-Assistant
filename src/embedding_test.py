from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

text = "Temple University student parking costs $266 per semester."

embedding = model.encode(text)

print(embedding)
print("Embedding dimension:", len(embedding))