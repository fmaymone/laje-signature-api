from langgraph.graph import END, START, StateGraph

from app.nodes import (
    apply_compatibility_node,
    apply_conflicts_node,
    complete_catalogs_node,
    filter_regional,
    finalize_recipe,
    retrieve_context,
    review_as_fernando,
    review_technical_execution,
    select_blocks_node,
    write_executable_recipe,
)
from app.routing import (
    after_fernando_review,
    after_technical_review,
)
from app.state import CulinaryState


def build_culinary_graph():
    """
    Pedido
      → retrieve
      → regional
      → select_blocks          (flavor_blocks)
      → complete_catalogs     (bases / acidity / textures / aromas / seasonality)
      → apply_compatibility   (compatibility_rules)
      → apply_conflicts       (conflict_rules)
      → write (LLM)
      → technical ⇄ write
      → critic ⇄ select_blocks
      → finalizer
    """
    builder = StateGraph(CulinaryState)

    builder.add_node("retrieve", retrieve_context)
    builder.add_node("regional", filter_regional)
    builder.add_node("select_blocks", select_blocks_node)
    builder.add_node("complete_catalogs", complete_catalogs_node)
    builder.add_node("apply_compatibility", apply_compatibility_node)
    builder.add_node("apply_conflicts", apply_conflicts_node)
    builder.add_node("write", write_executable_recipe)
    builder.add_node("technical", review_technical_execution)
    builder.add_node("critic", review_as_fernando)
    builder.add_node("finalizer", finalize_recipe)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "regional")
    builder.add_edge("regional", "select_blocks")
    builder.add_edge("select_blocks", "complete_catalogs")
    builder.add_edge("complete_catalogs", "apply_compatibility")
    builder.add_edge("apply_compatibility", "apply_conflicts")
    builder.add_edge("apply_conflicts", "write")
    builder.add_edge("write", "technical")

    builder.add_conditional_edges(
        "technical",
        after_technical_review,
        {
            "critic": "critic",
            "revise": "write",
        },
    )

    builder.add_conditional_edges(
        "critic",
        after_fernando_review,
        {
            "finalize": "finalizer",
            "revise": "select_blocks",
            "finalize_with_warning": "finalizer",
        },
    )

    builder.add_edge("finalizer", END)
    return builder.compile()


culinary_graph = build_culinary_graph()
