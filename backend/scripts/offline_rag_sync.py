#!/usr/bin/env python3
"""
Offline RAG Sync Script
-----------------------
Pulls verified knowledge items from Supabase and stores two local files inside
`backend/data/`:
 1. `knowledge_embeddings.npy` – NumPy array of shape (N, D)
 2. `knowledge_meta.json`       – List[dict] with id, title, content_type, category

These files enable the AI Agent to perform Retrieval-Augmented Generation even
when Supabase is unavailable (offline fallback).

Run manually or via cron:
    $ python backend/scripts/offline_rag_sync.py
"""
import os, json, argparse, hashlib, datetime
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
from dotenv import load_dotenv
from supabase import create_client

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

EMBED_PATH = DATA_DIR / "knowledge_embeddings.npy"
META_PATH = DATA_DIR / "knowledge_meta.json"
LAST_SYNC_PATH = DATA_DIR / ".last_sync"

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY env vars")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def fetch_knowledge(updated_after: Optional[str] = None, limit: int = 1000) -> List[Dict]:
    """Fetch knowledge items changed after timestamp (iso UTC)"""
    rows: List[Dict] = []
    offset = 0
    while True:
        q = (
            supabase.table("rag_knowledge_base")
            .select("id, title, content, embedding, content_type, category, updated_at")
            .eq("is_verified", True)
            .range(offset, offset + limit - 1)
        )
        if updated_after:
            q = q.gte("updated_at", updated_after)
        resp = q.execute()
        batch = resp.data or []
        if not batch:
            break
        rows.extend(batch)
        offset += limit
        if len(batch) < limit:
            break
    return rows


def build_numpy_matrix(rows: List[Dict]) -> np.ndarray:
    """Stack embeddings into numpy float32 matrix"""
    if not rows:
        return np.empty((0, 0), dtype=np.float32)
    dim = len(rows[0]["embedding"])
    mat = np.vstack([r["embedding"] for r in rows]).astype("float32")
    assert mat.shape[1] == dim, "Embedding dimension mismatch"
    return mat


def md5_of(obj) -> str:
    m = hashlib.md5()
    m.update(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode())
    return m.hexdigest()


def load_meta() -> List[Dict]:
    if not META_PATH.exists():
        return []
    with META_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(new_rows: List[Dict]):
    """Merge and save snapshot atomically"""
    if not new_rows:
        print("⚡ No new/updated rows – nothing to write")
        return

    existing_rows = load_meta()
    by_id = {r["id"]: r for r in existing_rows}
    for r in new_rows:
        by_id[r["id"]] = r  # insert or update

    combined_rows = list(by_id.values())

    # Hash compare to avoid unnecessary writes
    if md5_of(combined_rows) == md5_of(existing_rows):
        print("⚡ Snapshot already up-to-date")
        return

    # Write to temp then replace
    tmp_embed = EMBED_PATH.with_suffix(".tmp.npy")
    tmp_meta = META_PATH.with_suffix(".tmp.json")

    np.save(tmp_embed, build_numpy_matrix(combined_rows))
    with tmp_meta.open("w", encoding="utf-8") as f:
        json.dump(combined_rows, f, ensure_ascii=False)

    os.replace(tmp_embed, EMBED_PATH)
    os.replace(tmp_meta, META_PATH)

    # touch last sync file
    LAST_SYNC_PATH.write_text(datetime.datetime.utcnow().isoformat())

    print(f"✅ Snapshot updated ({len(combined_rows)} items)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync RAG knowledge from Supabase")
    parser.add_argument("--full", action="store_true", help="Full rebuild instead of incremental")
    args = parser.parse_args()

    since_ts = None
    if not args.full and LAST_SYNC_PATH.exists():
        since_ts = (datetime.datetime.utcnow() - datetime.timedelta(minutes=15)).isoformat()

    try:
        rows = fetch_knowledge(updated_after=since_ts)
        save_snapshot(rows)
    except Exception as e:
        print(f"❌ Offline knowledge sync failed: {e}") 