# Florida Docketing Assistant - Quick Start Guide

## What's Been Built

I've created a complete foundation for your Florida Legal Docketing Assistant with:

### Backend (FastAPI + Python)
- ✅ FastAPI application with PostgreSQL database models
- ✅ SQLAlchemy models for users, cases, documents, deadlines, chat messages
- ✅ Claude AI service for document analysis
- ✅ PDF text extraction and parsing
- ✅ Document upload endpoint with automatic case routing
- ✅ Case management API endpoints
- ✅ Docker Compose setup for PostgreSQL

### Frontend (Next.js + TypeScript)
- ✅ Next.js 14 with TypeScript and Tailwind CSS
- ✅ Professional landing page with drag-and-drop upload
- ✅ API client configuration
- ✅ TypeScript types for all data models
- ✅ Responsive design with "LawTech" theme

### Key Features Implemented
1. **Smart PDF Upload**: Drag-and-drop interface that accepts PDF files
2. **AI Document Analysis**: Claude extracts case number, parties, court, document type
3. **Automatic Case Routing**: Checks if case exists, routes to existing or creates new
4. **Case Management**: Full CRUD operations for cases
5. **Database Schema**: Complete PostgreSQL schema ready for all planned features

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15 (via Docker)
- Your Claude API key (already configured)

### 1. Start PostgreSQL Database

```bash
cd /Users/jackson/docketassist-v3
docker compose up -d
```

Wait ~10 seconds for PostgreSQL to initialize.

### 2. Start Backend API

```bash
cd /Users/jackson/docketassist-v3/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: **http://localhost:8000**
API docs at: **http://localhost:8000/api/docs**

### 3. Start Frontend

```bash
cd /Users/jackson/docketassist-v3/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: **http://localhost:3000**

## Testing the Application

1. Open **http://localhost:3000** in your browser
2. Drag and drop a PDF legal document (or click to select)
3. The app will:
   - Extract text from the PDF
   - Analyze it with Claude AI
   - Extract case number, parties, and metadata
   - Create a new case or route to existing case
   - Redirect you to the Case Room

## Project Structure

```
/Users/jackson/docketassist-v3/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API endpoints
│   │   │   ├── documents.py  # PDF upload
│   │   │   └── cases.py      # Case management
│   │   ├── models/           # Database models
│   │   ├── services/         # Business logic
│   │   │   ├── ai_service.py       # Claude integration
│   │   │   └── document_service.py # PDF processing
│   │   ├── utils/
│   │   │   └── pdf_parser.py # PDF text extraction
│   │   ├── config.py         # Settings
│   │   ├── database.py       # DB connection
│   │   └── main.py           # FastAPI app
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Landing page
│   │   ├── layout.tsx        # Root layout
│   │   └── globals.css       # Global styles
│   ├── lib/
│   │   └── api-client.ts     # Axios client
│   ├── types/
│   │   └── index.ts          # TypeScript types
│   └── package.json
│
└── docker-compose.yml        # PostgreSQL setup
```

## API Endpoints

### Documents
- `POST /api/v1/documents/upload` - Upload and analyze PDF
- `GET /api/v1/documents/{id}` - Get document details

### Cases
- `GET /api/v1/cases` - List all user cases
- `GET /api/v1/cases/{id}` - Get case details
- `GET /api/v1/cases/{id}/documents` - Get case documents

## What's Next

### Phase 2: Case Room (3-Panel Layout)
Next steps to build the Case Room interface:
1. Create `/app/cases/[caseId]/page.tsx` with 3-panel layout
2. **Panel A**: Document library (chronological list)
3. **Panel B**: Calendar with deadlines
4. **Panel C**: AI chat interface

### Phase 3: RAG System
1. Setup Pinecone account
2. Ingest Florida court rules
3. Implement RAG retrieval in `rag_service.py`
4. Enhance chat with court rules context

### Phase 4: Deadline Extraction
1. Build `deadline_service.py`
2. Implement Florida rules deadline calculations
3. Auto-extract deadlines from documents
4. Display in calendar

## Configuration

### Environment Variables

Backend (`.env` file - create from `.env.example`):
```env
DATABASE_URL=postgresql://docketassist:password@localhost:5432/docketassist
ANTHROPIC_API_KEY=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
```

Frontend (`.env.local` - already created):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Database Schema

The PostgreSQL database includes these tables:
- `users` - User accounts
- `cases` - Legal cases
- `documents` - Uploaded PDFs
- `deadlines` - Calculated deadlines
- `chat_messages` - AI conversation history
- `calendar_events` - Calendar entries

All tables use UUIDs for IDs and include proper foreign key relationships.

## Troubleshooting

### Database Connection Error
```bash
# Check if PostgreSQL is running
docker ps

# View logs
docker logs docketassist-db

# Restart database
docker compose restart
```

### Backend Import Errors
```bash
# Make sure you're in the backend directory
cd /Users/jackson/docketassist-v3/backend

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend Not Loading
```bash
# Clear Next.js cache
cd /Users/jackson/docketassist-v3/frontend
rm -rf .next
npm install
npm run dev
```

## Features Demonstrated

1. **Drag-and-Drop Upload**: Professional UI with progress indicator
2. **Claude AI Integration**: Document analysis working end-to-end
3. **Case Detection**: Automatically extracts case numbers from PDFs
4. **Smart Routing**: Creates new cases or routes to existing ones
5. **Database Persistence**: All data stored in PostgreSQL
6. **Type Safety**: Full TypeScript types for frontend
7. **API Documentation**: Auto-generated docs at /api/docs

## Development Workflow

1. **Backend Changes**: The server auto-reloads with `--reload` flag
2. **Frontend Changes**: Next.js has fast refresh enabled
3. **Database Changes**: Use Alembic for migrations (to be set up)

## Current Status

✅ **Completed**:
- Project structure
- Backend API with FastAPI
- Database models
- Claude AI integration
- PDF upload and analysis
- Document service
- Next.js frontend
- Landing page with upload
- API client setup

🚧 **In Progress**:
- Case Room UI (3-panel layout)
- RAG system with Pinecone
- Deadline extraction service
- Chat interface

📋 **Planned**:
- Authentication system
- AWS S3 integration (currently using local storage)
- RAG knowledge base ingestion
- Calendar integration
- Email notifications
- Production deployment

## Support

For questions or issues:
1. Check the main README.md
2. Review API docs at http://localhost:8000/api/docs
3. Check backend logs in terminal
4. Review browser console for frontend errors

---

**Built with**: FastAPI, PostgreSQL, Claude AI, Next.js, TypeScript, Tailwind CSS
