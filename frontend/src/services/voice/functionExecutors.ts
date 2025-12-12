import config from '../../config';
import type { EventbriteEvent, SessionInfo, SearchResult } from './types';

/**
 * Result of a function execution
 */
export interface FunctionResult {
  success: boolean;
  output: string;
}

/**
 * Execute the meeting_notes function
 */
export async function executeMeetingNotes(args: {
  action: string;
  filter?: string;
  query?: string;
  top_k?: number;
  session_filter?: string;
}): Promise<FunctionResult> {
  const action = args.action;

  if (action === 'list_sessions') {
    return await listSessions(args.filter);
  } else if (action === 'search') {
    return await searchMeetingNotes(args.query || '', args.top_k || 5, args.session_filter);
  } else {
    return {
      success: false,
      output: `Unknown action: ${action}. Use 'list_sessions' or 'search'.`
    };
  }
}

/**
 * List available sessions
 */
async function listSessions(filter?: string): Promise<FunctionResult> {
  try {
    const params = new URLSearchParams();
    if (filter) {
      params.append('filter', filter);
    }

    const url = `${config.apiBaseUrl}/v1/sessions${params.toString() ? '?' + params : ''}`;
    const response = await fetch(url);

    if (!response.ok) {
      return {
        success: false,
        output: `Failed to list sessions: ${response.statusText}`
      };
    }

    const data = await response.json();

    if (data.sessions && data.sessions.length > 0) {
      const output = `Found ${data.sessions.length} session(s):\n` +
        data.sessions.map((s: SessionInfo, i: number) =>
          `${i + 1}. ${s.session_info} (${s.chunk_count} chunks)`
        ).join('\n');
      return { success: true, output };
    } else {
      return { success: true, output: 'No sessions found matching the filter.' };
    }
  } catch (error) {
    return {
      success: false,
      output: 'Error listing sessions: ' + (error instanceof Error ? error.message : 'Unknown error')
    };
  }
}

/**
 * Search meeting notes
 */
async function searchMeetingNotes(
  query: string,
  topK: number,
  sessionFilter?: string
): Promise<FunctionResult> {
  try {
    const params = new URLSearchParams({
      question: query,
      top_k: String(topK)
    });

    if (sessionFilter) {
      params.append('session_filter', sessionFilter);
    }

    const url = `${config.apiBaseUrl}/v1/search?${params}`;
    const response = await fetch(url);

    if (!response.ok) {
      return {
        success: false,
        output: `Search failed: ${response.statusText}`
      };
    }

    const results = await response.json();

    if (results.results && results.results.length > 0) {
      const output = results.results.map((r: SearchResult, i: number) =>
        `${i + 1}. [Session: ${r.session_info}, Timestamp: ${r.timestamp}, Score: ${r.score.toFixed(3)}]\n   ${r.text}`
      ).join('\n\n');
      return { success: true, output };
    } else {
      return { success: true, output: 'No relevant meeting notes found for this query.' };
    }
  } catch (error) {
    return {
      success: false,
      output: 'Error searching: ' + (error instanceof Error ? error.message : 'Unknown error')
    };
  }
}

/**
 * Extended event type with full details
 */
interface EventbriteEventFull extends EventbriteEvent {
  id: string;
  full_description?: string;
  agenda?: Array<{ time: string; title: string }>;
}

/**
 * Execute the eventbrite function (list or details)
 */
export async function executeEventbrite(args: {
  action: string;
  limit?: number;
  event_id?: string;
}): Promise<FunctionResult> {
  try {
    const action = args.action || 'list';

    if (action === 'details') {
      return await fetchEventDetails(args.event_id);
    } else {
      return await fetchEventList(args.limit || 3);
    }
  } catch (error) {
    return {
      success: false,
      output: 'Error with eventbrite: ' + (error instanceof Error ? error.message : 'Unknown error')
    };
  }
}

/**
 * Fetch list of upcoming events
 */
