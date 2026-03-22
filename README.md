# 🔬 AI Research Agent

An AI-powered research assistant that can browse papers on arXiv and Semantic Scholar, search the web, read papers in depth, perform research analysis, and generate ready-to-publish research papers — all through a conversational interface.

Built with **Langgraph** (agentic workflows), **Gemini/Groq/OpenAI** (multi-LLM), and **Streamlit** (frontend).

---

## ✨ Features

- 🔍 **arXiv Search** — Searches arXiv for the latest academic papers on any topic
- 🎓 **Semantic Scholar** — Finds papers with citation counts and impact metrics
- 🌐 **Web Search** — Searches the web via DuckDuckGo for blog posts, tutorials, and resources
- 📖 **PDF Reader** — Downloads and extracts text from research papers
- 📄 **LaTeX PDF Generator** — Writes publication-ready papers with mathematical equations
- 🤖 **Multi-LLM Support** — Switch between Google Gemini, Groq (Llama), and OpenAI (GPT) from the sidebar
- 🧠 **Memory** — Thread-based conversation persistence using MemorySaver
- 💬 **Chat Interface** — Interactive Streamlit UI with real-time tool call visibility
- 📤 **Export Options** — Download chat history as Markdown, Word (.docx), or JSON

---

## 🏗️ Architecture

```
User ──► Streamlit Chat UI ──► Langgraph ReAct Agent ──► Tools
                │                      │                    ├── arXiv Search
                │                      │                    ├── Semantic Scholar
                │                      │                    ├── Web Search (DuckDuckGo)
           LLM Selector                ▼                    ├── PDF Reader
          (Gemini/Groq/           LLM Provider              └── LaTeX PDF Writer
           OpenAI)
```

The agent uses a **ReAct loop** (`agent ↔ tools`) with conditional edges:
- The LLM decides which tool to call based on the conversation
- Tool results are fed back to the LLM
- The loop continues until the LLM has a final response

---

## 📁 Project Structure

```
├── .env.example          # API key template (Gemini, Groq, OpenAI)
├── requirements.txt      # Python dependencies
├── app.py                # Streamlit chat-based frontend
├── agent/
│   ├── __init__.py
│   └── graph.py          # Langgraph workflow (multi-LLM, ReAct agent)
├── tools/
│   ├── __init__.py
│   ├── arxiv_tool.py     # arXiv paper search (raw API + XML parsing)
│   ├── semantic_scholar.py  # Semantic Scholar search (citation metrics)
│   ├── web_search.py     # DuckDuckGo web search
│   ├── pdf_reader.py     # PDF text extraction (PyPDF2)
│   └── pdf_writer.py     # LaTeX → PDF generation (tectonic)
└── output/               # Generated PDFs stored here
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/aniketmondal1210/Agentic-AI-Researcher.git
cd Agentic-AI-Researcher
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Tectonic (for LaTeX PDF rendering)

- **Windows:** `choco install tectonic`
- **macOS:** `brew install tectonic`
- **Linux:** See [tectonic-typesetting.github.io](https://tectonic-typesetting.github.io/en-US/install.html)

### 4. Set up your API key

```bash
cp .env.example .env
```

Edit `.env` and add your API key(s):

```env
# Required — at least one LLM provider
GOOGLE_API_KEY=your_gemini_key_here

# Optional — for multi-LLM support
GROQ_API_KEY=your_groq_key_here
OPENAI_API_KEY=your_openai_key_here
```

| Provider | Free Tier | Get API Key |
|----------|-----------|-------------|
| **Gemini** | ✅ Yes | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **Groq** | ✅ Yes (generous) | [console.groq.com](https://console.groq.com) |
| **OpenAI** | ❌ Paid | [platform.openai.com](https://platform.openai.com/api-keys) |

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 💬 How to Use

1. **Choose your LLM** — Pick Gemini, Groq, or OpenAI from the sidebar
2. **Enter a research topic** — e.g., "Transformer attention mechanisms"
3. **Browse papers** — The agent searches arXiv, Semantic Scholar, and the web
4. **Pick a paper** — Ask the agent to read a specific paper in depth
5. **Discuss ideas** — The agent analyzes future research directions
6. **Generate a paper** — Ask it to write and export a LaTeX research paper
7. **Export** — Download the PDF, or export the chat as Markdown/Word/JSON

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Google Gemini, Groq (Llama), OpenAI (GPT) |
| **Agent Framework** | Langgraph (StateGraph, ToolNode, MemorySaver) |
| **Paper Search** | arXiv API, Semantic Scholar API |
| **Web Search** | DuckDuckGo (no API key needed) |
| **PDF Reading** | PyPDF2 |
| **PDF Generation** | Tectonic (LaTeX compiler) |
| **Chat Export** | Markdown, python-docx (Word), JSON |
| **Frontend** | Streamlit |

---

## 📜 License

This project is for **educational purposes only**.

---

## 🙏 Acknowledgments

Inspired by [AIwithhassan/ai-researcher](https://github.com/AIwithhassan/ai-researcher).
