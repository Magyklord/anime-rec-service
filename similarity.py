from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

# Cowboy Bebop's vibe
bebop = "A bounty hunter drifts through space haunted by his past, jazz and melancholy"

# A range of other shows — some similar, some not
others = {
    "Trigun":           "A legendary gunman wanders a desert planet avoiding his violent past",
    "One Piece":        "Pirates sail the seas searching for treasure and friendship",
    "Vinland Saga":     "A viking warrior seeks revenge but finds peace, haunted by violence",
    "Fullmetal Alchemist": "Brothers use alchemy to recover what they lost, facing dark truths",
    "Sword Art Online": "Players get trapped inside a virtual reality MMO game",
}

# Embed everything
bebop_vector = model.encode(bebop)
other_vectors = model.encode(list(others.values()))

# Compute similarities
print("Similarity to Cowboy Bebop:\n")
for i, (title, _) in enumerate(others.items()):
    score = util.cos_sim(bebop_vector, other_vectors[i]).item()
    bar = "█" * int(score * 40)   # visual bar so you can see the spread
    print(f"{title:<30} {score:.3f}  {bar}")