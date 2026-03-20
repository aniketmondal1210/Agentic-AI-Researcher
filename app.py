"""
Streamlit Frontend — AI Research Agent
A chat-based interface for the AI Research Agent powered by Langgraph.
"""

import sys
import os
import json
import io
from datetime import datetime

# Add the project root to path
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from agent.graph import INITIAL_PROMPT, graph, build_graph
from pathlib import Path
import logging
import uuid
from langchain_core.messages import AIMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Page Configuration ───
st.set_page_config(
    page_title="AI Research Agent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS for Premium Styling ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .main-header h1 {
        color: #e0e0ff;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #8888bb;
        font-size: 1rem;
        margin-top: 0.4rem;
        font-weight: 300;
    }

    /* Tool call info boxes */
    .tool-call-box {
        background: rgba(30, 30, 58, 0.7);
        border-left: 3px solid #6c5ce7;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
        color: #a0a0cc;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #12122a 0%, #1a1a35 100%);
    }

    /* Hide default branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─── Session State Initialization ───
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    logger.info("Initialized chat history")

if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "current_provider" not in st.session_state:
    st.session_state.current_provider = "gemini"

if "current_graph" not in st.session_state:
    st.session_state.current_graph = graph


# ─── Helper: Extract text from AIMessage content ───
def extract_text(content):
    """Extract clean text from AIMessage content (handles string and list formats)."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


# ─── Helper: Export chat to Markdown ───
def export_chat_markdown():
    """Export chat history as a Markdown string."""
    lines = [f"# AI Research Agent — Chat Export\n"]
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**Session:** {st.session_state.thread_id[:8]}\n\n---\n")
    for msg in st.session_state.chat_history:
        role = "🧑 User" if msg["role"] == "user" else "🤖 Assistant"
        lines.append(f"### {role}\n\n{msg['content']}\n\n---\n")
    return "\n".join(lines)


# ─── Helper: Export chat to Word ───
def export_chat_docx():
    """Export chat history as a .docx file."""
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()

    # Title
    title = doc.add_heading("AI Research Agent — Chat Export", level=0)
    doc.add_paragraph(
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"Session: {st.session_state.thread_id[:8]}"
    )
    doc.add_paragraph("")  # spacer

    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]

        # Role heading
        heading = doc.add_heading(
            "User" if role == "user" else "Assistant", level=2
        )
        run = heading.runs[0]
        run.font.color.rgb = RGBColor(50, 50, 150) if role == "user" else RGBColor(0, 128, 80)

        # Content
        para = doc.add_paragraph(content)
        para.style.font.size = Pt(11)

        doc.add_paragraph("")  # spacer

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ─── Sidebar ───
with st.sidebar:
    st.markdown("## 🧠 Research Agent")
    st.markdown("---")

    # ── LLM Provider Selector ──
    st.markdown("### 🤖 LLM Provider")
    provider_options = {
        "gemini": "🔷 Google Gemini",
        "groq": "🟢 Groq (Llama)",
        "openai": "🟠 OpenAI (GPT)",
    }
    selected_provider = st.selectbox(
        "Choose LLM",
        options=list(provider_options.keys()),
        format_func=lambda x: provider_options[x],
        index=list(provider_options.keys()).index(st.session_state.current_provider),
        label_visibility="collapsed",
    )

    # Model name override
    default_models = {
        "gemini": "gemini-3-flash-preview",
        "groq": "llama-3.3-70b-versatile",
        "openai": "gpt-4o-mini",
    }
    model_name = st.text_input(
        "Model name",
        value=default_models[selected_provider],
        help="Override the default model for the selected provider",
    )

    # Rebuild graph if provider changed
    if selected_provider != st.session_state.current_provider:
        try:
            st.session_state.current_graph = build_graph(selected_provider, model_name)
            st.session_state.current_provider = selected_provider
            st.success(f"Switched to {provider_options[selected_provider]}")
        except Exception as e:
            st.error(f"Failed to switch: {str(e)}")

    st.markdown("---")

    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.pdf_path = None
        st.session_state.thread_id = str(uuid.uuid4())
        # Rebuild graph for new session (fresh memory)
        try:
            st.session_state.current_graph = build_graph(
                st.session_state.current_provider, model_name
            )
        except Exception:
            pass
        st.rerun()

    st.markdown(f"**Session:** `{st.session_state.thread_id[:8]}...`")
    st.markdown("---")

    st.markdown("### 🛠️ Agent Tools")
    st.markdown("""
    - 🔍 **arXiv Search** — Academic papers
    - 🎓 **Semantic Scholar** — Citations & metrics
    - 🌐 **Web Search** — Blogs & resources
    - 📖 **PDF Reader** — Extract text
    - 📄 **LaTeX PDF** — Generate papers
    """)

    st.markdown("---")
    st.markdown("### 📋 How to Use")
    st.markdown("""
    1. Choose your LLM provider above
    2. Tell the agent your research topic
    3. Browse papers it finds
    4. Pick a paper to read in depth
    5. Ask it to write & export a paper
    """)

    # ── Export Section ──
    if st.session_state.chat_history:
        st.markdown("---")
        st.markdown("### 📤 Export Chat")

        col1, col2 = st.columns(2)

        # Markdown export
        with col1:
            md_content = export_chat_markdown()
            st.download_button(
                label="📝 Markdown",
                data=md_content,
                file_name=f"research_chat_{st.session_state.thread_id[:8]}.md",
                mime="text/markdown",
                use_container_width=True,
            )

        # JSON export (chat history download)
        with col2:
            json_content = json.dumps(
                {
                    "session_id": st.session_state.thread_id,
                    "timestamp": datetime.now().isoformat(),
                    "provider": st.session_state.current_provider,
                    "messages": st.session_state.chat_history,
                },
                indent=2,
            )
            st.download_button(
                label="📋 JSON",
                data=json_content,
                file_name=f"research_chat_{st.session_state.thread_id[:8]}.json",
                mime="application/json",
                use_container_width=True,
            )

        # Word export
        try:
            docx_bytes = export_chat_docx()
            st.download_button(
                label="📄 Download as Word (.docx)",
                data=docx_bytes,
                file_name=f"research_chat_{st.session_state.thread_id[:8]}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except ImportError:
            st.caption("Install `python-docx` for Word export")
        except Exception as e:
            st.caption(f"Word export error: {e}")

    # ── Generated PDFs ──
    output_dir = Path("output")
    if output_dir.exists():
        pdf_files = list(output_dir.glob("*.pdf"))
        if pdf_files:
            st.markdown("---")
            st.markdown("### 📥 Generated Papers")
            for pdf_file in sorted(pdf_files, reverse=True)[:5]:
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label=f"⬇️ {pdf_file.name}",
                        data=f.read(),
                        file_name=pdf_file.name,
                        mime="application/pdf",
                        use_container_width=True,
                    )


# ─── Main Content ───
st.markdown("""
<div class="main-header">
    <h1>📄 AI Research Agent</h1>
    <p>Conversational AI that searches arXiv, Semantic Scholar & the web — then writes publication-ready research</p>
</div>
""", unsafe_allow_html=True)

# ─── Display Chat History ───
for msg in st.session_state.chat_history:
    role = msg["role"]
    content = msg["content"]
    if role in ("user", "assistant"):
        st.chat_message(role).write(content)

# ─── Chat Input ───
user_input = st.chat_input("What research topic would you like to explore?")

if user_input:
    # Log and display user input
    logger.info(f"User input: {user_input}")
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Prepare input for the agent
    chat_input = {
        "messages": [
            {"role": "system", "content": INITIAL_PROMPT}
        ] + st.session_state.chat_history
    }
    logger.info("Starting agent processing...")

    # Config for thread-based memory
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    # Stream agent response
    full_response = ""
    with st.spinner("🤖 Agent is thinking..."):
        try:
            for s in st.session_state.current_graph.stream(
                chat_input, config, stream_mode="values"
            ):
                message = s["messages"][-1]

                # Handle tool calls (log and show)
                if getattr(message, "tool_calls", None):
                    for tool_call in message.tool_calls:
                        logger.info(f"Tool call: {tool_call['name']}")
                        st.markdown(
                            f"<div class='tool-call-box'>🔧 Using tool: <b>{tool_call['name']}</b></div>",
                            unsafe_allow_html=True,
                        )

                # Handle assistant response
                if isinstance(message, AIMessage) and message.content:
                    text_content = extract_text(message.content)
                    full_response = text_content

            # Display final response
            if full_response:
                st.chat_message("assistant").write(full_response)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": full_response}
                )

            # Check if a PDF was generated
            output_dir = Path("output")
            if output_dir.exists():
                pdf_files = sorted(output_dir.glob("*.pdf"), reverse=True)
                if pdf_files:
                    latest_pdf = pdf_files[0]
                    if st.session_state.pdf_path != str(latest_pdf):
                        st.session_state.pdf_path = str(latest_pdf)
                        st.success(f"📄 New PDF generated: {latest_pdf.name}")
                        with open(latest_pdf, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download {latest_pdf.name}",
                                data=f.read(),
                                file_name=latest_pdf.name,
                                mime="application/pdf",
                                use_container_width=True,
                            )

        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            logger.error(f"Agent error: {str(e)}", exc_info=True)
