# Step1: Define State
from typing_extensions import TypedDict
from typing import Annotated, Literal
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()


class State(TypedDict):
    messages: Annotated[list, add_messages]


# Step2: Define ToolNode & Tools
import sys
import os

# Add the project root to path so tools can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.arxiv_tool import arxiv_search
from tools.pdf_reader import read_pdf
from tools.pdf_writer import render_latex_pdf
from tools.web_search import web_search
from tools.semantic_scholar import semantic_scholar_search
from tools.summarizer import summarize_paper
from tools.rag_store import store_paper_in_rag, query_rag_store
from tools.quality_scorer import score_paper_quality
from tools.literature_table import generate_literature_table
from langgraph.prebuilt import ToolNode

tools = [
    arxiv_search, read_pdf, render_latex_pdf, web_search,
    semantic_scholar_search, summarize_paper,
    store_paper_in_rag, query_rag_store,
    score_paper_quality, generate_literature_table,
]
tool_node = ToolNode(tools)


# Step3: Setup LLM (supports multiple providers)
from langchain_google_genai import ChatGoogleGenerativeAI


def get_model(provider: str = "gemini", model_name: str = None, bind: bool = True):
    """Create an LLM instance based on the selected provider.

    Args:
        provider: One of 'gemini', 'groq', 'openai'
        model_name: Optional model name override
        bind: Whether to bind tools to the model (default True)

    Returns:
        LLM instance, optionally bound with tools
    """
    if provider == "gemini":
        name = model_name or "gemini-2.0-flash"
        model = ChatGoogleGenerativeAI(
            model=name,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq

        name = model_name or "llama-3.3-70b-versatile"
        model = ChatGroq(
            model=name,
            api_key=os.getenv("GROQ_API_KEY"),
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        name = model_name or "gpt-4o-mini"
        model = ChatOpenAI(
            model=name,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return model.bind_tools(tools) if bind else model


# Default model (can be overridden by frontend)
_current_provider = os.getenv("LLM_PROVIDER", "gemini")
model = get_model(_current_provider)


# Step4: Setup Graph
from langgraph.graph import END, START, StateGraph


def call_model(state: State):
    """Call the LLM with the current messages."""
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def should_continue(state: State) -> Literal["tools", "__end__"]:
    """Decide whether to continue with tools or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def build_graph(provider: str = "gemini", model_name: str = None):
    """Build and compile the agent graph with the specified LLM provider.

    Args:
        provider: One of 'gemini', 'groq', 'openai'
        model_name: Optional model name override

    Returns:
        Compiled graph
    """
    global model
    model = get_model(provider, model_name)

    workflow = StateGraph(State)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Build default graph
from langgraph.checkpoint.memory import MemorySaver

workflow = StateGraph(State)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# Step5: System Prompt
INITIAL_PROMPT = """
You are an expert researcher in the fields of physics, mathematics,
computer science, quantitative biology, quantitative finance, statistics,
electrical engineering and systems science, and economics.

You are going to analyze recent research papers in one of these fields in
order to identify promising new research directions and then write a new
research paper. For research information or getting papers, ALWAYS use arxiv.org.
You also have access to web search and Semantic Scholar for additional sources.
You will use the tools provided to search for papers, read them, and write a new
paper based on the ideas you find.

Available tools:
- arxiv_search: Search arXiv for academic papers
- semantic_scholar_search: Search Semantic Scholar for papers with citation metrics
- web_search: Search the web for additional information, blog posts, and resources
- read_pdf: Read and extract text from PDF files
- summarize_paper: Generate structured paper summaries
- store_paper_in_rag: Store paper content in the knowledge base for later retrieval
- query_rag_store: Search the knowledge base for relevant content from previously read papers
- score_paper_quality: Evaluate a paper's quality on academic criteria
- generate_literature_table: Create a comparison table of multiple papers
- render_latex_pdf: Generate a LaTeX PDF document

IMPORTANT WORKFLOW:
1. When you read a paper with read_pdf, ALWAYS store it in RAG with store_paper_in_rag too.
2. When writing a paper, use query_rag_store to find relevant quotes and evidence.
3. After writing, use score_paper_quality to evaluate the output.
4. When comparing multiple papers, use generate_literature_table.

To start with, have a conversation with me in order to figure out what topic
to research. Then tell me about some recently published papers with that topic.
Once I've decided which paper I'm interested in, go ahead and read it in order
to understand the research that was done and the outcomes.

Pay particular attention to the ideas for future research and think carefully
about them, then come up with a few ideas. Let me know what they are and I'll
decide what one you should write a paper about.

Finally, I'll ask you to go ahead and write the paper. Make sure that you
include mathematical equations in the paper. Once it's complete, you should
render it as a LaTeX PDF. Make sure that the TEX file is correct and there is
no error in it so that the PDF is easily exported. When you give papers
references, always attach the pdf links to the paper.
"""

