"""Figures 2, 3, 4, and 5 of the camera-ready, drawn from the verified fact files (no hand-typed numbers)."""
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
# red = official compressor, teal = AuthorityKV (light teal: roles + provenance only); text stays in ink
RED, TEAL, TEAL_L, GRAY, INK = '#C84A5A', '#087F7B', '#A8DAD5', '#69717D', '#1F2430'
CELLS = [('h2o', 0.2), ('h2o', 0.4), ('knorm', 0.2), ('knorm', 0.4), ('streaming', 0.2), ('streaming', 0.4)]
NAME = {'h2o': 'H2O', 'knorm': 'Knorm', 'streaming': 'Stream.'}


def cell_sum(arm, s, r, rule='up'):
    return sum(c[rule]['reversal'] for c in T['ih_cells'] if c['arm'] == arm and c['scorer'] == s and abs(c['ratio'] - r) < 1e-9)


fig = plt.figure(figsize=(6.3, 2.4))
# Column layout in points (the figure is printed at \textwidth = 453.6pt): each gap is sized for the row labels it holds.
FW = 6.3 * 72
COLS = {'a': (56, 114), 'b': (206, 80), 'c1': (343, 38), 'c2': (391, 50)}  # left edge, width
def panel(key):
    x0, w = COLS[key]
    return fig.add_axes([x0 / FW, 0.345, w / FW, 0.545])

# ---- (a) reversals per compressor and budget (same row grammar as panels b and c)
ax = panel('a')
ROWS_A = [('streaming', 0.2), ('streaming', 0.4), ('knorm', 0.2), ('knorm', 0.4), ('h2o', 0.2), ('h2o', 0.4)]
base = [cell_sum('base', s, r) for s, r in ROWS_A]
rp = [cell_sum('rpstrict', s, r) for s, r in ROWS_A]
full = [cell_sum('full', s, r) for s, r in ROWS_A]
assert sum(base) == T['ih_totals']['all|base']['reversal_up'] and sum(rp) == T['ih_totals']['all|rpstrict']['reversal_up']
assert all(v == 0 for v in full)  # the note inside the panel states this
ya = list(range(len(ROWS_A)))[::-1]; hb = 0.37
ax.barh([y + hb / 2 for y in ya], base, hb, color='white', edgecolor=RED, hatch='////', linewidth=0.8, label='Official compressor')
ax.barh([y - hb / 2 for y in ya], rp, hb, color=TEAL_L, edgecolor=TEAL, linewidth=0.8, label='+AuthorityKV, roles\n+ provenance')
for y, b0, r0 in zip(ya, base, rp):
    ax.text(b0 + 18, y + hb / 2, f'{b0:,}', ha='left', va='center', fontsize=8, color=INK)
    ax.text(r0 + 18, y - hb / 2 - 0.02, f'{r0:,}', ha='left', va='center', fontsize=8, color=INK)
ax.set_yticks(ya); ax.set_yticklabels([f'{NAME[s]} {int(r*100)}%' for s, r in ROWS_A])
ax.set_xlim(0, 1500); ax.set_xticks([0, 400, 800, 1200]); ax.set_xlabel('Reversals (of 1,200)')
ax.set_ylim(-0.6, len(ROWS_A) - 0.4)
ax.legend(frameon=False, fontsize=8, loc='lower right', bbox_to_anchor=(1.03, 0.20), handlelength=1.2, borderaxespad=0.0,
          labelspacing=0.4, handletextpad=0.45)
ax.text(1.03, 0.0, '+ span boundaries:\n0 in every row', transform=ax.transAxes, ha='right', va='bottom', fontsize=8,
        color=INK, linespacing=1.15)
ax.set_title('(a) IH-CacheBench', loc='left', fontsize=9, fontweight='bold', pad=4)
ax.tick_params(axis='y', length=0)

