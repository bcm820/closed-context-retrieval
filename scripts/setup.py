import os

for dir in ['embeddings', 'models']:
    path = os.path.join('data', dir)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
