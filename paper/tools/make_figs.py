"""Figures 2, 3, 4, and 6 of the camera-ready, drawn from the verified fact files (no hand-typed numbers)."""
import json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:  # print the tie-rule arrows at 0.82x instead of mathtext's default 0.7x so they stay readable
    import matplotlib._mathtext as _mt
    _mt.SHRINK_FACTOR = 0.82
except Exception:
    pass

FD, OUT = sys.argv[1], sys.argv[2]
_t1 = os.path.join(FD, 'T1_facts.json')
T = json.load(open(_t1 if os.path.exists(_t1) else os.path.join(FD, 't1', 'T1_facts.json'), encoding='utf-8'))
fam = 'Liberation Sans'
plt.rcParams.update({'font.family': fam, 'font.size': 8, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'axes.linewidth': 0.6,
                     'axes.spines.top': False, 'axes.spines.right': False, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
                     'hatch.linewidth': 0.6})
RED, TEAL, BLUE, GRAY = '#C84A5A', '#087F7B', '#3767B1', '#69717D'
CELLS = [('h2o', 0.2), ('h2o', 0.4), ('knorm', 0.2), ('knorm', 0.4), ('streaming', 0.2), ('streaming', 0.4)]
NAME = {'h2o': 'H2O', 'knorm': 'Knorm', 'streaming': 'Stream.'}


def cell_sum(arm, s, r, rule='up'):
    return sum(c[rule]['reversal'] for c in T['ih_cells'] if c['arm'] == arm and c['scorer'] == s and abs(c['ratio'] - r) < 1e-9)


fig = plt.figure(figsize=(6.3, 2.4))
# Column layout in points (the figure is printed at \textwidth = 453.6pt): each gap is sized for the row labels it holds.
FW = 6.3 * 72
COLS = {'a': (53, 112), 'b': (205, 78), 'c1': (338, 40), 'c2': (392, 54)}  # left edge, width
def panel(key):
    x0, w = COLS[key]
    return fig.add_axes([x0 / FW, 0.3, w / FW, 0.585])

# ---- (a) reversals per compressor and budget (same row grammar as panels b and c)
ax = panel('a')
ROWS_A = [('streaming', 0.2), ('streaming', 0.4), ('knorm', 0.2), ('knorm', 0.4), ('h2o', 0.2), ('h2o', 0.4)]
base = [cell_sum('base', s, r) for s, r in ROWS_A]
rp = [cell_sum('rpstrict', s, r) for s, r in ROWS_A]
full = [cell_sum('full', s, r) for s, r in ROWS_A]
assert sum(base) == T['ih_totals']['all|base']['reversal_up'] and sum(rp) == T['ih_totals']['all|rpstrict']['reversal_up']
assert all(v == 0 for v in full)  # the note inside the panel states this
ya = list(range(len(ROWS_A)))[::-1]; hb = 0.36
ax.barh([y + hb / 2 for y in ya], base, hb, color='white', edgecolor=RED, hatch='////', linewidth=0.8, label='Official compressor')
ax.barh([y - hb / 2 for y in ya], rp, hb, color=BLUE, edgecolor=BLUE, linewidth=0.8, label='+AuthorityKV, roles\n+ provenance')
for y, b0, r0 in zip(ya, base, rp):
    ax.text(b0 + 16, y + hb / 2, f'{b0:,}', ha='left', va='center', fontsize=6.8, color=RED)
    ax.text(r0 + 16, y - hb / 2 - 0.02, f'{r0:,}', ha='left', va='center', fontsize=6.8, color=BLUE)
ax.set_yticks(ya); ax.set_yticklabels([f'{NAME[s]} {int(r*100)}%' for s, r in ROWS_A])
ax.set_xlim(0, 1480); ax.set_xticks([0, 400, 800, 1200]); ax.set_xlabel('Reversals (of 1,200)')
ax.set_ylim(-0.6, len(ROWS_A) - 0.4)
from matplotlib.patches import Patch
hs, ls = ax.get_legend_handles_labels()
hs.append(Patch(facecolor=TEAL, edgecolor=TEAL, linewidth=0.8)); ls.append('+ span boundaries:\n0 in every row')
ax.legend(hs, ls, frameon=False, fontsize=6.8, loc='lower right', bbox_to_anchor=(1.0, 0.0), handlelength=1.3, borderaxespad=0.0,
          labelspacing=0.45, handletextpad=0.5)
ax.set_title('(a) IH-CacheBench', loc='left', fontsize=8.5, fontweight='bold', pad=4)
ax.tick_params(axis='y', length=0)

