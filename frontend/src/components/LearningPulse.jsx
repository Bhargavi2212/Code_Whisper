/**
 * Learning Pulse: real-time "Understanding" % ring during session.
 * Green 75–100%, yellow 50–74%, red &lt;50%. Small, corner; visible only when session active.
 */
function LearningPulse({ score = 0 }) {
  const clamped = Math.min(100, Math.max(0, Math.round(score)));
  const radius = 18;
  const stroke = 3;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  const color =
    clamped >= 75 ? 'text-emerald-600' : clamped >= 50 ? 'text-amber-500' : 'text-red-500';
  const strokeColor =
    clamped >= 75 ? '#10b981' : clamped >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div
      className="fixed bottom-20 right-4 z-10 flex items-center gap-2 rounded-lg border border-gray-200 bg-white/95 px-2 py-1.5 shadow-sm backdrop-blur-sm"
      title="Understanding"
      aria-label={`Understanding ${clamped}%`}
    >
      <div className="relative h-10 w-10 flex-shrink-0">
        <svg className="h-10 w-10 -rotate-90" viewBox={`0 0 ${radius * 2 + stroke * 2} ${radius * 2 + stroke * 2}`}>
          <circle
            cx={radius + stroke}
            cy={radius + stroke}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={stroke}
          />
          <circle
            cx={radius + stroke}
            cy={radius + stroke}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-out"
          />
        </svg>
        <span
          className={`absolute inset-0 flex items-center justify-center text-xs font-medium ${color}`}
        >
          {clamped}%
        </span>
      </div>
      <span className="text-xs font-medium text-gray-600">Understanding</span>
    </div>
  );
}

export default LearningPulse;
