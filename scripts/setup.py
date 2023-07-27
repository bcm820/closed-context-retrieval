import os

if not os.getcwd().endswith('jarvis'):
    print('Must run from project root dir')
    exit(1)

for dir in ['downloads', 'index', 'models']:
    path = os.path.join('data', dir)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

for dir in ['embeddings', 'llama']:
    path = os.path.join('data', 'models', dir)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
