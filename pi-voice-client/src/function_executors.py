"""
Function executors for OpenAI Realtime API function calling.

Handles executing functions called by the AI and returning results.
"""

import logging
import json
from typing import Dict, Any
import httpx
from .config import config

logger = logging.getLogger(__name__)


async def execute_meeting_notes(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute meeting_notes function.
    
    Args:
        args: Function arguments with 'action', 'filter', 'query', 'top_k', 'session_filter'
    
    Returns:
        Dictionary with 'success' (bool) and 'output' (str) keys
    """
    action = args.get("action", "")
    
    if action == "list_sessions":
        return await _list_sessions(args.get("filter"))
    elif action == "search":
        return await _search_meeting_notes(
            args.get("query", ""),
            args.get("top_k", 5),
            args.get("session_filter")
        )
    else:
        return {
            "success": False,
            "output": f"Unknown action: {action}. Use 'list_sessions' or 'search'."
        }


async def _list_sessions(filter_text: str = None) -> Dict[str, Any]:
    """List available meeting sessions."""
    try:
        params = {}
        if filter_text:
            params["filter"] = filter_text
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{config.API_BASE_URL}/v1/sessions",
                params=params
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "output": f"Failed to list sessions: {response.status_code}"
                }
            
            data = response.json()
            sessions = data.get("sessions", [])
            
            if sessions:
                output_lines = [f"Found {len(sessions)} session(s):"]
                for i, s in enumerate(sessions, 1):
                    session_info = s.get("session_info", "Unknown")
                    chunk_count = s.get("chunk_count", 0)
                    output_lines.append(f"{i}. {session_info} ({chunk_count} chunks)")
                return {"success": True, "output": "\n".join(output_lines)}
            else:
                return {
                    "success": True,
                    "output": "No sessions found matching the filter."
                }
    
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return {
            "success": False,
            "output": f"Error listing sessions: {str(e)}"
        }


async def _search_meeting_notes(
    query: str, top_k: int = 5, session_filter: str = None
) -> Dict[str, Any]:
    """Search meeting notes."""
    try:
        params = {
            "question": query,
            "top_k": str(top_k)
        }
        if session_filter:
            params["session_filter"] = session_filter
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{config.API_BASE_URL}/v1/search",
                params=params
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "output": f"Search failed: {response.status_code}"
                }
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                output_lines = []
                for i, r in enumerate(results, 1):
                    session = r.get("session_info", "Unknown")
                    timestamp = r.get("timestamp", "")
                    score = r.get("score", 0.0)
                    text = r.get("text", "")
                    output_lines.append(
                        f"{i}. Session: {session}, Time: {timestamp}, "
                        f"Score: {score:.3f}\n   {text}"
                    )
                return {
                    "success": True,
                    "output": "\n\n".join(output_lines)
                }
            else:
                return {
                    "success": True,
                    "output": "No relevant meeting notes found for this query."
                }
    
    except Exception as e:
        logger.error(f"Error searching meeting notes: {e}")
        return {
            "success": False,
            "output": f"Error searching: {str(e)}"
        }


async def execute_eventbrite(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute eventbrite function.
    
    Args:
        args: Function arguments with 'action', 'limit', 'event_id'
    
    Returns:
        Dictionary with 'success' (bool) and 'output' (str) keys
    """
    action = args.get("action", "list")
    
    if action == "details":
        return await _get_event_details(args.get("event_id"))
    else:
        return await _list_events(args.get("limit", 3))


async def _list_events(limit: int = 3) -> Dict[str, Any]:
    """List upcoming events."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{config.API_BASE_URL}/v1/events",
                params={"action": "list", "limit": limit}
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "output": f"Failed to fetch events: {response.status_code}"
                }
            
            data = response.json()
            events = data.get("events", [])
            
            if events:
                output_lines = []
                for i, event in enumerate(events, 1):
                    name = event.get("name", "Unknown Event")
                    event_id = event.get("id", "")
                    date = event.get("start_date", "")
                    time = event.get("start_time", "")
                    location = event.get("location", "")
                    
                    lines = [f"{i}. {name} (ID: {event_id})"]
                    if date:
                        end_time = event.get("end_time", "")
                        time_str = f"{time} - {end_time}" if end_time else time
                        lines.append(f"   Date: {date} at {time_str}")
                    if location:
                        lines.append(f"   Location: {location}")
                    
                    description = event.get("description", "")
                    if description:
                        desc = description[:150] + "..." if len(description) > 150 else description
                        lines.append(f"   Description: {desc}")
                    
                    # Add price info
                    if event.get("price"):
                        lines.append(f"   Price: {event.get('price')}")
                        if event.get("tickets_available") is not None:
                            lines.append(f"   Tickets Available: {event.get('tickets_available')}")
                    elif event.get("is_free"):
                        lines.append("   Price: Free")
                    
                    # Add URL
                    if event.get("url"):
                        lines.append(f"   Register: {event.get('url')}")
                    
                    output_lines.append("\n".join(lines))
                
                return {
                    "success": True,
                    "output": "\n\n".join(output_lines)
                }
            else:
                return {
                    "success": True,
                    "output": "No upcoming events found."
                }
    
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        return {
            "success": False,
            "output": f"Error fetching events: {str(e)}"
        }


async def _get_event_details(event_id: str = None) -> Dict[str, Any]:
    """Get details for a specific event."""
    if not event_id:
        return {
            "success": False,
            "output": "Error: event_id is required for details action"
        }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{config.API_BASE_URL}/v1/events",
                params={"action": "details", "event_id": event_id}
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "output": f"Failed to fetch event details: {response.status_code}"
                }
            
            data = response.json()
            event = data.get("event")
            
            if not event:
                return {
                    "success": False,
                    "output": f"Event {event_id} not found."
                }
            
            lines = [event.get("name", "Unknown Event")]
            
            date = event.get("start_date")
            time = event.get("start_time")
            end_time = event.get("end_time")
            if date:
                time_str = f"{time} - {end_time}" if end_time else time
                lines.append(f"Date: {date} at {time_str}")
            
            location = event.get("location")
            if location:
                lines.append(f"Location: {location}")
            
            # Use full description if available
            description = event.get("full_description") or event.get("description")
            if description:
                lines.append(f"\nDescription:\n{description}")
            
            # Add agenda if available
            agenda = event.get("agenda")
            if agenda and isinstance(agenda, list) and len(agenda) > 0:
                lines.append("\nAgenda:")
                for item in agenda:
                    if isinstance(item, dict):
                        item_time = item.get("time", "")
                        item_title = item.get("title", "")
                        lines.append(f"  - {item_time}: {item_title}")
            
            # Add price info
            if event.get("price"):
                lines.append(f"\nPrice: {event.get('price')}")
                if event.get("tickets_available") is not None:
                    lines.append(f"Tickets Available: {event.get('tickets_available')}")
            elif event.get("is_free"):
                lines.append("\nPrice: Free")
            
            # Add URL
            if event.get("url"):
                lines.append(f"\nRegister: {event.get('url')}")
            
            return {"success": True, "output": "\n".join(lines)}
    
    except Exception as e:
        logger.error(f"Error getting event details: {e}")
        return {
            "success": False,
            "output": f"Error fetching event details: {str(e)}"
        }


async def execute_function(name: str, args_json: str) -> Dict[str, Any]:
    """
    Execute a function by name.
    
    Args:
        name: Function name
        args_json: JSON string of function arguments
    
    Returns:
        Dictionary with 'success' (bool) and 'output' (str) keys
    """
    try:
        args = json.loads(args_json or "{}")
        
        if name == "meeting_notes":
            return await execute_meeting_notes(args)
        elif name in ["get_upcoming_events", "eventbrite"]:
            return await execute_eventbrite(args)
        else:
            return {
                "success": False,
                "output": f"Unknown function: {name}"
            }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse function arguments: {e}")
        return {
            "success": False,
            "output": f"Error parsing arguments: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error executing function {name}: {e}")
        return {
            "success": False,
            "output": f"Error executing function: {str(e)}"
        }
