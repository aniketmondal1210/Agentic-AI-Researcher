"""
Streamlit Frontend — AI Research Agent
Chat interface with multi-agent system, citation graphs, auth, and export options.
"""

import sys
import os
import json
import io
import re
from datetime import datetime

# Add the project root to path
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import streamlit.components.v1 as components
from agent.graph import INITIAL_PROMPT, graph, build_graph
from agent.multi_agent import build_multi_agent_graph, MULTI_AGENT_PROMPT
from tools.citation_graph import build_citation_graph_html
from pathlib import Path
import logging
import uuid
import yaml
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

# ─── Custom CSS ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem; text-align: center;
        border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 { color: #e0e0ff; font-size: 2.2rem; font-weight: 700; margin: 0; }
    .main-header p { color: #8888bb; font-size: 1rem; margin-top: 0.4rem; font-weight: 300; }

    .tool-call-box {
        background: rgba(30,30,58,0.7); border-left: 3px solid #6c5ce7;
        border-radius: 6px; padding: 0.6rem 1rem; margin: 0.5rem 0;
        font-size: 0.85rem; color: #a0a0cc;
    }

    .agent-badge {
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600; margin-right: 0.5rem;
    }
    .agent-badge.search { background: rgba(0,184,148,0.2); color: #00b894; }
    .agent-badge.reader { background: rgba(108,92,231,0.2); color: #a29bfe; }
    .agent-badge.writer { background: rgba(231,76,60,0.2); color: #e74c3c; }
    .agent-badge.supervisor { background: rgba(253,203,110,0.2); color: #fdcb6e; }

    .legend-item {
        display: inline-block; margin: 0.3rem 0.5rem; padding: 0.3rem 0.6rem;
        border-radius: 8px; font-size: 0.8rem;
    }

    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #12122a 0%, #1a1a35 100%); }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── Authentication ───
def check_auth():
    """Handle user authentication."""
    try:
        import streamlit_authenticator as stauth

        # Load auth config
        config_path = Path(__file__).parent / "auth_config.yaml"
        if not config_path.exists():
            return True  # No auth config, skip auth

        with open(config_path) as f:
            config = yaml.safe_load(f)

        authenticator = stauth.Authenticate(
            config["credentials"],
            config["cookie"]["name"],
            config["cookie"]["key"],
            config["cookie"]["expiry_days"],
        )

        authenticator.login(location="main")

        if st.session_state.get("authentication_status"):
            authenticator.logout("🚪 Logout", location="sidebar")
            st.sidebar.markdown(f"**Welcome, {st.session_state.get('name', 'User')}!**")
            return True
        elif st.session_state.get("authentication_status") is False:
            st.error("❌ Invalid username or password")
            return False
        else:
            st.info("🔒 Please log in to use the AI Research Agent")
            st.markdown("**Default accounts:** `admin` / `admin123` or `researcher` / `research123`")
            return False

    except ImportError:
        # streamlit-authenticator not installed, skip auth
        return True
    except Exception as e:
        logger.warning(f"Auth error (skipping): {e}")
        return True


# Run auth check
if not check_auth():
    st.stop()


# ─── Helper Functions ───
def extract_text(content):
    """Extract clean text from AIMessage content."""
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


def export_chat_markdown():
    """Export chat history as Markdown."""
    lines = [f"# AI Research Agent — Chat Export\n"]
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**Session:** {st.session_state.thread_id[:8]}\n\n---\n")
    for msg in st.session_state.chat_history:
        role = "🧑 User" if msg["role"] == "user" else "🤖 Assistant"
        lines.append(f"### {role}\n\n{msg['content']}\n\n---\n")
    return "\n".join(lines)


def export_chat_docx():
    """Export chat history as .docx."""
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()
    doc.add_heading("AI Research Agent — Chat Export", level=0)
    doc.add_paragraph(
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"Session: {st.session_state.thread_id[:8]}"
    )
    for msg in st.session_state.chat_history:
        heading = doc.add_heading(
            "User" if msg["role"] == "user" else "Assistant", level=2
        )
        run = heading.runs[0]
        run.font.color.rgb = RGBColor(50, 50, 150) if msg["role"] == "user" else RGBColor(0, 128, 80)
        doc.add_paragraph(msg["content"]).style.font.size = Pt(11)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def extract_paper_titles_from_chat() -> list[str]:
    """Extract paper titles mentioned in the chat history."""
    titles = []
    for msg in st.session_state.chat_history:
        if msg["role"] == "assistant":
            content = msg["content"]
            # Match patterns like "**1. Title Here**" or "**Title:** Something"
            patterns = [
                r'\*\*\d+\.\s*(.+?)\*\*',
                r'\*\*Title:\*\*\s*(.+?)(?:\n|$)',
                r'\"(.{20,80})\"',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                titles.extend(matches)
    # Deduplicate and limit
    seen = set()
    unique = []
    for t in titles:
        t_clean = t.strip().rstrip(".")
        if t_clean not in seen and len(t_clean) > 10:
            seen.add(t_clean)
            unique.append(t_clean)
    return unique[:10]


# ─── Session State ───
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "current_provider" not in st.session_state:
    st.session_state.current_provider = "gemini"
if "agent_mode" not in st.session_state:
    st.session_state.agent_mode = "single"
if "current_graph" not in st.session_state:
    st.session_state.current_graph = graph


# ─── Sidebar ───
with st.sidebar:
    st.markdown("## 🧠 Research Agent")
    st.markdown("---")

    # ── Agent Mode ──
    st.markdown("### ⚙️ Agent Mode")
    agent_mode = st.radio(
        "Mode",
        options=["single", "multi"],
        format_func=lambda x: "🤖 Single Agent (ReAct)" if x == "single" else "👥 Multi-Agent (Supervisor)",
        index=0 if st.session_state.agent_mode == "single" else 1,
        label_visibility="collapsed",
    )

    # ── LLM Provider ──
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
    default_models = {
        "gemini": "gemini-3-flash-preview",
        "groq": "llama-3.3-70b-versatile",
        "openai": "gpt-4o-mini",
    }
    model_name = st.text_input("Model name", value=default_models[selected_provider])

    # Rebuild graph if settings changed
    if (selected_provider != st.session_state.current_provider or
            agent_mode != st.session_state.agent_mode):
        try:
            if agent_mode == "multi":
                st.session_state.current_graph = build_multi_agent_graph(selected_provider, model_name)
            else:
                st.session_state.current_graph = build_graph(selected_provider, model_name)
            st.session_state.current_provider = selected_provider
            st.session_state.agent_mode = agent_mode
            st.success(f"Switched to {provider_options[selected_provider]} ({agent_mode} mode)")
        except Exception as e:
            st.error(f"Failed: {str(e)}")

    st.markdown("---")

    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.pdf_path = None
        st.session_state.thread_id = str(uuid.uuid4())
        try:
            if st.session_state.agent_mode == "multi":
                st.session_state.current_graph = build_multi_agent_graph(
                    st.session_state.current_provider, model_name
                )
            else:
                st.session_state.current_graph = build_graph(
                    st.session_state.current_provider, model_name
                )
        except Exception:
            pass
        st.rerun()

    st.markdown(f"**Session:** `{st.session_state.thread_id[:8]}...`")
    st.markdown("---")

    # ── Tools Info ──
    st.markdown("### 🛠️ Agent Tools")
    if agent_mode == "multi":
        st.markdown("""
        **🔍 Search Agent:** arXiv, Semantic Scholar, Web
        **📖 Reader Agent:** PDF Reader, Summarizer
        **✍️ Writer Agent:** LaTeX PDF Generator
        **🧑‍💼 Supervisor:** Coordinates all agents
        """)
    else:
        st.markdown("""
        - 🔍 arXiv Search
        - 🎓 Semantic Scholar
        - 🌐 Web Search
        - 📖 PDF Reader
        - ✍️ Paper Summarizer
        - 📄 LaTeX PDF Generator
        """)

    # ── Export ──
    if st.session_state.chat_history:
        st.markdown("---")
        st.markdown("### 📤 Export Chat")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📝 Markdown", export_chat_markdown(),
                f"chat_{st.session_state.thread_id[:8]}.md",
                "text/markdown", use_container_width=True,
            )
        with col2:
            st.download_button(
                "📋 JSON",
                json.dumps({
                    "session_id": st.session_state.thread_id,
                    "timestamp": datetime.now().isoformat(),
                    "provider": st.session_state.current_provider,
                    "mode": st.session_state.agent_mode,
                    "messages": st.session_state.chat_history,
                }, indent=2),
                f"chat_{st.session_state.thread_id[:8]}.json",
                "application/json", use_container_width=True,
            )
        try:
            st.download_button(
                "📄 Word (.docx)", export_chat_docx(),
                f"chat_{st.session_state.thread_id[:8]}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except ImportError:
            st.caption("Install `python-docx` for Word export")
        except Exception:
            pass

    # ── PDFs ──
    output_dir = Path("output")
    if output_dir.exists():
        pdf_files = list(output_dir.glob("*.pdf"))
        if pdf_files:
            st.markdown("---")
            st.markdown("### 📥 Generated Papers")
            for pdf_file in sorted(pdf_files, reverse=True)[:5]:
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        f"⬇️ {pdf_file.name}", f.read(),
                        pdf_file.name, "application/pdf",
                        use_container_width=True,
                    )


# ─── Main Content ───
st.markdown("""
<div class="main-header">
    <h1>📄 AI Research Agent</h1>
    <p>Multi-agent AI that searches arXiv, Semantic Scholar & the web — then writes publication-ready research</p>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ───
tab_chat, tab_citations = st.tabs(["💬 Chat", "🔗 Citation Graph"])

# ═══════════════════════════════════════════
#  TAB 1: Chat
# ═══════════════════════════════════════════
with tab_chat:
    # Show agent mode badge
    if st.session_state.agent_mode == "multi":
        st.markdown(
            "<span class='agent-badge supervisor'>👥 Multi-Agent Mode</span>"
            "<span class='agent-badge search'>🔍 Search</span>"
            "<span class='agent-badge reader'>📖 Reader</span>"
            "<span class='agent-badge writer'>✍️ Writer</span>",
            unsafe_allow_html=True,
        )

    # Display chat history
    for msg in st.session_state.chat_history:
        if msg["role"] in ("user", "assistant"):
            st.chat_message(msg["role"]).write(msg["content"])

    # Chat input
    user_input = st.chat_input("What research topic would you like to explore?")

    if user_input:
        logger.info(f"User input: {user_input}")
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        # Choose the right prompt
        system_prompt = (
            MULTI_AGENT_PROMPT if st.session_state.agent_mode == "multi"
            else INITIAL_PROMPT
        )

        chat_input_data = {
            "messages": [
                {"role": "system", "content": system_prompt}
            ] + st.session_state.chat_history
        }

        # Add multi-agent state fields if needed
        if st.session_state.agent_mode == "multi":
            chat_input_data["current_agent"] = ""
            chat_input_data["task_complete"] = False

        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        full_response = ""
        with st.spinner("🤖 Agent is working..."):
            try:
                for s in st.session_state.current_graph.stream(
                    chat_input_data, config, stream_mode="values"
                ):
                    message = s["messages"][-1]

                    # Show tool calls
                    if getattr(message, "tool_calls", None):
                        for tc in message.tool_calls:
                            logger.info(f"Tool call: {tc['name']}")
                            st.markdown(
                                f"<div class='tool-call-box'>🔧 Using tool: <b>{tc['name']}</b></div>",
                                unsafe_allow_html=True,
                            )

                    # Show agent routing (multi-agent mode)
                    if "current_agent" in s and s["current_agent"]:
                        agent_name = s["current_agent"]
                        badge_class = {
                            "search_agent": "search",
                            "reader_agent": "reader",
                            "writer_agent": "writer",
                        }.get(agent_name, "supervisor")
                        st.markdown(
                            f"<div class='tool-call-box'>"
                            f"<span class='agent-badge {badge_class}'>"
                            f"Routing to: {agent_name}</span></div>",
                            unsafe_allow_html=True,
                        )

                    # Capture assistant response
                    if isinstance(message, AIMessage) and message.content:
                        text_content = extract_text(message.content)
                        if text_content.strip():
                            full_response = text_content

                if full_response:
                    st.chat_message("assistant").write(full_response)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": full_response}
                    )

                # Check for new PDFs
                output_dir = Path("output")
                if output_dir.exists():
                    pdf_files = sorted(output_dir.glob("*.pdf"), reverse=True)
                    if pdf_files:
                        latest = pdf_files[0]
                        if st.session_state.pdf_path != str(latest):
                            st.session_state.pdf_path = str(latest)
                            st.success(f"📄 New PDF: {latest.name}")
                            with open(latest, "rb") as f:
                                st.download_button(
                                    f"⬇️ Download {latest.name}",
                                    f.read(), latest.name,
                                    "application/pdf",
                                    use_container_width=True,
                                )

            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                logger.error(f"Agent error: {str(e)}", exc_info=True)


# ═══════════════════════════════════════════
#  TAB 2: Citation Graph
# ═══════════════════════════════════════════
with tab_citations:
    st.markdown("### 🔗 Citation Network Graph")
    st.markdown(
        "Visualize how papers cite each other. "
        "Enter paper titles below or auto-extract from the chat."
    )

    # Auto-extract titles from chat
    auto_titles = extract_paper_titles_from_chat()

    col1, col2 = st.columns([3, 1])
    with col1:
        paper_input = st.text_area(
            "Paper titles (one per line)",
            value="\n".join(auto_titles[:5]) if auto_titles else "",
            height=120,
            placeholder="Enter paper titles, one per line...",
        )
    with col2:
        st.markdown("")  # Spacer
        st.markdown("")
        build_btn = st.button("🔍 Build Graph", use_container_width=True, type="primary")

    # Legend
    st.markdown(
        "<div>"
        "<span class='legend-item' style='background:rgba(231,76,60,0.2);color:#e74c3c;'>● Main Papers</span>"
        "<span class='legend-item' style='background:rgba(0,184,148,0.2);color:#00b894;'>● Citing Papers</span>"
        "<span class='legend-item' style='background:rgba(108,92,231,0.2);color:#6c5ce7;'>● References</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if build_btn and paper_input.strip():
        titles = [t.strip() for t in paper_input.strip().split("\n") if t.strip()]

        if titles:
            with st.spinner("⏳ Fetching citation data from Semantic Scholar..."):
                try:
                    html = build_citation_graph_html(titles, height="550px")
                    components.html(html, height=600, scrolling=True)
                except Exception as e:
                    st.error(f"Error building graph: {str(e)}")
        else:
            st.warning("Please enter at least one paper title.")
    elif build_btn:
        st.warning("Please enter paper titles first.")
