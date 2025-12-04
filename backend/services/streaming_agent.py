"""
Streaming Agent for Meeting Notes Q&A

This module provides a streaming agent that answers questions about meeting notes
using the OpenAI Agents SDK with real-time token streaming. The agent uses RAGService
as a tool to search meeting notes.
"""

from datetime import datetime
from pathlib import Path
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, function_tool, WebSearchTool
from typing import AsyncGenerator

from services.langfuse_tracing import get_langfuse_client


def load_prompt() -> str:
    """Load the WillAIam prompt from file."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "willaim.txt"
    with open(prompt_path, "r") as f:
        return f.read()


class StreamingMeetingNotesAgent:
    """Agent that streams conversational answers about meeting notes using RAG"""

    def __init__(self, rag_service, model: str = "gpt-5-mini", enable_web_search: bool = True):
        """
        Initialize the streaming agent

        Args:
            rag_service: RAGService instance to use for searching notes
            model: OpenAI model to use (default: gpt-5-mini)
            enable_web_search: Whether to enable web search tool (default: True)
        """
        self.rag_service = rag_service
        self.model = model
        self.enable_web_search = enable_web_search
        # Load prompt from file and inject current date
        prompt_template = load_prompt()
        self.instructions = prompt_template.format(
            current_date=datetime.now().strftime('%d %B %Y')
        )

    def _create_search_tool(self):
        """Create the search tool function for the agent"""
        rag_service = self.rag_service

        @function_tool
        async def search_meeting_notes(query: str, top_k: int = 5, session_filter: str = None) -> str:
            """
            Search meeting notes for relevant information.

            Args:
                query: The search query
                top_k: Number of top results to return (default: 5)
                session_filter: Optional filter to narrow results by session name.
                    Examples: "August 2025", "March 2025", "Breakout", "Hackathon", "General meetup".
                    Use this when the user asks about a specific month, year, or event type.

            Returns:
                Formatted search results with session info, timestamp, and content
            """
            results = await rag_service.search_meeting_notes(query, top_k, session_filter)

            if not results:
                if session_filter:
                    return f"No relevant meeting notes found for this query with session filter '{session_filter}'."
                return "No relevant meeting notes found for this query."

            # Format results for the agent
            formatted = []
            for idx, result in enumerate(results, start=1):
                formatted.append(
                    f"{idx}. [Session: {result['session_info']}, Timestamp: {result['timestamp']}, Score: {result['score']:.3f}]\n"
                    f"   {result['text']}"
                )

            return "\n\n".join(formatted)

        return search_meeting_notes

    async def stream_answer(self, question: str, messages: list = None, user_id: str = None) -> AsyncGenerator[str, None]:
        """
        Stream a conversational answer to a question

        Args:
            question: The user's question
            messages: Optional conversation history as list of {"role": "user/assistant", "content": "..."}
            user_id: Optional user ID for tracing (e.g., client IP)

        Yields:
            Text chunks as they are generated
        """
        # Create tools list
        tools = [self._create_search_tool()]

        # Add web search tool if enabled
        if self.enable_web_search:
            tools.append(WebSearchTool())

        # Build instructions with conversation history injected
        instructions = self.instructions
        if messages and len(messages) > 0:
            # Inject conversation history into instructions for context
            history_text = "\n\nConversation history:\n"
            for msg in messages[-10:]:  # Keep last 10 messages to avoid token limits
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_text += f"{role.capitalize()}: {content}\n"
            instructions = self.instructions + history_text

        agent = Agent(
            name="WillAIam",
            instructions=instructions,
            model=self.model,
            tools=tools,
        )

        # Stream events from agent
        async def stream_events():
            result = Runner.run_streamed(agent, input=question)
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    yield event.data.delta

        # Run agent with Langfuse tracing if enabled
        langfuse = get_langfuse_client()

        if langfuse:
            with langfuse.start_as_current_span(
                name="WillAIam Chat",
                input=question
            ) as span:
                span.update_trace(
                    user_id=user_id or "anonymous",
                    tags=["willaim", "meeting-notes"],
                    metadata={
                        "model": self.model,
                        "web_search_enabled": self.enable_web_search,
                        "message_count": len(messages) if messages else 0
                    }
                )

                chunks = []
                async for chunk in stream_events():
                    chunks.append(chunk)
                    yield chunk

                span.update(output="".join(chunks))
        else:
            async for chunk in stream_events():
                yield chunk

    async def get_complete_answer(self, question: str) -> str:
        """
        Get the complete answer by collecting all streamed chunks

        Args:
            question: The user's question

        Returns:
            Complete answer as a string
        """
        chunks = []
        async for chunk in self.stream_answer(question):
            chunks.append(chunk)
        return "".join(chunks)
