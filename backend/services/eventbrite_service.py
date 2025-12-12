from typing import List, Dict
from datetime import datetime
import re

from clients.eventbrite import get_eventbrite_client, get_org_id, get_api_token, is_configured


class EventbriteService:
    """Service for fetching upcoming events from Eventbrite"""

    async def get_upcoming_events(self, limit: int = 5) -> List[Dict]:
        """
        Fetch upcoming events from Eventbrite.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of events with full details
        """
        if not is_configured():
            return []

        client = get_eventbrite_client()
        org_id = get_org_id()

        params = {
            "token": get_api_token(),
            "status": "live",
            "time_filter": "current_future",
            "expand": "venue,ticket_classes",
            "order_by": "start_asc",
            "page_size": limit,
        }

        response = await client.get(f"/organizations/{org_id}/events/", params=params)

        if response.status_code != 200:
            return []

        data = response.json()
        events = data.get("events", [])

        return [self._transform_event(event) for event in events]

    def _transform_event(self, event: dict) -> Dict:
        """Transform Eventbrite event response to clean format"""
        # Parse dates
        start = event.get("start", {})
        end = event.get("end", {})
        start_dt = self._parse_datetime(start.get("local"))
        end_dt = self._parse_datetime(end.get("local"))

        # Get venue info
        venue = event.get("venue", {})
        location = self._format_location(venue)

        # Get ticket info
        ticket_classes = event.get("ticket_classes", [])
        ticket_info = self._get_ticket_info(ticket_classes)

        # Clean HTML from description
        description = event.get("description", {})
        description_text = self._strip_html(description.get("text", "") or "")

        return {
            "id": event.get("id"),
            "name": event.get("name", {}).get("text", ""),
            "description": description_text[:500] if description_text else None,
            "start_date": start_dt.strftime("%A, %B %d, %Y") if start_dt else None,
            "start_time": start_dt.strftime("%I:%M %p").lstrip("0") if start_dt else None,
            "end_time": end_dt.strftime("%I:%M %p").lstrip("0") if end_dt else None,
            "location": location,
            "url": event.get("url"),
            "capacity": event.get("capacity"),
            "tickets_available": ticket_info.get("available"),
            "ticket_types": ticket_info.get("types", []),
            "price": ticket_info.get("price"),
            "is_free": event.get("is_free", False),
        }

    def _parse_datetime(self, dt_str: str) -> datetime | None:
        """Parse Eventbrite datetime string"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            return None

    def _format_location(self, venue: dict) -> str | None:
        """Format venue into readable location string"""
        if not venue:
            return None

        parts = []
        if venue.get("name"):
            parts.append(venue["name"])
        if venue.get("address", {}).get("localized_address_display"):
            parts.append(venue["address"]["localized_address_display"])

        return ", ".join(parts) if parts else None

    def _get_ticket_info(self, ticket_classes: list) -> Dict:
        """Calculate ticket availability from ticket classes"""
        total_available = 0
        types = []
        lowest_price_display = None
        lowest_price_value = float('inf')

        for ticket in ticket_classes:
            # Skip hidden tickets
            if ticket.get("hidden") or ticket.get("hidden_currently"):
                continue

            if ticket.get("on_sale_status") == "AVAILABLE":
                quantity_total = ticket.get("quantity_total", 0) or 0
                quantity_sold = ticket.get("quantity_sold", 0) or 0
                available = quantity_total - quantity_sold
                total_available += available

                # Get price display
                cost = ticket.get("cost", {})
                price_display = cost.get("display") if cost else "Free"
                price_value = cost.get("value", 0) if cost else 0

                # Track lowest price
                if ticket.get("free"):
                    lowest_price_display = "Free"
                    lowest_price_value = 0
                elif price_value < lowest_price_value:
                    lowest_price_display = price_display
                    lowest_price_value = price_value

                types.append({
                    "name": ticket.get("name"),
                    "price": price_display,
                    "available": available,
                })

        return {
            "available": total_available if total_available > 0 else None,
            "types": types,
            "price": lowest_price_display,
        }

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        clean = re.sub(r"<[^>]+>", "", text)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()

    async def get_event_details(self, event_id: str) -> Dict | None:
        """
        Fetch full details for a specific event including structured content.

        Args:
            event_id: Eventbrite event ID

        Returns:
            Event details with full description, agenda, etc.
        """
        if not is_configured():
            return None

        client = get_eventbrite_client()
        token = get_api_token()

        # Fetch basic event info
        event_response = await client.get(f"/events/{event_id}/", params={
            "token": token,
            "expand": "venue,ticket_classes"
        })

        if event_response.status_code != 200:
            return None

        event = event_response.json()
        base_info = self._transform_event(event)

        # Fetch structured content for full description
        content_url = f"/events/{event_id}/structured_content/"
        content_response = await client.get(content_url, params={"token": token})

        if content_response.status_code == 200:
            content = content_response.json()
            full_description = self._extract_structured_content(content)
            agenda = self._extract_agenda(content)

            if full_description:
                base_info["full_description"] = full_description
            if agenda:
                base_info["agenda"] = agenda

        return base_info

    def _extract_structured_content(self, content: dict) -> str | None:
        """Extract text content from structured content response"""
        modules = content.get("modules", [])

        for module in modules:
            if module.get("type") == "text":
                body = module.get("data", {}).get("body", {})
                html_text = body.get("text", "")
                if html_text:
                    return self._strip_html(html_text)

        return None

    def _extract_agenda(self, content: dict) -> list | None:
        """Extract agenda from structured content widgets"""
        widgets = content.get("widgets", [])

        for widget in widgets:
            if widget.get("type") == "agenda":
                tabs = widget.get("data", {}).get("tabs", [])
                if tabs:
                    slots = tabs[0].get("slots", [])
                    return [
                        {
                            "time": f"{slot.get('startTime', '')} - {slot.get('endTime', '')}",
                            "title": slot.get("title", "")
                        }
                        for slot in slots
                    ]

        return None
