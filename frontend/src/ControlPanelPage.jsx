/**
 * ControlPanelPage — minimal popup UI for mode, pause, end session.
 * Designed to stay visible while sharing IDE; communicates with opener via postMessage.
 */
import { useState, useEffect } from 'react';
import './styles/globals.css';

const MODES = [
  { id: 'sportscaster', label: 'Sportscaster', icon: '🔊' },
  { id: 'catchup', label: 'Pause', icon: '⏸', hint: 'Go quiet' },
  { id: 'review', label: 'Review', icon: '👁' },
];

function sendToOpener(action, payload = {}) {
  if (window.opener && !window.opener.closed) {
    window.opener.postMessage({ type: 'codewhisper', action, ...payload }, window.location.origin);
  }
}

export default function ControlPanelPage() {
  const [currentMode, setCurrentMode] = useState('sportscaster');
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (window.opener) {
      window.opener.postMessage({ type: 'codewhisper', action: 'popupReady' }, window.location.origin);
    }
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (e.origin !== window.location.origin || e.data?.type !== 'codewhisper') return;
      const { action, mode } = e.data;
      if (action === 'mode' && mode) setCurrentMode(mode);
      if (action === 'status' && e.data.connected !== undefined) setConnected(e.data.connected);
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  const handleMode = (mode) => {
    setCurrentMode(mode);
    sendToOpener('switchMode', { mode });
  };

  const handleEndSession = () => {
    sendToOpener('endSession');
  };

  if (!window.opener) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
        <p className="text-sm text-slate-600">Open this from CodeWhisper during a session.</p>
      </div>
    );
  }

  return (
    <div className="min-h-full flex flex-col bg-white border border-slate-200 rounded-lg shadow-lg p-3 gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-700">CodeWhisper</span>
        <span className={`h-2 w-2 rounded-full flex-shrink-0 ${connected ? 'bg-green-500' : 'bg-slate-300'}`} />
      </div>
      <p className="text-[10px] text-slate-500">Keep this window beside your IDE</p>
      <div className="flex flex-wrap gap-1">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => handleMode(m.id)}
            className={`rounded border px-2 py-1 text-xs font-medium ${
              currentMode === m.id
                ? 'border-emerald-500 bg-emerald-50 text-emerald-800'
                : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
            }`}
          >
            <span className="mr-0.5">{m.icon}</span>
            {m.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={handleEndSession}
        className="rounded border border-red-300 bg-white px-2 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
      >
        End Session
      </button>
    </div>
  );
}
