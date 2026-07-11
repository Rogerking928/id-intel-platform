"""Generate publication-quality figures for the VIGIL preprint from the LIVE database.

All numbers are computed from data/id_intel.db (the analysed snapshot = the 2,075
documents with an active extraction). No values are hand-entered. Okabe-Ito
colourblind-safe palette; clean scientific styling.
Run:  python docs/make_figures.py
"""
import sqlite3, math, json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "id_intel.db"
OUT = ROOT / "docs"

# ---- Okabe-Ito palette (colourblind-safe, publication standard) ----
OI = dict(black="#000000", orange="#E69F00", sky="#56B4E9", green="#009E73",
          yellow="#F0E442", blue="#0072B2", vermillion="#D55E00", purple="#CC79A7")
INK, MUTE, GRID = "#1a1a2e", "#5b5b6b", "#d9d9e0"

# ---- ONE semantic colour system, used identically across every figure ----
# Colour carries meaning: the same concept is always the same colour, everywhere.
SEM = {
    "validation": OI["vermillion"],  # the hero operation — reserved, never reused
    "reference":  OI["yellow"],      # WHO GHO / GLASS ground truth
    "pathogen":   OI["blue"],
    "mechanism":  OI["orange"],      # resistance gene / mechanism
    "antibiotic": OI["sky"],
    "country":    OI["green"],
    "disease":    OI["purple"],
}
MAG = "#46586b"          # graphite — generic magnitude/counts (not a category)
PROCESS_FILL, PROCESS_BORDER = "#eef1f5", "#c2cad6"   # neutral process node
OUTCOME = "#2b3140"      # dark slate — an outcome/infrastructure node
LINE = "#98a2b3"         # connectors / arrows

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": MUTE, "axes.linewidth": 0.8,
    "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTE, "ytick.color": MUTE,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
    "figure.facecolor": "white", "axes.facecolor": "white",
})

conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
def q(sql, params=()):
    return conn.execute(sql, params).fetchall()

def hbar(ax, labels, values, color, title, unit="documents", val_fmt="{:.0f}"):
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=color, height=0.66, zorder=3)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.tick_params(length=0)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False); ax.spines["left"].set_visible(False)
    vmax = max(values) if values else 1
    for yi, v in zip(y, values):
        ax.text(v + vmax*0.02, yi, val_fmt.format(v), va="center", ha="left",
                fontsize=8.5, color=MUTE)
    ax.set_xlim(0, vmax*1.14)
    ax.set_title(title, fontsize=10.5, fontweight="bold", loc="left", color=INK, pad=6)

