## closed-context retrieval

Code for my foray into local LLMs using:
* [llama.cpp](https://github.com/ggerganov/llama.cpp) in a container with an inference endpoint
* [quantized](https://huggingface.co/TheBloke/airoboros-l2-13B-2.2.1-GGUF) [airoboros](https://huggingface.co/jondurbin/airoboros-l2-13b-2.2.1) as the model
* [discord.py](https://discordpy.readthedocs.io/en/stable/) for interacting with the model in a private server
* [Redis Stack Server](https://redis.io/docs/about/about-stack/) for doing vector-similarity search and Q&A retrieval

The model allows for structured and unstructured closed-context Q&A retrieval (i.e. the model will only use the provided context to answer questions).


### Getting Started

Install PDM for managing dependencies

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
