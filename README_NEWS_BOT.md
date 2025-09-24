# 🤖 News Bot - EventRegistry + Gemini AI

Automated news bot that fetches news from EventRegistry API and generates enhanced articles using Google's Gemini AI.

## 🚀 Quick Start

### 1. Set up API Keys (GitHub Secrets)
- `EVENTREGISTRY_API_KEY`: Get from [eventregistry.org](https://eventregistry.org/)
- `GOOGLE_API_KEY`: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 2. Run the Bot
- **Automated**: Runs daily at 9:00 AM UTC
- **Manual**: Go to Actions → "Simple News Bot" → "Run workflow"

### 3. Files Generated
- `examples/` - Jupyter notebook and Python script
- `.github/workflows/` - GitHub Actions workflows
- `docs/` - Complete setup documentation

## 📖 Full Documentation
See [docs/NEWS_BOT_GITHUB_ACTIONS.md](docs/NEWS_BOT_GITHUB_ACTIONS.md) for complete setup instructions.

## 🎯 Features
- ✅ Daily automated news fetching
- ✅ AI-enhanced article generation
- ✅ Multiple writing styles (professional/casual/academic)
- ✅ Category-based news filtering
- ✅ Markdown and JSON outputs
- ✅ Secure API key management
- ✅ Pull request automation

Generated files are uploaded as artifacts and can be automatically committed via pull requests.
