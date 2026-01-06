# 📋 LitDocket - Legal Docket Management System

**AI-powered deadline tracking and case management for legal professionals**

[![Deploy Status](https://img.shields.io/badge/deploy-ready-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## 🚀 Quick Start

### Local Development

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your keys
npm run dev
```

Open http://localhost:3000

---

## 🌐 Deploy to Production

**Ready to deploy to litdocket.com?**

👉 **See: [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)** (Quick 2-hour guide)

👉 **See: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** (Detailed step-by-step)

**Stack:**
- Frontend: Vercel (Free)
- Backend: Railway ($5/month)
- Database: PostgreSQL (Included)
- Storage: Firebase (Free)

---

## 📦 Project Structure

```
docketassist-v3/
├── backend/              # FastAPI Python backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   └── utils/       # Utilities
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/            # Next.js React frontend
│   ├── app/            # App routes
│   ├── components/     # React components
│   ├── lib/            # Utilities
│   └── .env.example
│
└── knowledge-base/      # Legal rules database
    ├── rules/
    └── scripts/
```

---

## ✨ Features

### Core Features
- 📄 **Document Analysis** - AI extracts case info and deadlines from PDFs
- 🤖 **AI Chat** - Ask questions about your cases
- 📅 **Smart Deadlines** - Automatic calculation with full transparency
- 🎯 **Trigger Events** - One date generates 50+ related deadlines
- 📊 **Case Insights** - AI-powered case health monitoring
- 🔍 **Global Search** - Search across all cases, documents, and deadlines

### Advanced Features
- **10/10 Legal Defensibility** - Every deadline shows complete calculation basis
- **Service Method Extensions** - Automatic +5 days for mail (FL state), +3 days (Federal)
- **Holiday Adjustment** - Rolls deadlines to next business day
- **Confidence Scoring** - Each deadline has AI confidence rating
- **Verification Gate** - Review AI-extracted deadlines before accepting
- **Real-time Updates** - Dynamic UI updates across components

---

## 🛠️ Tech Stack

**Frontend:**
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Firebase Auth

**Backend:**
- FastAPI (Python)
- SQLAlchemy (ORM)
- PostgreSQL
- Claude AI (Anthropic)

**Infrastructure:**
- Vercel (Frontend hosting)
- Railway (Backend + DB)
- Firebase (Auth + Storage)

---

## 🔐 Security

- ✅ All secrets in environment variables
- ✅ JWT authentication
- ✅ Firebase Auth integration
- ✅ CORS protection
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ HTTPS enforced in production

---

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment walkthrough
- **[DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)** - Quick deployment checklist
- **[SYSTEM_STATUS.md](backend/SYSTEM_STATUS.md)** - Current system status
- **[REAL_FIXES_COMPLETE.md](backend/REAL_FIXES_COMPLETE.md)** - Recent bug fixes
- **[TIMELINE_DATE_FIX.md](backend/TIMELINE_DATE_FIX.md)** - Timeline date fix details
- **[TRIGGER_VISIBILITY_FIX.md](TRIGGER_VISIBILITY_FIX.md)** - Trigger display fix

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Manual Testing Checklist
- [ ] Upload PDF → Case created
- [ ] Trigger detection → Deadlines generated
- [ ] Chat → Messages send/receive
- [ ] Insights → Case health displayed
- [ ] Calendar export → .ics file downloads

---

## 🐛 Known Issues

See [GitHub Issues](https://github.com/YOUR_USERNAME/litdocket/issues) for current bugs and feature requests.

---

## 📈 Roadmap

### Phase 1: MVP (Complete ✅)
- [x] Document upload and analysis
- [x] AI deadline extraction
- [x] Case management
- [x] Chat interface
- [x] Authentication

### Phase 2: Production Polish (In Progress 🚧)
- [x] Deploy to litdocket.com
- [ ] Improve deadline UI with expandable cards
- [ ] Add bulk actions
- [ ] Email notifications
- [ ] Calendar integrations (Google, Outlook)

### Phase 3: Advanced Features (Planned 📋)
- [ ] Multi-user collaboration
- [ ] Document comparison
- [ ] Advanced search filters
- [ ] Mobile app
- [ ] API for integrations

---

## 💰 Cost Estimate

**Monthly costs for production:**

| Service | Cost |
|---------|------|
| Railway (Backend + PostgreSQL) | $5 |
| Vercel (Frontend) | FREE |
| Firebase (Storage + Auth) | FREE |
| Anthropic API (AI) | ~$10-50 |
| Domain (litdocket.com) | ~$1 |

**Total: ~$16-56/month** (mostly AI usage)

---

## 🤝 Contributing

This is a private project, but if you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🆘 Support

**Issues?**
- Check logs (Railway for backend, Vercel for frontend)
- See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) troubleshooting section
- Open a GitHub issue

**Need help deploying?**
- Follow [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)
- Check Railway docs: https://docs.railway.app
- Check Vercel docs: https://vercel.com/docs

---

## 🎯 Getting Started Checklist

- [ ] Clone repository
- [ ] Set up backend (.env file)
- [ ] Set up frontend (.env.local file)
- [ ] Run locally (backend + frontend)
- [ ] Test document upload
- [ ] Deploy to Railway (backend)
- [ ] Deploy to Vercel (frontend)
- [ ] Connect domain
- [ ] Test in production
- [ ] Invite users!

---

## 🌟 Features Overview

### For Lawyers
- **Never miss a deadline** - AI tracks everything automatically
- **10/10 transparency** - See exactly how each deadline was calculated
- **One date, 50+ deadlines** - Trigger events cascade automatically
- **Chat with your cases** - Ask questions, get instant answers

### For Law Firms
- **Case health monitoring** - Know which cases need attention
- **Team collaboration** - Share cases with team members
- **Audit trail** - Complete history of all actions
- **Export anywhere** - iCal, CSV, or API integration

---

**Built with ❤️ for legal professionals**

**Last Updated**: January 6, 2026
**Version**: 1.0.0
**Status**: Production Ready 🚀