# ---- (b) System-IFEval dumbbells: one row per compressor, filled marker for R-up and open marker for R-down
ax = panel('b')
SB = ['streaming', 'knorm', 'h2o']
for i, sc in enumerate(SB):
    for rule, off in [('R↑', 0.2), ('R↓', -0.2)]:
        d = T['sys'][f'{sc}|{rule}']; b0, a0 = d['base_gated'][0], d['akv_gated'][0]
        assert d['base_gated'][1] == 88 and d['akv_gated'][1] == 88
        y = len(SB) - 1 - i + off
        ax.plot([b0, a0], [y, y], color=GRAY, lw=1.6, alpha=0.55, zorder=1)
        ax.scatter([b0], [y], marker='x', s=26, color=RED, linewidths=1.3, zorder=3)
        ax.scatter([a0], [y], marker='o', s=30, color=TEAL if rule == 'R↑' else 'white', edgecolor=TEAL, linewidths=1.2, zorder=3)
        ax.text(b0 - 5.5, y, str(b0), ha='right', va='center', fontsize=8, color=INK)
        ax.text(a0 + 5.5, y, str(a0), ha='left', va='center', fontsize=8, color=INK)
ax.set_yticks(range(len(SB))[::-1]); ax.set_yticklabels([NAME[sc] for sc in SB])
ax.set_xlim(-16, 102); ax.set_xticks([0, 44, 88]); ax.set_xlabel('Prompts satisfied (of 88)')
ax.set_ylim(-0.6, len(SB) - 0.4)
ax.set_title('(b) System-IFEval', loc='left', fontsize=9, fontweight='bold', pad=4)
ax.tick_params(axis='y', length=0)
from matplotlib.lines import Line2D
h = [Line2D([], [], marker='x', color=RED, ls='', ms=5, mew=1.2, label='Official compressor'),
     Line2D([], [], marker='o', color=TEAL, ls='', ms=5, label=r'+AuthorityKV, R$_{\!\uparrow}$'),
     Line2D([], [], marker='o', mfc='white', mec=TEAL, ls='', ms=5, label=r'+AuthorityKV, R$_{\!\downarrow}$')]
fig.legend(handles=h, frameon=False, fontsize=8, loc='lower center', bbox_to_anchor=(0.71, -0.015), ncol=3, handletextpad=0.1, columnspacing=1.2, borderaxespad=0.2)

# ---- (c) LongBench + injection: attacks and joint
M = T['mixed']
rows = [('streaming', 0.2), ('streaming', 0.4), ('knorm', 0.4)]
for j, (key, title, xl, lim, ticks) in enumerate([('attack', '(c) LongBench', 'Attacks\n(of 64)', (-3.6, 10.8), [0, 4, 8]), ('joint', None, 'Safe + correct\n(of 64)', (33, 70), [40, 52, 64])]):
    ax = panel('c1' if j == 0 else 'c2')
    for i, (s, r) in enumerate(rows):
        for k, off in [('up', 0.2), ('dn', -0.2)]:
            y = len(rows) - 1 - i + off
            b0 = M[f'{s}|{r}|explicit_attack|base'][k][key]; a0 = M[f'{s}|{r}|explicit_attack|full'][k][key]
            ax.plot([b0, a0], [y, y], color=GRAY, lw=1.6, alpha=0.55, zorder=1)
            ax.scatter([b0], [y], marker='x', s=22, color=RED, linewidths=1.2, zorder=3)
            ax.scatter([a0], [y], marker='o', s=26, color=TEAL if k == 'up' else 'white', edgecolor=TEAL, linewidths=1.1, zorder=3)
            # value labels on the outer side of each marker, as in panel (b)
            gap = 1.0 if j == 0 else 2.4
            if a0 == b0:
                ax.text(a0 + 1.5 * gap, y, str(a0), ha='left', va='center', fontsize=8, color=INK)
            else:
                lo, hi = (a0, b0) if a0 < b0 else (b0, a0)
                ax.text(lo - gap, y, str(lo), ha='right', va='center', fontsize=8, color=INK)
                ax.text(hi + gap, y, str(hi), ha='left', va='center', fontsize=8, color=INK)
    ax.set_yticks(range(len(rows))[::-1])
    ax.set_yticklabels([f'{NAME[s]} {int(r*100)}%' for s, r in rows] if j == 0 else [])
    ax.set_xlim(*lim); ax.set_xticks(ticks); ax.set_xlabel(xl); ax.set_ylim(-0.6, len(rows) - 0.4)
    if title:
        ax.set_title(title, loc='left', fontsize=9, fontweight='bold', pad=4)
    ax.tick_params(axis='y', length=0)
fig.savefig(os.path.join(OUT, 'fig2_results.pdf'), metadata={'CreationDate': None})  # no timestamp: reruns are byte-identical
fig.savefig(os.path.join(OUT, 'fig2_results.png'), dpi=220)
print('font', fam, 'base', base, 'rp', rp, 'full', full)

