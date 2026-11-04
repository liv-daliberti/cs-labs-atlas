"""The model registry: how each embedding model is loaded, what text it reads and how its vector is pooled. No torch import here.

Every model's vectors are a set of their own (EMB/<key>/...), stored raw (the pooled output, float16; the study normalizes at analysis time).
`revision` is filled in from the Hugging Face cache snapshot actually loaded and recorded in each container's index meta table.

kinds        abstract: one vector per paper from its abstract.  fulltext: the body cut into chunk-token windows (chunk vectors kept) and their mean.
abs_fmt      'sep'  title [SEP] abstract (SPECTER2 / SciNCL, as ai-writing/embed.py);  'plain'  title, blank line, abstract.
pool         cls | last (last token; the end-of-text token is appended to every window) | mean.
chunk        tokens per full-text window, special tokens included; cap = most windows of one paper (windows are evenly spaced when more exist);
             tail windows shorter than min_tail tokens are dropped unless they are the paper's only window.
budget       padded tokens per batch (sized for an 8 GB RTX 2080 in fp16; a batch that still runs out of memory is split).
Qwen3-Embedding-4B is not in the list: fp16 weights alone are about 8 GB, the whole of an RTX 2080's memory (docs/ENVIRONMENT.md).
"""
MODELS = {
    'specter2_base': dict(hf='allenai/specter2_base', pool='cls', kinds=('abstract', 'fulltext'), abs_fmt='sep', abs_max=512, chunk=512, cap=64,
                          min_tail=64, budget=32768, prefix='', dim=768, note='CLS of title [SEP] abstract; as ai-writing/embed.py'),
    'specter2_proximity': dict(hf='allenai/specter2_base', adapter='allenai/specter2', adapter_name='proximity', pool='cls', kinds=('abstract', 'fulltext'),
                               abs_fmt='sep', abs_max=512, chunk=512, cap=64, min_tail=64, budget=32768, prefix='', dim=768,
                               note='SPECTER2 base + the proximity adapter (allenai/specter2), CLS'),
    'scincl': dict(hf='malteos/scincl', pool='cls', kinds=('abstract',), abs_fmt='sep', abs_max=512, chunk=512, cap=64, min_tail=64,
                   budget=32768, prefix='', dim=768, note='SciNCL, CLS of title [SEP] abstract'),
    'qwen3_0p6b': dict(hf='Qwen/Qwen3-Embedding-0.6B', pool='last', kinds=('abstract', 'fulltext'), abs_fmt='plain', abs_max=8192, chunk=8192, cap=8,
                       min_tail=256, budget=16384, prefix='', dim=1024, note='last-token pooling, documents without an instruction'),
    'gte_qwen2_1p5b': dict(hf='Alibaba-NLP/gte-Qwen2-1.5B-instruct', pool='last', kinds=('abstract', 'fulltext'), abs_fmt='plain', abs_max=8192, chunk=8192,
                           cap=8, min_tail=256, budget=12288, prefix='', dim=1536, note='last-token pooling, documents without an instruction'),
    'bge_m3': dict(hf='BAAI/bge-m3', pool='cls', kinds=('abstract', 'fulltext'), abs_fmt='plain', abs_max=8192, chunk=8192, cap=8, min_tail=256,
                   budget=16384, prefix='', dim=1024, sparse=True, note='dense = CLS; sparse = relu(sparse_linear(hidden)) per token id, max over occurrences and chunks'),
    'nomic_v15': dict(hf='nomic-ai/nomic-embed-text-v1.5', pool='mean', kinds=('abstract', 'fulltext'), abs_fmt='plain', abs_max=8192, chunk=8192, cap=8,
                      min_tail=256, budget=16384, prefix='clustering: ', dim=768, remote=True,
                      note="mean pooling, task prefix 'clustering: ' (similarity and topic use), rotary_scaling_factor=2 for the 8k context"),
}
ORDER = ['specter2_base', 'specter2_proximity', 'scincl', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']
