"""Graph factory for creating customizable LangGraph agents with approval workflows.

This module provides a factory pattern for creating LangGraph agents with
configurable approval systems, making it easy to integrate into other projects.
"""

from typing import Any, Dict, List, Optional, Set, Callable, Type
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from approval_system import (
    ApprovalSystem, 
    create_approval_node, 
    create_approval_router, 
    create_model_output_router
)
from state import State, InputState
from context import Context


class GraphFactory:
    """Factory for creating LangGraph agents with approval workflows.
    
    This class provides a flexible way to create LangGraph agents with
    configurable approval systems, tools, and routing logic.
    """
    
    def __init__(
        self,
        state_class: Type[State] = State,
        input_state_class: Type[InputState] = InputState,
        context_class: Type[Context] = Context
    ):
        """Initialize the graph factory.
        
        Args:
            state_class: State class to use (default: State)
            input_state_class: Input state class to use (default: InputState)
            context_class: Context class to use (default: Context)
        """
        self.state_class = state_class
        self.input_state_class = input_state_class
        self.context_class = context_class
    
    def create_graph(
        self,
        call_model_func: Callable,
        tools: List[Any],
        write_tools: Optional[Set[str]] = None,
        approval_checker: Optional[Callable[[str], bool]] = None,
        description_generator: Optional[Callable[[str, Dict[str, Any]], str]] = None,
        approval_keywords: Optional[Set[str]] = None,
        graph_name: str = "ReAct Agent",
        enable_approval: bool = True
    ) -> StateGraph:
        """Create a LangGraph with approval workflow.
        
        Args:
            call_model_func: Function to call the LLM
            tools: List of tools available to the agent
            write_tools: Set of tool names that require approval
            approval_checker: Custom function to check if a tool requires approval
            description_generator: Custom function to generate approval descriptions
            approval_keywords: Set of keywords that indicate approval
            graph_name: Name for the compiled graph
            enable_approval: Whether to enable approval workflow (default: True)
            
        Returns:
            Compiled StateGraph ready for use
        """
        # Create approval system if enabled
        approval_system = None
        if enable_approval:
            approval_system = ApprovalSystem(
                write_tools=write_tools,
                approval_checker=approval_checker,
                description_generator=description_generator,
                approval_keywords=approval_keywords
            )
        
        # Create the graph builder
        builder = StateGraph(
            self.state_class, 
            input_schema=self.input_state_class, 
            context_schema=self.context_class
        )
        
        # Add the main nodes
        builder.add_node("call_model", call_model_func)
        builder.add_node("tools", ToolNode(tools))
        
        # Add approval node if enabled
        if enable_approval and approval_system:
            approval_node_func = create_approval_node(approval_system)
            builder.add_node("approval_node", approval_node_func)
        
        # Set the entrypoint
        builder.add_edge("__start__", "call_model")
        
        # Add conditional edges
        if enable_approval and approval_system:
            # Route from call_model based on whether approval is needed
            model_router = create_model_output_router(approval_system)
            builder.add_conditional_edges("call_model", model_router)
            
            # Route from approval_node
            approval_router = create_approval_router(approval_system)
            builder.add_conditional_edges("approval_node", approval_router)
        else:
            # Simple routing without approval
            def simple_router(state):
                last_message = state.messages[-1]
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    return "tools"
                return "__end__"
            
            builder.add_conditional_edges("call_model", simple_router)
        
        # Add edge from tools back to call_model
        builder.add_edge("tools", "call_model")
        
        # Compile and return the graph
        return builder.compile(name=graph_name)
    
    def create_simple_graph(
        self,
        call_model_func: Callable,
        tools: List[Any],
        graph_name: str = "Simple Agent"
    ) -> StateGraph:
        """Create a simple LangGraph without approval workflow.
        
        Args:
            call_model_func: Function to call the LLM
            tools: List of tools available to the agent
            graph_name: Name for the compiled graph
            
        Returns:
            Compiled StateGraph ready for use
        """
        return self.create_graph(
            call_model_func=call_model_func,
            tools=tools,
            enable_approval=False,
            graph_name=graph_name
        )


# Convenience function for quick graph creation
def create_approval_graph(
    call_model_func: Callable,
    tools: List[Any],
    write_tools: Optional[Set[str]] = None,
    **kwargs
) -> StateGraph:
    """Create a LangGraph with approval workflow.
    
    This is a convenience function that creates a graph with approval workflow
    using default settings.
    
    Args:
        call_model_func: Function to call the LLM
        tools: List of tools available to the agent
        write_tools: Set of tool names that require approval
        **kwargs: Additional arguments passed to GraphFactory.create_graph
        
    Returns:
        Compiled StateGraph ready for use
    """
    factory = GraphFactory()
    return factory.create_graph(
        call_model_func=call_model_func,
        tools=tools,
        write_tools=write_tools,
        **kwargs
    )


def create_simple_graph(
    call_model_func: Callable,
    tools: List[Any],
    **kwargs
) -> StateGraph:
    """Create a simple LangGraph without approval workflow.
    
    This is a convenience function that creates a simple graph without
    approval workflow.
    
    Args:
        call_model_func: Function to call the LLM
        tools: List of tools available to the agent
        **kwargs: Additional arguments passed to GraphFactory.create_graph
        
    Returns:
        Compiled StateGraph ready for use
    """
    factory = GraphFactory()
    return factory.create_simple_graph(
        call_model_func=call_model_func,
        tools=tools,
        **kwargs
    )
