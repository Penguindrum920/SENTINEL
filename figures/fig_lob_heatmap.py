"""
Generate LOB depth heatmap showing institutional TWAP and spoofing effects.
Output: figures/fig_lob_heatmap.pdf
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

np.random.seed(123)

# ── Parameters ──
n_time = 600          # 10 minutes at 1-second resolution
n_levels = 20         # 10 bid + 10 ask price levels
mid_price = 100.0
tick_size = 0.01

# Create price levels (centered on mid-price)
price_levels = np.array([mid_price + (i - n_levels//2) * tick_size for i in range(n_levels)])

# ── Generate baseline depth ──
depth = np.zeros((n_time, n_levels))
for t in range(n_time):
    for i in range(n_levels):
        dist_from_mid = abs(i - n_levels//2)
        base_vol = max(50, 400 - dist_from_mid * 30 + np.random.normal(0, 40))
        depth[t, i] = max(0, base_vol)

# ── Inject institutional TWAP buy order (depletes ask side) ──
twap_start = 100
twap_end = 450
ask_indices = list(range(n_levels//2, n_levels))  # ask side
for t in range(twap_start, twap_end):
    progress = (t - twap_start) / (twap_end - twap_start)
    for idx in ask_indices[:5]:
        depletion = progress * 0.7 * depth[t, idx]
        depth[t, idx] = max(10, depth[t, idx] - depletion)

# ── Market Maker replenishment after TWAP ──
for t in range(twap_end, min(twap_end + 100, n_time)):
    recovery = (t - twap_end) / 100
    for idx in ask_indices[:5]:
        target = 300 + np.random.normal(0, 30)
        depth[t, idx] = depth[t, idx] + recovery * max(0, target - depth[t, idx])

# ── Inject Spoofing agent effects (brief phantom bid-side depth) ──
spoof_events = [(180, 195), (320, 335)]
bid_indices = list(range(0, n_levels//2))
for s_start, s_end in spoof_events:
    for t in range(s_start, min(s_end, n_time)):
        for idx in bid_indices[3:7]:
            depth[t, idx] += np.random.uniform(800, 2000)
    # Rapid cancellation visible as sharp drop
    if s_end < n_time:
        for idx in bid_indices[3:7]:
            depth[s_end, idx] = max(50, depth[s_end, idx] * 0.1)

# ── Create custom colormap ──
colors_bid = ['#0F172A', '#1E3A5F', '#2563EB', '#60A5FA', '#BFDBFE']
colors_ask = ['#0F172A', '#5F1E1E', '#DC2626', '#F87171', '#FECACA']

# Single colormap: dark → bright
cmap = LinearSegmentedColormap.from_list('depth',
    ['#0F172A', '#1E3A5F', '#2563EB', '#22C55E', '#F59E0B', '#EF4444', '#FFFFFF'], N=256)

# ── Plot ──
fig, ax = plt.subplots(figsize=(8.0, 3.5), dpi=300)

# Time axis in minutes
time_axis = np.arange(n_time) / 60  # minutes

im = ax.pcolormesh(time_axis, price_levels, depth.T, cmap=cmap,
                   shading='nearest', vmin=0, vmax=1500)

# Mid-price line
mid_line = np.ones(n_time) * mid_price
ax.plot(time_axis, mid_line, '--', color='white', linewidth=0.8, alpha=0.7, label='Mid-price')

# Annotations
ax.annotate('TWAP buy\nstart', xy=(twap_start/60, 100.04),
            fontsize=6, color='white', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='white', lw=0.8),
            xytext=(twap_start/60 - 0.5, 100.08))

ax.annotate('TWAP\nend', xy=(twap_end/60, 100.04),
            fontsize=6, color='white', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='white', lw=0.8),
            xytext=(twap_end/60 + 0.3, 100.08))

for se in spoof_events:
    ax.axvspan(se[0]/60, se[1]/60, alpha=0.15, color='#F59E0B', zorder=0)
    ax.text((se[0]+se[1])/120, 99.915, 'Spoof', fontsize=5, color='#FCD34D',
            ha='center', fontweight='bold')

# Labels
ax.set_xlabel('Time (minutes)', fontsize=8)
ax.set_ylabel('Price Level ($)', fontsize=8)
ax.set_title('LOB Depth Heatmap — TWAP Execution & Spoofing Events', fontsize=10, fontweight='bold')
ax.tick_params(labelsize=7)

# Colorbar
cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
cbar.set_label('Volume (shares)', fontsize=7)
cbar.ax.tick_params(labelsize=6)

# Labels for bid/ask sides
ax.text(0.1, 99.935, 'BID SIDE', fontsize=7, color='#60A5FA', fontweight='bold')
ax.text(0.1, 100.06, 'ASK SIDE', fontsize=7, color='#F87171', fontweight='bold')

plt.tight_layout()
plt.savefig('figures/fig_lob_heatmap.pdf', bbox_inches='tight', dpi=300)
plt.savefig('figures/fig_lob_heatmap.png', bbox_inches='tight', dpi=300)
print("✓ fig_lob_heatmap.pdf generated")
