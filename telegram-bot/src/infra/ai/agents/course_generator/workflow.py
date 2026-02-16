from langgraph.graph import END, START, StateGraph

from .nodes import AgentState, generate_modules, plan_course_structure, reasoning

graph = StateGraph(AgentState)

graph.add_node("reasoning", reasoning)
graph.add_node("plan_course_structure", plan_course_structure)
graph.add_node("generate_modules", generate_modules)

graph.add_edge(START, "reasoning")
graph.add_edge("reasoning", "plan_course_structure")
graph.add_edge("plan_course_structure", "generate_modules")
graph.add_edge("generate_modules", END)

agent = graph.compile()