# ---- (b) System-IFEval dumbbells: one row per compressor, filled marker for R-up and open marker for R-down
ax = panel('b')
SB = ['streaming', 'knorm', 'h2o']
for i, sc in enumerate(SB):
    for rule, off in [('R↑', 0.19), ('R↓', -0.19)]:
        d = T['sys'][f'{sc}|{rule}']; b0, a0 = d['base_gated'][0], d['akv_gated'][0]
        assert d['base_gated'][1] == 88 and d['akv_gated'][1] == 88
        y = len(SB) - 1 - i + off
        ax.plot([b0, a0], [y, y], color=GRAY, lw=1.6, alpha=0.55, zorder=1)
        ax.scatter([b0], [y], marker='x', s=26, color=RED, linewidths=1.3, zorder=3)
        ax.scatter([a0], [y], marker='o', s=30, color=TEAL if rule == 'R↑' else 'white', edgecolor=TEAL, linewidths=1.2, zorder=3)
        ax.text(b0 - 5.5, y, str(b0), ha='right', va='center', fontsize=7, color=RED)
        ax.text(a0 + 5.5, y, str(a0), ha='left', va='center', fontsize=7, color=TEAL)
ax.set_yticks(range(len(SB))[::-1]); ax.set_yticklabels([NAME[sc] for sc in SB])
ax.set_xlim(-12, 100); ax.set_xticks([0, 22, 44, 66, 88]); ax.set_xlabel('Prompts satisfied (of 88)')
ax.set_ylim(-0.6, len(SB) - 0.4)
ax.set_title('(b) System-IFEval', loc='left', fontsize=8.5, fontweight='bold', pad=4)
ax.tick_params(axis='y', length=0)
from matplotlib.lines import Line2D
h = [Line2D([], [], marker='x', color=RED, ls='', ms=5, mew=1.2, label='Official compressor'),
     Line2D([], [], marker='o', color=TEAL, ls='', ms=5, label=r'+AuthorityKV, R$_{\!\uparrow}$'),
     Line2D([], [], marker='o', mfc='white', mec=TEAL, ls='', ms=5, label=r'+AuthorityKV, R$_{\!\downarrow}$')]
fig.legend(handles=h, frameon=False, fontsize=7.4, loc='lower center', bbox_to_anchor=(0.705, -0.012), ncol=3, handletextpad=0.1, columnspacing=1.4, borderaxespad=0.2)

# ---- (c) LongBench + injection: attacks and joint
M = T['mixed']
rows = [('streaming', 0.2), ('streaming', 0.4), ('knorm', 0.4)]
for j, (key, title, xl, lim, ticks) in enumerate([('attack', '(c) Attacks', 'of 64', (-2.8, 10.2), [0, 4, 8]), ('joint', 'Safe+correct', 'of 64', (34, 68), [40, 52, 64])]):
    ax = panel('c1' if j == 0 else 'c2')
    yy = []
    for i, (s, r) in enumerate(rows):
        for k, off in [('up', 0.19), ('dn', -0.19)]:
            y = len(rows) - 1 - i + off
            b0 = M[f'{s}|{r}|explicit_attack|base'][k][key]; a0 = M[f'{s}|{r}|explicit_attack|full'][k][key]
            ax.plot([b0, a0], [y, y], color=GRAY, lw=1.6, alpha=0.55, zorder=1)
            ax.scatter([b0], [y], marker='x', s=22, color=RED, linewidths=1.2, zorder=3)
            ax.scatter([a0], [y], marker='o', s=26, color=TEAL if k == 'up' else 'white', edgecolor=TEAL, linewidths=1.1, zorder=3)
            # value labels on the outer side of each marker, as in panel (b)
            gap = 1.05 if j == 0 else 2.3
            if a0 == b0:
                ax.text(a0 + 1.5 * gap, y, str(a0), ha='left', va='center', fontsize=6.6, color=GRAY)
            else:
                lo, hi = (a0, b0) if a0 < b0 else (b0, a0)
                lo_col, hi_col = (TEAL, RED) if a0 < b0 else (RED, TEAL)
                ax.text(lo - gap, y, str(lo), ha='right', va='center', fontsize=6.6, color=lo_col)
                ax.text(hi + gap, y, str(hi), ha='left', va='center', fontsize=6.6, color=hi_col)
    ax.set_yticks(range(len(rows))[::-1])
    ax.set_yticklabels([f'{NAME[s]} {int(r*100)}%' for s, r in rows] if j == 0 else [])
    ax.set_xlim(*lim); ax.set_xticks(ticks); ax.set_xlabel(xl); ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_title(title, loc='left', fontsize=8.5, fontweight='bold', pad=4)
    ax.tick_params(axis='y', length=0)
fig.savefig(os.path.join(OUT, 'fig2_results.pdf'), metadata={'CreationDate': None})  # no timestamp: reruns are byte-identical
fig.savefig(os.path.join(OUT, 'fig2_results.png'), dpi=220)
print('font', fam, 'base', base, 'rp', rp, 'full', full)

