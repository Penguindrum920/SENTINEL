"""
Generate representative per-agent-type cumulative P&L curves.
Output: figures/fig_equity_curves.pdf
"""

import matplotlib.pyplot as plt
import numpy as np

np.random.seed(2024)

n_steps = 1500  # ~minutes in a trading day
time = np.arange(n_steps) / 60  # hours

# ── Simulate P&L curves for each agent type ──
def cum_pnl(drift, vol, jumps=0, jump_size=0):
    """Cumulative P&L with optional jumps."""
    ret = np.random.normal(drift, vol, n_steps)
    if jumps > 0:
        jump_idx = np.random.choice(n_steps, jumps, replace=False)
        ret[jump_idx] += np.random.normal(jump_size, abs(jump_size)*0.5, jumps)
    return np.cumsum(ret)

# Market Maker: steady income, occasional drawdowns
mm = cum_pnl(0.8, 3.0, jumps=5, jump_size=-15)

# HFT: sharp frequent gains, occasional steep losses
hft = cum_pnl(0.3, 5.0, jumps=8, jump_size=-25)

# Institutional: negative during TWAP, may recover
inst_base = np.zeros(n_steps)
twap_start, twap_end = 200, 700
inst_base[twap_start:twap_end] = np.cumsum(np.random.normal(-0.5, 1.5, twap_end - twap_start))
inst_base[twap_end:] = inst_base[twap_end-1] + np.cumsum(np.random.normal(0.3, 1.0, n_steps - twap_end))
inst = inst_base

# Retail: noisy small gains/losses
retail = cum_pnl(0.05, 1.5)

# Informed: step functions around signals
informed = np.zeros(n_steps)
sig_points = [300, 600, 1000]
for sp in sig_points:
    sign = np.random.choice([-1, 1])
    informed[sp:sp+100] += np.cumsum(np.random.normal(sign*0.8, 0.5, 100))
informed = np.cumsum(np.diff(np.concatenate([[0], informed])) + np.random.normal(0, 0.3, n_steps))

# Noise: random walk around zero
noise = cum_pnl(0.0, 2.0)

# Momentum: profits during trends, gives back during reversals
momentum = np.zeros(n_steps)
trend_phases = [(100, 400, 1.2), (500, 700, -0.8), (900, 1200, 1.5)]
for s, e, d in trend_phases:
    momentum[s:e] = np.cumsum(np.random.normal(d, 2.0, e-s))
    if e < n_steps:
        momentum[e:e+100] = momentum[e-1] + np.cumsum(np.random.normal(-d*0.6, 1.5, min(100, n_steps-e)))

# Mean Reversion: opposite of momentum timing
mean_rev = -momentum * 0.5 + cum_pnl(0.1, 1.0)

# Spoofing: stepped P&L (flat → gain → flat → gain)
spoof = np.zeros(n_steps)
spoof_cycles = [(200, 210, 80), (450, 460, 120), (700, 710, 90), (1000, 1010, 110)]
current_level = 0
for s, e, gain in spoof_cycles:
    spoof[s:e] = np.linspace(current_level, current_level + gain, e-s)
    current_level += gain
    if e < n_steps:
        spoof[e:] = current_level
spoof += np.random.normal(0, 2, n_steps)
spoof = np.cumsum(np.diff(np.concatenate([[0], spoof])))

# Sentiment: sharp moves during herding, reversals during contrarian
sentiment = np.zeros(n_steps)
herd_phases = [(150, 350, 0.8), (600, 800, -1.0), (1100, 1300, 0.6)]
for s, e, d in herd_phases:
    phase_len = min(e, n_steps) - s
    sentiment[s:s+phase_len] = np.cumsum(np.random.normal(d, 2.5, phase_len))
    if e < n_steps:
        rev_len = min(100, n_steps - e)
        sentiment[e:e+rev_len] = sentiment[min(e-1, n_steps-1)] + np.cumsum(np.random.normal(-d*0.7, 1.5, rev_len))

# ── Normalize all to starting inventory value (percentage) ──
curves = {
    'Market Maker': mm / 100,
    'HFT': hft / 150,
    'Institutional': inst / 200,
    'Retail': retail / 50,
    'Informed': informed / 100,
    'Noise': noise / 50,
    'Momentum': momentum / 100,
    'Mean Reversion': mean_rev / 80,
    'Spoofing': spoof / 100,
    'Sentiment': sentiment / 80,
}

colors = {
    'Market Maker': '#2563EB',
    'HFT': '#7C3AED',
    'Institutional': '#059669',
    'Retail': '#F59E0B',
    'Informed': '#DC2626',
    'Noise': '#94A3B8',
    'Momentum': '#EC4899',
    'Mean Reversion': '#14B8A6',
    'Spoofing': '#1E293B',
    'Sentiment': '#F97316',
}

fig, ax = plt.subplots(figsize=(8.0, 3.8), dpi=300)

for name, curve in curves.items():
    lw = 1.8 if name in ['Market Maker', 'Momentum', 'Mean Reversion', 'Spoofing'] else 1.0
    alpha = 0.9 if name in ['Market Maker', 'Momentum', 'Mean Reversion', 'Spoofing'] else 0.65
    ax.plot(time, curve[:len(time)], label=name, color=colors[name],
            linewidth=lw, alpha=alpha)

ax.axhline(y=0, color='#CBD5E1', linewidth=0.5, linestyle='--')
ax.set_xlabel('Time (hours)', fontsize=9)
ax.set_ylabel('Cumulative P&L (% of initial capital)', fontsize=9)
ax.set_title('Per-Agent-Type Equity Curves — Single Simulated Day', fontsize=10, fontweight='bold')
ax.legend(fontsize=5.5, ncol=5, loc='upper center', bbox_to_anchor=(0.5, -0.15),
          framealpha=0.8, columnspacing=1.0)
ax.tick_params(labelsize=7)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(True, alpha=0.15)

plt.tight_layout()
plt.savefig('figures/fig_equity_curves.pdf', bbox_inches='tight', dpi=300)
plt.savefig('figures/fig_equity_curves.png', bbox_inches='tight', dpi=300)
print("✓ fig_equity_curves.pdf generated")
