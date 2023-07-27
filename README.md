Install pdm

```
curl -sSL https://pdm.fming.dev/dev/install-pdm.py | python -
```

Install llama-cpp-python with GPU acceleration (CuBLAS is best for Nvidia GPUs)

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
cd data/models/llama && wget https://huggingface.co/TheBloke/WizardLM-13B-V1.2-GGML/resolve/main/wizardlm-13b-v1.2.ggmlv3.q2_K.bin
```

Download embedding model

```
git clone https://huggingface.co/intfloat/e5-large-v2 data/models/embeddings
```

Run

```
pdm run start
```
