import { ProjectOverview } from '@/types/dashboard';
import SectionCard from '@/components/dashboard/SectionCard';

interface ProjectOverviewPanelProps {
  overview: ProjectOverview;
}

export default function ProjectOverviewPanel({ overview }: ProjectOverviewPanelProps) {
  return (
    <SectionCard
      title="Project Overview"
      subtitle="Research system status and implementation coverage"
      rightSlot={
        <span className="rounded-full border border-[var(--line-soft)] bg-[var(--card-elevated)] px-3 py-1 text-[11px] uppercase tracking-[0.12em] text-[var(--sky)]">
          {overview.currentStage}
        </span>
      }
    >
      <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-strong)]">{overview.name}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-soft)]">{overview.summary}</p>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-4">
          <p className="text-xs uppercase tracking-[0.12em] text-[var(--mint)]">Features Completed</p>
          <ul className="mt-3 space-y-2 text-sm text-[var(--text-soft)]">
            {overview.completed.map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[var(--mint)]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-4">
          <p className="text-xs uppercase tracking-[0.12em] text-[var(--gold)]">In Progress</p>
          <ul className="mt-3 space-y-2 text-sm text-[var(--text-soft)]">
            {overview.inProgress.map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[var(--gold)]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </SectionCard>
  );
}
