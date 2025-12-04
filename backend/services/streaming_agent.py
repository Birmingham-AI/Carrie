"""
Streaming Agent for Meeting Notes Q&A

This module provides a streaming agent that answers questions about meeting notes
using the OpenAI Agents SDK with real-time token streaming. The agent uses RAGService
as a tool to search meeting notes.
"""

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, set_tracing_disabled, function_tool, WebSearchTool
from typing import AsyncGenerator

# Disable tracing for ZDR (Zero Data Retention) organizations
set_tracing_disabled(True)


class StreamingMeetingNotesAgent:
    """Agent that streams conversational answers about meeting notes using RAG"""

    def __init__(self, rag_service, model: str = "gpt-4.1-mini", enable_web_search: bool = True):
        """
        Initialize the streaming agent

        Args:
            rag_service: RAGService instance to use for searching notes
            model: OpenAI model to use (default: gpt-4.1-mini)
            enable_web_search: Whether to enable web search tool (default: True)
        """
        self.rag_service = rag_service
        self.model = model
        self.enable_web_search = enable_web_search
        self.instructions = (
            "You are WillAIam, the friendly AI assistant and unofficial historian of the Birmingham AI community. "
            "You love this community and get genuinely excited when discussing AI topics from past sessions - you're a bit of a nerd about it, "
            "and you remember the fascinating discussions, the brilliant speakers, and the ideas that sparked great conversations. "
            "\n\n"
            "Your personality:\n"
            "- Warm and welcoming, like a local showing someone around their favourite spots\n"
            "- Knowledgeable archivist who takes pride in preserving the community's history\n"
            "- Enthusiastic AI nerd who lights up when connecting topics across different sessions\n"
            "\n\n"
            "Guidelines:\n"
            "- Use the search_meeting_notes tool to find relevant information from past meetings\n"
            "- If the meeting notes don't have enough information, use web_search for additional context\n"
            "- Be conversational but concise. Don't hallucinate or make up answers\n"
            "- If you don't know something, be honest about it\n"
            "- IMPORTANT: Only cite sources that DIRECTLY answer the question. Quality over quantity\n"
            "- Include the timestamp(s) at the end of your response when available"
        )

    def _create_search_tool(self):
        """Create the search tool function for the agent"""
        rag_service = self.rag_service

        @function_tool
        async def search_meeting_notes(query: str, top_k: int = 5) -> str:
            """
            Search meeting notes for relevant information.

            Args:
                query: The search query
                top_k: Number of top results to return (default: 5)

            Returns:
                Formatted search results with year, month, slide, and content
            """
            results = await rag_service.search_meeting_notes(query, top_k)

            if not results:
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

    async def stream_answer(self, question: str, messages: list = None) -> AsyncGenerator[str, None]:
        """
        Stream a conversational answer to a question

        Args:
            question: The user's question
            messages: Optional conversation history as list of {"role": "user/assistant", "content": "..."}

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

        # Run agent with current question
        result = Runner.run_streamed(agent, input=question)

        # Stream token-by-token output
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                yield event.data.delta

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
