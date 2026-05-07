"""
Generate the SENTINEL system architecture diagram.
Produces a layered architecture figure showing the five cooperating layers.
Output: figures/fig_architecture.pdf
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, ax = plt.subplots(figsize=(8.5, 6.0), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.5)
ax.axis('off')

# Color palette
C_SIM = '#2563EB'       # blue
C_MATCH = '#7C3AED'     # purple
C_PRED = '#059669'      # green
C_BACK = '#D97706'      # amber
C_FRONT = '#DC2626'     # red
C_AGENT = '#3B82F6'     # light blue
C_BG = '#F8FAFC'
C_ARROW = '#475569'

# Helper: rounded box
def draw_box(x, y, w, h, color, label, fontsize=9, alpha=0.85):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                         facecolor=color, edgecolor='white',
                         linewidth=1.5, alpha=alpha)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, label, ha='center', va='center',
            fontsize=fontsize, color='white', fontweight='bold',
            wrap=True)

def draw_box_dark(x, y, w, h, color, label, fontsize=7.5, alpha=0.75):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                         facecolor=color, edgecolor=color,
                         linewidth=0.8, alpha=alpha)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, label, ha='center', va='center',
            fontsize=fontsize, color='white', fontweight='normal')

# ── Layer 1: Frontend (top) ──
draw_box(0.5, 6.2, 9.0, 0.9, C_FRONT, 
         'Frontend Layer — Next.js 14 + TypeScript Terminal Dashboard', fontsize=9.5)

# Dashboard panels
panels = ['LOB\nHeatmap', 'Price\nChart', 'Liquidity\nGauge', 'Trade\nTape', 'Agent\nEquity', 'Alert\nFeed']
pw = 1.35
for i, p in enumerate(panels):
    draw_box_dark(0.7 + i*1.48, 5.45, pw, 0.6, '#EF4444', p, fontsize=6.5)

# ── Layer 2: Backend ──
draw_box(0.5, 4.2, 9.0, 0.9, C_BACK,
         'Backend Layer — FastAPI (REST + WebSocket @ 20 Hz)', fontsize=9.5)

# Backend sub-items
backs = ['REST API', 'WebSocket\nFan-out', 'CORS', 'Lifecycle\nMgmt']
for i, b in enumerate(backs):
    draw_box_dark(1.0 + i*2.1, 3.55, 1.8, 0.5, '#B45309', b, fontsize=6.5)

# ── Layer 3: Prediction ──
draw_box(5.3, 2.0, 4.2, 1.2, C_PRED,
         '', fontsize=9)
ax.text(7.4, 2.95, 'Prediction Layer', ha='center', va='center',
        fontsize=9, color='white', fontweight='bold')
# Sub boxes
draw_box_dark(5.5, 2.15, 1.85, 0.55, '#047857', 'Liquidity Shock\nPredictor (RF+XGB)', fontsize=6)
draw_box_dark(7.55, 2.15, 1.8, 0.55, '#047857', 'Large Order\nDetector (Z-score)', fontsize=6)

# ── Layer 4: Matching Engine ──
draw_box(2.5, 2.0, 2.5, 1.2, C_MATCH,
         '', fontsize=9)
ax.text(3.75, 2.95, 'Matching Engine', ha='center', va='center',
        fontsize=9, color='white', fontweight='bold')
draw_box_dark(2.65, 2.15, 2.15, 0.55, '#6D28D9', 'Price-Time Priority\nLOB (O(log n))', fontsize=6)

# ── Layer 5: Simulation Layer (bottom) ──
draw_box(0.5, 0.15, 9.0, 1.5, C_SIM,
         '', fontsize=9)
ax.text(5.0, 1.35, 'Simulation Layer — 10 Agent Archetypes (40 Agents)', ha='center', va='center',
        fontsize=9.5, color='white', fontweight='bold')

agents = ['MM\n×3', 'HFT\n×2', 'INST\n×2', 'RET\n×10', 'INF\n×3', 
          'NOISE\n×10', 'MOM\n×2', 'MR\n×2', 'SPOOF\n×1', 'SENT\n×5']
aw = 0.82
for i, a in enumerate(agents):
    draw_box_dark(0.65 + i*0.9, 0.3, aw, 0.75, '#1D4ED8', a, fontsize=5.5)

# ── Arrows ──
arrow_style = "Simple,tail_width=1.5,head_width=8,head_length=5"

# Simulation → Matching Engine
ax.annotate('', xy=(3.75, 2.0), xytext=(3.75, 1.65),
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(4.3, 1.78, 'orders', fontsize=6, color=C_ARROW, style='italic')

# Simulation → Prediction
ax.annotate('', xy=(7.0, 2.0), xytext=(7.0, 1.65),
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(7.35, 1.78, 'snapshots\n(50 ms)', fontsize=5.5, color=C_ARROW, style='italic')

# Matching → Backend
ax.annotate('', xy=(3.75, 3.55), xytext=(3.75, 3.2),
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))

# Prediction → Backend
ax.annotate('', xy=(7.4, 3.55), xytext=(7.4, 3.2),
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(7.8, 3.35, 'signals', fontsize=6, color=C_ARROW, style='italic')

# Backend → Frontend
ax.annotate('', xy=(5.0, 5.45), xytext=(5.0, 5.1),
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(5.35, 5.22, 'WebSocket\n@ 20 Hz', fontsize=6, color=C_ARROW, style='italic')

# Every 50ms label
ax.text(0.65, 3.35, '50 ms\ncycle', fontsize=6, color=C_PRED, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.2', facecolor='#ECFDF5', edgecolor=C_PRED, alpha=0.8))

plt.tight_layout(pad=0.3)
plt.savefig('figures/fig_architecture.pdf', bbox_inches='tight', dpi=300)
plt.savefig('figures/fig_architecture.png', bbox_inches='tight', dpi=300)
print("✓ fig_architecture.pdf generated")
