from transformers import pipeline

print("Downloading BART model... this will take a few minutes")
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli"
)
print("Done! Model cached successfully.")