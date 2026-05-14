"""
split_data.py - Called by GitHub Actions after parser.py
Splits the full dashboard_data.json into lightweight files for the web app.
"""
import json, os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(SRC, 'dashboard_data.json')) as f:
    d = json.load(f)

# 1) summary_data.json — no distributions, no timelines
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

# 2) distributions.json — histograms only
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

# 3) Per-worker JSON files
workers_dir = os.path.join(SRC, 'workers')
os.makedirs(workers_dir, exist_ok=True)
for wid, wdata in d['workers'].items():
    with open(os.path.join(workers_dir, f'{wid}.json'), 'w') as f:
        json.dump(wdata, f, ensure_ascii=False)

print(f"Split complete: {len(d['workers'])} workers, {len(d['periods'])} periods")
