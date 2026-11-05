# Embeddings, topics and novelty for every paper (owner 2026-11-04)

The study's sample (ai-writing/embeddings.npz, 60k texts) extended to **all lab papers**: the 7 released schools (princeton, cmu, epfl, mit,
berkeley, stanford, michigan) plus the onboarding schools whose packages exist (uchicago, gatech; marked unreleased in the report). One row per
work (atlas id `atl:w:...`, else `oa:<W id>`), 132,660 works in `universe.sqlite` on 2026-11-04.

## Pipeline
| step | code | where | output (under `EMB` = `ai-writing/data/embeddings`, slot `EMBEDDINGS`) |
|---|---|---|---|
| paper list | `universe.py build` (`universe.slurm`) | CPU, 30 min | `universe.sqlite`: `papers`, `lab_papers` (lab, PI, department per work), `oa_ids` |
| abstracts + OpenAlex topics | `oa_fields.py filter/merge` (`oa_fields.slurm`, 64 tasks) | CPU, S3 stream, no API | `oa_fields.sqlite`: abstract text rebuilt from `abstract_inverted_index`, primary topic, topics, keywords |
| texts | `texts.py abstracts / fulltext` (`texts.slurm`) | CPU | `texts.sqlite`: `abstracts`, `fulltext` (body zlib, `usable`, text hash) |
| models | `download_models.py` | CPU, network | `env/hf-cache` |
| vectors | `embed.py run` (`embed.slurm`) | 1 RTX 2080 per task | parts, then `embed.py merge` -> containers |
| topics, novelty | `topics.py`, `novelty_run.py` (`analyze.slurm`) | CPU/GPU | `results/*.parquet` |
| report | `emb_report.py` | CPU | `ai-writing/diversity/reports/EMBEDDINGS-TOPICS-NOVELTY.md` |

**Why a new OpenAlex pass.** The local filtered snapshot (`external/openalex-snapshot/current`) kept neither `abstract_inverted_index` nor
`topics` (docs/OPENALEX-SNAPSHOT.md section 2, "Not kept"), and the ext stores of onboarding schools are the same projection. `oa_fields.py` streams
the works partitions of the same bulk snapshot (2026-10-14, S3, free, no API credits) once more and keeps only the universe's works.
Abstracts the 2026-10 API pass of `build_corpus.py` cached (`ai-writing/abstracts.sqlite`) fill any work the snapshot has none for.

