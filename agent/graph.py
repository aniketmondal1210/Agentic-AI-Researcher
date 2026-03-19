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
from langgraph.prebuilt import ToolNode

tools = [arxiv_search, read_pdf, render_latex_pdf]
tool_node = ToolNode(tools)


# Step3: Setup LLM — supports both .env (local) and st.secrets (Streamlit Cloud)
from langchain_google_genai import ChatGoogleGenerativeAI

def _get_api_key():
    """Get API key from st.secrets (cloud) or .env (local)."""
    try:
        import streamlit as st
        return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return os.getenv("GOOGLE_API_KEY")

model = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    api_key=_get_api_key(),
)
model = model.bind_tools(tools)


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


workflow = StateGraph(State)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

from langgraph.checkpoint.memory import MemorySaver

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
You will use the tools provided to search for papers, read them, and write a new
paper based on the ideas you find.

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
