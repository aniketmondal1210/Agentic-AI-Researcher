"""
Multi-Agent System — Supervisor + Specialist agents for research tasks.
Each specialist has its own system prompt and tools.
"""

import os
import sys
from typing import Annotated, Literal
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.arxiv_tool import arxiv_search
from tools.pdf_reader import read_pdf
from tools.pdf_writer import render_latex_pdf
from tools.web_search import web_search
from tools.semantic_scholar import semantic_scholar_search
from tools.summarizer import summarize_paper


# ─── State ───
class MultiAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_agent: str
    task_complete: bool


# ─── Tool Groups ───
search_tools = [arxiv_search, semantic_scholar_search, web_search]
reader_tools = [read_pdf, summarize_paper]
writer_tools = [render_latex_pdf]
all_tools = search_tools + reader_tools + writer_tools

search_tool_node = ToolNode(search_tools)
reader_tool_node = ToolNode(reader_tools)
writer_tool_node = ToolNode(writer_tools)


# ─── Agent Prompts ───
SUPERVISOR_PROMPT = """You are a research project supervisor coordinating a team of specialist agents.
Your job is to understand the user's request and delegate to the right specialist.

Your team:
- **search_agent**: Finds papers on arXiv, Semantic Scholar, and the web. Use for finding papers, exploring topics.
- **reader_agent**: Reads PDFs and summarizes papers. Use when a user wants to understand a specific paper.
- **writer_agent**: Writes research papers and generates LaTeX PDFs. Use when ready to write/export.
- **respond**: Use this when you can directly answer the user without any specialist (e.g., for greetings, clarifications, or simple questions).

Based on the conversation, decide which agent should handle the next step.
Respond with ONLY one of these words: search_agent, reader_agent, writer_agent, respond

If the user is asking about finding papers or exploring topics → search_agent
If the user wants to read or summarize a paper → reader_agent
If the user wants to write a paper or generate a PDF → writer_agent
If you can answer directly → respond"""

SEARCH_AGENT_PROMPT = """You are a research search specialist. Your expertise is finding relevant academic papers.

You have access to these tools:
- arxiv_search: Search arXiv for academic papers
- semantic_scholar_search: Search Semantic Scholar for papers with citation metrics
- web_search: Search the web for additional resources

When searching:
1. Use multiple search tools to find the most relevant papers
2. Present papers clearly with titles, authors, year, citation count, and brief summaries
3. Highlight the most promising or highly-cited papers
4. Suggest which papers might be worth reading in depth

Always provide PDF links when available so the user can ask the reader agent to analyze them."""

READER_AGENT_PROMPT = """You are a research paper reading specialist. Your expertise is extracting insights from papers.

You have access to these tools:
- read_pdf: Read and extract text from a PDF URL
- summarize_paper: Generate a structured summary of paper content

When reading papers:
1. Extract the key findings, methodology, and contributions
2. Identify limitations and future research directions
3. Highlight mathematical formulations or novel techniques
4. Provide a clear, organized analysis of the paper
5. Suggest how this paper connects to the broader research landscape"""

WRITER_AGENT_PROMPT = """You are a research paper writing specialist. Your expertise is composing academic papers.

You have access to:
- render_latex_pdf: Compile LaTeX content into a PDF

When writing papers:
1. Structure the paper with: Abstract, Introduction, Literature Review, Methodology, Results/Discussion, Conclusion, References
2. Include mathematical equations where appropriate
3. Cite source papers properly with PDF links
4. Write in formal academic English
5. Generate complete, valid LaTeX code
6. Make sure the LaTeX compiles without errors
7. Use proper LaTeX packages for formatting"""

REVIEWER_PROMPT = """You are a senior academic reviewer. Review the research paper content and provide:
1. Strengths and weaknesses
2. Suggestions for improvement
3. Missing references or arguments
4. Rating (1-10) on academic quality

Be constructive and specific in your feedback."""


def _get_model(provider: str = "gemini", model_name: str = None):
    """Create an LLM instance."""
    if provider == "gemini":
        name = model_name or "gemini-3-flash-preview"
        return ChatGoogleGenerativeAI(
            model=name,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        name = model_name or "llama-3.3-70b-versatile"
        return ChatGroq(model=name, api_key=os.getenv("GROQ_API_KEY"))
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        name = model_name or "gpt-4o-mini"
        return ChatOpenAI(model=name, api_key=os.getenv("OPENAI_API_KEY"))
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# ─── Node Functions ───

def supervisor_node(state: MultiAgentState, llm):
    """Supervisor decides which specialist should handle the request."""
    messages = state["messages"]

    response = llm.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        *messages[-10:],  # Last 10 messages for context
        HumanMessage(content="Which agent should handle this? Reply with ONLY: search_agent, reader_agent, writer_agent, or respond"),
    ])

    # Extract the decision
    content = response.content if isinstance(response.content, str) else str(response.content)
    decision = content.strip().lower().replace("*", "").replace("`", "").strip()

    # Map to valid agent names
    if "search" in decision:
        next_agent = "search_agent"
    elif "read" in decision:
        next_agent = "reader_agent"
    elif "writ" in decision:
        next_agent = "writer_agent"
    else:
        next_agent = "respond"

    return {"current_agent": next_agent}


