# AI Creative Writing Assistant

A sophisticated web application for intelligent creative writing assistance, built with Flask, LangChain, and GraphRAG. Features real-time streaming responses, multi-book cross-reference capabilities, and interactive AI thinking process visualization.

## 🚀 Features

### Core Capabilities
- **Single Book Mode**: GraphRAG-based retrieval and generation for selected books
- **Cross-Book Mode**: Multi-book parallel retrieval with unified context fusion
- **Real-time Streaming**: Server-Sent Events (SSE) for token-level streaming responses
- **AI Thinking Process**: Visual display of tool calls, LLM reasoning, and book-grouped events
- **In-place Enhancement**: Polish and critique buttons for each assistant message
- **Book Management**: List, switch, and add books with top status display

### Technical Highlights
- **GraphRAG Integration**: Advanced graph-based retrieval augmented generation
- **Streaming Architecture**: True real-time token streaming with SSE
- **Multi-Agent System**: Specialized agents for different tasks (analysis, polish, cross-book)
- **Modern UI**: Responsive design with real-time updates and animations

## 🏗️ Architecture

```
├── frontend/                 # Frontend assets
│   ├── index.html           # Main page structure
│   ├── styles.css           # Styling (chat, thinking process, buttons, animations)
│   └── script_enhanced.js   # Frontend logic (SSE parsing, UI events, cross-book mode)
├── app.py                   # Flask entry point and API routes
├── langchain_agent.py       # Main LangChain Agent (tool chain, retrieval/generation)
├── cross_book_agent.py      # Cross-book orchestration (parallel sub-agents, context fusion)
├── polish_agent.py          # Independent polish/critique agent
├── prompt_utils.py          # Agent guidelines, constraints, output templates
├── search/                  # GraphRAG engines
│   ├── rag_engine.py        # GraphRAG engine wrapper
│   └── quick_engine.py      # Conservative parameter engine
└── book_data/               # Book data directories (output/ parquet + lancedb)
```

## 🛠️ Technology Stack

### Backend
- **Flask**: Web framework with CORS support
- **LangChain**: LLM orchestration and agent framework
- **GraphRAG**: Graph-based retrieval augmented generation
- **Azure OpenAI**: LLM provider (GPT-4o, GPT-4.1)
- **LanceDB**: Vector database for embeddings
- **Pandas**: Data processing for graph entities

### Frontend
- **Vanilla JavaScript**: No framework dependencies
- **Server-Sent Events (SSE)**: Real-time streaming
- **CSS3**: Modern styling with animations
- **HTML5**: Semantic markup

## 📋 Prerequisites

- Python 3.11+ (strongly recommended)
- Windows 10/11 or Linux (Ubuntu 20.04+)
- Azure OpenAI API key

## ⚙️ Installation

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd ai-creative-writing-assistant
```

### 2. Set Up Environment Variables
Copy the example environment file and configure your settings:
```bash
cp env.example .env
```

Edit `.env` with your actual values:
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
# Optional: Separate embedding key
Embedding_key=your_embedding_api_key
```

### 3. Create Virtual Environment
```bash
# Windows PowerShell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python3.11 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -U pip
pip install -r requirements.txt
```

### 5. Prepare Book Data
Each book should have an `output/` directory containing:
- `communities.parquet`
- `entities.parquet`
- `community_reports.parquet`
- `relationships.parquet`
- `text_units.parquet`
- `lancedb/` directory (entity description embeddings)

## 🚀 Running the Application

### Development Mode
```bash
python app.py
```

### Production Mode (Recommended)
```bash
python -m waitress --listen=0.0.0.0:5000 app:app
```

### Access the Application
- Frontend: `http://localhost:5000/`
- Health Check: `http://localhost:5000/api/health`

## 📚 API Reference

