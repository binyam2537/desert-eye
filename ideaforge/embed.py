"""Local text embeddings. model2vec static embeddings by default (no GPU, no API key);
falls back to a numpy TF-IDF over word + char n-grams if the model can't be loaded."""
from __future__ import annotations

import os
import re
import sys
from collections import Counter

import numpy as np

DEFAULT_MODEL = os.environ.get("IDEAFORGE_EMBED_MODEL", "minishlab/potion-base-32M")


def _normalize(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


def _tfidf(texts: list[str]) -> np.ndarray:
    def feats(t: str) -> list[str]:
        t = t.lower()
        words = re.findall(r"[a-z0-9]+", t)
        grams = [t[i:i + 4] for i in range(max(0, len(t) - 3))]
        return words + grams

    docs = [Counter(feats(t)) for t in texts]
    df = Counter(f for d in docs for f in d)
    vocab = {f: i for i, f in enumerate(df)}
    m = np.zeros((len(texts), len(vocab)), dtype=np.float32)
    n = len(texts)
    for r, d in enumerate(docs):
        for f, c in d.items():
            m[r, vocab[f]] = (1 + np.log(c)) * np.log((1 + n) / (1 + df[f]))
    return m


def embed(texts: list[str], model: str = DEFAULT_MODEL) -> np.ndarray:
    """Return L2-normalised embeddings, one row per text."""
    if not texts:
        return np.zeros((0, 1), dtype=np.float32)
    if model != "tfidf":
        try:
            from model2vec import StaticModel
            return _normalize(np.asarray(StaticModel.from_pretrained(model).encode(texts),
                                         dtype=np.float32))
        except Exception as e:  # offline, package missing, bad model name
            print(f"[embed] model2vec unavailable ({e}); falling back to TF-IDF", file=sys.stderr)
    return _normalize(_tfidf(texts))


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a @ b.T
