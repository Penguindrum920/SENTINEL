import SectionCard from '@/components/dashboard/SectionCard';
import { KernelEvent } from '@/types/dashboard';

interface EventLogPanelProps {
  events: KernelEvent[];
}

const eventTone = {
  info: 'border-[var(--sky)]/25 bg-[var(--sky)]/5',
  warning: 'border-[var(--gold)]/35 bg-[var(--gold)]/5',
  critical: 'border-[var(--rose)]/40 bg-[var(--rose)]/8',
};

export default function EventLogPanel({ events }: EventLogPanelProps) {
  return (
    <SectionCard title="Kernel Event Stream" subtitle="Recent submissions, matches, fills, cancellations, and latency events">
      <div className="max-h-[360px] space-y-2 overflow-auto pr-1">
        {events.map((event) => (
          <div key={event.id} className={`rounded-xl border p-3 ${eventTone[event.severity]}`}>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-soft)]">{event.type}</p>
              <span className="text-[11px] text-[var(--text-muted)]">{event.time}</span>
            </div>
            <p className="mt-1 text-sm text-[var(--text-strong)]">{event.message}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
