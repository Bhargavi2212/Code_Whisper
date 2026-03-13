function StatusBar({ isConnected, sessionState, geminiStatus, isRecording, isCapturing }) {
  const sessionLabel = {
    idle: 'Ready',
    connecting: 'Connecting...',
    active: 'Session Active',
    ending: 'Ending...',
    ended: 'Session Ended',
    error: 'Error',
  }[sessionState] ?? sessionState;

  const geminiLabel = geminiStatus
    ? geminiStatus === 'gemini_connected'
      ? 'Gemini connected'
      : geminiStatus === 'gemini_speaking'
        ? 'Speaking'
        : geminiStatus === 'gemini_listening'
          ? 'Listening'
          : geminiStatus
    : null;

  return (
    <div className="fixed bottom-0 left-0 right-0 flex items-center justify-center gap-4 border-t border-gray-200 bg-gray-50 px-4 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
          aria-hidden
        />
        <span className="text-gray-600">
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>
      <div className="text-gray-600">{sessionLabel}</div>
      {sessionState === 'active' && (
        <div className="flex items-center gap-1.5 text-gray-500">
          <span
            className={`h-2 w-2 rounded-full ${isCapturing ? 'bg-blue-500' : 'bg-gray-300'}`}
            title={isCapturing ? 'Screen sharing' : 'Screen off'}
          />
          <span
            className={`h-2 w-2 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-gray-300'}`}
            title={isRecording ? 'Mic active' : 'Mic off'}
          />
          {isRecording && <span className="text-gray-500">Listening</span>}
        </div>
      )}
      {geminiLabel && (
        <div className="text-gray-500">{geminiLabel}</div>
      )}
    </div>
  );
}

export default StatusBar;
