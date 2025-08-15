# rag.py
from __future__ import annotations

import os
import json
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import numpy as np

logger = logging.getLogger("recoveryos")

# ----------------------
# Config / Paths
# ----------------------
RAG_MODEL = os.getenv("RAG_MODEL", "all-MiniLM-L6-v2")
RAG_DEVICE = os.getenv("RAG_DEVICE", "cpu")  # "cpu" or "cuda"
RAG_DIR = Path(os.getenv("RAG_STORE_DIR", "rag_store"))
RAG_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_FILE = RAG_DIR / "embeddings.npy"  # shape: (N, d) float32 (normalized)
METADATA_FILE = RAG_DIR / "metadata.json"  # list[Dict]
MANIFEST_FILE = RAG_DIR / "manifest.json"  # {model, dim, count, updated_at}

# Thread lock to avoid concurrent writers
_STORE_LOCK = threading.Lock()

# ----------------------
# Optional import with helpful error
# ----------------------
try:
    from sentence_transformers import SentenceTransformer
except Exception as e:  # pragma: no cover
    raise ImportError(
        "sentence-transformers is required for rag.py. Add to requirements.txt:\n"
        "sentence-transformers>=2.6.0\n"
        f"Import error: {e}"
    )

_MODEL: Optional[SentenceTransformer] = None
_DIM: Optional[int] = None


def _get_model() -> SentenceTransformer:
    global _MODEL, _DIM
    if _MODEL is None:
        logger.info(f"Loading embedding model '{RAG_MODEL}' on device '{RAG_DEVICE}'")
        _MODEL = SentenceTransformer(RAG_MODEL, device=RAG_DEVICE)
        # Probe vector dim
        vec = _MODEL.encode(["probe"], show_progress_bar=False)
        _DIM = int(vec.shape[-1])
        logger.info(f"Model ready | dim={_DIM}")
    return _MODEL


def _atomic_write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _load_manifest() -> Dict[str, Any]:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Manifest unreadable, recreating…")
    return {}


def _save_manifest(model_name: str, dim: int, count: int) -> None:
    manifest = {
        "model": model_name,
        "dim": dim,
        "count": count,
        "updated_at": _now_iso(),
    }
    _atomic_write_json(MANIFEST_FILE, manifest)


def _now_iso() -> str:
    from datetime import datetime

    return datetime.utcnow().isoformat() + "Z"


def _normalize(mat: np.ndarray) -> np.ndarray:
    # Avoid div by zero
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    return (mat / norms).astype(np.float32, copy=False)


def _chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> List[str]:
    """Lightweight chunker: respects sentence-ish boundaries when possible."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        # Try to break at last period/newline within window
        window = text[start:end]
        break_idx = max(window.rfind("."), window.rfind("\n"))
        if break_idx < int(0.6 * len(window)):  # don't cut too short
            break_idx = len(window)
        chunk = window[:break_idx].strip()
        if chunk:
            chunks.append(chunk)
        # Overlap back by 'overlap'
        start = start + break_idx - overlap
        if start < 0:
            start = 0
        if start >= len(text):
            break
    return chunks


def _ensure_store_shapes(dim: int) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Load or initialize store; validates dims; returns (embeddings, metadata)."""
    if EMBEDDINGS_FILE.exists() and METADATA_FILE.exists():
        try:
            emb = np.load(EMBEDDINGS_FILE, mmap_mode=None)
            meta = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
            if emb.ndim != 2 or emb.shape[1] != dim:
                logger.warning(
                    "Embedding dim mismatch (have=%s, expected=%s). Rebuilding store.",
                    emb.shape,
                    dim,
                )
                return np.empty((0, dim), dtype=np.float32), []
            if len(meta) != emb.shape[0]:
                logger.warning(
                    "Metadata length mismatch with embeddings. Rebuilding store."
                )
                return np.empty((0, dim), dtype=np.float32), []
            return emb.astype(np.float32, copy=False), meta
        except Exception as e:
            logger.warning(f"Failed to load store ({e}). Rebuilding new store.")
    return np.empty((0, dim), dtype=np.float32), []


