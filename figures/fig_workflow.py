"""
Generate the SENTINEL simulation loop and real-time signal detection workflow diagram.
Output: figures/fig_workflow.pdf
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 8.5)
ax.axis('off')

# Colors
C_STEP = '#1E40AF'
C_PRED = '#047857'
C_WS = '#B45309'
C_AGENT = '#7C3AED'
C_ARROW = '#334155'
C_TIMER = '#DC2626'

def draw_rect(x, y, w, h, color, label, fontsize=8, text_color='white'):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                         facecolor=color, edgecolor='white', linewidth=1.2, alpha=0.9)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, label, ha='center', va='center',
            fontsize=fontsize, color=text_color, fontweight='bold')

def draw_diamond(cx, cy, size, color, label, fontsize=6.5):
    diamond = plt.Polygon(
        [(cx, cy+size), (cx+size*1.5, cy), (cx, cy-size), (cx-size*1.5, cy)],
        facecolor=color, edgecolor='white', linewidth=1.2, alpha=0.85)
    ax.add_patch(diamond)
    ax.text(cx, cy, label, ha='center', va='center', fontsize=fontsize,
            color='white', fontweight='bold')

def arrow(x1, y1, x2, y2, label='', label_offset=(0.15, 0), color=C_ARROW):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.8))
    if label:
        mx, my = (x1+x2)/2 + label_offset[0], (y1+y2)/2 + label_offset[1]
        ax.text(mx, my, label, fontsize=6, color=color, style='italic')

# Title
ax.text(5.0, 8.2, 'SENTINEL Simulation Loop & Signal Detection', ha='center',
        fontsize=11, fontweight='bold', color='#1E293B')

# ── Main loop column (left side) ──
# Step 1: Timer
draw_rect(1.5, 7.0, 2.5, 0.7, C_TIMER, 'Tick Timer\n(Δt = 10 ms)', fontsize=8)

# Step 2: Agent Collection
draw_rect(1.5, 5.8, 2.5, 0.7, C_AGENT, 'Collect Orders\nfrom 40 Agents', fontsize=8)
arrow(2.75, 7.0, 2.75, 6.5, '')

# Step 3: Matching Engine
draw_rect(1.5, 4.6, 2.5, 0.7, C_STEP, 'Matching Engine\n(Price-Time Priority)', fontsize=8)
arrow(2.75, 5.8, 2.75, 5.3, '')

# Step 4: Fills distributed
draw_rect(1.5, 3.4, 2.5, 0.7, C_STEP, 'Distribute Fill\nNotifications', fontsize=8)
arrow(2.75, 4.6, 2.75, 4.1, '')

# Step 5: Snapshot
draw_rect(1.5, 2.2, 2.5, 0.7, C_STEP, 'Snapshot LOB\nState', fontsize=8)
arrow(2.75, 3.4, 2.75, 2.9, '')

# Loop-back arrow
ax.annotate('', xy=(0.8, 7.35), xytext=(0.8, 2.55),
            arrowprops=dict(arrowstyle='->', color=C_TIMER, lw=1.5,
                           connectionstyle="arc3,rad=0.3"))
ax.text(0.15, 4.9, 'next\ntick', fontsize=6, color=C_TIMER, fontweight='bold', ha='center')

# ── Decision diamond: every 5th tick? ──
draw_diamond(5.5, 4.95, 0.35, C_PRED, '5th\ntick?', fontsize=6)
arrow(4.0, 4.95, 4.65, 4.95, '', (0.05, 0.12))
ax.text(4.2, 5.15, 'snapshot', fontsize=6, color=C_ARROW, style='italic')

# Yes branch → Prediction Layer
draw_rect(6.5, 5.8, 2.8, 0.7, C_PRED, 'Prediction Layer\n(every 50 ms)', fontsize=8)
arrow(5.5, 5.3, 7.9, 5.8, 'Yes', (0.2, 0.1), color=C_PRED)

# Prediction sub-items
draw_rect(6.6, 4.9, 1.2, 0.55, '#065F46', 'Liquidity\nShock', fontsize=6.5)
draw_rect(8.0, 4.9, 1.2, 0.55, '#065F46', 'Large Order\nDetect', fontsize=6.5)
arrow(7.9, 5.8, 7.2, 5.45, '', color=C_PRED)
arrow(7.9, 5.8, 8.6, 5.45, '', color=C_PRED)

# No branch → straight to WebSocket
ax.text(5.7, 4.45, 'No', fontsize=6, color=C_ARROW, fontweight='bold')
arrow(5.5, 4.6, 5.5, 3.6, '', color=C_ARROW)

# ── WebSocket Broadcast ──
draw_rect(4.5, 2.2, 4.5, 0.7, C_WS, 'WebSocket Broadcast (20 Hz)\nMarket State + Signals', fontsize=8)

# Prediction → WebSocket
arrow(7.9, 4.9, 6.75, 2.9, 'signals', (0.15, 0.1), color=C_PRED)

# No → WebSocket
arrow(5.5, 3.05, 6.75, 2.9, '', color=C_ARROW)

# ── Dashboard ──
draw_rect(4.5, 0.8, 4.5, 0.7, C_WS, 'Next.js Dashboard\n(6 Live Panels)', fontsize=8)
arrow(6.75, 2.2, 6.75, 1.5, '', color=C_WS)

# Agent latency annotations
agents_info = [
    ('HFT: ~0.1 ms', 4.7, 7.4),
    ('MM: ~0.5 ms', 4.7, 7.1),
    ('Retail: 10–100 ms', 4.7, 6.8),
    ('Sentiment: ~50 ms', 4.7, 6.5),
]
for label, x, y in agents_info:
    ax.text(x, y, label, fontsize=5.5, color='#6B7280', style='italic')

# Latency box
lat_box = FancyBboxPatch((4.4, 6.3), 2.0, 1.3, boxstyle="round,pad=0.08",
                          facecolor='#F1F5F9', edgecolor='#94A3B8', linewidth=0.8)
ax.add_patch(lat_box)
ax.text(5.4, 7.45, 'Agent Latency Jitter', fontsize=6.5, color='#475569', fontweight='bold', ha='center')

plt.tight_layout(pad=0.3)
plt.savefig('figures/fig_workflow.pdf', bbox_inches='tight', dpi=300)
plt.savefig('figures/fig_workflow.png', bbox_inches='tight', dpi=300)
print("✓ fig_workflow.pdf generated")
