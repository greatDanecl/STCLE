"""
STCLE Dashboard - Data Parser
Parses all Excel files (Publicado + Efectuado) from /data folder
and generates a unified JSON for the dashboard.
"""

import pandas as pd
import numpy as np
import json
import os
import re
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')

# Activity classification
def classify_activity(act):
    if pd.isna(act):
        return 'OTRO'
    act = str(act).strip().upper()
    if re.match(r'^LA\d+', act) or act == 'LA':
        return 'VUELO'
    if act.startswith('AS'):
        return 'TURNO_AEROPUERTO'
    if act.startswith('HS'):
        return 'TURNO_DOMICILIO'
    if act in ('B',):
        return 'DIA_BLANCO'
    if act in ('VAC', 'VC'):
        return 'VACACIONES'
    if act in ('DO',):
        return 'DIA_LIBRE'
    if act in ('SICK', 'ME', 'MT', 'MTC', 'MTU', 'LW'):
        return 'LICENCIA_MEDICA'
    if act in ('VUSA',):
        return 'VUSA'
    if act in ('Q',):
        return 'BLOQUE_LIBRE'
    if act in ('DR',):
        return 'DIA_LIBRE_SOLICITADO'
    if act in ('OOF',):
        return 'FUERA_VUELO'
    if act in ('RL1', 'RL3', 'RL'):
        return 'REVA'
    if act.startswith('CLA'):
        return 'CLASES_TIERRA'
    if act in ('DH',):
        return 'DH'
    if act in ('LP',):
        return 'LP'
    if act in ('ADM',):
        return 'ADM'
    if act.startswith('HB'):
        return 'OTRO'
    if act in ('DB',):
        return 'OTRO'
    return 'OTRO'

AUSENCIA_PROLONGADA = {'VACACIONES', 'FUERA_VUELO', 'LICENCIA_MEDICA', 'VUSA'}

def timedelta_to_hours(val):
    if pd.isna(val):
        return 0.0
    if isinstance(val, pd.Timedelta):
        return val.total_seconds() / 3600
    if hasattr(val, 'hour'):
        return val.hour + val.minute / 60 + getattr(val, 'second', 0) / 3600
    return 0.0

def parse_str_dt(val):
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, (pd.Timestamp, datetime)):
        return pd.Timestamp(val)
    s = str(val).strip()
    # Format: 28JAN2026
    try:
        return pd.to_datetime(s, format='%d%b%Y')
    except:
        pass
    try:
        return pd.to_datetime(s)
    except:
        return pd.NaT

def load_file(filepath):
    """Load a single xlsx file and normalize to standard format."""
    xl = pd.ExcelFile(filepath)
    df = pd.read_excel(filepath, sheet_name=xl.sheet_names[0])

    fname = os.path.basename(filepath).upper()

    # Determine rol type
    tipo_rol = 'Publicado'
    if 'EFECTUADO' in fname or 'EFECT' in fname or 'EF_' in fname or '_EF_' in fname:
        tipo_rol = 'Efectuado'
    if 'tipo_rol' in df.columns:
        tipo_rol = df['tipo_rol'].iloc[0] if not df.empty else tipo_rol

    # Normalize nombre completo
    if 'Nombre completo' not in df.columns:
        if 'First Name' in df.columns and 'Last Name' in df.columns:
            df['Nombre completo'] = (df['First Name'].fillna('') + ' ' + df['Last Name'].fillna('')).str.strip()
        else:
            df['Nombre completo'] = df.get('Staff Num', '').astype(str)

    # Normalize Str Dt
    df['Str Dt'] = df['Str Dt'].apply(parse_str_dt)

    # Normalize periodo
    if 'periodo' not in df.columns or df['periodo'].isna().all():
        # Infer from filename or from data
        df['periodo'] = df['Str Dt'].dt.to_period('M').dt.to_timestamp()
    else:
        df['periodo'] = pd.to_datetime(df['periodo'])

    # Normalize Block Time to hours
    df['block_hours'] = df['Block Time'].apply(timedelta_to_hours)

    # Activity classification
    df['act_type'] = df['Activity'].apply(classify_activity)

    # tipo_rol column
    df['tipo_rol'] = tipo_rol

    # Ensure sindicato
    if 'sindicato' not in df.columns:
        df['sindicato'] = 'CABLU'

    keep = ['Staff Num', 'Nombre completo', 'Rank', 'Activity', 'act_type',
            'Str Dt', 'End Dt', 'block_hours', 'Dep Port', 'Arv Port',
            'periodo', 'tipo_rol', 'sindicato']
    for c in keep:
        if c not in df.columns:
            df[c] = np.nan

    return df[keep].copy()

