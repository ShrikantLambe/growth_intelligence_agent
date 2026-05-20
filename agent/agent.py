"""
Phase 5: Core Growth Intelligence Agent.
LangChain agent with tool-use powered by Claude or OpenAI.
"""

import os
import logging
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# ── LLM setup ───────────────────────────────────────────────────────────────────

def get_llm():
    """Return the configured LLM (Claude or OpenAI)."""
    model = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key and api_key != "your_anthropic_api_key_here":
        from langchain_anthropic import ChatAnthropic
        logger.info("Using Anthropic model: %s", model)
        return ChatAnthropic(model=model, api_key=api_key, temperature=0)

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        from langchain_openai import ChatOpenAI
        logger.info("Using OpenAI model: gpt-4o")
        return ChatOpenAI(model="gpt-4o", api_key=openai_key, temperature=0)

    raise ValueError(
        "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file."
    )


def _extract_text(output) -> str:
    """Normalize LLM output to a plain string regardless of SDK version."""
    if isinstance(output, list):
        return " ".join(item.get("text", "") for item in output if isinstance(item, dict))
    return str(output)


# ── Agent factory ───────────────────────────────────────────────────────────────

def build_agent():
    """Build and return the Growth Intelligence agent graph."""
    from tools.mcp_tools import ALL_TOOLS
    from agent.prompts import SYSTEM_PROMPT

    llm = get_llm()
    graph = create_react_agent(llm, tools=ALL_TOOLS, prompt=SYSTEM_PROMPT)
    logger.info("Agent built with %d tools", len(ALL_TOOLS))
    return graph


# ── High-level API ──────────────────────────────────────────────────────────────

_agent_instance = None


def get_agent():
    """Singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = build_agent()
    return _agent_instance


def ask(question: str, chat_history: list = None) -> dict:
    """
    Ask the Growth Intelligence Agent a question.

    Args:
        question: Natural language question about growth metrics
        chat_history: Optional list of prior (human, ai) message tuples

    Returns:
        dict with 'answer' and 'steps' keys
    """
    logger.info("Agent query: %s", question[:120])
    agent = get_agent()

    messages = []
    if chat_history:
        for human_msg, ai_msg in chat_history:
            messages.append(HumanMessage(content=human_msg))
            messages.append(AIMessage(content=ai_msg))
    messages.append(HumanMessage(content=question))

    result = agent.invoke({"messages": messages})

    # Extract tool steps from message history
    steps = []
    tool_outputs = {}
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            tool_outputs[msg.tool_call_id] = str(msg.content)
    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                out = tool_outputs.get(tc["id"], "")
                steps.append({
                    "tool": tc["name"],
                    "input": tc["args"],
                    "output": out[:500] + "..." if len(out) > 500 else out,
                })

    final_msg = result["messages"][-1]
    answer = _extract_text(final_msg.content)
    logger.info("Agent answered (%d chars, %d tool steps)", len(answer), len(steps))

    return {
        "answer": answer,
        "steps": steps,
    }


def generate_full_analysis() -> str:
    """Run a comprehensive growth analysis across all metrics and data sources."""
    from agent.prompts import INSIGHT_GENERATION_PROMPT
    from tools.mcp_tools import get_metric, get_pipeline_by_segment, get_product_usage, get_company_context

    logger.info("Running full growth analysis")
    metrics = get_metric.invoke("all metrics")
    crm = get_pipeline_by_segment.invoke("by region")
    usage = get_product_usage.invoke("summary")
    context = get_company_context.invoke("growth strategy targets and ICP")

    prompt = INSIGHT_GENERATION_PROMPT.format(
        metrics=metrics,
        crm_data=crm,
        usage_data=usage,
        rag_context=context,
    )
    llm = get_llm()
    response = llm.invoke(prompt)
    return _extract_text(response.content)


if __name__ == "__main__":
    print("🧠 Growth Intelligence Agent — Interactive Mode\n")
    print("Type 'analyze' for a full analysis, 'quit' to exit.\n")

    history = []
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if question.lower() == "analyze":
            print("\n📊 Running full growth analysis...\n")
            print(generate_full_analysis())
        else:
            result = ask(question, history)
            print(f"\nAgent: {result['answer']}\n")
            history.append((question, result["answer"]))
