"""
Quick diagnostic script to identify why H-RAG retrieval returns 0 results.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import validate_config
validate_config()

from src.db import get_table_counts, _get_client
from src.embedder import embed_single

print("=== Step 1: Check table counts ===")
counts = get_table_counts()
for table, count in counts.items():
    status = "OK" if count > 0 else "EMPTY!"
    print(f"  {table}: {count} rows  [{status}]")

print("\n=== Step 2: Test direct SQL query (bypassing RPC) ===")
client = _get_client()

# Check if data exists with a simple select
result = client.table("hrag_folder_summaries").select("id, folder_path, content").execute()
print(f"  Folder summaries found: {len(result.data)}")
for row in result.data:
    print(f"    - {row['folder_path']}: {row['content'][:80]}...")

print("\n=== Step 3: Test embedding + RPC ===")
test_query = "What is RAG?"
embedding = embed_single(test_query)
print(f"  Embedding generated: dim={len(embedding)}, first 3 values={embedding[:3]}")

# Try the RPC function
try:
    rpc_result = client.rpc("match_folder_summaries", {
        "query_embedding": embedding,
        "match_count": 3,
    }).execute()
    print(f"  RPC match_folder_summaries returned: {len(rpc_result.data)} results")
    for row in rpc_result.data:
        print(f"    - {row.get('folder_path', '?')} (sim={row.get('similarity', '?')})")
except Exception as e:
    print(f"  RPC FAILED: {e}")

print("\n=== Step 4: Test direct vector search (no index) ===")
try:
    # Use raw SQL via RPC to bypass any index issues
    raw_result = client.rpc("match_folder_summaries", {
        "query_embedding": embedding,
        "match_count": 3,
    }).execute()
    print(f"  Results: {len(raw_result.data)}")
except Exception as e:
    print(f"  Direct search FAILED: {e}")

print("\n=== Step 5: Check if vector column has data ===")
try:
    check = client.table("hrag_folder_summaries").select("id, folder_path").execute()
    print(f"  Rows in folder_summaries: {len(check.data)}")
    if check.data:
        # Check if embedding column is null
        check2 = client.table("hrag_folder_summaries").select("id, embedding").limit(1).execute()
        if check2.data:
            emb = check2.data[0].get("embedding")
            if emb is None:
                print("  WARNING: embedding column is NULL! Data was stored without embeddings.")
            else:
                print(f"  Embedding exists, type: {type(emb)}, length: {len(emb) if isinstance(emb, (list, str)) else 'unknown'}")
except Exception as e:
    print(f"  Check FAILED: {e}")

print("\nDone.")