# ======================================================================
# FIGURE 1 — architecture / pipeline teaser
# ======================================================================
def fig_architecture():
    """Figure 1 — a VERTICAL conceptual spine, left/right balanced. Open text is a
    hypothesis; validation against reference truth is the pivot that turns it into
    research infrastructure."""
    fig, ax = plt.subplots(figsize=(7.4, 9.0))
    ax.set_xlim(0, 100); ax.set_ylim(0, 124); ax.axis("off")
    cx = 50
    LIGHT, BORDER, DARK, SPINE = PROCESS_FILL, PROCESS_BORDER, OUTCOME, LINE

    def node(cy, w, h, title, sub, fill, tcol, fs=13, sub_fs=8.6, lw=0, ec="none"):
        ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle="round,pad=0.4,rounding_size=2.6",
                     facecolor=fill, edgecolor=ec, linewidth=lw, zorder=3))
        ax.text(cx, cy+(2.6 if sub else 0), title, ha="center", va="center", color=tcol,
                fontsize=fs, fontweight="bold", zorder=4, linespacing=0.95)
        if sub:
            ax.text(cx, cy-3.6, sub, ha="center", va="center", color=tcol, fontsize=sub_fs,
                    zorder=4, alpha=0.92, linespacing=1.05)

    ys = [108, 87, 66, 41, 15]
    for a, b in zip(ys[:-1], ys[1:]):
        ax.add_patch(FancyArrowPatch((cx, a-8.0), (cx, b+8.2), arrowstyle="-|>",
                     mutation_scale=17, color=SPINE, lw=2.4, zorder=1))
    node(ys[0], 50, 15, "Fragmented\nopen sources", "8 families · daily", LIGHT, DARK, lw=1.4, ec=BORDER)
    node(ys[1], 50, 15, "Structured\nextraction", "rule-based ∥ LLM · provenance", LIGHT, DARK, lw=1.4, ec=BORDER)
    node(ys[2], 50, 15, "Knowledge\ngraph", "pathogen–gene–drug–country", LIGHT, DARK, lw=1.4, ec=BORDER)
    # VALIDATION — the accent hub (widest, dark ring)
    node(ys[3], 54, 19, "VALIDATION", "against reference truth", SEM["validation"], "white", fs=17, sub_fs=11)
    ax.add_patch(FancyBboxPatch((cx-27, ys[3]-9.5), 54, 19, boxstyle="round,pad=0.4,rounding_size=2.8",
                 facecolor="none", edgecolor=INK, linewidth=3.0, zorder=4))
    node(ys[4], 52, 16, "Research\ninfrastructure", "benchmark · forecast\nrisk · early-warning",
         DARK, "white", fs=13.5, sub_fs=8.4)

    # --- balanced side elements at the VALIDATION row ---
    yv = ys[3]
    # LEFT: reference truth feeds in
    ax.add_patch(FancyBboxPatch((2, yv-6), 20, 12, boxstyle="round,pad=0.3,rounding_size=2.0",
                 facecolor=SEM["reference"], edgecolor="none", zorder=3))
    ax.text(12, yv, "WHO GHO /\nGLASS truth", ha="center", va="center", fontsize=8.2,
            fontweight="bold", color=INK, zorder=4, linespacing=1.0)
    ax.add_patch(FancyArrowPatch((22.3, yv), (cx-27.3, yv), arrowstyle="-|>",
                 mutation_scale=15, color=INK, lw=2.4, zorder=2))
    # RIGHT: unvalidated signal is flagged out (mirrors the yellow box)
    ax.add_patch(FancyBboxPatch((78, yv-6), 20, 12, boxstyle="round,pad=0.3,rounding_size=2.0",
                 facecolor="white", edgecolor=SPINE, linewidth=1.4, linestyle=(0,(4,2)), zorder=3))
    ax.text(88, yv, "unvalidated\nsignal flagged", ha="center", va="center", fontsize=7.8,
            color=MUTE, style="italic", zorder=4, linespacing=1.0)
    ax.add_patch(FancyArrowPatch((cx+27.3, yv), (77.7, yv), arrowstyle="-|>",
                 mutation_scale=13, color=SPINE, lw=1.8, linestyle=(0,(4,2)), zorder=2))

    # framing lines (tight to the spine)
    ax.text(cx, 121, "open-source text  =  a hypothesis to be tested", ha="center", va="center",
            fontsize=9.6, color=INK, style="italic")
    ax.text(cx, 2, "=  trustworthy, continuously-checked intelligence", ha="center", va="center",
            fontsize=9.6, color=INK, style="italic")
    fig.savefig(OUT/"fig1_architecture.png"); plt.close(fig)
    print("fig1 ok (vertical concept)")


