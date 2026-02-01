from langgraph.graph import END, START, StateGraph

from .nodes import AgentState, generate_modules, plan_course_structure, save_course

graph = StateGraph(AgentState)

graph.add_node("plan_course_structure", plan_course_structure)
graph.add_node("generate_modules", generate_modules)
graph.add_node("save_course", save_course)

graph.add_edge(START, "plan_course_structure")
graph.add_edge("plan_course_structure", "generate_modules")
graph.add_edge("generate_modules", "save_course")
graph.add_edge("save_course", END)

agent = graph.compile(debug=True)