def _save_store(emb: np.ndarray, meta: List[Dict[str, Any]], dim: int) -> None:
    # Persist embeddings and metadata atomically
    assert emb.shape[0] == len(meta)
    np.save(EMBEDDINGS_FILE, emb.astype(np.float32, copy=False))
    _atomic_write_json(METADATA_FILE, meta)
    _save_manifest(RAG_MODEL, dim, emb.shape[0])
    logger.info("🔐 RAG store saved | count=%s dim=%s", emb.shape[0], dim)


def _encode_texts(texts: List[str]) -> np.ndarray:
    model = _get_model()
    vectors = model.encode(
        texts, show_progress_bar=False, normalize_embeddings=False
    )  # we normalize ourselves
    vectors = np.array(vectors, dtype=np.float32)
    return _normalize(vectors)


def _mmr(
    query_vec: np.ndarray,
    doc_vecs: np.ndarray,
    top_k: int,
    lambda_mult: float = 0.7,
) -> List[int]:
    """
    Maximal Marginal Relevance for diverse top-k selection.
    query_vec: (d,)
    doc_vecs:  (N, d) normalized
    Returns indices.
    """
    N = doc_vecs.shape[0]
    if N == 0:
        return []
    # Base relevance
    rel = np.dot(doc_vecs, query_vec)  # (N,)
    selected: List[int] = []
    candidates = set(range(N))

    # Precompute doc-doc similarity for redundancy penalty
    doc_sim = np.clip(np.dot(doc_vecs, doc_vecs.T), -1.0, 1.0)

    for _ in range(min(top_k, N)):
        if not selected:
            idx = int(np.argmax(rel))
            selected.append(idx)
            candidates.remove(idx)
            continue
        # Compute MMR score
        max_red = np.max(doc_sim[list(candidates)][:, selected], axis=1)  # (|cand|,)
        cand_list = list(candidates)
        mmr_scores = lambda_mult * rel[cand_list] - (1 - lambda_mult) * max_red
        best_idx = int(np.argmax(mmr_scores))
        idx = cand_list[best_idx]
        selected.append(idx)
        candidates.remove(idx)
    return selected


# ----------------------
# Public API
# ----------------------
def ingest_documents(documents: List[Dict[str, str]], *, chunk: bool = True) -> None:
    """
    Ingest/append documents to the vector store (id, title, content[, source, tags]).
    Existing store is preserved and appended to.
    """
    if not documents:
        logger.warning("No documents provided to ingest.")
        return

    model = _get_model()
    dim = _DIM or 384  # fallback

    with _STORE_LOCK:
        emb, meta = _ensure_store_shapes(dim)

        # Build chunked corpus
        texts: List[str] = []
        new_meta: List[Dict[str, Any]] = []
        for doc in documents:
            doc_id = str(doc.get("id") or f"doc-{len(meta)+len(new_meta)}")
            title = str(doc.get("title") or "Untitled")
            content = str(doc.get("content") or "").strip()
            if not content:
                continue

            chunks = _chunk_text(content) if chunk else [content]
            for i, c in enumerate(chunks):
                texts.append(c)
                new_meta.append(
                    {
                        "id": f"{doc_id}#{i}" if len(chunks) > 1 else doc_id,
                        "doc_id": doc_id,
                        "title": title,
                        "content": c,
                        "chunk_index": i,
                        "source": doc.get("source"),
                        "tags": doc.get("tags"),
                    }
                )

        if not texts:
            logger.warning("No text content to embed after preprocessing.")
            return

        # Encode and normalize
        new_vecs = _encode_texts(texts)  # (M, d)
        if new_vecs.shape[1] != dim:
            logger.warning(
                "Model dim changed mid-run; rebuilding store from new batch."
            )
            emb = np.empty((0, new_vecs.shape[1]), dtype=np.float32)
            meta = []
            dim = int(new_vecs.shape[1])

        # Append
        emb = np.vstack([emb, new_vecs]) if emb.size else new_vecs
        meta.extend(new_meta)

        # Save
        _save_store(emb, meta, dim)

        logger.info(
            "✅ Ingested %s chunks from %s docs (total=%s)",
            len(new_meta),
            len(documents),
            emb.shape[0],
        )