def load_all_files():
    """Load all xlsx files from data directory."""
    all_dfs = []
    for f in sorted(os.listdir(DATA_DIR)):
        if not f.endswith('.xlsx'):
            continue
        path = os.path.join(DATA_DIR, f)
        try:
            df = load_file(path)
            all_dfs.append(df)
            print(f"  Loaded: {f} → {len(df)} rows, tipo_rol={df['tipo_rol'].iloc[0]}")
        except Exception as e:
            print(f"  ERROR loading {f}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    # Deduplicate: same worker, same activity, same date, same tipo_rol
    combined = combined.drop_duplicates(
        subset=['Staff Num', 'Str Dt', 'Activity', 'tipo_rol'],
        keep='last'
    )
    return combined

def compute_kpis(df):
    """Compute all KPIs grouped by period, rank, worker."""

    periods = sorted(df['periodo'].dropna().unique())
    output = {
        'periods': [str(p)[:7] for p in periods],
        'monthly': {},
        'workers': {}
    }

    for period in periods:
        period_key = str(period)[:7]  # "2025-09"
        period_df = df[df['periodo'].dt.to_period('M') == pd.Period(period_key, 'M')]

        if period_df.empty:
            continue

        month_data = {}
        for tipo in ['Publicado', 'Efectuado']:
            tdf = period_df[period_df['tipo_rol'] == tipo]
            if tdf.empty:
                month_data[tipo] = None
                continue

            for rank in ['CCM', 'CC']:
                rdf = tdf[tdf['Rank'] == rank]
                if rdf.empty:
                    continue

                workers = rdf['Staff Num'].unique()
                # Active workers: not majority-absent
                active_workers = []
                for wid in workers:
                    wdf = rdf[rdf['Staff Num'] == wid]
                    total_days = wdf.shape[0]
                    absent_days = wdf[wdf['act_type'].isin(AUSENCIA_PROLONGADA)].shape[0]
                    if total_days > 0 and (absent_days / total_days) < 0.5:
                        active_workers.append(wid)

                active_rdf = rdf[rdf['Staff Num'].isin(active_workers)]

                # Hours per worker
                flight_hours_per_worker = (
                    active_rdf[active_rdf['act_type'] == 'VUELO']
                    .groupby('Staff Num')['block_hours'].sum()
                )
                flights_per_worker = (
                    active_rdf[active_rdf['act_type'] == 'VUELO']
                    .groupby('Staff Num')['Activity'].count()
                )
                duty_days_per_worker = (
                    active_rdf[~active_rdf['act_type'].isin({'DIA_LIBRE', 'DIA_BLANCO', 'VACACIONES', 'LICENCIA_MEDICA', 'FUERA_VUELO', 'BLOQUE_LIBRE'})]
                    .groupby('Staff Num')['Str Dt'].nunique()
                )

                # Airport turns
                at_workers = active_rdf[active_rdf['act_type'] == 'TURNO_AEROPUERTO']['Staff Num'].unique()
                at_counts = (
                    active_rdf[active_rdf['act_type'] == 'TURNO_AEROPUERTO']
                    .groupby('Staff Num')['Activity'].count()
                )

                # Home turns
                ht_counts = (
                    active_rdf[active_rdf['act_type'] == 'TURNO_DOMICILIO']
                    .groupby('Staff Num')['Activity'].count()
                )

                rank_key = f"{tipo}_{rank}"
                month_data[rank_key] = {
                    'total_workers': int(len(workers)),
                    'active_workers': int(len(active_workers)),
                    'avg_flight_hours': round(float(flight_hours_per_worker.mean()) if len(flight_hours_per_worker) > 0 else 0, 2),
                    'avg_flights': round(float(flights_per_worker.mean()) if len(flights_per_worker) > 0 else 0, 2),
                    'avg_duty_days': round(float(duty_days_per_worker.mean()) if len(duty_days_per_worker) > 0 else 0, 2),
                    'workers_with_airport_turns': int(len(at_workers)),
                    'avg_airport_turns': round(float(at_counts.mean()) if len(at_counts) > 0 else 0, 2),
                    'avg_home_turns': round(float(ht_counts.mean()) if len(ht_counts) > 0 else 0, 2),
                    # Distribution for histograms
                    'flight_hours_dist': {
                        str(k): round(float(v), 2)
                        for k, v in flight_hours_per_worker.items()
                    },
                    'airport_turns_dist': {
                        str(k): int(v)
                        for k, v in at_counts.items()
                    },
                }

        output['monthly'][period_key] = month_data

    # Per-worker data across all periods
    for wid in df['Staff Num'].unique():
        wdf = df[df['Staff Num'] == wid]
        name = wdf['Nombre completo'].iloc[0]
        rank = wdf['Rank'].iloc[0]

        worker_data = {
            'name': str(name),
            'rank': str(rank),
            'periods': {}
        }

        for period in periods:
            period_key = str(period)[:7]
            pwdf = wdf[wdf['periodo'].dt.to_period('M') == pd.Period(period_key, 'M')]
            if pwdf.empty:
                continue

            for tipo in ['Publicado', 'Efectuado']:
                tpwdf = pwdf[pwdf['tipo_rol'] == tipo]
                if tpwdf.empty:
                    continue

                flight_hours = float(tpwdf[tpwdf['act_type'] == 'VUELO']['block_hours'].sum())
                flight_count = int((tpwdf['act_type'] == 'VUELO').sum())
                airport_turns = int((tpwdf['act_type'] == 'TURNO_AEROPUERTO').sum())
                home_turns = int((tpwdf['act_type'] == 'TURNO_DOMICILIO').sum())
                free_days = int(tpwdf['act_type'].isin({'DIA_LIBRE', 'DIA_LIBRE_SOLICITADO'}).sum())
                white_days = int((tpwdf['act_type'] == 'DIA_BLANCO').sum())
                vac_days = int((tpwdf['act_type'] == 'VACACIONES').sum())
                sick_days = int((tpwdf['act_type'] == 'LICENCIA_MEDICA').sum())
                oof_days = int((tpwdf['act_type'] == 'FUERA_VUELO').sum())
                reva = int((tpwdf['act_type'] == 'REVA').sum())
                clases = int((tpwdf['act_type'] == 'CLASES_TIERRA').sum())
                bloque_libre = int((tpwdf['act_type'] == 'BLOQUE_LIBRE').sum())
                dh = int((tpwdf['act_type'] == 'DH').sum())

                # Day breakdown for timeline
                timeline = []
                for _, row in tpwdf.sort_values('Str Dt').iterrows():
                    timeline.append({
                        'date': str(row['Str Dt'])[:10] if not pd.isna(row['Str Dt']) else '',
                        'activity': str(row['Activity']),
                        'act_type': str(row['act_type']),
                        'block_hours': round(float(row['block_hours']), 2),
                        'dep': str(row['Dep Port']) if not pd.isna(row['Dep Port']) else '',
                        'arv': str(row['Arv Port']) if not pd.isna(row['Arv Port']) else '',
                    })

                pkey = f"{period_key}_{tipo}"
                worker_data['periods'][pkey] = {
                    'flight_hours': round(flight_hours, 2),
                    'flight_count': flight_count,
                    'airport_turns': airport_turns,
                    'home_turns': home_turns,
                    'free_days': free_days,
                    'white_days': white_days,
                    'vac_days': vac_days,
                    'sick_days': sick_days,
                    'oof_days': oof_days,
                    'reva': reva,
                    'clases': clases,
                    'bloque_libre': bloque_libre,
                    'dh': dh,
                    'timeline': timeline,
                }

        output['workers'][str(wid)] = worker_data

    return output

def build_workers_index(df):
    """Build a simple workers index {rank: [{id, name}]}"""
    idx = {}
    for rank in ['CCM', 'CC']:
        rdf = df[df['Rank'] == rank][['Staff Num', 'Nombre completo']].drop_duplicates('Staff Num')
        rdf = rdf.sort_values('Nombre completo')
        idx[rank] = [
            {'id': str(row['Staff Num']), 'name': str(row['Nombre completo'])}
            for _, row in rdf.iterrows()
        ]
    return idx

def main():
    print("STCLE Parser - Loading data...")
    df = load_all_files()
    print(f"Total rows: {len(df)}")
    print(f"Periods: {sorted(df['periodo'].dropna().dt.to_period('M').unique())}")
    print(f"Workers: {df['Staff Num'].nunique()}")

    print("Computing KPIs...")
    kpis = compute_kpis(df)

    print("Building workers index...")
    workers_index = build_workers_index(df)
    kpis['workers_index'] = workers_index

    out_path = os.path.join(OUTPUT_DIR, 'dashboard_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(kpis, f, ensure_ascii=False, default=str)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Output: {out_path} ({size_kb:.1f} KB)")
    print("Done!")

if __name__ == '__main__':
    main()
