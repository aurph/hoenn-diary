import {Dex} from '@pkmn/dex';

const g3 = Dex.forGen(3);

const res = await fetch('https://pokeapi.co/api/v2/pokedex/4');
const dexData = await res.json();
const entries = dexData.pokemon_entries;

const out = [];
for (const e of entries) {
  const slug = e.pokemon_species.name;
  const natId = parseInt(e.pokemon_species.url.match(/\/(\d+)\/?$/)[1], 10);
  const s = g3.species.get(slug);
  if (!s || !s.exists) {
    console.error('MISSING IN PKMN DEX:', slug);
    continue;
  }
  const abilities = [s.abilities['0'], s.abilities['1']].filter(Boolean);
  out.push({
    h: e.entry_number,
    n: natId,
    name: s.name,
    slug,
    id: s.id, // showdown id, used for sprite filename
    types: s.types,
    stats: s.baseStats,
    abilities,
    prevo: s.prevo || null,
    evoType: s.evoType || null,
    evoLevel: s.evoLevel || null,
    evoItem: s.evoItem || null,
    evoCondition: s.evoCondition || null,
    evos: s.evos || [],
  });
}

if (out.length !== 202) console.error('WARNING: expected 202 entries, got', out.length);
console.log(JSON.stringify(out, null, 1));
