# RFP RAG Agent

A Retrieval-Augmented Generation (RAG) agent built with [LangGraph](https://github.com/langchain-ai/langgraph) that combines document retrieval with language model generation to answer questions based on contextual information.

<div align="center">
  <img src="./static/studio_ui.png" alt="Graph view in LangGraph studio UI" width="75%" />
</div>

The core logic defined in `src/agent/graph.py` showcases a two-step RAG workflow:
1. **Retrieve**: Search for relevant documents based on the user's question
2. **Generate**: Use the retrieved context to generate an informed answer

This implementation follows LangGraph best practices with proper error handling, lazy initialization, and configurable components.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- OpenAI API key

### Installation

1. **Clone and navigate to the project directory**:
```bash
cd path/to/rfp-rag
```

2. **Create and activate a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install -e .
```

### Configuration

1. **Set up environment variables**:
```bash
cp env.template .env
```

2. **Edit the `.env` file and add your API keys**:
```text
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional configurations
EMBEDDING_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini
MAX_DOCS_RETRIEVE=4

# Optional: Enable LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=rfp-rag-agent
```

### Running the Application

**Start the LangGraph Server**:
```shell
langgraph dev
```

The server will start on `http://127.0.0.1:2024` with:
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs

For more information on LangGraph Server, [see the documentation](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/).

## How to customize

1. **Define runtime context**: Modify the `Context` class in the `graph.py` file to expose the arguments you want to configure per assistant. For example, in a chatbot application you may want to define a dynamic system prompt or LLM to use. For more information on runtime context in LangGraph, [see here](https://langchain-ai.github.io/langgraph/agents/context/?h=context#static-runtime-context).

2. **Extend the graph**: The core logic of the application is defined in [graph.py](./src/agent/graph.py). You can modify this file to add new nodes, edges, or change the flow of information.

## Development

While iterating on your graph in LangGraph Studio, you can edit past state and rerun your app from previous states to debug specific nodes. Local changes will be automatically applied via hot reload.

Follow-up requests extend the same thread. You can create an entirely new thread, clearing previous history, using the `+` button in the top right.

For more advanced features and examples, refer to the [LangGraph documentation](https://langchain-ai.github.io/langgraph/). These resources can help you adapt this template for your specific use case and build more sophisticated conversational agents.

LangGraph Studio also integrates with [LangSmith](https://smith.langchain.com/) for more in-depth tracing and collaboration with teammates, allowing you to analyze and optimize your chatbot's performance.