async function fetchEventList(limit: number): Promise<FunctionResult> {
  const url = `${config.apiBaseUrl}/v1/events?action=list&limit=${limit}`;
  const response = await fetch(url);

  if (!response.ok) {
    return {
      success: false,
      output: `Failed to fetch events: ${response.statusText}`
    };
  }

  const data = await response.json();

  if (data.events && data.events.length > 0) {
    const output = data.events.map((event: EventbriteEventFull, i: number) => {
      const parts = [`${i + 1}. **${event.name}** (ID: ${event.id})`];

      if (event.start_date) {
        let timeStr = event.start_time;
        if (event.end_time) {
          timeStr += ` - ${event.end_time}`;
        }
        parts.push(`   Date: ${event.start_date} at ${timeStr}`);
      }

      if (event.location) {
        parts.push(`   Location: ${event.location}`);
      }

      if (event.description) {
        const desc = event.description.length > 200
          ? event.description.substring(0, 200) + '...'
          : event.description;
        parts.push(`   Description: ${desc}`);
      }

      if (event.price) {
        parts.push(`   Price: ${event.price}`);
        if (event.tickets_available !== null) {
          parts.push(`   Tickets Available: ${event.tickets_available}`);
        }
      } else if (event.is_free) {
        parts.push('   Price: Free');
      }

      if (event.url) {
        parts.push(`   Register: ${event.url}`);
      }

      return parts.join('\n');
    }).join('\n\n');

    return { success: true, output };
  } else {
    return {
      success: true,
      output: 'No upcoming events found. Check back later or visit the Birmingham AI Eventbrite page.'
    };
  }
}

/**
 * Fetch full details for a specific event
 */
async function fetchEventDetails(eventId?: string): Promise<FunctionResult> {
  if (!eventId) {
    return {
      success: false,
      output: 'Error: event_id is required for details action'
    };
  }

  const url = `${config.apiBaseUrl}/v1/events?action=details&event_id=${eventId}`;
  const response = await fetch(url);

  if (!response.ok) {
    return {
      success: false,
      output: `Failed to fetch event details: ${response.statusText}`
    };
  }

  const data = await response.json();
  const event = data.event as EventbriteEventFull;

  if (!event) {
    return {
      success: false,
      output: `Event ${eventId} not found.`
    };
  }

  const parts = [`**${event.name}**`];

  if (event.start_date) {
    let timeStr = event.start_time;
    if (event.end_time) {
      timeStr += ` - ${event.end_time}`;
    }
    parts.push(`Date: ${event.start_date} at ${timeStr}`);
  }

  if (event.location) {
    parts.push(`Location: ${event.location}`);
  }

  if (event.full_description) {
    parts.push(`\n**Description:**\n${event.full_description}`);
  } else if (event.description) {
    parts.push(`\n**Description:**\n${event.description}`);
  }

  if (event.agenda && event.agenda.length > 0) {
    parts.push('\n**Agenda:**');
    for (const item of event.agenda) {
      parts.push(`  - ${item.time}: ${item.title}`);
    }
  }

  if (event.price) {
    parts.push(`\nPrice: ${event.price}`);
    if (event.tickets_available !== null) {
      parts.push(`Tickets Available: ${event.tickets_available}`);
    }
  } else if (event.is_free) {
    parts.push('\nPrice: Free');
  }

  if (event.url) {
    parts.push(`\nRegister: ${event.url}`);
  }

  return { success: true, output: parts.join('\n') };
}

/**
 * Execute a function by name
 */
export async function executeFunction(
  name: string,
  argsJson: string
): Promise<FunctionResult> {
  try {
    const args = JSON.parse(argsJson || '{}');

    switch (name) {
      case 'meeting_notes':
        return await executeMeetingNotes(args);
      case 'get_upcoming_events':
        return await executeEventbrite({ action: 'list', limit: args.limit });
      case 'eventbrite':
        return await executeEventbrite(args);
      default:
        return {
          success: false,
          output: `Unknown function: ${name}`
        };
    }
  } catch (error) {
    return {
      success: false,
      output: 'Error executing function: ' + (error instanceof Error ? error.message : 'Unknown error')
    };
  }
}
