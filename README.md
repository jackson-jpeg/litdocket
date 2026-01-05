# Florida Legal Docketing Assistant

A web-hosted legal docketing and case management assistant specialized in Florida jurisdictions with RAG-based AI knowledge of all Florida state, federal, and local court rules.

## Features

- **Smart PDF Upload**: Drag-and-drop PDF documents with automatic case detection
- **AI-Powered Analysis**: Extract case metadata, parties, and deadlines using Claude AI
- **Case Room**: 3-panel workspace with documents, calendar, and AI chatbot
- **RAG System**: Knowledge base of Florida court rules for accurate legal guidance
- **Deadline Extraction**: Automatic calculation of response deadlines based on Florida rules

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15
- **Vector DB**: Pinecone
- **AI**: Anthropic Claude
- **Storage**: AWS S3

### Frontend
- **Framework**: Next.js 14 (TypeScript)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- PostgreSQL 15
- AWS Account (for S3)
- Pinecone Account
- Anthropic API Key

### Backend Setup

1. Start PostgreSQL database:
```bash
docker-compose up -d
```

2. Create virtual environment and install dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the backend:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`
API docs at: `http://localhost:8000/api/docs`

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. Run the development server:
```bash
npm run dev
```

Frontend will be available at: `http://localhost:3000`

## Project Structure

```
docketassist-v3/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── main.py         # App entry point
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   └── components/    # React components
│   └── package.json
├── knowledge-base/        # Florida court rules
│   ├── scripts/          # Ingestion scripts
│   └── rules/           # Rule PDFs
└── docker-compose.yml    # PostgreSQL setup
```

## Development

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## Deployment

See `docs/DEPLOYMENT.md` for production deployment instructions.

## License

Proprietary - All rights reserved

## Contact

For questions or support, contact: [Your Contact Info]
