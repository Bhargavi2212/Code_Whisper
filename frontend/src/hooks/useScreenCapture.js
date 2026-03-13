import { useState, useRef, useCallback } from 'react';

const FRAME_SIZE = 768;
const FRAME_INTERVAL_MS = 1000;
const JPEG_QUALITY = 0.7;

/**
 * Manages screen sharing and frame capture at 768x768, ~1 FPS.
 * @returns {{ isCapturing: boolean, startCapture: function, stopCapture: function, latestFrame: string|null, error: string|null }}
 */
export function useScreenCapture() {
  const [isCapturing, setIsCapturing] = useState(false);
  const [latestFrame, setLatestFrame] = useState(null);
  const [error, setError] = useState(null);
  const [captureWidth, setCaptureWidth] = useState(null);
  const [captureHeight, setCaptureHeight] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const trackRef = useRef(null);

  const stopCapture = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (trackRef.current) {
      trackRef.current.removeEventListener('ended', stopCapture);
      trackRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current = null;
    }
    if (canvasRef.current) {
      canvasRef.current = null;
    }
    setIsCapturing(false);
    setLatestFrame(null);
    setCaptureWidth(null);
    setCaptureHeight(null);
    setError(null);
  }, []);

  const startCapture = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      streamRef.current = stream;

      const video = document.createElement('video');
      video.autoplay = true;
      video.muted = true;
      video.srcObject = stream;
      videoRef.current = video;

      const canvas = document.createElement('canvas');
      canvas.width = FRAME_SIZE;
      canvas.height = FRAME_SIZE;
      canvasRef.current = canvas;

      const ctx = canvas.getContext('2d');

      const track = stream.getVideoTracks()[0];
      trackRef.current = track;
      track.addEventListener('ended', stopCapture);

      const settings = track.getSettings();
      if (settings.width != null && settings.height != null) {
        setCaptureWidth(settings.width);
        setCaptureHeight(settings.height);
      }

      await video.play();

      intervalRef.current = setInterval(() => {
        if (!videoRef.current || !canvasRef.current || video.readyState < 2) return;
        const w = video.videoWidth;
        const h = video.videoHeight;
        if (w === 0 || h === 0) return;
        ctx.drawImage(video, 0, 0, w, h, 0, 0, FRAME_SIZE, FRAME_SIZE);
        const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
        setLatestFrame(dataUrl);
      }, FRAME_INTERVAL_MS);

      setIsCapturing(true);
    } catch (err) {
      setError(err.message || 'Screen share failed');
      stopCapture();
    }
  }, [stopCapture]);

  return { isCapturing, startCapture, stopCapture, latestFrame, error, captureWidth, captureHeight };
}
