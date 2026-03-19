# 🔬 AI Research Agent

An AI-powered research assistant that can browse papers on arXiv, read them in depth, perform research analysis, and generate ready-to-publish research papers — all through a conversational interface.

Built with **Langgraph** (agentic workflows), **Gemini** (LLM), and **Streamlit** (frontend).

---

## ✨ Features

- 🔍 **arXiv Search** — Searches arXiv for the latest papers on any topic
- 📖 **PDF Reader** — Downloads and extracts text from research papers
- 📄 **LaTeX PDF Generator** — Writes publication-ready papers with mathematical equations and renders them as PDF
- 🤖 **Conversational Agent** — ReAct agent that autonomously decides which tools to use
- 🧠 **Memory** — Thread-based conversation persistence using MemorySaver
- 💬 **Chat Interface** — Interactive Streamlit UI with real-time tool call visibility

---

## 🏗️ Architecture

```
User ──► Streamlit Chat UI ──► Langgraph ReAct Agent ──► Tools
                                      │                    ├── arXiv Search
                                      │                    ├── PDF Reader
                                      ▼                    └── LaTeX PDF Writer
                                 Gemini LLM
```

The agent uses a **ReAct loop** (`agent ↔ tools`) with conditional edges:
- The LLM decides which tool to call based on the conversation
- Tool results are fed back to the LLM
- The loop continues until the LLM has a final response

---

## 📁 Project Structure

```
├── .env.example          # API key template
├── requirements.txt      # Python dependencies
├── app.py                # Streamlit chat-based frontend
├── agent/
│   ├── __init__.py
│   └── graph.py          # Langgraph workflow (State, ToolNode, ReAct agent)
├── tools/
│   ├── __init__.py
│   ├── arxiv_tool.py     # arXiv paper search (raw API + XML parsing)
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

Edit `.env` and add your Google Gemini API key:

```
GOOGLE_API_KEY=your_api_key_here
```

Get a free key from [Google AI Studio](https://aistudio.google.com/apikey).

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 💬 How to Use

1. **Enter a research topic** — e.g., "Transformer attention mechanisms"
2. **Browse papers** — The agent searches arXiv and presents recent papers
3. **Pick a paper** — Ask the agent to read a specific paper in depth
4. **Discuss ideas** — The agent analyzes future research directions
5. **Generate a paper** — Ask it to write and export a LaTeX research paper
6. **Download PDF** — Download the generated paper from the sidebar

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Google Gemini (via `langchain-google-genai`) |
| **Agent Framework** | Langgraph (StateGraph, ToolNode, MemorySaver) |
| **Paper Search** | arXiv API (raw HTTP + XML parsing) |
| **PDF Reading** | PyPDF2 |
| **PDF Generation** | Tectonic (LaTeX compiler) |
| **Frontend** | Streamlit |
| **State Management** | Langgraph MemorySaver (thread-based) |

---

## 📜 License

This project is for **educational purposes only**.

---

## 🙏 Acknowledgments

Inspired by [AIwithhassan/ai-researcher](https://github.com/AIwithhassan/ai-researcher).
