"""DINOv2 embeddings of every extracted figure (a self-supervised image model: it encodes visual style and layout, not
caption text). Each figure crop is padded to a square on white, resized to 224, and embedded; the vector is the CLS
token concatenated with the mean patch token (2 x 768), L2-normalized per half. GPU when there is one, else CPU.
-> data/emb-<shard>.npz: keys (paper key per figure), page, idx, X (float16, n x 1536)
usage: embed.py [--shard i] [--batch B]   (reads data/figures-<shard>.sqlite)
"""
import argparse, io, os, sqlite3
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('FIGLAB_DATA', HERE / 'data'))  # a mini run uses its own folder
MODEL = 'facebook/dinov2-base'


def square(im):
    s = max(im.size)
    c = Image.new('RGB', (s, s), 'white'); c.paste(im, ((s - im.width) // 2, (s - im.height) // 2))
    return c


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--shard', type=int, default=0); ap.add_argument('--batch', type=int, default=64)
    a = ap.parse_args()
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    proc = AutoImageProcessor.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, torch_dtype=torch.float16 if dev == 'cuda' else torch.float32).to(dev).eval()
    db = sqlite3.connect(f'file:{DATA / f"figures-{a.shard:02d}.sqlite"}?mode=ro', uri=True)
    rows = db.execute('select key, page, idx, png from figures order by key, page, idx').fetchall()
    keys, pages, idxs, X = [], [], [], []
    for i in range(0, len(rows), a.batch):
        chunk = rows[i:i + a.batch]
        ims = [square(Image.open(io.BytesIO(r[3])).convert('RGB')) for r in chunk]
        inp = proc(images=ims, return_tensors='pt', size={'shortest_edge': 224}, crop_size={'height': 224, 'width': 224}).to(dev)
        if dev == 'cuda':
            inp['pixel_values'] = inp['pixel_values'].half()
        with torch.no_grad():
            h = model(**inp).last_hidden_state.float()
        cls, mean = h[:, 0], h[:, 1:].mean(1)
        v = torch.cat([torch.nn.functional.normalize(cls, dim=1), torch.nn.functional.normalize(mean, dim=1)], 1)
        X.append(v.cpu().numpy().astype(np.float16))
        keys += [r[0] for r in chunk]; pages += [r[1] for r in chunk]; idxs += [r[2] for r in chunk]
        print(f'{i + len(chunk)}/{len(rows)}', flush=True) if (i // a.batch) % 20 == 0 else None
    np.savez(DATA / f'emb-{a.shard:02d}.npz', keys=np.array(keys), page=np.array(pages), idx=np.array(idxs),
             X=np.concatenate(X) if X else np.zeros((0, 1536), np.float16))
    print(dict(shard=a.shard, figures=len(keys), device=dev))


if __name__ == '__main__':
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    main()
