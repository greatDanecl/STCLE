"""
split_data.py - Called by GitHub Actions after parser.py
Splits the full dashboard_data.json into:
  summary_data.json          — monthly KPIs + workers index (no timelines)
  distributions.json         — histogram data per period/rank
  workers_CCM.json           — slim KPIs for all CCM (no timelines)
  workers_CC.json            — slim KPIs for all CC (no timelines)
  timelines_CCM_YYYY-MM.json — compact timelines for CCM, loaded on demand
  timelines_CC_YYYY-MM.json  — compact timelines for CC, loaded on demand
"""
import json, os

SRC = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SRC, 'dashboard_data.json')) as f:
    d = json.load(f)

# 1) summary_data.json
summary = {'periods': d['periods'], 'workers_index': d['workers_index'], 'monthly': {}}
for period, mdata in d['monthly'].items():
    summary['monthly'][period] = {}
    for key, val in mdata.items():
        if val is None:
            summary['monthly'][period][key] = None
        else:
            summary['monthly'][period][key] = {
                k: v for k, v in val.items()
                if k not in ('flight_hours_dist', 'airport_turns_dist')
            }
with open(os.path.join(SRC, 'summary_data.json'), 'w') as f:
    json.dump(summary, f, ensure_ascii=False)

# 2) distributions.json
dists = {}
for period, mdata in d['monthly'].items():
    dists[period] = {}
    for key, val in mdata.items():
        if val and isinstance(val, dict):
            dists[period][key] = {
                'flight_hours_dist': val.get('flight_hours_dist', {}),
                'airport_turns_dist': val.get('airport_turns_dist', {}),
            }
with open(os.path.join(SRC, 'distributions.json'), 'w') as f:
    json.dump(dists, f, ensure_ascii=False)

def compact_timeline(tl):
    """Convert timeline dicts to compact arrays: [date, activity, act_type, hours, dep, arv]"""
    return [[e['date'], e['activity'], e['act_type'], e['block_hours'], e['dep'], e['arv']] for e in tl]

# 3) workers_CCM.json and workers_CC.json (slim, no timelines)
# 4) timelines_RANK_PERIOD.json (compact arrays, lazy-loaded for calendar)
for rank in ['CCM', 'CC']:
    slim = {}
    for wid, wdata in d['workers'].items():
        if wdata['rank'] != rank:
            continue
        periods_slim = {
            pkey: {k: v for k, v in pdata.items() if k != 'timeline'}
            for pkey, pdata in wdata['periods'].items()
        }
        slim[wid] = {'name': wdata['name'], 'rank': wdata['rank'], 'periods': periods_slim}

    with open(os.path.join(SRC, f'workers_{rank}.json'), 'w') as f:
        json.dump({'workers': slim}, f, ensure_ascii=False)

    # Timeline files per period
    for period in d['periods']:
        tdata = {}
        for wid, wdata in d['workers'].items():
            if wdata['rank'] != rank:
                continue
            entry = {}
            pub = wdata['periods'].get(f'{period}_Publicado', {})
            ef  = wdata['periods'].get(f'{period}_Efectuado', {})
            if pub.get('timeline'):
                entry['p'] = compact_timeline(pub['timeline'])
            if ef.get('timeline'):
                entry['e'] = compact_timeline(ef['timeline'])
            if entry:
                tdata[wid] = entry
        if tdata:
            fname = os.path.join(SRC, f'timelines_{rank}_{period}.json')
            with open(fname, 'w') as f:
                json.dump(tdata, f, ensure_ascii=False, separators=(',', ':'))

    n = len(slim)
    size = os.path.getsize(os.path.join(SRC, f'workers_{rank}.json')) // 1024
    print(f"workers_{rank}.json → {size} KB ({n} workers)")

print(f"Split complete: {len(d['workers'])} workers, {len(d['periods'])} periods")
