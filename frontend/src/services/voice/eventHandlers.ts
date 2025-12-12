import type { VoiceEvent, PendingFunctionCall } from './types';
import { executeFunction } from './functionExecutors';

/**
 * Context for handling realtime events
 */
export interface EventHandlerContext {
  emit: (event: VoiceEvent) => void;
  sendFunctionResult: (callId: string, output: string) => void;
  pendingFunctionCalls: Map<string, PendingFunctionCall>;
}

/**
 * OpenAI Realtime API event structure
 */
interface RealtimeEvent {
  type: string;
  transcript?: string;
  delta?: string;
  item?: {
    id?: string;
    type?: string;
    name?: string;
    call_id?: string;
  };
  call_id?: string;
  name?: string;
  arguments?: string;
  error?: {
    message?: string;
  };
}

/**
 * Handle events from OpenAI Realtime API
 */
export async function handleRealtimeEvent(
  event: RealtimeEvent,
  context: EventHandlerContext
): Promise<void> {
  const { emit, sendFunctionResult, pendingFunctionCalls } = context;

  switch (event.type) {
    case 'conversation.item.input_audio_transcription.completed':
      emit({
        type: 'transcript',
        data: event.transcript as string
      });
      break;

    case 'response.text.delta':
      emit({
        type: 'response_text',
        data: event.delta as string
      });
      break;

    case 'response.audio.delta':
      // Audio is handled by WebRTC track
      break;

    case 'response.audio_transcript.delta':
      emit({
        type: 'response_text',
        data: event.delta as string
      });
      break;

    case 'response.output_item.added':
      handleOutputItemAdded(event, context);
      break;

    case 'response.done':
      emit({ type: 'response_audio_ended' });
      break;

    case 'response.function_call_arguments.delta':
      handleFunctionCallArgumentsDelta(event, pendingFunctionCalls);
      break;

    case 'response.function_call_arguments.done':
      await handleFunctionCallDone(event, context);
      break;

    case 'error':
      emit({
        type: 'error',
        data: event.error?.message || 'Unknown error'
      });
      break;
  }
}

/**
 * Handle output item added event
 */
function handleOutputItemAdded(
  event: RealtimeEvent,
  context: EventHandlerContext
): void {
  const { emit, pendingFunctionCalls } = context;
  const item = event.item;

  if (!item) return;

  if (item.type === 'message') {
    emit({ type: 'response_audio_started' });
  } else if (item.type === 'function_call' && item.call_id) {
    pendingFunctionCalls.set(item.call_id, {
      name: item.name || '',
      arguments: ''
    });
  }
}

/**
 * Handle function call arguments delta
 */
function handleFunctionCallArgumentsDelta(
  event: RealtimeEvent,
  pendingFunctionCalls: Map<string, PendingFunctionCall>
): void {
  const callId = event.call_id as string;
  const existing = pendingFunctionCalls.get(callId);

  if (existing) {
    existing.arguments += event.delta as string;
    if (event.name) {
      existing.name = event.name as string;
    }
  } else {
    pendingFunctionCalls.set(callId, {
      name: event.name as string || '',
      arguments: event.delta as string || ''
    });
  }
}

/**
 * Handle function call completion
 */
async function handleFunctionCallDone(
  event: RealtimeEvent,
  context: EventHandlerContext
): Promise<void> {
  const { emit, sendFunctionResult, pendingFunctionCalls } = context;

  const callId = event.call_id as string;
  const functionCall = pendingFunctionCalls.get(callId) || {
    name: event.name as string,
    arguments: event.arguments as string
  };
  pendingFunctionCalls.delete(callId);

  emit({
    type: 'function_call',
    data: { callId, ...functionCall }
  });

  const funcName = functionCall.name || event.name as string;
  const funcArgs = functionCall.arguments || event.arguments as string;

  if (funcName) {
    const result = await executeFunction(funcName, funcArgs);
    sendFunctionResult(callId, result.output);
  }
}