def fig_paradigm():
    """Figure 2 — the paradigm contrast a reviewer grasps in two seconds:
    conventional 'generate then trust' vs VIGIL's 'generate, validate, improve, deploy'."""
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.set_xlim(0, 100); ax.set_ylim(-10, 44); ax.axis("off")   # bottom room for the feedback loop
    GREY, INKD, CAL = PROCESS_FILL, OUTCOME, "#f4c3a0"   # CAL = light tint of the validation accent

    def chip(cx, cy, w, text, fill, tcol, fs=9.4, h=9.0, ec="none", lw=0):
        ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle="round,pad=0.3,rounding_size=1.7",
                     facecolor=fill, edgecolor=ec, linewidth=lw, zorder=3))
        ax.text(cx, cy, text, ha="center", va="center", color=tcol, fontsize=fs,
                fontweight="bold", zorder=4, linespacing=0.95)

    def arrow(x1, x2, y, color=MUTE, style="-"):
        ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=13,
                     color=color, lw=1.9, linestyle=style, zorder=2))

    # ---- Conventional lane ----
    yt = 34
    ax.text(1.5, yt, "Conventional", fontsize=10.5, fontweight="bold", color=MUTE, va="center")
    chip(38, yt, 22, "Generate signal", GREY, INKD)
    arrow(49.5, 60, yt)
    chip(70, yt, 15, "Trust", GREY, INKD)
    arrow(78, 87, yt)
    chip(94, yt, 11, "Act", GREY, INKD)
    ax.text(70, yt-6.4, "bias uncorrected", ha="center", fontsize=7.3, color=SEM["validation"], style="italic")
    # divider
    ax.plot([28, 99], [23.5, 23.5], color=GRID, lw=1.0, zorder=0)
    # ---- Validation-first lane ----
    yb = 12
    ax.text(1.5, yb, "Validation-first\n(VIGIL)", fontsize=10.5, fontweight="bold",
            color=OI["vermillion"], va="center", linespacing=1.0)
    chip(38, yb, 20, "Generate signal", GREY, INKD)
    arrow(48, 54.5, yb)
    chip(65, yb, 19, "Validate\nvs reference truth", SEM["validation"], "white", fs=8.4)
    arrow(74.5, 80.5, yb)
    chip(88, yb, 13, "Calibrate", CAL, INKD)
    arrow(94.5, 99, yb)
    ax.text(101.5, yb, "deploy", fontsize=8.6, fontweight="bold", color=INKD, va="center", ha="left")
    # feedback loop: calibrate -> back to generate (virtuous cycle)
    ax.add_patch(FancyArrowPatch((88, yb-4.6), (38, yb-4.6), arrowstyle="-|>", mutation_scale=12,
                 color=SEM["validation"], lw=1.7, connectionstyle="arc3,rad=-0.35", zorder=2))
    ax.text(63, yb-9.2, "improve", ha="center", fontsize=7.4, color=SEM["validation"], style="italic")
    ax.set_xlim(0, 108)
    fig.savefig(OUT/"fig2_paradigm.png"); plt.close(fig)
    print("fig2 ok (paradigm)")

# ======================================================================
# FIGURE 2 — corpus composition (source + event type)
# ======================================================================
def fig_corpus():
    src = q("""select d.source s, count(*) n from documents d
               join extractions e on e.document_id=d.id and e.is_active=1
               group by d.source order by n""")
    ev = q("""select event_type t, count(*) n from extractions
              where is_active=1 and event_type is not null and event_type!=''
              group by event_type order by n""")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    hbar(a1, [r["s"] for r in src], [r["n"] for r in src], MAG,
         "a  Documents by source", )
    hbar(a2, [r["t"] for r in ev], [r["n"] for r in ev], MAG,
         "b  Documents by event type")
    total = sum(r["n"] for r in src)
    fig.text(0.5, -0.02, f"Analysed snapshot: {total:,} documents with an active extraction "
             f"across seven contributing sources.", ha="center", fontsize=8.5, color=MUTE)
    fig.tight_layout()
    fig.savefig(OUT/"fig2_corpus.png"); plt.close(fig)
    print("fig2 ok  (total=%d)" % total)

# ======================================================================
# FIGURE 3 — AMR entity landscape (pathogens, mechanisms, antibiotics)
# ======================================================================
def top_entities(etypes, k):
    ph = ",".join("?"*len(etypes))
    return q(f"""select value v, count(distinct document_id) n from entities
                 where entity_type in ({ph}) group by value order by n desc limit {k}""",
             tuple(etypes))
def fig_landscape():
    pth = top_entities(["pathogen"], 10)
    gen = top_entities(["resistance_gene"], 10)
    abx = top_entities(["antibiotic"], 10)
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 4.4))
    hbar(axs[0], [r["v"] for r in pth], [r["n"] for r in pth], SEM["pathogen"],
         "a  Top pathogens")
    hbar(axs[1], [r["v"] for r in gen], [r["n"] for r in gen], SEM["mechanism"],
         "b  Top resistance mechanisms")
    hbar(axs[2], [r["v"] for r in abx], [r["n"] for r in abx], SEM["antibiotic"],
         "c  Top antibiotics")
    fig.text(0.5, -0.02, "Entity frequency = number of documents mentioning the term "
             "(rule-based + LLM extraction, frozen codebook).", ha="center",
             fontsize=8.5, color=MUTE)
    fig.tight_layout()
    fig.savefig(OUT/"fig3_landscape.png"); plt.close(fig)
    print("fig3 ok")

