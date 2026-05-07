import SectionCard from '@/components/dashboard/SectionCard';
import { DepthHeatLevel } from '@/types/dashboard';

interface DepthHeatmapPanelProps {
  levels: DepthHeatLevel[];
}

function depthCellColor(value: number): string {
  const alpha = Math.min(0.92, value / 280);
  return `rgba(96, 210, 166, ${alpha})`;
}

function askCellColor(value: number): string {
  const alpha = Math.min(0.92, value / 280);
  return `rgba(255, 125, 125, ${alpha})`;
}

export default function DepthHeatmapPanel({ levels }: DepthHeatmapPanelProps) {
  return (
    <SectionCard title="Order Book Depth" subtitle="Approximate bid/ask heat profile across 12 levels">
      <div className="space-y-2">
        <div className="grid grid-cols-[auto_1fr_1fr] gap-2 text-[11px] uppercase tracking-[0.08em] text-[var(--text-soft)]">
          <span>Level</span>
          <span>Bid Depth</span>
          <span>Ask Depth</span>
        </div>

        {levels.map((row) => (
          <div key={row.level} className="grid grid-cols-[auto_1fr_1fr] items-center gap-2">
            <span className="w-9 text-[12px] text-[var(--text-soft)]">L{row.level}</span>
            <div className="h-6 rounded-md px-2 text-right text-[11px] leading-6 text-[#04150f]" style={{ backgroundColor: depthCellColor(row.bidDepth) }}>
              {Math.round(row.bidDepth)}
            </div>
            <div className="h-6 rounded-md px-2 text-right text-[11px] leading-6 text-[#220707]" style={{ backgroundColor: askCellColor(row.askDepth) }}>
              {Math.round(row.askDepth)}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
