import VoiceService from './VoiceService';

// Export types
export type { VoiceEvent, VoiceEventType, VoiceEventCallback } from './types';

// Export singleton instance
const voiceService = new VoiceService();
export default voiceService;