def retrieve(
    query: str,
    k: int = 3,
    *,
    min_score: float = 0.25,
    use_mmr: bool = True,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top-k most relevant chunks for a query.
    Returns: [{"id","title","content","score","doc_id","chunk_index","source","tags"}, ...]
    """
    if not query or not query.strip():
        return []

    model = _get_model()
    dim = _DIM or 384

    if not EMBEDDINGS_FILE.exists() or not METADATA_FILE.exists():
        logger.warning("RAG store not initialized — returning empty results")
        return []

    try:
        with _STORE_LOCK:
            emb = np.load(EMBEDDINGS_FILE).astype(np.float32, copy=False)
            meta: List[Dict[str, Any]] = json.loads(
                METADATA_FILE.read_text(encoding="utf-8")
            )
            if emb.ndim != 2 or emb.shape[1] != dim or len(meta) != emb.shape[0]:
                logger.warning("Store corrupted or mismatched; returning empty results")
                return []

        # Encode query and normalize
        q = _encode_texts([query])[0]  # (d,)

        # Cosine similarity (vectors are normalized)
        sims = np.dot(emb, q)  # (N,)

        if use_mmr and k > 1 and emb.shape[0] > k:
            idxs = _mmr(q, emb, top_k=k, lambda_mult=0.7)
        else:
            idxs = np.argsort(sims)[::-1][:k].tolist()

        results: List[Dict[str, Any]] = []
        for idx in idxs:
            score = float(np.clip(sims[idx], -1.0, 1.0))
            if score < min_score:
                continue
            item = dict(meta[idx])  # shallow copy
            item["score"] = score
            results.append(item)

        top = max((r["score"] for r in results), default=0.0)
        logger.info(
            "RAG retrieved %s results | k=%s | top=%.3f | query='%s'",
            len(results),
            k,
            top,
            query[:120],
        )
        return results

    except Exception as e:
        logger.error(f"RAG retrieval failed | Error: {e}")
        return []


# ----------------------
# Maintenance helpers
# ----------------------
def clear_store() -> None:
    """Dangerous: wipe the vector store."""
    with _STORE_LOCK:
        for p in [EMBEDDINGS_FILE, METADATA_FILE, MANIFEST_FILE]:
            if p.exists():
                p.unlink()
        logger.warning("RAG store cleared.")


# ----------------------
# Example Usage
# ----------------------
if __name__ == "__main__":
    # Simulate your clinical knowledge base
    docs = [
        {
            "id": "harm-reduction-101",
            "title": "Harm Reduction Principles",
            "content": "Harm reduction meets patients where they are. It prioritizes safety, dignity, and incremental progress over abstinence-only goals. Key practices: needle exchange, naloxone access, non-judgmental engagement.",
        },
        {
            "id": "de-escalation",
            "title": "De-escalation Techniques",
            "content": "Use a soft tone, non-threatening posture, and active listening. Offer choices to restore sense of control. Validate feelings without agreeing. 'I see this is really hard' is better than 'Calm down.'",
        },
        {
            "id": "urge-surfing",
            "title": "Urge Surfing Technique",
            "content": "Teach patients to visualize cravings as waves: they rise, peak, and fall. Encourage riding the urge without acting. Mindfulness and breath are key tools.",
        },
    ]

    # Ingest once (append-safe)
    ingest_documents(docs)

    # Retrieve
    hits = retrieve("How do I help a patient with strong urges?")
    for r in hits:
        print(f"📄 {r['title']} (Score: {r['score']:.2f})\n{r['content']}\n")
