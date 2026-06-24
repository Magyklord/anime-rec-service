from sentence_transformers import SentenceTransformer
import json

# Load the model — downloads on first run, cached after
model = SentenceTransformer("all-MiniLM-L6-v2")

# A few descriptions to embed
texts = [
    "A bounty hunter drifts through space haunted by his past",
    "Pirates sail the seas searching for the ultimate treasure",
    "A boy inherits supernatural power and must protect his city",
    "In a dystopian future, humanity hides behind walls from giants",
]

# Generate embeddings for all texts at once
embeddings = model.encode(texts)

# Look at what we got
print(f"Shape: {embeddings.shape}")        # (4, 384) — 4 texts, 384 dimensions each  -- the 4 texts represent the 4 texts just above this
print(f"Type: {type(embeddings)}")         # numpy array ---prints the dataype
print(f"\nFirst vector (first 10 values):")
print(embeddings[0][:10])                  # peek at the first 10 coordinates which are basically the machine understood idea of each line
#what it means is it looked into the first text(For cowboy bebop) and then showed the first 10 coordinate numbers out of 384 dimensions. In short those 10 numbers represent scores in various different dimensions

# ^ you might have some questions about how the values are actually created and what their basis is for the first 10 vectors we print
# the model we use has self trained itself internally to assign about 384 dimensions to various labels and categories. The values we get are based on THAT