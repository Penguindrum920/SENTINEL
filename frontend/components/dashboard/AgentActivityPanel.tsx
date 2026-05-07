import SectionCard from '@/components/dashboard/SectionCard';
import { AgentActivity } from '@/types/dashboard';

interface AgentActivityPanelProps {
  activity: AgentActivity;
}

function statusClass(status: string): string {
  if (status === 'Filled') return 'text-[var(--mint)]';
  if (status === 'Cancelled') return 'text-[var(--rose)]';
  if (status === 'Partial Fill') return 'text-[var(--gold)]';
  return 'text-[var(--sky)]';
}

export default function AgentActivityPanel({ activity }: AgentActivityPanelProps) {
  return (
    <SectionCard title="Agent Activity" subtitle="Behavior traces and execution summary">
      <div className="grid gap-4 lg:grid-cols-[1.05fr_1fr]">
        <div className="space-y-3">
          <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
            <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">Market Maker</p>
            <p className="mt-1 text-sm text-[var(--text-strong)]">{activity.marketMakerAction}</p>
          </div>
          <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
            <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">Noise Agent</p>
            <p className="mt-1 text-sm text-[var(--text-strong)]">{activity.noiseAgentAction}</p>
          </div>
          <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
            <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">RL Agent Status</p>
            <p className="mt-1 text-sm text-[var(--text-strong)]">{activity.rlAgentStatus}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
              <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">Orders Submitted</p>
              <p className="mt-1 text-xl font-semibold text-[var(--text-strong)]">
                {activity.executionSummary.submitted}
              </p>
            </div>
            <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
              <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">Match Rate</p>
              <p className="mt-1 text-xl font-semibold text-[var(--mint)]">
                {activity.executionSummary.matchRate}%
              </p>
            </div>
            <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
              <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">Fills</p>
              <p className="mt-1 text-xl font-semibold text-[var(--sky)]">{activity.executionSummary.fills}</p>
            </div>
            <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
              <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">Cancellations</p>
              <p className="mt-1 text-xl font-semibold text-[var(--rose)]">
                {activity.executionSummary.cancelled}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-[var(--line-soft)] bg-[var(--card-elevated)] p-3">
          <p className="mb-2 text-[11px] uppercase tracking-[0.1em] text-[var(--text-soft)]">Recent Orders and Fills</p>
          <div className="max-h-72 overflow-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-[var(--line-soft)] text-left text-[var(--text-muted)]">
                  <th className="py-2 pr-2 font-medium">ID</th>
                  <th className="py-2 pr-2 font-medium">Agent</th>
                  <th className="py-2 pr-2 font-medium">Side</th>
                  <th className="py-2 pr-2 font-medium">Px</th>
                  <th className="py-2 pr-2 font-medium">Qty</th>
                  <th className="py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {activity.recentOrders.map((order) => (
                  <tr key={order.id} className="border-b border-[var(--line-soft)]/70 text-[var(--text-soft)]">
                    <td className="py-2 pr-2 text-[var(--text-muted)]">{order.id}</td>
                    <td className="py-2 pr-2">{order.agent}</td>
                    <td className={`py-2 pr-2 ${order.side === 'BUY' ? 'text-[var(--mint)]' : 'text-[var(--rose)]'}`}>
                      {order.side}
                    </td>
                    <td className="py-2 pr-2">{order.price.toFixed(3)}</td>
                    <td className="py-2 pr-2">{order.quantity}</td>
                    <td className={`py-2 ${statusClass(order.status)}`}>{order.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
