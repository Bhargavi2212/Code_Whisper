/**
 * FlowModeIndicator — shows current Flow Mode and allows manual switching.
 * Sportscaster: active commentary. Catch-Up: silent, summarize on request. Review: fully silent, review at end.
 * Props: currentMode, onSwitchMode, sessionState (hide when idle/ended).
 */
export default function FlowModeIndicator({ currentMode, onSwitchMode, sessionState }) {
  const modes = [
    {
      id: 'sportscaster',
      label: 'Sportscaster',
      icon: '🔊',
      hint: 'Active commentary',
      className: 'border-emerald-500 bg-emerald-50 text-emerald-800',
      activeClass: 'ring-2 ring-emerald-500',
    },
    {
      id: 'catchup',
      label: 'Catch-Up',
      icon: '⏸',
      hint: 'Quiet until you ask',
      className: 'border-amber-500 bg-amber-50 text-amber-800',
      activeClass: 'ring-2 ring-amber-500',
    },
    {
      id: 'review',
      label: 'Review',
      icon: '👁',
      hint: 'Save for the end',
      className: 'border-slate-500 bg-slate-50 text-slate-800',
      activeClass: 'ring-2 ring-slate-500',
    },
  ];

  const show = sessionState && ['connecting', 'active', 'ending'].includes(sessionState);
  const canSwitch = sessionState === 'active';
  if (!show) return null;

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
        Flow Mode
      </span>
      <div className="flex flex-wrap gap-2">
        {modes.map((m) => {
          const isActive = currentMode === m.id;
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => canSwitch && onSwitchMode(m.id)}
              disabled={!canSwitch}
              className={`rounded-lg border px-3 py-2 text-sm font-medium transition-all ${
                canSwitch ? 'hover:opacity-90 cursor-pointer' : 'cursor-not-allowed opacity-60'
              } ${m.className} ${isActive ? m.activeClass : 'opacity-75'}`}
              title={m.hint}
            >
              <span className="mr-1.5" aria-hidden>{m.icon}</span>
              {m.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
