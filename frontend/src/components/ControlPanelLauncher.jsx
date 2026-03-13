/**
 * ControlPanelLauncher — opens a small popup with mode/pause/end controls.
 * Auto-opens when session is active so you can position it beside your shared IDE.
 */
import { useRef, useEffect, useCallback, useState } from 'react';

export default function ControlPanelLauncher({
  sessionState,
  isConnected,
  currentMode,
  switchMode,
  endSession,
}) {
  const popupRef = useRef(null);
  const hasAutoOpenedRef = useRef(false);
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  const isActive = sessionState === 'active' || sessionState === 'connecting';

  const openPopup = useCallback(() => {
    if (popupRef.current && !popupRef.current.closed) {
      popupRef.current.focus();
      return;
    }
    const w = 280;
    const h = 140;
    // Position top-right so user can drag it beside their IDE
    const left = window.screenX + window.outerWidth - w - 20;
    const top = window.screenY + 20;
    popupRef.current = window.open(
      '/control-panel.html',
      'codewhisper-controls',
      `width=${w},height=${h},left=${left},top=${top},popup=1,scrollbars=no,alwaysRaised=1`
    );
    hasAutoOpenedRef.current = true;
    setIsPopupOpen(true);
  }, []);

  // Detect when popup is closed (e.g. user closed it)
  useEffect(() => {
    if (!popupRef.current) return;
    const id = setInterval(() => {
      if (popupRef.current?.closed) {
        setIsPopupOpen(false);
      }
    }, 500);
    return () => clearInterval(id);
  }, [isPopupOpen]);

  // Auto-open Control Panel when session becomes active
  useEffect(() => {
    if (sessionState === 'active' && !hasAutoOpenedRef.current) {
      hasAutoOpenedRef.current = true;
      openPopup();
    }
    if (sessionState === 'idle' || sessionState === 'ended') {
      hasAutoOpenedRef.current = false;
    }
  }, [sessionState, openPopup]);

  const sendStateToPopup = useCallback(() => {
    const popup = popupRef.current;
    if (popup && !popup.closed) {
      try {
        popup.postMessage(
          { type: 'codewhisper', action: 'mode', mode: currentMode },
          window.location.origin
        );
        popup.postMessage(
          { type: 'codewhisper', action: 'status', connected: isConnected },
          window.location.origin
        );
      } catch (_) {}
    }
  }, [currentMode, isConnected]);

  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type !== 'codewhisper') return;
      const { action, mode } = e.data;
      if (action === 'popupReady') sendStateToPopup();
      if (action === 'switchMode' && mode) switchMode(mode);
      if (action === 'endSession') endSession();
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [switchMode, endSession, sendStateToPopup]);

  useEffect(() => {
    sendStateToPopup();
  }, [currentMode, isConnected, sendStateToPopup]);

  if (!isActive) return null;

  return (
    <button
      type="button"
      onClick={openPopup}
      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      title="Open controls — keep this window beside your IDE to change mode without switching"
    >
      {isPopupOpen ? 'Focus Control Panel' : 'Open Control Panel'}
    </button>
  );
}
