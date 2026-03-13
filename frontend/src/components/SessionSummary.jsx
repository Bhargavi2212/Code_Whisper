import { useCallback } from 'react';

/**
 * Renders end-of-session summary: section headers, bullets, bold; Download .md and Start New Session.
 * Parses markdown by hand (no library): split on ##, then bullets and **bold** within sections.
 */
function SessionSummary({ summaryText = '', onStartNewSession, finalPulseScore }) {
  const downloadMarkdown = useCallback(() => {
    const blob = new Blob([summaryText], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'codewhisper-summary.md';
    a.click();
    URL.revokeObjectURL(url);
  }, [summaryText]);

  // Parse into sections (## Header) and render with simple formatting
  const sections = [];
  if (summaryText && typeof summaryText === 'string') {
    const trimmedFull = summaryText.trim();
    if (!trimmedFull.includes('##')) {
      sections.push({ header: null, body: trimmedFull });
    } else {
      const parts = summaryText.split(/(?=^##\s)/m);
      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) continue;
        const firstLineEnd = trimmed.indexOf('\n');
        const firstLine = firstLineEnd >= 0 ? trimmed.slice(0, firstLineEnd) : trimmed;
        const rest = firstLineEnd >= 0 ? trimmed.slice(firstLineEnd + 1).trim() : '';
        const header = firstLine.replace(/^##\s*/, '').trim();
        sections.push({ header, body: rest });
      }
    }
  }

  const renderLine = (line, lineKey) => {
    const trimmed = line.trim();
    if (!trimmed) return null;
    const isBullet = /^[-*]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed);
    const content = trimmed.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '');
    // Inline **bold**
    const parts = [];
    let remaining = content;
    let key = 0;
    while (remaining.length > 0) {
      const boldStart = remaining.indexOf('**');
      if (boldStart === -1) {
        parts.push(<span key={key}>{remaining}</span>);
        break;
      }
      parts.push(<span key={key}>{remaining.slice(0, boldStart)}</span>);
      key += 1;
      const boldEnd = remaining.indexOf('**', boldStart + 2);
      if (boldEnd === -1) {
        parts.push(<span key={key}>{remaining.slice(boldStart + 2)}</span>);
        break;
      }
      parts.push(<strong key={key}>{remaining.slice(boldStart + 2, boldEnd)}</strong>);
      key += 1;
      remaining = remaining.slice(boldEnd + 2);
    }
    return (
      <p key={lineKey} className={`mb-1 ${isBullet ? 'ml-4 pl-2 border-l-2 border-gray-200' : ''}`}>
        {parts}
      </p>
    );
  };

  const renderBody = (body) => {
    if (!body) return null;
    const lines = body.split('\n').filter((l) => l.trim());
    return <div className="space-y-0.5">{lines.map((line, i) => renderLine(line, i))}</div>;
  };

  return (
    <div
      className="flex flex-col items-center w-full max-w-2xl mx-auto px-4 opacity-100 transition-opacity duration-300"
      data-testid="session-summary"
    >
      <div className="w-full rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden flex flex-col max-h-[70vh]">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Session Summary</h2>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 text-gray-700 text-sm space-y-4">
          {sections.length === 0 && (
            <p className="text-gray-500">{summaryText || 'No summary available.'}</p>
          )}
          {sections.map(({ header, body }, i) => (
            <section key={i}>
              {header && (
                <h3 className="text-base font-semibold text-gray-900 mb-2 mt-2 first:mt-0">
                  {header}
                </h3>
              )}
              <div className="space-y-1">{body ? renderBody(body) : null}</div>
            </section>
          ))}
        </div>
        {typeof finalPulseScore === 'number' && (
          <div className="px-5 py-2 border-t border-gray-100 text-sm text-gray-600">
            Understanding score: {Math.min(100, Math.max(0, Math.round(finalPulseScore)))}%
          </div>
        )}
        <div className="px-5 py-4 border-t border-gray-100 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={downloadMarkdown}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Download as Markdown
          </button>
          <button
            type="button"
            onClick={onStartNewSession}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Start New Session
          </button>
        </div>
      </div>
    </div>
  );
}

export default SessionSummary;
