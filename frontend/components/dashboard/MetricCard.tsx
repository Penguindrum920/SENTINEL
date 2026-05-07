interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  tone?: 'neutral' | 'positive' | 'negative' | 'accent';
}

const toneStyles = {
  neutral: 'text-[var(--text-strong)]',
  positive: 'text-[var(--mint)]',
  negative: 'text-[var(--rose)]',
  accent: 'text-[var(--gold)]',
};

export default function MetricCard({ label, value, hint, tone = 'neutral' }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
      <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-soft)]">{label}</p>
      <p className={`mt-2 text-2xl font-semibold leading-none ${toneStyles[tone]}`}>{value}</p>
      {hint ? <p className="mt-2 text-xs text-[var(--text-muted)]">{hint}</p> : null}
    </div>
  );
}
