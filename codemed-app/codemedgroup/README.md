# CodeMed Group Platform

**Layer 2:** Regulatory Intelligence API  
**Layer 1:** NexusAuth RCM Portal (built on the API)

## Stack
- Python + Flask
- SQLite (nexusauth.db) — swap for PostgreSQL at scale
- Anthropic Claude (claude-sonnet-4) via API
- Gunicorn for production

## Local Setup

```bash
# 1. Clone and install
git clone https://github.com/codemedgroup/platform
cd platform
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Build the database
python data/build_seed_db.py

# 4. Run locally
python app.py
# → http://localhost:5000
```

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...    # Required
SECRET_KEY=random_string         # Change in production
DB_PATH=data/nexusauth.db       # Default
PORT=5000                        # Default
```

## Deploy to Railway

1. Push to GitHub (codemedgroup/platform)
2. Connect repo at railway.app
3. Add environment variables in Railway dashboard:
   - ANTHROPIC_API_KEY
   - SECRET_KEY (generate a random one)
4. Railway auto-deploys on push

railway.json handles the build + DB initialization automatically.

## API Endpoints

```
GET  /api/v1/status              # Health check (no auth)
POST /api/v1/query               # RAG query (X-API-Key required)
GET  /api/v1/v28/lookup?code=    # V28 HCC lookup
POST /api/v1/v28/batch           # Batch V28 audit
GET  /api/v1/policies/search     # Policy search
GET  /api/v1/policies/:id        # Policy detail
POST /api/v1/classify            # Document classification
POST /api/v1/appeals/generate    # Appeal letter generation
```

## Portal Routes

```
/        Dashboard
/chat    CodeMed AI Chat
/v28     V28 HCC Checker
/appeals Appeal Generator
/docs    API Docs + Key Management
```

## Upgrading the Corpus

When you have the real CMS data (1,307+ policies):
```bash
python build_db.py --lcd current_lcd.zip --ncd ncd.zip --out data/nexusauth.db
```
The Flask app will use the real data automatically — no code changes needed.

---
codemedgroup.com · mason@codemedgroup.com