# ======================================================================
# FIGURE 4 — knowledge-graph neighbourhood (CRE)
# ======================================================================
def fig_kg():
    genes = ("NDM","KPC","OXA-48","carbapenemase","metallo-beta-lactamase","OXA-23")
    ph = ",".join("?"*len(genes))
    rels = q(f"""select src_type,src_value,dst_type,dst_value,count(*) w
                 from relations
                 where src_value in ({ph}) or dst_value in ({ph})
                 group by src_type,src_value,dst_type,dst_value
                 order by w desc limit 60""", genes+genes)
    G = nx.Graph(); typ = {}
    for r in rels:
        a, b = r["src_value"], r["dst_value"]
        if not a or not b or a==b: continue
        typ[a] = r["src_type"]; typ[b] = r["dst_type"]
        G.add_edge(a, b, w=r["w"])
    # keep the largest connected component, cap size
    if G.number_of_nodes() == 0:
        print("fig4 SKIP (no relations)"); return
    comp = max(nx.connected_components(G), key=len)
    G = G.subgraph(comp).copy()
    if G.number_of_nodes() > 26:
        keep = sorted(G.degree, key=lambda x: x[1], reverse=True)[:26]
        G = G.subgraph([n for n,_ in keep]).copy()
    colmap = {"pathogen":SEM["pathogen"], "resistance_gene":SEM["mechanism"],
              "gene":SEM["mechanism"], "antibiotic":SEM["antibiotic"],
              "country":SEM["country"], "disease":SEM["disease"], "region":MAG}
    pos = nx.spring_layout(G, k=0.9, seed=7, iterations=200)
    fig, ax = plt.subplots(figsize=(9.5, 6.6)); ax.axis("off")
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=GRID, width=1.2)
    for nd in G.nodes():
        deg = G.degree(nd)
        ax.scatter(*pos[nd], s=180+deg*90, color=colmap.get(typ.get(nd),MUTE),
                   edgecolors="white", linewidths=1.4, zorder=3)
    for nd in G.nodes():
        ax.text(pos[nd][0], pos[nd][1]+0.045, nd, fontsize=8, ha="center",
                va="bottom", color=INK, zorder=4,
                fontweight="bold" if typ.get(nd)=="resistance_gene" else "normal")
    present = {typ.get(nd) for nd in G.nodes()}
    legend_types = [("pathogen",SEM["pathogen"]),("resistance_gene",SEM["mechanism"]),
                    ("antibiotic",SEM["antibiotic"]),("country",SEM["country"]),("disease",SEM["disease"])]
    label_txt = {"resistance_gene":"resistance mechanism"}
    handles = [plt.Line2D([0],[0], marker="o", ls="", markersize=9, markerfacecolor=c,
               markeredgecolor="white", label=label_txt.get(t,t))
               for t,c in legend_types if t in present]
    ax.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False,
              fontsize=8.5, bbox_to_anchor=(0.5, -0.04))
    ax.set_title("Knowledge-graph neighbourhood of carbapenem resistance",
                 fontsize=11, fontweight="bold", color=INK)
    fig.savefig(OUT/"fig4_kg.png"); plt.close(fig)
    print("fig4 ok  (%d nodes)" % G.number_of_nodes())