### Core Endpoints
- `GET /api/health` - Health check with agent status
- `GET /api/books` - List loaded books with current selection
- `POST /api/switch-book` - Switch current book
- `POST /api/add-book` - Add new book
- `POST /api/chat` - Single book chat/creation (SSE streaming)
- `POST /api/cross-chat` - Cross-book creation (SSE streaming)
- `POST /api/polish` - Polish message (SSE streaming)
- `POST /api/critique` - Critique message (SSE streaming)

### SSE Event Types
- `status` - Connection status
- `run_start/run_end` - Chain execution events
- `plan/plan_done` - Agent planning events
- `tool_start/tool_end` - Tool execution events
- `llm_start/llm_token/llm_end` - LLM processing events
- `final` - Final response
- `done` - Stream completion
- `error` - Error events

## 🎯 Usage Guide

### Single Book Mode
1. Select a book from the left sidebar
2. Choose "Single Book Mode" from the top dropdown
3. Enter your question or creative instruction
4. Watch the AI thinking process in real-time
5. Use polish/critique buttons for message enhancement

### Cross-Book Mode
1. Select "Cross-Book Mode" from the top dropdown
2. Click "Select Books" to choose multiple books
3. Enter your question - the system will retrieve from all selected books
4. View book-grouped thinking processes
5. Receive unified response with cross-book context

### Real-time Features
- **Streaming Responses**: See text appear token by token
- **Thinking Process**: Monitor tool calls and LLM reasoning
- **In-place Actions**: Polish or critique any assistant message instantly

## 🔧 Configuration

### Azure OpenAI Settings
Modify deployment names and versions in:
- `langchain_agent.py`
- `polish_agent.py`
- `cross_book_agent.py`

### GraphRAG Parameters
Adjust retrieval parameters in:
- `search/rag_engine.py` - Main engine
- `search/quick_engine.py` - Conservative engine

### Book Data Paths
Configure book paths in `app.py`:
```python
DEFAULT_BOOKS = [
    "book4/output/",    # Ordinary World
    "book5/output/",    # Three-Body Problem
    "book6/output/",    # Three-Body Problem 2
    # ... more books
]
```

## 🚀 Production Deployment

### 1. Server Setup
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv

# Deploy application
cd /opt/ai-writing-assistant
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Systemd Service (Linux)
Create `/etc/systemd/system/ai-writing.service`:
```ini
[Unit]
Description=AI Creative Writing Assistant
After=network.target

[Service]
WorkingDirectory=/opt/ai-writing-assistant
ExecStart=/opt/ai-writing-assistant/.venv/bin/python -m waitress --listen=0.0.0.0:5000 app:app
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

### 3. Reverse Proxy (Nginx)
```nginx
location /api/ {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
    proxy_buffering off;        # Critical for SSE
    proxy_cache off;
}
```

### 4. Firewall Configuration
```bash
# Open port 5000 (or your proxy port)
sudo ufw allow 5000
```

## 🐛 Troubleshooting

### Common Issues

**Agent Not Initialized**
- Check book data paths and required files
- Verify Azure OpenAI API key in `.env`
- Ensure proper initialization in production mode

**SSE Not Streaming**
- Confirm `llm_token` events are not filtered
- Check proxy buffering settings (`proxy_buffering off`)
- Verify waitress is listening on `0.0.0.0:5000`

**Book Management Issues**
- Test `/api/books` endpoint directly
- Check book data integrity (parquet files + lancedb)
- Verify file permissions

**Dependency Installation**
- Use Python 3.11+ for compatibility
- Create fresh virtual environment
- Update pip before installation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain**: For the excellent LLM orchestration framework
- **GraphRAG**: For graph-based retrieval augmented generation
- **Azure OpenAI**: For providing the LLM services
- **Flask**: For the lightweight and flexible web framework

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section above
- Review the API documentation

---

**Built with ❤️ for creative writing enthusiasts**

---

## 📝 Changelog

### Version 1.0.0 (2025-01-XX)
- Initial release
- GraphRAG-based book analysis
- Real-time streaming responses
- Multi-book cross-reference capabilities
- Text polishing and critique features

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

