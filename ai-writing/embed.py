"""SPECTER2 embeddings of every lab paper with an abstract (Hao et al. 2024, Fig. 3A: title + abstract, 768 dimensions).

allenai/specter2_base, title [SEP] abstract, CLS vector, at most 512 tokens, on CPU (no GPU queue). Papers whose abstract
has fewer than 50 words are left out, as in the detector. Incremental: a paper already in embeddings.npz keeps its vector
(the same title and abstract text, checked by a hash); only new or changed ones are embedded. Written to a temporary file
and renamed, so readers never see a partial file.
-> ai-writing/embeddings.npz {keys, X (float16, n x 768), h (text hash)}
"""
import gzip, hashlib, json, os
from pathlib import Path
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer

HERE = Path(__file__).resolve().parent
torch.set_num_threads(int(os.environ.get('THREADS', '32')))
papers = [json.loads(l) for l in gzip.open(HERE / 'papers.jsonl.gz', 'rt')]
papers = [p for p in papers if p['abstract'] and len(p['abstract'].split()) >= 50 and p['title']]
tok = AutoTokenizer.from_pretrained('allenai/specter2_base'); model = AutoModel.from_pretrained('allenai/specter2_base').eval()
H = [hashlib.sha1((p['title'] + tok.sep_token + p['abstract']).encode()).hexdigest() for p in papers]
X = np.zeros((len(papers), 768), np.float16)
old = {}
if (HERE / 'embeddings.npz').exists():
    E = np.load(HERE / 'embeddings.npz'); EX = E['X']  # read each array once: an NpzFile re-reads on every access
    oh = E['h'] if 'h' in E.files else [None] * len(E['keys'])  # the first build stored no hash: trust the key
    old = {k: (i, h) for i, (k, h) in enumerate(zip(E['keys'], oh))}
todo = []
for j, (p, h) in enumerate(zip(papers, H)):
    o = old.get(p['key'])
    if o and (o[1] is None or o[1] == h):
        X[j] = EX[o[0]]
    else:
        todo.append(j)
print(json.dumps(dict(papers=len(papers), reused=len(papers) - len(todo), to_embed=len(todo))), flush=True)
with torch.inference_mode():
    for i in range(0, len(todo), 32):
        b = todo[i:i + 32]
        enc = tok([papers[j]['title'] + tok.sep_token + papers[j]['abstract'] for j in b], padding=True, truncation=True, max_length=512, return_tensors='pt')
        X[b] = model(**enc).last_hidden_state[:, 0].numpy().astype(np.float16)
        if i % 3200 == 0:
            print(json.dumps(dict(done=i, of=len(todo))), flush=True)
tmp = HERE / '.tmp_embeddings.npz'
np.savez(tmp, keys=np.array([p['key'] for p in papers]), X=X, h=np.array(H))
os.replace(tmp, HERE / os.environ.get('EMB_OUT', 'embeddings.npz'))
print(json.dumps(dict(embedded=len(todo), total=len(papers))))