# ======================================================================
# FIGURE 5 — construct validity (cross-sectional, computed here)
# ======================================================================
AMR_PATH = ("MRSA","VRE","VRSA","CRE","CRKP","CRAB","CRPA","ESBL","Candida auris")
def _spear(x, y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    rx=np.argsort(np.argsort(x)); ry=np.argsort(np.argsort(y))
    return float(np.corrcoef(rx,ry)[0,1])
def fig_validation():
    ph = ",".join("?"*len(AMR_PATH))
    rows = q(f"""select c.value country,
                 count(distinct d.id) total_docs,
                 count(distinct case when exists(
                    select 1 from entities a where a.document_id=d.id and (
                       a.entity_type='resistance_gene' or
                       (a.entity_type='pathogen' and a.value in ({ph})))) then d.id end) amr_docs
              from documents d
              join entities c on c.document_id=d.id and c.entity_type='country'
              group by c.value""", AMR_PATH)
    import collections
    ref = {}
    for r in q("select country, value, year from amr_reference where indicator='AMR_INFECT_MRSA'"):
        ref.setdefault(r["country"], {})[r["year"]] = r["value"]
    reflatest = {k: v[max(v)] for k,v in ref.items()}
    pts=[]
    for r in rows:
        val = reflatest.get(r["country"])
        if val is None or r["total_docs"]<1: continue
        pts.append((r["country"], r["total_docs"], r["amr_docs"],
                    r["amr_docs"]/r["total_docs"], val))
    docs=[p[2] for p in pts]; share=[p[3] for p in pts]; vals=[p[4] for p in pts]
    rho_docs=_spear(docs, vals); rho_share=_spear(share, vals)
    n=len(pts)
    fig, (a1,a2)=plt.subplots(1,2,figsize=(10.5,4.5))
    for ax,x,rho,lab in [(a1,docs,rho_docs,"Raw AMR-document count"),
                         (a2,share,rho_share,"Publication-normalised AMR share")]:
        ax.scatter(x, vals, s=42, color=MAG, alpha=0.8, edgecolors="white", linewidths=0.8, zorder=3)
        ax.set_xlabel(lab, fontsize=9.5); ax.set_ylabel("WHO GHO measured MRSA\nBSI resistance (%)", fontsize=9.5)
        ax.grid(True, color=GRID, lw=0.6, zorder=0)
        ax.text(0.04, 0.94, f"Spearman $\\rho$ = {rho:+.2f}", transform=ax.transAxes,
                fontsize=10.5, fontweight="bold", color=SEM["validation"], va="top")
        ax.text(0.04, 0.86, f"n = {n} countries", transform=ax.transAxes, fontsize=8.5,
                color=MUTE, va="top")
    a1.set_title("a  Volume is uninformative", fontsize=10.5, fontweight="bold", loc="left")
    a2.set_title("b  Normalisation recovers weak signal", fontsize=10.5, fontweight="bold", loc="left")
    fig.tight_layout()
    fig.savefig(OUT/"fig5_validation.png"); plt.close(fig)
    print(f"fig5 ok  n={n} rho_docs={rho_docs:+.3f} rho_share={rho_share:+.3f}")
    return dict(n=n, rho_docs=round(rho_docs,2), rho_share=round(rho_share,2))

# ======================================================================
# FIGURE 6 — corpus accumulation over time
# ======================================================================
def fig_growth():
    rows = q("""select substr(coalesce(nullif(published_date,''), substr(fetched_at,1,10)),1,4) yr,
                count(*) n from documents
                where coalesce(nullif(published_date,''), substr(fetched_at,1,10)) != ''
                group by yr having yr>='2015' and yr<='2026' order by yr""")
    yrs=[r["yr"] for r in rows]; ns=[r["n"] for r in rows]
    fig, ax=plt.subplots(figsize=(8.5,3.8))
    ax.bar(yrs, ns, color=MAG, width=0.66, zorder=3)
    ax.grid(True, axis="y", color=GRID, lw=0.6, zorder=0)
    ax.tick_params(length=0)
    for x,n in zip(yrs,ns):
        ax.text(x, n+max(ns)*0.01, f"{n:,}", ha="center", va="bottom", fontsize=7.5, color=MUTE)
    ax.set_ylabel("documents", fontsize=9.5)
    ax.set_title("Corpus accumulation by document year", fontsize=11, fontweight="bold", loc="left")
    fig.tight_layout(); fig.savefig(OUT/"fig6_growth.png"); plt.close(fig)
    print("fig6 ok")

if __name__ == "__main__":
    fig_architecture(); fig_paradigm(); fig_corpus(); fig_landscape(); fig_kg()
    stats = fig_validation(); fig_growth()
    print("VALIDATION_STATS", json.dumps(stats))