## Storage layout (no per-paper files)
```
EMB/universe.sqlite  oa_fields.sqlite  texts.sqlite
EMB/parts/<model>/<kind>/part_<job>_<task>_<seq>.npz     a run's finished chunk (atomic rename); merged and removed by `embed.py merge`
EMB/<model>/<school>/<kind>.npz                          the container, one per model x home school x text kind
EMB/<model>/<school>/<kind>.index.sqlite                 papers(paper_id PK, row, off, n, ntok, text_hash), meta(key, value)
EMB/results/*.parquet                                    analysis tables
```
`kind` is `abstract` or `fulltext`. Container arrays: `ids`, `hashes` (hash of the exact text embedded), `n` (vectors per paper), `ntok`, `off`
(offsets into `X`), `M` (float16, papers x dim: the abstract vector, or the mean over a paper's chunks), `X` (full text only: every chunk vector),
`sp_ptr`/`sp_idx`/`sp_val` (BGE-M3 lexical weights, CSR; full text: max over chunks). A paper is stored once, under its **home school** (the first
of princeton, cmu, epfl, mit, berkeley, stanford, michigan, uchicago, gatech that has it); `universe.sqlite` `lab_papers` lists all its labs.
The index `meta` records the model id, the exact Hugging Face revision (snapshot hash), pooling, prefix, dtype, school, kind and merge time.
Vectors are stored raw (the pooled output, float16); analyses centre on the corpus mean and normalize. `store.py` is the only reader/writer.

## Models (each its own vector set)
| key | model | text kinds | vector |
|---|---|---|---|
| `specter2_base` | allenai/specter2_base | abstract, full text (512-token windows) | CLS, 768 |
| `specter2_proximity` | allenai/specter2_base + adapter allenai/specter2 (proximity) | the same | CLS, 768 |
| `scincl` | malteos/scincl | abstract | CLS, 768 |
| `qwen3_0p6b` | Qwen/Qwen3-Embedding-0.6B | abstract, full text (8k-token chunks) | last token, 1024 |
| `gte_qwen2_1p5b` | Alibaba-NLP/gte-Qwen2-1.5B-instruct | the same | last token, 1536 |
| `bge_m3` | BAAI/bge-m3 | the same, plus lexical weights | CLS dense 1024; sparse |
| `nomic_v15` | nomic-ai/nomic-embed-text-v1.5, prefix `clustering: ` | the same | mean, 768 |

**Qwen3-Embedding-4B (`qwen3_4b`) runs on node105's RTX A5000s (`embed-a5000.slurm`; abstracts done, full text at ~3.5k tokens/s per card).** On the 2080 Ti it ran on abstracts only, one card at a time: fp16 weights are about 8 GB; the cards report 11 GB (RTX 2080 Ti), the peak at an 8k window measured 9.28 GB of 10.58 GB (headroom 1.29 GB < 2 GB), so full text is not run. Abstracts: title [SEP] abstract for SPECTER2 and SciNCL (as `ai-writing/embed.py`), title, blank line, abstract for the others.
Full text: the stored body (the existing extraction, `vendor/homogenization_tools/fulltext_store.py`: pdftotext 60 pages, Introduction to the last
References heading, at most 300,000 characters), cut into consecutive token windows (512 for SPECTER2; 8,192 for the others, special tokens included),
at most 64 / 8 windows per paper (evenly spaced when more), a tail shorter than 64 / 256 tokens dropped unless it is the only window. Full texts are
the ones `common.usable_text` accepts (>= 1000 words, a PDF must show the paper's title on its first page), as in the diversity battery.
fp16, sdpa attention (no flash-attention: Turing), batches sized by padded tokens for 8 GB with a split-on-OOM fallback, a non-finite output stops the run.

## Resume and compute
Jobs are 59-minute tasks (`--partition=mltheory --account=mltheory --gres=gpu:rtx_2080:1 --exclude=node302,node105`; under an hour the cluster routes
them through the shared pool, which starts at once, while a longer request waits days) that stop starting new parts after a time budget. A paper belongs to
shard `sha1(id) % n`, so shards stay disjoint while the todo shrinks; the todo is every paper whose text hash is not in a part or a container.
`submit_embed.sh` queues chains of `afterany` tasks per shard and never more than 8 GPUs at once. `embed.py status` counts what is done.

## Reading the vectors
```python
import store
c = store.load('qwen3_0p6b', 'cmu', 'fulltext', chunks=True)   # ids, hashes, n, off, M, X
store.meta('qwen3_0p6b', 'cmu', 'fulltext')['revision']
```
Tests: `tests/test_embeddings.py` (store, index, resume, merge, chunking, batching, OpenAlex rebuild, entropy, novelty against brute force).

## Finishing and re-running after the packages change (runbook)
1. Rebuild the paper list once gatech and uchicago are final: `sbatch universe.slurm` (new papers appear, ids stay), then `sbatch texts.slurm abstracts` and `sbatch texts.slurm fulltext` (repeat the full-text job until it logs no `todo`; it resumes).
2. Embed the delta: `lanes.sh` (full text, 8 lanes) and `submit_embed.sh <model> abstract 1 3` per model; a paper is redone only when its text hash is new.
3. `merge.slurm <model> <kind> ...` for every model and kind (idempotent; papers whose home school changed move containers), then `analyze.slurm novelty <model> <kind>`, `analyze.slurm bertopic <model>` (about 35 minutes: set `--time=00:59:00`) and `analyze.slurm entropy <model|openalex>` for the topic models, then `EMB_REPORT_DIR=<dir> sbatch analyze.slurm report` and copy the file into `ai-writing/diversity/reports/`.
Status: `embed.py status` (done / total per model and kind) from a compute node.

## node105 A5000 lanes (owner 2026-11-04: the mltheory 2080 nodes are out of service)
`embed-a5000.slurm` is shardable: `SHARD`/`OF` (default 0/1) mean exactly `embed.py --shard/--of` (`sha1(id) % OF`; done work is skipped, shards never overlap), and
`EMB_BUDGET_SCALE` multiplies the padded-token batch budget of `models.py` (sized for 8 GB; 2 is safe on the 24 GB card, and a batch that still fails is split). Measured
(A5000, scale 2, 8k-token chunks): Qwen3-0.6B 12.3k tokens/s, gte-Qwen2-1.5B 9.5k, SPECTER2 not measured, Qwen3-4B 3.5k (scale 1; compute-bound). At most 3 of our lanes plus the qwen3_4b job on node105.
```
MODEL=gte_qwen2_1p5b KIND=fulltext SHARD=1 OF=3 EMB_BUDGET_SCALE=2 sbatch --export=ALL embed-a5000.slurm     # one lane = one chain of afterany jobs
sbatch status.slurm [--model M]                                                                           # embed.py status as a CPU job
```
Year rule (owner 2026-11-04): no 2026 in any series, table or estimate; series end at 2025, post = 2023-2025 (`emb_load.YEARS/POST`; the report and `novelty_run.py` follow).

### After the embeddings finish (for the AI-dose analysis; run from the code root, another agent owns agent/ai-dose)
Full text is merged and novelty done for a model when `embed.py status` shows done = total and `results/novelty_trend_<M>_fulltext.parquet` exists. Then, per model M in
`specter2_base specter2_proximity bge_m3 nomic_v15 qwen3_0p6b gte_qwen2_1p5b` (and `qwen3_4b` once its full text is merged):
```
sbatch ai-writing/dose/dose_cpu.slurm dose_analysis.py paper --kind fulltext --model M
sbatch ai-writing/dose/dose_cpu.slurm dose_analysis.py boot  --kind fulltext --model M     # if the study bootstraps the same model
```
(`dose_analysis.py` also takes `--exposure`, `--scope`, `--boot N`; see `ai-writing/dose/README.md` on agent/ai-dose.)
