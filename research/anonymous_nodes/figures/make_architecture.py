"""Architecture figure for METHODOLOGY.md / the Tsoru doc -> figures/architecture.png"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

fig, ax = plt.subplots(figsize=(10, 5.6), dpi=200)
ax.set_xlim(0, 10); ax.set_ylim(0, 5.6); ax.axis("off")
EDGE, ACC, INK, MUTED = "#555555", "#2b6cb0", "#111111", "#666666"

def box(x, y, w, h, title, sub=None, fill="white", ec=EDGE, lw=1.1, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=ec, lw=lw))
    if sub:
        ax.text(x + w/2, y + h*0.64, title, ha="center", va="center", fontsize=8.6, weight="bold" if bold else "normal", color=INK)
        ax.text(x + w/2, y + h*0.30, sub, ha="center", va="center", fontsize=7, color=MUTED, linespacing=1.15)
    else:
        ax.text(x + w/2, y + h/2, title, ha="center", va="center", fontsize=8.6, weight="bold" if bold else "normal", color=INK)

def arrow(x1, y1, x2, y2, label=None, color=EDGE):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=color, lw=1.1, shrinkA=0, shrinkB=0))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2 + 0.09, label, ha="center", va="bottom", fontsize=6.8, color=MUTED)

ax.text(0.1, 5.38, "A description becomes a KB query; the number of answers decides what we emit",
        fontsize=10.5, weight="bold", color=INK)

# Row 1
y1, h = 4.05, 0.9
box(0.1, y1, 1.75, h, "Text + context", "sentence, topic,\nprevious sentence", fill="#f4f4f4")
box(2.25, y1, 1.75, h, "M1 Detect & parse", "unnamed mention ->\nDescription IR")
box(4.4, y1, 1.75, h, "M2 Resolve anchor", "link / coref, in-text first /\nrecurse if nested")
box(6.55, y1, 1.75, h, "M3 Map relations", "phrase -> property path\n+ gender, ordinal, time")
for xa, xb in ((1.85, 2.25), (4.0, 4.4), (6.15, 6.55)):
    arrow(xa, y1 + h/2, xb, y1 + h/2)

# Row 2
y2 = 2.25
box(0.1, y2, 1.9, h, "M4 Compile query", "IR -> SPARQL dialect\nvia adapter")
box(2.35, y2, 2.3, h, "M5 Execute & normalise", "containment, conventions,\nsameAs, type filter")
# M3 -> M4, routed above the outcome boxes
ax.plot([7.425, 7.425, 1.05, 1.05], [y1, 3.85, 3.85, 3.6], color=EDGE, lw=1.1)
arrow(1.05, 3.6, 1.05, y2 + h)
arrow(2.0, y2 + h/2, 2.35, y2 + h/2)
cx, cy = 5.4, y2 + h/2
ax.add_patch(Polygon([[cx-0.65, cy], [cx, cy+0.52], [cx+0.65, cy], [cx, cy-0.52]], closed=True, fc="white", ec=EDGE, lw=1.1))
ax.text(cx, cy+0.06, "M6 Decide", ha="center", va="center", fontsize=8.4, weight="bold", color=INK)
ax.text(cx, cy-0.17, "answer count", ha="center", va="center", fontsize=6.8, color=MUTED)
arrow(4.65, cy, cx-0.65, cy)
ox, ow, oh, bus = 6.95, 2.98, 0.4, 6.3
outs = [("GROUNDED: entity IRI", "exactly 1", ACC, "#e8f0fa"),
        ("AMBIGUOUS: anon. node + candidates", "2 or more", EDGE, "white"),
        ("MISSING FACT: anon. node + gap tag", "0 answers", EDGE, "white"),
        ("UNRESOLVED: anon. node, no claim", "unmapped", EDGE, "white")]
oys = [3.2, 2.7, 2.2, 1.7]
ax.plot([cx+0.65, bus], [cy, cy], color=EDGE, lw=0.9)
ax.plot([bus, bus], [oys[-1] + oh/2, oys[0] + oh/2], color=EDGE, lw=0.9)
for (t, lab, ec, fc), oy in zip(outs, oys):
    ax.add_patch(FancyBboxPatch((ox, oy), ow, oh, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.6 if ec == ACC else 1.1))
    ax.text(ox + ow/2, oy + oh/2, t, ha="center", va="center", fontsize=7.8, color=INK, weight="bold" if ec == ACC else "normal")
    arrow(bus, oy + oh/2, ox, oy + oh/2)
    ax.text(bus + 0.07, oy + oh/2 + 0.04, lab, ha="left", va="bottom", fontsize=6.2, color=MUTED)
# all outcomes -> M7
box(4.3, 0.95, 2.3, 0.6, "M7 Emit + verify", "triples + provenance; SPARQL gate")
ax.plot([ox + ow/2, ox + ow/2], [oys[-1], 1.25], color=EDGE, lw=1.1)
arrow(ox + ow/2, 1.25, 6.6, 1.25)
ax.text(ox + ow/2 + 0.07, 1.4, "every outcome", ha="left", va="center", fontsize=6.2, color=MUTED)

# adapter band
box(0.1, 0.12, 9.8, 0.62, "Ontology adapters - the only KB-specific code",
    "OntologyAdapter (properties, relation lexicon, containment, conventions)  |  EntityIndex  |  KBQuery  |  OutputWriter        Wikidata  -  DBpedia  -  (YAGO 4.5)",
    fill="#f4f4f4")
for x in (3.1, 5.2, 7.4, 1.05, 3.45):
    pass
ax.text(0.15, 0.8, "used by M2, M3, M4, M5, M7", fontsize=6.6, color=MUTED)
fig.savefig("figures/architecture.png", bbox_inches="tight", facecolor="white")
print("saved")