# ---------------------------------------------------------------- Figure 3: what the cache keeps (retention by span type)
R = {}
for line in open(os.path.join(FD, 'RESPONSE_FACTS.jsonl'), encoding='utf-8'):
    r = json.loads(line); R[r['id']] = r
spans = [('system', 'System prompt'), ('answer', 'Answer sentences'), ('question', 'Question'), ('injection', 'Injected note')]
fig, ax = plt.subplots(figsize=(3.03, 1.62))
fig.subplots_adjust(left=0.33, right=0.97, top=0.87, bottom=0.27)
h = 0.34
for i, (k, lab) in enumerate(spans):
    y = len(spans) - 1 - i
    b0 = float(R[f'A4-str40-para-base-{k}']['number']); a0 = float(R[f'A4-str40-para-full-{k}']['number'])
    ax.barh(y + h / 2, b0, h, color='white', edgecolor=RED, hatch='////', linewidth=0.8, label='Official StreamingLLM' if i == 0 else None)
    ax.barh(y - h / 2, a0, h, color=TEAL, edgecolor=TEAL, linewidth=0.8, label='+AuthorityKV' if i == 0 else None)
    ax.text(b0 + 0.02, y + h / 2 + 0.03, f'{b0:.2f}', va='center', ha='left', fontsize=6.8, color=RED)
    ax.text(a0 + 0.02, y - h / 2 - 0.04, f'{a0:.2f}', va='center', ha='left', fontsize=6.8, color=TEAL)
ax.set_yticks(range(len(spans))[::-1]); ax.set_yticklabels([s[1] for s in spans])
ax.set_xlim(0, 1.16); ax.set_xticks([0, 0.5, 1.0]); ax.set_xlabel('Fraction of span retained in the cache')
ax.tick_params(axis='y', length=0)
ax.legend(frameon=False, fontsize=6.8, loc='lower center', bbox_to_anchor=(0.36, 0.985), ncol=2, handlelength=1.3, columnspacing=1.0, borderaxespad=0)
fig.savefig(os.path.join(OUT, 'fig3_retention.pdf'), metadata={'CreationDate': None})
fig.savefig(os.path.join(OUT, 'fig3_retention.png'), dpi=220)


# ---------------------------------------------------------------- Appendix figure: reversals per cell along the metadata ladder
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
MODELS = [('qwen7b', 'Qwen2.5-7B'), ('mistral7b', 'Mistral-7B'), ('yi9b', 'Yi-1.5-9B')]
LADDER = [('base', 'Official'), ('rpstrict', 'Roles +\nprov.'), ('e3bdet', '+ Sent.\ndetector'), ('full', '+ Span\nbound.')]
ROWS = [('h2o', 0.2), ('h2o', 0.4), ('knorm', 0.2), ('knorm', 0.4), ('streaming', 0.2), ('streaming', 0.4)]
CID = {('h2o', 0.2): 'h2o20', ('h2o', 0.4): 'h2o40', ('knorm', 0.2): 'knorm20', ('knorm', 0.4): 'knorm40',
       ('streaming', 0.2): 'streaming20', ('streaming', 0.4): 'streaming40'}


def ih_value(model, arm, s, r):
    if arm == 'e3bdet':
        f = R[f'E3b-e3bdet-{model}-main-{CID[(s, r)]}-reversal']
        assert f['denominator'] == 400
        return int(f['number'])
    hits = [c for c in T['ih_cells'] if c['model'] == model and c['arm'] == arm and c['scorer'] == s and abs(c['ratio'] - r) < 1e-9]
    assert len(hits) == 1 and hits[0]['up']['conflict_n'] == 400
    return hits[0]['up']['reversal']


