"""Shared pieces of the AI-writing detector v3 (builds on detector_v2: same splitter, same split, same normalizer).

Families and generators. A "family" is a model lineage; leave-one-family-out holds a whole family out of training.
v2's three generators (3 tasks) are kept as they are; v3 adds ten open generators with six tasks.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'detector_v2'))
import v2common as V  # noqa: E402  (paths, split_of, norm, passages, snapshot)

AIW = Path(V.P.AI_WRITING)  # the main checkout's ai-writing/: data, models and results never live in a worktree
V.AIW = AIW; V.FULLTEXT = AIW / 'fulltext.sqlite'  # v2 helpers (prep.load_meta, ...) resolve data through these
OUT = AIW / 'detector_v3'
DATA, MODELS, RESULTS, LOGS = OUT / 'data', OUT / 'models', OUT / 'results', OUT / 'logs'
V2DATA = AIW / 'detector_v2' / 'data'
SEED = V.SEED
SPLIT_OF = V.split_of
TASKS3 = ('polish', 'paraphrase', 'notes', 'continue', 'humanize', 'partial')

# gen -> (family, HF repo, size class)
GEN = {
    'qwen72b': ('qwen', 'Qwen/Qwen2.5-72B-Instruct', 'v2'),
    'qwen7b': ('qwen', 'Qwen/Qwen2.5-7B-Instruct', 'v2'),
    'llama70b': ('llama', 'meta-llama/Llama-3.3-70B-Instruct', 'v2'),
    'qwen14b': ('qwen', 'Qwen/Qwen2.5-14B-Instruct', 'v3'),
    'llama31-8b': ('llama', 'NousResearch/Meta-Llama-3.1-8B-Instruct', 'v3'),
    'llama32-3b': ('llama', 'unsloth/Llama-3.2-3B-Instruct', 'v3'),
    'phi4': ('phi', 'microsoft/phi-4', 'v3'),
    'nemo': ('mistral', 'mistralai/Mistral-Nemo-Instruct-2407', 'v3'),
    'mistral7b': ('mistral', 'mistralai/Mistral-7B-Instruct-v0.3', 'v3'),
    'gemma2-9b': ('gemma', 'unsloth/gemma-2-9b-it', 'v3'),
    'gemma3-12b': ('gemma', 'unsloth/gemma-3-12b-it', 'v3'),
    'olmo2-7b': ('olmo', 'allenai/OLMo-2-1124-7B-Instruct', 'v3'),
    'granite33-8b': ('granite', 'ibm-granite/granite-3.3-8b-instruct', 'v3'),
}
FAMILY = {g: v[0] for g, v in GEN.items()}
V3GENS = [g for g, v in GEN.items() if v[2] == 'v3']
FAMILIES = sorted(set(FAMILY.values()))
HELD = ('llama', 'gemma', 'qwen')  # families held out, one leave-one-family-out model each
NEXT_BASE = 'answerdotai/ModernBERT-large'
