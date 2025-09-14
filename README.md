# Azure AI Search REST Operations

This repo provides Python scripts to manage documents in Azure AI Search using REST APIs. Supports upload, delete, merge, and reindex operations.

## Setup
1. Copy `.env.example` to `.env` and fill in your Azure Search credentials.
2. Install dependencies: `pip install requests python-dotenv`
3. Run scripts from the `scripts/` folder.

## Scripts
- `upload_documents.py`: Add or replace documents
- `delete_documents.py`: Remove documents by ID
- `merge_documents.py`: Update specific fields
- `reindex_documents.py`: Rebuild index from scratch

## License
MIT