grid = {m: [[ih_value(m, arm, s, r) for arm, _ in LADDER] for s, r in ROWS] for m, _ in MODELS}
# the per-model sums are the per-model columns of Table 2
assert [sum(row[0] for row in grid[m]) for m, _ in MODELS] == [T['ih_totals'][f'{m}|base']['reversal_up'] for m, _ in MODELS]
assert [sum(row[1] for row in grid[m]) for m, _ in MODELS] == [T['ih_totals'][f'{m}|rpstrict']['reversal_up'] for m, _ in MODELS]
assert [sum(row[3] for row in grid[m]) for m, _ in MODELS] == [T['ih_totals'][f'{m}|full']['reversal_up'] for m, _ in MODELS]
cmap = LinearSegmentedColormap.from_list('akvred', ['#FFFFFF', '#F3C9CF', '#E08A96', RED, '#7E2533'])
norm = PowerNorm(gamma=0.5, vmin=0, vmax=400)
LADDER_NAMES = ['Official compressor', '+AuthorityKV, roles + provenance', '+ sentence detector', '+ span boundaries']
fig = plt.figure(figsize=(6.3, 1.62))
PW, PX = 95, [121, 238, 355]  # panel width and left edges in points
for k, (m, mname) in enumerate(MODELS):
    ax = fig.add_axes([PX[k] / FW, 0.06, PW / FW, 0.56])
    data = [[grid[m][i][j] for i in range(len(ROWS))] for j in range(len(LADDER))]  # rows: ladder, columns: cells
    ax.imshow(data, cmap=cmap, norm=norm, aspect='auto')
    for j, row in enumerate(data):
        for i, v in enumerate(row):
            ink = 'white' if v >= 150 else ('#1F2430' if v > 0 else '#8A919C')
            ax.text(i, j, f'{v}', ha='center', va='center', fontsize=6.8, color=ink)
    ax.set_xticks(range(len(ROWS))); ax.set_xticklabels([f'{int(r * 100)}' for _, r in ROWS], fontsize=6.6)
    ax.xaxis.tick_top(); ax.tick_params(axis='x', length=0, pad=1.5)
    for g, gname in enumerate(['H2O', 'Knorm', 'Stream.']):
        ax.text(2 * g + 0.5, -1.25, gname, ha='center', va='bottom', fontsize=7)
    ax.set_yticks(range(len(LADDER)))
    ax.set_yticklabels(LADDER_NAMES if k == 0 else [], fontsize=7)
    ax.tick_params(axis='y', length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, len(ROWS))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(LADDER))], minor=True)
    ax.grid(which='minor', color='white', linewidth=1.4)
    ax.tick_params(which='minor', length=0)
    ax.axvline(1.5, color='white', linewidth=3.4); ax.axvline(3.5, color='white', linewidth=3.4)
    ax.set_title(mname, fontsize=8.5, fontweight='bold', pad=21)
fig.savefig(os.path.join(OUT, 'fig_app_cells.pdf'), metadata={'CreationDate': None})
fig.savefig(os.path.join(OUT, 'fig_app_cells.png'), dpi=220)

# ---------------------------------------------------------------- Appendix figure: official-base reversals by authority relation
RELS = [('system_vs_user', 'System / user'), ('developer_vs_user', 'Developer / user'), ('system_vs_tool', 'System / tool'),
        ('developer_vs_retrieved_document', 'Developer / retrieved'), ('multi_tier', 'Multi-tier')]
SCOR = [('h2o', 'H2O'), ('knorm', 'Knorm'), ('streaming', 'StreamingLLM')]
by = {}
for c in T['ih_cells']:
    if c['arm'] in ('base', 'full'):
        for rel, v in c['up']['by_relation'].items():
            assert v['n'] == 80
            by[(c['arm'], c['scorer'], rel)] = by.get((c['arm'], c['scorer'], rel), 0) + v['reversal']
assert all(by[('full', s, r)] == 0 for s, _ in SCOR for r, _ in RELS)
for s, _ in SCOR:  # each scorer's five relations add up to its share of the 2,055 reversals
    assert sum(by[('base', s, r)] for r, _ in RELS) == sum(c['up']['reversal'] for c in T['ih_cells'] if c['arm'] == 'base' and c['scorer'] == s)
fig = plt.figure(figsize=(6.3, 1.55))
PW2, PX2 = 100, [92, 214, 336]
for k, (s, sname) in enumerate(SCOR):
    ax = fig.add_axes([PX2[k] / FW, 0.25, PW2 / FW, 0.62])
    vals = [by[('base', s, r)] for r, _ in RELS]
    ys = list(range(len(RELS)))[::-1]
    ax.barh(ys, vals, 0.62, color='white', edgecolor=RED, hatch='////', linewidth=0.8)
    for y, v, (r, _) in zip(ys, vals, RELS):
        ax.text(v + 9, y, f'{v}', ha='left', va='center', fontsize=6.6, color='#1F2430')
    ax.set_xlim(0, 480); ax.set_xticks([0, 240, 480])
    ax.set_ylim(-0.6, len(RELS) - 0.4)
    ax.set_yticks(ys); ax.set_yticklabels([lab for _, lab in RELS] if k == 0 else [])
    ax.tick_params(axis='y', length=0)
    ax.set_title(sname, loc='left', fontsize=8.5, fontweight='bold', pad=4)
    if k == 1:
        ax.set_xlabel('Reversals by the official compressor (of 480 per relation)')
fig.savefig(os.path.join(OUT, 'fig_app_relations.pdf'), metadata={'CreationDate': None})
fig.savefig(os.path.join(OUT, 'fig_app_relations.png'), dpi=220)
print('appendix figures', {m: [sum(r[j] for r in grid[m]) for j in range(4)] for m, _ in MODELS})
