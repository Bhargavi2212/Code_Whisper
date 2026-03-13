import { useState, useRef, useCallback } from 'react';
import { base64ToArrayBuffer, int16ToFloat32 } from '../utils/audioUtils';

const SAMPLE_RATE = 24000;
// Only reset play schedule when gap between chunks is large (avoids cutting off on network jitter)
const GAP_RESET_MS = 1500;

/**
 * Manages playing PCM audio chunks (24kHz, 16-bit mono) through speakers.
 * AudioContext is created lazily on first playChunk. Resets schedule when gap > 500ms.
 * @returns {{ isPlaying: boolean, playChunk: function, stop: function, setVolume: function }}
 */
export function useAudioOutput() {
  const [isPlaying, setIsPlaying] = useState(false);

  const contextRef = useRef(null);
  const gainNodeRef = useRef(null);
  const nextPlayTimeRef = useRef(0);
  const lastChunkTimeRef = useRef(0);

  const ensureContext = useCallback(() => {
    if (contextRef.current?.state === 'closed') {
      contextRef.current = null;
      gainNodeRef.current = null;
    }
    if (!contextRef.current) {
      const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
      contextRef.current = ctx;
      const gain = ctx.createGain();
      gain.connect(ctx.destination);
      gain.gain.value = 1;
      gainNodeRef.current = gain;
      nextPlayTimeRef.current = 0;
      lastChunkTimeRef.current = 0;
    }
    return contextRef.current;
  }, []);

  const stop = useCallback(() => {
    if (contextRef.current) {
      contextRef.current.close();
      contextRef.current = null;
      gainNodeRef.current = null;
    }
    nextPlayTimeRef.current = 0;
    lastChunkTimeRef.current = 0;
    setIsPlaying(false);
  }, []);

  const setVolume = useCallback((level) => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = Math.max(0, Math.min(1, level));
    }
  }, []);

  const playChunk = useCallback(async (base64Data) => {
    const ctx = ensureContext();
    if (!ctx || !gainNodeRef.current) return;

    // Resume if suspended (browser autoplay policy) — required for audio to play
    if (ctx.state === 'suspended') {
      try {
        await ctx.resume();
        console.log('[CodeWhisper] AudioContext resumed (was suspended)');
      } catch (e) {
        console.warn('[CodeWhisper] AudioContext resume failed:', e);
      }
    }

    const now = ctx.currentTime;
    const timeSinceLastChunk = (now - lastChunkTimeRef.current) * 1000;
    if (timeSinceLastChunk > GAP_RESET_MS || nextPlayTimeRef.current < now) {
      nextPlayTimeRef.current = now;
    }
    lastChunkTimeRef.current = now;

    const buffer = base64ToArrayBuffer(base64Data);
    const int16 = new Int16Array(buffer);
    const float32 = int16ToFloat32(int16);

    const audioBuffer = ctx.createBuffer(1, float32.length, SAMPLE_RATE);
    audioBuffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(gainNodeRef.current);
    source.start(nextPlayTimeRef.current);
    nextPlayTimeRef.current += audioBuffer.duration;

    setIsPlaying(true);
    source.onended = () => {
      if (contextRef.current && nextPlayTimeRef.current <= contextRef.current.currentTime + 0.05) {
        setIsPlaying(false);
      }
    };
  }, [ensureContext]);

  return { isPlaying, playChunk, stop, setVolume };
}
