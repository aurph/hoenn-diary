"""Assemble hoenn-diary.html from species.json + encounters_ruby.json + manual_data.py + template.html"""
import json, re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
import manual_data as M

BASE = os.path.dirname(os.path.abspath(__file__))
species = json.load(open(f'{BASE}/data/species.json'))
encounters = json.load(open(f'{BASE}/data/encounters_ruby.json'))

by_id = {x['id']: x for x in species}
by_name = {x['name']: x for x in species}
hoenn_ids = {x['id'] for x in species}

FLOOR_PAT = re.compile(r'-(b?\d+f.*|entrance|1fsmall-room)$')

def area_key(slug):
    s = slug[6:] if slug.startswith('hoenn-') else slug
    if s.endswith('-area'):
        s = s[:-5]
    if s in M.AREA_LABELS:
        return s
    collapsed = FLOOR_PAT.sub('', s)
    if collapsed in M.AREA_LABELS:
        return collapsed
    return s

METHOD_KIND = {
    'walk': 'grass', 'surf': 'surf', 'old-rod': 'rod', 'good-rod': 'rod', 'super-rod': 'rod',
    'rock-smash': 'smash', 'seaweed': 'underwater', 'gift': 'gift', 'gift-egg': 'gift',
    'only-one': 'static', 'npc-trade': 'trade', 'devon-scope': 'static',
    'feebas-tile-fishing': 'rod', 'roaming-grass': 'roam', 'roaming-water': 'roam',
    'colosseum-bonus-disc-us': 'event', 'pokemon-channel-pal': 'event',
}

def rate_word(c):
    if c >= 40: return 'very common'
    if c >= 20: return 'common'
    if c >= 10: return 'uncommon'
    if c >= 5: return 'rare'
    return 'very rare'

unknown_areas = set()

def wild_rows(nat):
    rows = {}
    for e in encounters.get(str(nat), []):
        if e['method'] in M.DROP_METHODS:
            continue
        key = area_key(e['area'])
        if key not in M.AREA_LABELS:
            unknown_areas.add(key)
            label = key.replace('-', ' ').title()
        else:
            label = M.AREA_LABELS[key]
        mk = (key, e['method'])
        cur = rows.get(mk)
        if cur is None:
            rows[mk] = dict(key=key, label=label, method=e['method'],
                            chance=e['chance'], lo=e['min'], hi=e['max'])
        else:
            cur['chance'] = max(cur['chance'], e['chance'])
            cur['lo'] = min(cur['lo'], e['min'])
            cur['hi'] = max(cur['hi'], e['max'])
    out = []
    for (key, method), r in sorted(rows.items(), key=lambda kv: (kv[1]['method'] != 'gift', kv[1]['label'])):
        kind = METHOD_KIND.get(method, 'grass')
        mlabel = M.METHOD_LABELS.get(method, method)
        if method == 'walk':
            mlabel = 'Grass' if key.startswith('route-') or key.endswith('(water)') else 'Walking'
            if key in M.CAVE_ROOTS or any(key.startswith(c) for c in M.CAVE_ROOTS):
                mlabel = 'Cave'
        lv = f"Lv {r['lo']}" if r['lo'] == r['hi'] else f"Lv {r['lo']}-{r['hi']}"
        if kind in ('gift', 'static', 'trade', 'event', 'roam'):
            d = f"{mlabel} · {lv}"
        else:
            d = f"{mlabel} · ~{r['chance']}% ({rate_word(r['chance'])}) · {lv}"
        out.append(dict(k=kind, t=r['label'], d=d, key=key))
    return out

def evo_text(mon):
    et, lvl, item, cond = mon['evoType'], mon['evoLevel'], mon['evoItem'], mon['evoCondition']
    sid = mon['id']
    if sid == 'shedinja':
        return 'Evolve Nincada at Lv 20 with an empty party slot AND a spare Poké Ball: Shedinja appears alongside Ninjask.'
    if sid in ('silcoon', 'cascoon'):
        return 'Wurmple at Lv 7. Which cocoon you get is random (personality value), no way to influence it.'
    if sid in M.TRADE_EVO_NOTE:
        return M.TRADE_EVO_NOTE[sid]
    if et == 'useItem':
        return f'Use {item}.'
    if et == 'levelFriendship':
        return 'Level up with high friendship.'
    if et == 'levelExtra' and sid == 'milotic':
        return 'Level up Feebas with max Beauty (dry Pokéblocks). See the side quest.'
    if et == 'trade':
        return f'Trade {mon["prevo"]}' + (f' holding {item}.' if item else '.')
    if lvl:
        return f'Reach Lv {lvl}.'
    if cond:
        return f'{cond}.'
    return 'Level up.'