# ---------------------------------------------------------------- Figure 3: what the cache keeps (retention by span type)
R = {}
for line in open(os.path.join(FD, 'RESPONSE_FACTS.jsonl'), encoding='utf-8'):
    r = json.loads(line); R[r['id']] = r
spans = [('system', 'System prompt'), ('answer', 'Answer sentences'), ('question', 'Question'), ('injection', 'Injected note')]
fig, ax = plt.subplots(figsize=(3.03, 1.64))
fig.subplots_adjust(left=0.335, right=0.97, top=0.865, bottom=0.285)
h = 0.34
for i, (k, lab) in enumerate(spans):
    y = len(spans) - 1 - i
    b0 = float(R[f'A4-str40-para-base-{k}']['number']); a0 = float(R[f'A4-str40-para-full-{k}']['number'])
    ax.barh(y + h / 2, b0, h, color='white', edgecolor=RED, hatch='////', linewidth=0.8, label='Official StreamingLLM' if i == 0 else None)
    ax.barh(y - h / 2, a0, h, color=TEAL, edgecolor=TEAL, linewidth=0.8, label='+AuthorityKV' if i == 0 else None)
    ax.text(b0 + 0.02, y + h / 2 + 0.05, f'{b0:.2f}', va='center', ha='left', fontsize=8, color=INK)
    ax.text(a0 + 0.02, y - h / 2 - 0.06, f'{a0:.2f}', va='center', ha='left', fontsize=8, color=INK)
