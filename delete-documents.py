import requests
import os
import json
from dotenv import load_dotenv
import argparse

# Load environment from .env (if present)
load_dotenv()

# Load configuration from environment
endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX")

def parse_args():
    p = argparse.ArgumentParser(description="Search and delete documents from an Azure Search index")
    p.add_argument("--index", "-i", dest="index", help="Index name to use (overrides AZURE_SEARCH_INDEX env var)")
    return p.parse_args()

def validate_env():
    missing = [k for k, v in (
        ("AZURE_SEARCH_ENDPOINT", endpoint),
        ("AZURE_SEARCH_API_KEY", api_key),
        ("AZURE_SEARCH_INDEX", index_name),
    ) if not v]
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")

def delete_documents(doc_ids):
    """Delete documents by id list from the Azure Search index using REST API.

    Args:
        doc_ids (list[str]): list of document ids to delete.

    Returns:
        requests.Response: the HTTP response object.
    """
    validate_env()

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    documents_to_delete = [
        {"@search.action": "delete", "id": doc_id} for doc_id in doc_ids
    ]

    url = f"{endpoint.rstrip('/')}/indexes/{index_name}/docs/index?api-version=2023-10-01-Preview"

    # Use json= to let requests encode the body and set content-type
    # Optional debug output
    debug = os.getenv("DEBUG")
    if debug and debug != "0":
        masked_headers = headers.copy()
        if "api-key" in masked_headers:
            masked_headers["api-key"] = "***REDACTED***"
        print("DEBUG: POST", url)
        print("DEBUG: headers:", masked_headers)
        print("DEBUG: payload:", json.dumps({"value": documents_to_delete}, indent=2))

    response = requests.post(url, headers=headers, json={"value": documents_to_delete})
    return response


def search_doc_ids(search_text=None, filter_expr=None, top=50):
    """Search the index and return a list of document ids (keys).

    This uses the Azure Search "search" endpoint and requests only the key field.
    Adjust the 'searchFields' or 'select' parameters if your key field is named differently.
    """
    validate_env()

    # The search endpoint: /indexes/{indexName}/docs/search?api-version=...
    url = f"{endpoint.rstrip('/')}/indexes/{index_name}/docs/search?api-version=2023-10-01-Preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    body = {
        "top": top,
        "select": "id",  # request only the id/key field; change if your key is named differently
    }
    if search_text is not None:
        body["search"] = search_text
    else:
        body["search"] = "*"

    if filter_expr:
        body["filter"] = filter_expr

    debug = os.getenv("DEBUG")
    if debug and debug != "0":
        masked_headers = headers.copy()
        masked_headers["api-key"] = "***REDACTED***"
        print("DEBUG: SEARCH POST", url)
        print("DEBUG: headers:", masked_headers)
        print("DEBUG: body:", json.dumps(body, indent=2))

    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"Search failed: {resp.status_code} {resp.text}")

    data = resp.json()
    ids = []
    for doc in data.get("value", []):
        # assumes key field is 'id' — adjust if your index uses a different key name
        if "id" in doc:
            ids.append(doc["id"])
        else:
            # fallback: take first property as key
            for k, v in doc.items():
                ids.append(v)
                break
    return ids


if __name__ == "__main__":
    # Example usage
    try:
        args = parse_args()
        # allow CLI override of index name
        if args.index:
            index_name = args.index

        # Interactive: if you know the IDs, enter comma-separated IDs.
        # Otherwise enter a search query (or leave blank for all) to find candidate IDs.
        inp = input("Enter comma-separated doc IDs to delete, or press Enter to search: ").strip()
        if inp:
            docs = [s.strip() for s in inp.split(",") if s.strip()]
        else:
            q = input("Enter search text (leave empty for '*'): ").strip()
            f = input("Enter filter expression (optional, e.g. 'category eq \"books\"'): ").strip()
            ids = search_doc_ids(search_text=q if q else None, filter_expr=f if f else None, top=100)
            if not ids:
                print("No documents found for that query/filter.")
                raise SystemExit(0)
            print(f"Found {len(ids)} documents. Showing up to 100 ids:")
            for i, _id in enumerate(ids, start=1):
                print(f"{i}. {_id}")
            sel = input("Enter comma-separated numbers to select ids to delete, or 'all' to delete all listed: ").strip()
            if sel.lower() == 'all':
                docs = ids
            else:
                nums = [int(s.strip()) for s in sel.split(',') if s.strip()]
                docs = [ids[n-1] for n in nums if 1 <= n <= len(ids)]

        if not docs:
            print("No document ids selected, exiting.")
            raise SystemExit(0)

        print("About to delete the following documents:")
        for d in docs:
            print(" -", d)
        ok = input("Proceed? (y/N): ").strip().lower()
        if ok != 'y':
            print("Aborted by user.")
            raise SystemExit(0)

        resp = delete_documents(docs)
        print("Status:", resp.status_code)
        try:
            print("Response:", resp.json())
        except ValueError:
            print("Response (non-json):", resp.text)
    except Exception as e:
        print("Error:", str(e))
