"""Fetch the embedding models into the project's Hugging Face cache (env/hf-cache; HF_HOME), once; the GPU jobs then run offline.
Only the files the embedder reads (weights, tokenizer, config, BGE-M3's sparse head, the code of Nomic's custom architecture).
usage: download_models.py [model key ...]     (default: all)
"""
import sys

import ecommon as C
from models import MODELS, ORDER

REPOS = {  # extra repos some models need, and the file patterns to take
    'nomic_v15': ['nomic-ai/nomic-embed-text-v1.5', 'nomic-ai/nomic-bert-2048'],
    'specter2_proximity': ['allenai/specter2_base', 'allenai/specter2'],
}
PATTERNS = ['*.json', '*.txt', '*.model', '*.py', '*.safetensors', '*.bin', 'sparse_linear.pt', 'merges.txt', 'vocab.*', 'tokenizer*']
IGNORE = ['*onnx*', 'onnx/*', '*.msgpack', '*.h5', '*.ot', 'imgs/*', 'colbert_linear.pt', '*openvino*']


def main(keys):
    from huggingface_hub import snapshot_download
    for k in keys:
        for repo in REPOS.get(k, [MODELS[k]['hf']]):
            kw = dict(allow_patterns=PATTERNS, ignore_patterns=IGNORE)
            if repo == 'BAAI/bge-m3':
                kw['ignore_patterns'] = IGNORE + ['pytorch_model.bin.index.json']
            path = snapshot_download(repo, **kw)
            C.log(model=k, repo=repo, path=path)


if __name__ == '__main__':
    main(sys.argv[1:] or ORDER)
