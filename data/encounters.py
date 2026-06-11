"""Fetch Ruby-version wild encounter data for all 202 Hoenn dex Pokemon from PokeAPI."""
import json, time, os, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, 'cache')
os.makedirs(CACHE, exist_ok=True)

species = json.load(open(os.path.join(BASE, 'species.json')))

out = {}
for i, sp in enumerate(species):
    nid = sp['n']
    cf = os.path.join(CACHE, f'enc_{nid}.json')
    if os.path.exists(cf):
        data = json.load(open(cf))
    else:
        url = f'https://pokeapi.co/api/v2/pokemon/{nid}/encounters'
        req = urllib.request.Request(url, headers={'User-Agent': 'hoenn-diary-build/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        json.dump(data, open(cf, 'w'))
        time.sleep(0.12)
    ruby = []
    for area in data:
        la = area['location_area']['name']
        for vd in area['version_details']:
            if vd['version']['name'] != 'ruby':
                continue
            methods = {}
            for ed in vd['encounter_details']:
                m = ed['method']['name']
                rec = methods.setdefault(m, {'chance': 0, 'min': 99, 'max': 0, 'conds': set()})
                rec['chance'] += ed['chance']
                rec['min'] = min(rec['min'], ed['min_level'])
                rec['max'] = max(rec['max'], ed['max_level'])
                for c in ed.get('condition_values', []):
                    rec['conds'].add(c['name'])
            for m, rec in methods.items():
                ruby.append({
                    'area': la, 'method': m,
                    'chance': min(rec['chance'], 100),
                    'min': rec['min'], 'max': rec['max'],
                    'conds': sorted(rec['conds']),
                })
    if ruby:
        out[str(nid)] = ruby
    if (i + 1) % 25 == 0:
        print(f'{i+1}/202 done', flush=True)

json.dump(out, open(os.path.join(BASE, 'encounters_ruby.json'), 'w'), indent=1)
print('species with ruby wild encounters:', len(out))