ax.set_yticks(range(len(spans))[::-1]); ax.set_yticklabels([s[1] for s in spans])
ax.set_xlim(0, 1.2); ax.set_xticks([0, 0.5, 1.0]); ax.set_xlabel('Fraction of span retained in the cache')
ax.tick_params(axis='y', length=0)
ax.legend(frameon=False, fontsize=8, loc='lower center', bbox_to_anchor=(0.33, 0.985), ncol=2, handlelength=1.2, columnspacing=0.9, handletextpad=0.4, borderaxespad=0)
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
LADDER_NAMES = ['Official compressor', '+AuthorityKV,\nroles + provenance', '+ sentence detector', '+ span boundaries']
fig = plt.figure(figsize=(6.3, 1.95))
PW, PX = 102, [100, 220, 340]  # panel width and left edges in points
for k, (m, mname) in enumerate(MODELS):
    ax = fig.add_axes([PX[k] / FW, 0.04, PW / FW, 0.62])
    data = [[grid[m][i][j] for i in range(len(ROWS))] for j in range(len(LADDER))]  # rows: ladder, columns: cells
    # vector cells (pcolormesh), so the figure prints sharply and does not depend on image resampling
    ax.pcolormesh([x - 0.5 for x in range(len(ROWS) + 1)], [y - 0.5 for y in range(len(LADDER) + 1)], data,
                  cmap=cmap, norm=norm, edgecolors='white', linewidth=1.4)
    ax.set_xlim(-0.5, len(ROWS) - 0.5); ax.set_ylim(len(LADDER) - 0.5, -0.5)
    for j, row in enumerate(data):
        for i, v in enumerate(row):
            ink = 'white' if v >= 150 else ('#1F2430' if v > 0 else '#8A919C')
            ax.text(i, j, f'{v}', ha='center', va='center', fontsize=8, color=ink)
    ax.set_xticks(range(len(ROWS))); ax.set_xticklabels([f'{int(r * 100)}' for _, r in ROWS], fontsize=8)
    ax.xaxis.tick_top(); ax.tick_params(axis='x', length=0, pad=1.5)
    for g, gname in enumerate(['H2O', 'Knorm', 'Stream.']):
        ax.text(2 * g + 0.5, -1.3, gname, ha='center', va='bottom', fontsize=8)
    ax.set_yticks(range(len(LADDER)))
    ax.set_yticklabels(LADDER_NAMES if k == 0 else [], fontsize=8, linespacing=1.0)
    ax.tick_params(axis='y', length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.axvline(1.5, color='white', linewidth=3.4); ax.axvline(3.5, color='white', linewidth=3.4)
    ax.set_title(mname, fontsize=9, fontweight='bold', pad=30)
fig.savefig(os.path.join(OUT, 'fig_app_cells.pdf'), metadata={'CreationDate': None})
fig.savefig(os.path.join(OUT, 'fig_app_cells.png'), dpi=220)

# ---------------------------------------------------------------- Appendix figure: official-base reversals by authority relation
RELS = [('system_vs_user', 'System / user'), ('developer_vs_user', 'Developer / user'), ('system_vs_tool', 'System / tool'),
        ('developer_vs_retrieved_document', 'Developer / retrieved'), ('multi_tier', 'Multi-tier')]
by = {}  # (arm, scorer, ratio, relation) -> reversals summed over the three models (240 decisions per cell)
for c in T['ih_cells']:
    if c['arm'] in ('base', 'full'):
        for rel, v in c['up']['by_relation'].items():
            assert v['n'] == 80
            key = (c['arm'], c['scorer'], round(c['ratio'], 2), rel)
            by[key] = by.get(key, 0) + v['reversal']
assert all(v == 0 for k, v in by.items() if k[0] == 'full')  # the caption states this
for s_, r_ in ROWS:  # each cell's five relations add up to its total in Table 2's source
    assert sum(by[('base', s_, r_, rel)] for rel, _ in RELS) == cell_sum('base', s_, r_)
# the same counts as the statistics file recomputed from the raw predictions (when that file is present)
_cat = os.path.join(os.path.dirname(os.path.abspath(FD)), 'reports', 'acl_final_closure', 'parent_statistics', 'category_summary.csv')
if os.path.exists(_cat):
    import csv
    _m = {'kvpress_h2o': 'h2o', 'kvpress_knorm': 'knorm', 'kvpress_streaming': 'streaming'}
    _models = {'Qwen/Qwen2.5-7B-Instruct', 'mistralai/Mistral-7B-Instruct-v0.3', '01-ai/Yi-1.5-9B-Chat'}
    _sum = {}
    for row in csv.DictReader(open(_cat, encoding='utf-8')):
        if row['method'] in _m and row['model'] in _models and row['dataset'].endswith('natural_short_500.jsonl') \
                and row['category'] != 'benign_utility':
            k_ = ('base', _m[row['method']], round(float(row['keep_ratio']), 2), row['category'])
            _sum[k_] = _sum.get(k_, 0) + int(row['authority_reversal_num'])
    assert all(_sum[('base', s_, r_, rel)] == by[('base', s_, r_, rel)] for s_, r_ in ROWS for rel, _ in RELS)
data = [[by[('base', s_, r_, rel)] for s_, r_ in ROWS] for rel, _ in RELS]
fig = plt.figure(figsize=(3.03, 1.72))
FC = 3.03 * 72
ax = fig.add_axes([94 / FC, 0.04, 118 / FC, 0.70])
ax.pcolormesh([x - 0.5 for x in range(len(ROWS) + 1)], [y - 0.5 for y in range(len(RELS) + 1)], data,
              cmap=cmap, norm=PowerNorm(gamma=0.5, vmin=0, vmax=240), edgecolors='white', linewidth=1.4)
ax.set_xlim(-0.5, len(ROWS) - 0.5); ax.set_ylim(len(RELS) - 0.5, -0.5)
for j, row in enumerate(data):
    for i, v in enumerate(row):
        ink = 'white' if v >= 90 else ('#1F2430' if v > 0 else '#8A919C')
        ax.text(i, j, f'{v}', ha='center', va='center', fontsize=8, color=ink)
ax.set_xticks(range(len(ROWS))); ax.set_xticklabels([f'{int(r * 100)}' for _, r in ROWS], fontsize=8)
ax.xaxis.tick_top(); ax.tick_params(axis='x', length=0, pad=1.5)
for g, gname in enumerate(['H2O', 'Knorm', 'Stream.']):
    ax.text(2 * g + 0.5, -1.35, gname, ha='center', va='bottom', fontsize=8)
ax.set_yticks(range(len(RELS))); ax.set_yticklabels([lab for _, lab in RELS], fontsize=8)
ax.tick_params(axis='y', length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.axvline(1.5, color='white', linewidth=3.4); ax.axvline(3.5, color='white', linewidth=3.4)
fig.savefig(os.path.join(OUT, 'fig_app_relations.pdf'), metadata={'CreationDate': None})
fig.savefig(os.path.join(OUT, 'fig_app_relations.png'), dpi=220)
print('appendix figures', {m: [sum(r[j] for r in grid[m]) for j in range(4)] for m, _ in MODELS})
