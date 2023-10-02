Install pdm for managing dependencies

```
curl -sSL https://pdm.fming.dev/dev/install-pdm.py | python -
```

Install llama-cpp-python with GPU acceleration (CuBLAS is for Nvidia GPUs)

```
export CMAKE_ARGS="-DLLAMA_CUBLAS=on"
export FORCE_CMAKE=1
export LLAMA_CUBLAS=on
pdm add llama-cpp-python -v
```

Install all other packages

```
pdm install
```

Create data directories

```
pdm run setup
```

Download LLM

```
cd data/models
wget https://huggingface.co/TheBloke/airoboros-l2-13B-2.2.1-GGUF/resolve/main/airoboros-l2-13b-2.2.1.Q6_K.gguf
```

Download embedding model

```
git clone https://huggingface.co/intfloat/e5-large-v2 data/embeddings
```

Run

```
docker compose up -d
pdm run start
```
