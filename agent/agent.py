"""
Phase 5: Core Growth Intelligence Agent.
LangChain agent with tool-use powered by Claude or OpenAI.
"""

import os
from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# ── LLM setup ───────────────────────────────────────────────────────────────────

def get_llm():
    """Return the configured LLM (Claude or OpenAI)."""
    model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key and api_key != "your_anthropic_api_key_here":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=api_key, temperature=0)

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", api_key=openai_key, temperature=0)

    raise ValueError(
        "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file."
    )


# ── Agent factory ───────────────────────────────────────────────────────────────

def build_agent() -> AgentExecutor:
    """Build and return the Growth Intelligence AgentExecutor."""
    from tools.mcp_tools import ALL_TOOLS
    from agent.prompts import SYSTEM_PROMPT

    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=8,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )
    return executor


# ── High-level API ──────────────────────────────────────────────────────────────

_agent_instance = None


def get_agent() -> AgentExecutor:
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
    agent = get_agent()
    history_messages = []
    if chat_history:
        for human_msg, ai_msg in chat_history:
            history_messages.append(HumanMessage(content=human_msg))
            history_messages.append(AIMessage(content=ai_msg))

    result = agent.invoke({
        "input": question,
        "chat_history": history_messages,
    })

    steps = []
    for action, observation in result.get("intermediate_steps", []):
        steps.append({
            "tool": action.tool,
            "input": action.tool_input,
            "output": observation[:500] + "..." if len(str(observation)) > 500 else observation,
        })

    return {
        "answer": result["output"],
        "steps": steps,
    }


def generate_full_analysis() -> str:
    """Run a comprehensive growth analysis across all metrics and data sources."""
    from agent.prompts import INSIGHT_GENERATION_PROMPT
    from tools.mcp_tools import get_metric, get_pipeline_by_segment, get_product_usage, get_company_context

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
    return response.content


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