def family(mon):
    root = mon
    seen = set()
    while root['prevo'] and root['prevo'] in by_name and root['prevo'] not in seen:
        seen.add(root['prevo'])
        root = by_name[root['prevo']]
    fam, queue = [], [root]
    while queue:
        cur = queue.pop(0)
        if cur['h'] in fam:
            continue
        fam.append(cur['h'])
        for ev in cur['evos']:
            if ev in by_name:
                queue.append(by_name[ev])
    return fam

mons_out = []
for x in species:
    ov = M.OBTAIN_OVERRIDES.get(x['id'], {})
    rows = [] if 'replace' in ov else wild_rows(x['n'])
    rows = [{k: v for k, v in r.items() if k != 'key'} for r in rows]
    if 'replace' in ov:
        rows = list(ov['replace'])
    for extra in ov.get('extra', []):
        rows.append(dict(extra))
    flags = {}
    if any(r['k'] == 'sapphire' for r in rows): flags['s'] = 1
    if x['id'] in ('latias', 'jirachi', 'deoxys'): flags['e'] = 1
    if x['prevo'] and x['prevo'] in by_name:
        t = evo_text(x)
        rows.append(dict(k='evolve', t=f"Evolve {x['prevo']}", d=t))
        if x['evoType'] == 'trade' or x['id'] in ('alakazam', 'machamp', 'golem', 'kingdra', 'huntail', 'gorebyss'):
            flags['t'] = 1
    note = ov.get('note')
    loc = ' '.join(set([r['t'].lower() for r in rows] + [x['name'].lower()]))
    entry = dict(
        h=x['h'], n=x['n'], name=x['name'], id=x['id'], types=x['types'],
        st=[x['stats'][k] for k in ('hp', 'atk', 'def', 'spa', 'spd', 'spe')],
        ab=x['abilities'], ob=rows, fam=family(x), loc=loc,
    )
    if note: entry['note'] = note
    if flags: entry['fl'] = flags
    if x['id'] in M.STARTER_LINES: entry['stl'] = M.STARTER_LINES[x['id']]
    if x['id'] in M.FOSSIL_LINES: entry['fol'] = M.FOSSIL_LINES[x['id']]
    mons_out.append(entry)

# sanity: completable baseline (no starter/fossil chosen) = mons without s/e/t flags
base_countable = [m for m in mons_out if not m.get('fl')]
assert len(base_countable) == 186, f'expected 186 baseline-countable, got {len(base_countable)}'

# ----- per-chapter & landmark catch lists
def catch_for(areas):
    keys = set(areas)
    found = []
    for x in species:
        for e in encounters.get(str(x['n']), []):
            if e['method'] in M.DROP_METHODS: continue
            if area_key(e['area']) in keys:
                found.append(x['h']); break
    return sorted(set(found))

chapters_out = []
total_cps = 0
for c in M.CHAPTERS:
    o = dict(c)
    o['catch'] = catch_for(c.get('areas', []))
    o.pop('areas', None)
    total_cps += len(c.get('cps', []))
    chapters_out.append(o)
sides_out = []
for s in M.SIDES:
    total_cps += len(s.get('cps', []))
    sides_out.append(dict(s))
lms_out = []
for l in M.LANDMARKS:
    o = dict(l)
    o['catch'] = catch_for(l.get('areas', []))
    o.pop('areas', None)
    lms_out.append(o)

# every side 'after' must reference a real chapter
chapter_ids = {c['id'] for c in chapters_out}
for s in sides_out:
    assert s['after'] in chapter_ids, f"side {s['id']} after unknown chapter {s['after']}"

DATA = dict(
    mons=mons_out, chapters=chapters_out, sides=sides_out, landmarks=lms_out,
    tips=M.DAILY_TIPS, rival=M.RIVAL, badges=M.BADGES, chart=M.TYPE_CHART,
)

if unknown_areas:
    print('WARNING unknown areas:', sorted(unknown_areas))

payload = json.dumps(DATA, ensure_ascii=False, separators=(',', ':'))
tpl = open(f'{BASE}/template.html', encoding='utf-8').read()
assert '/*__DATA__*/' in tpl, 'placeholder missing'
html = tpl.replace('/*__DATA__*/', 'window.HD=' + payload + ';')
out = f'{BASE}/index.html'
open(out, 'w', encoding='utf-8').write(html)
print(f'built {out}: {len(html)//1024} KB · {len(mons_out)} mons ({len(base_countable)} solo-completable) · '
      f'{len(chapters_out)} chapters · {len(sides_out)} side cards · {total_cps} checkpoints')