def search_agent_node(state: MultiAgentState, llm):
    """Search specialist — finds papers using search tools."""
    model_with_tools = llm.bind_tools(search_tools)
    messages = state["messages"]

    response = model_with_tools.invoke([
        SystemMessage(content=SEARCH_AGENT_PROMPT),
        *messages,
    ])
    return {"messages": [response]}


def reader_agent_node(state: MultiAgentState, llm):
    """Reader specialist — reads and summarizes papers."""
    model_with_tools = llm.bind_tools(reader_tools)
    messages = state["messages"]

    response = model_with_tools.invoke([
        SystemMessage(content=READER_AGENT_PROMPT),
        *messages,
    ])
    return {"messages": [response]}


def writer_agent_node(state: MultiAgentState, llm):
    """Writer specialist — writes papers and generates PDFs."""
    model_with_tools = llm.bind_tools(writer_tools)
    messages = state["messages"]

    response = model_with_tools.invoke([
        SystemMessage(content=WRITER_AGENT_PROMPT),
        *messages,
    ])
    return {"messages": [response]}


def respond_node(state: MultiAgentState, llm):
    """Direct response — supervisor responds without specialist."""
    messages = state["messages"]

    response = llm.invoke([
        SystemMessage(content=(
            "You are a helpful research assistant. Answer the user's question directly. "
            "If they're asking about research topics, help them narrow down their interest. "
            "If they greet you, introduce yourself and explain what you can do: "
            "search papers (arXiv, Semantic Scholar, web), read papers (PDF), "
            "summarize papers, and write publication-ready LaTeX research papers."
        )),
        *messages,
    ])
    return {"messages": [response]}


# ─── Routing Functions ───

def route_supervisor(state: MultiAgentState) -> str:
    """Route based on supervisor's decision."""
    return state.get("current_agent", "respond")


def should_continue_search(state: MultiAgentState) -> Literal["search_tools", "supervisor"]:
    """Check if search agent needs to call tools."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "search_tools"
    return "supervisor"


def should_continue_reader(state: MultiAgentState) -> Literal["reader_tools", "supervisor"]:
    """Check if reader agent needs to call tools."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "reader_tools"
    return "supervisor"


def should_continue_writer(state: MultiAgentState) -> Literal["writer_tools", "supervisor"]:
    """Check if writer agent needs to call tools."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "writer_tools"
    return "supervisor"


def should_supervisor_end(state: MultiAgentState) -> Literal["search_agent", "reader_agent", "writer_agent", "respond", "__end__"]:
    """After supervisor routes, check if we should end or continue."""
    agent = state.get("current_agent", "respond")

    # If the last message is an AI response (not a tool call), end
    last = state["messages"][-1]
    if agent == "respond":
        return "respond"

    return agent


# ─── Build Multi-Agent Graph ───

def build_multi_agent_graph(provider: str = "gemini", model_name: str = None):
    """Build and compile the multi-agent research graph.

    Returns:
        Compiled graph with supervisor + specialist agents
    """
    llm = _get_model(provider, model_name)

    # Create node functions with LLM bound
    def _supervisor(state):
        return supervisor_node(state, llm)

    def _search(state):
        return search_agent_node(state, llm)

    def _reader(state):
        return reader_agent_node(state, llm)

    def _writer(state):
        return writer_agent_node(state, llm)

    def _respond(state):
        return respond_node(state, llm)

    # Build graph
    workflow = StateGraph(MultiAgentState)

    # Add nodes
    workflow.add_node("supervisor", _supervisor)
    workflow.add_node("search_agent", _search)
    workflow.add_node("reader_agent", _reader)
    workflow.add_node("writer_agent", _writer)
    workflow.add_node("respond", _respond)
    workflow.add_node("search_tools", search_tool_node)
    workflow.add_node("reader_tools", reader_tool_node)
    workflow.add_node("writer_tools", writer_tool_node)

    # Entry point
    workflow.add_edge(START, "supervisor")

    # Supervisor routes to specialists
    workflow.add_conditional_edges("supervisor", route_supervisor, {
        "search_agent": "search_agent",
        "reader_agent": "reader_agent",
        "writer_agent": "writer_agent",
        "respond": "respond",
    })

    # Each specialist can call tools or return to supervisor
    workflow.add_conditional_edges("search_agent", should_continue_search)
    workflow.add_conditional_edges("reader_agent", should_continue_reader)
    workflow.add_conditional_edges("writer_agent", should_continue_writer)

    # Tools return to their specialist
    workflow.add_edge("search_tools", "search_agent")
    workflow.add_edge("reader_tools", "reader_agent")
    workflow.add_edge("writer_tools", "writer_agent")

    # Respond goes to END
    workflow.add_edge("respond", END)

    # Compile
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# ─── System Prompt for Multi-Agent Mode ───
MULTI_AGENT_PROMPT = """You are an AI research team with multiple specialist agents:
- 🔍 Search Agent: Finds papers on arXiv, Semantic Scholar, and the web
- 📖 Reader Agent: Reads and summarizes research papers
- ✍️ Writer Agent: Writes and exports LaTeX research papers
- 🔍 Reviewer: Reviews paper quality

A supervisor coordinates these agents automatically based on your requests.
Just tell me what you need and the right specialist will handle it!"""
