# CodeMed AI: V28 HCC Risk Adjustment & Medical Billing Intelligence

CodeMed AI is a HIPAA-aware platform powered by the Codemed LLM, designed to provide intelligent insights for V28 HCC risk adjustment and medical billing. It offers a suite of tools for healthcare professionals to navigate the complexities of medical coding and compliance.

## Key Features

- **V28 HCC Risk Adjustment Engine**: Perform real-time and batch V28 HCC lookups to ensure accurate risk scoring.
- **RAG-Powered Query Engine**: Ask complex questions about medical coding, compliance, and billing, and get answers from a rich knowledge base of CMS policies and guidelines.
- **Appeal Letter Generation**: Automatically generate well-structured and evidence-based appeal letters for denied claims.
- **Policy Search**: Search and browse a comprehensive library of CMS LCD/NCD policies.
- **ComboCode Enforcer**: Identify and flag incorrect code combinations to prevent claim denials.
- **RADV Risk Flags**: Proactively identify and mitigate RADV audit risks.

## Tech Stack

CodeMed AI is built with a modern and robust tech stack:

- **Backend**: Flask 3.0+, SQLite with FTS5 for full-text search.
- **AI & Machine Learning**: Anthropic Claude for natural language processing and generation.
- **Frontend**: A Next.js sub-application provides a modern user interface, with components for chat, document management, and more.
- **Database**: Supabase for the Next.js application.
- **Payments**: Stripe for subscription management.
- **Deployment**: The Flask application is deployed on Railway.

## Project Structure

The repository is organized into the following key directories:

- `codemedgroup/`: The core Flask application, containing the backend logic, API endpoints, and Jinja2 templates.
- `nextjs/`: The Next.js sub-application, which provides the modern user interface.
- `data/`: Contains data ingestion scripts and the SQLite database.

## API Endpoints

The Flask application exposes several API endpoints for interacting with the CodeMed AI platform. These endpoints require an API key for authentication.

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/status` | GET | Health check (no auth required) |
| `/api/v1/query` | POST | RAG query against the policy knowledge base (API key required) |
| `/api/v1/v28/lookup?code=` | GET | V28 HCC coefficient lookup |
| `/api/v1/v28/batch` | POST | Batch V28 HCC audit |
| `/api/v1/policies/search` | GET | Search CMS LCD/NCD policies |
| `/api/v1/policies/:id` | GET | Policy detail |
| `/api/v1/classify` | POST | Document classification |
| `/api/v1/appeals/generate` | POST | Appeal letter generation |

The platform also includes a web portal with routes for the Dashboard (`/`), AI Chat (`/chat`), V28 HCC Checker (`/v28`), Appeal Generator (`/appeals`), and API Docs (`/docs`).

## License

This project is licensed under the terms of the MIT license. See the [LICENSE](LICENSE) file for more details.
