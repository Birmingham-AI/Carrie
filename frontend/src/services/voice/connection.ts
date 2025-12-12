import config from '../../config';

/**
 * WebRTC connection resources
 */
export interface ConnectionResources {
  peerConnection: RTCPeerConnection;
  dataChannel: RTCDataChannel;
  mediaStream: MediaStream;
  audioElement: HTMLAudioElement;
}

/**
 * Get ephemeral token from backend
 */
async function getEphemeralToken(): Promise<string> {
  const response = await fetch(`${config.apiBaseUrl}/v1/realtime/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.statusText}`);
  }

  const sessionData = await response.json();
  const ephemeralKey = sessionData.client_secret?.value;

  if (!ephemeralKey) {
    throw new Error('No ephemeral key received from backend');
  }

  return ephemeralKey;
}

/**
 * Get microphone access
 */
async function getMicrophoneStream(): Promise<MediaStream> {
  return await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      sampleRate: 24000
    }
  });
}

/**
 * Create peer connection with audio track
 */
function createPeerConnection(
  mediaStream: MediaStream,
  onTrack: (stream: MediaStream) => void
): RTCPeerConnection {
  const peerConnection = new RTCPeerConnection();

  const audioTrack = mediaStream.getAudioTracks()[0];
  peerConnection.addTrack(audioTrack, mediaStream);

  peerConnection.ontrack = (event) => {
    if (event.streams[0]) {
      onTrack(event.streams[0]);
    }
  };

  return peerConnection;
}

/**
 * Create audio element for playback
 */
function createAudioElement(): HTMLAudioElement {
  const audioElement = document.createElement('audio');
  audioElement.autoplay = true;
  return audioElement;
}

/**
 * Exchange SDP with OpenAI
 */
async function exchangeSdp(
  peerConnection: RTCPeerConnection,
  ephemeralKey: string
): Promise<void> {
  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);

  const response = await fetch(
    'https://api.openai.com/v1/realtime?model=gpt-realtime',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${ephemeralKey}`,
        'Content-Type': 'application/sdp'
      },
      body: offer.sdp
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to establish WebRTC connection: ${response.statusText}`);
  }

  const answerSdp = await response.text();
  await peerConnection.setRemoteDescription({
    type: 'answer',
    sdp: answerSdp
  });
}

/**
 * Establish WebRTC connection to OpenAI Realtime API
 */
export async function createConnection(
  onDataChannelMessage: (event: MessageEvent) => void
): Promise<ConnectionResources> {
  // Get ephemeral token
  const ephemeralKey = await getEphemeralToken();

  // Get microphone access
  const mediaStream = await getMicrophoneStream();

  // Create audio element
  const audioElement = createAudioElement();

  // Create peer connection
  const peerConnection = createPeerConnection(mediaStream, (stream) => {
    audioElement.srcObject = stream;
  });

  // Create data channel
  const dataChannel = peerConnection.createDataChannel('oai-events');
  dataChannel.onmessage = onDataChannelMessage;

  // Exchange SDP
  await exchangeSdp(peerConnection, ephemeralKey);

  return {
    peerConnection,
    dataChannel,
    mediaStream,
    audioElement
  };
}

/**
 * Clean up connection resources
 */
export function cleanupConnection(resources: Partial<ConnectionResources>): void {
  if (resources.dataChannel) {
    resources.dataChannel.close();
  }

  if (resources.peerConnection) {
    resources.peerConnection.close();
  }

  if (resources.mediaStream) {
    resources.mediaStream.getTracks().forEach(track => track.stop());
  }

  if (resources.audioElement) {
    resources.audioElement.srcObject = null;
  }
}

/**
 * Send message through data channel
 */
export function sendMessage(
  dataChannel: RTCDataChannel | null,
  message: object
): boolean {
  if (!dataChannel || dataChannel.readyState !== 'open') {
    return false;
  }

  dataChannel.send(JSON.stringify(message));
  return true;
}

/**
 * Check if WebRTC is supported
 */
export function isWebRTCSupported(): boolean {
  return !!(
    typeof RTCPeerConnection !== 'undefined' &&
    navigator.mediaDevices &&
    navigator.mediaDevices.getUserMedia
  );
}
