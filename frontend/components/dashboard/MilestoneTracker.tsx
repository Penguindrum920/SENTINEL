import SectionCard from '@/components/dashboard/SectionCard';
import { Milestone } from '@/types/dashboard';

interface MilestoneTrackerProps {
  milestones: Milestone[];
}

const statusStyles = {
  completed: 'bg-[var(--mint)]/15 text-[var(--mint)] border-[var(--mint)]/30',
  'in-progress': 'bg-[var(--gold)]/15 text-[var(--gold)] border-[var(--gold)]/30',
  pending: 'bg-[var(--line-soft)] text-[var(--text-soft)] border-[var(--line-soft)]',
};

export default function MilestoneTracker({ milestones }: MilestoneTrackerProps) {
  return (
    <SectionCard
      title="Progress Tracker"
      subtitle="Delivery phases for simulation realism and RL deployment"
    >
      <div className="space-y-3">
        {milestones.map((milestone) => (
          <div
            key={milestone.phase}
            className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-4"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-[var(--text-strong)]">
                {milestone.phase}: {milestone.title}
              </p>
              <span
                className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.1em] ${statusStyles[milestone.status]}`}
              >
                {milestone.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-[var(--text-soft)]">{milestone.detail}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
