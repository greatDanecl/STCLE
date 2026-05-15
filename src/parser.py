"""
STCLE Dashboard - Data Parser
Parses all Excel files (Publicado + Efectuado) from /data folder
and generates a unified JSON for the dashboard.

Activity codes based on CA__DIGOS_IFN.xlsx:
  Column D = Code IFN (used in role files)
  Column B = Description (Spanish label)
"""

import pandas as pd
import numpy as np
import json
import os
import re
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')

# ──────────────────────────────────────────────────────────────
# ACTIVITY MAP  {code_ifn: (act_type, label_es)}
# ──────────────────────────────────────────────────────────────
ACTIVITY_MAP = {
    'ASB':    ('TURNO_AEROPUERTO',    'Turno en Aeropuerto'),
    'ASB1':   ('TURNO_AEROPUERTO',    'Turno en Aeropuerto'),
    'ASB2':   ('TURNO_AEROPUERTO',    'Turno en Aeropuerto'),
    'ASB3':   ('TURNO_AEROPUERTO',    'Turno en Aeropuerto'),
    'HSB':    ('TURNO_DOMICILIO',     'Turno en Casa'),
    'HSB1':   ('TURNO_DOMICILIO',     'Turno en Casa'),
    'HSB2':   ('TURNO_DOMICILIO',     'Turno en Casa'),
    'HB7':    ('TURNO_DOMICILIO',     'Turno en Casa'),
    'DO':     ('DIA_LIBRE',           'Dia Libre Normal'),
    'DOA':    ('DIA_LIBRE',           'Dia Libre'),
    'DOC':    ('DIA_LIBRE',           'Dia Libre'),
    'DOM':    ('DIA_LIBRE',           'Lactancia'),
    'DB':     ('DIA_LIBRE',           'Cumpleanos TC'),
    'DH':     ('DIA_LIBRE',           'Libre Feriado'),
    'DW':     ('DIA_LIBRE',           'Libre Fin de Semana'),
    'DR':     ('DIA_LIBRE_SOLICITADO','Dia Libre Pedido'),
    'DOR1':   ('DIA_LIBRE_SOLICITADO','Libre Solicitado 1'),
    'DOR2':   ('DIA_LIBRE_SOLICITADO','Libre Solicitado 2'),
    'DOR3':   ('DIA_LIBRE_SOLICITADO','Libre Solicitado 3'),
    'DOR4':   ('DIA_LIBRE_SOLICITADO','Libre Solicitado 4'),
    'B':      ('DIA_BLANCO',          'Blanco en Rol'),
    'Q':      ('BLOQUE_LIBRE',        'Bloque Libre Quincena'),
    'ME':     ('LICENCIA_MEDICA',     'MAE Cabina'),
    'MT':     ('LICENCIA_MEDICA',     'Reunion'),
    'MTC':    ('LICENCIA_MEDICA',     'Reunion Jefatura'),
    'MTE':    ('LICENCIA_MEDICA',     'Reunion Ampliada'),
    'MTI':    ('LICENCIA_MEDICA',     'Reunion Instructor'),
    'MTU':    ('LICENCIA_MEDICA',     'Reunion Sindical'),
    'SICK':   ('LICENCIA_MEDICA',     'Licencia Medica'),
    'LW':     ('LICENCIA_MEDICA',     'Licencia Medica'),
    'VAC':    ('VACACIONES',          'Vacaciones'),
    'VC':     ('VACACIONES',          'Vacaciones'),
    'OOF':    ('FUERA_VUELO',         'Fuera de Vuelo'),
    'LNP':    ('FUERA_VUELO',         'Fuera de Vuelo'),
    'RL1':    ('REVA',                'REVA'),
    'RL3':    ('REVA',                'REVA'),
    'RV8':    ('REVA',                'REVA'),
    'CLA':    ('CLASES_TIERRA',       'Curso en Tierra'),
    'ASC':    ('CLASES_TIERRA',       'Curso Ascensos'),
    'CBT':    ('CLASES_TIERRA',       'CBT'),
    'CLP':    ('CLASES_TIERRA',       'Curso LP'),
    'CRM':    ('CLASES_TIERRA',       'Curso CRM'),
    'CRS':    ('CLASES_TIERRA',       'Curso'),
    'DIT':    ('CLASES_TIERRA',       'Ditching'),
    'EGA':    ('CLASES_TIERRA',       'Entrenamiento Anual'),
    'EMG':    ('CLASES_TIERRA',       'Entrenamiento Anual'),
    'EVA':    ('CLASES_TIERRA',       'Evacuacion'),
    'IET':    ('CLASES_TIERRA',       'Instructor Tierra'),
    'ING':    ('CLASES_TIERRA',       'Curso Ingles'),
    'ITP':    ('CLASES_TIERRA',       'Instr. Terrestre Per.'),
    'MCK':    ('CLASES_TIERRA',       'Practicas Emergencia'),
    'REV':    ('CLASES_TIERRA',       'Revalidacion'),
    'SIM_XX': ('CLASES_TIERRA',       'Simulador'),
    'SVC':    ('CLASES_TIERRA',       'Capacitacion Servicio'),
    'SVC2':   ('CLASES_TIERRA',       'Capacitacion Servicio'),
    'TTS':    ('CLASES_TIERRA',       'Traslado Trip. Base'),
    'TTB':    ('CLASES_TIERRA',       'Traslado Trip. Base'),
    'CAA':    ('CLASES_TIERRA',       'Capacitacion'),
    'CNH':    ('CLASES_TIERRA',       'Capacitacion'),
    'CNA':    ('CLASES_TIERRA',       'Capacitacion'),
    'CH':     ('CLASES_TIERRA',       'Capacitacion'),
    'BCM':    ('CLASES_TIERRA',       'Capacitacion'),
    'BCN':    ('CLASES_TIERRA',       'Capacitacion'),
    'ADM':    ('ADM',                 'Administrativo'),
    'BKF':    ('ADM',                 'Desayuno'),
    'CS':     ('ADM',                 'Comision de Servicio'),
    'EVE':    ('ADM',                 'Evento'),
    'FB':     ('ADM',                 'Feedback'),
    'LP':     ('LP',                  'LP'),
    'VUSA':   ('VUSA',                'Entrevista de Visa'),
}

LABEL_MAP = {code: v[1] for code, v in ACTIVITY_MAP.items()}
AUSENCIA_PROLONGADA = {'VACACIONES', 'FUERA_VUELO', 'LICENCIA_MEDICA', 'VUSA'}


def classify_activity(act):
    if pd.isna(act):
        return 'OTRO'
    act = str(act).strip().upper()
    if re.match(r'^LA\d+', act) or act == 'LA':
        return 'VUELO'
    if act in ACTIVITY_MAP:
        return ACTIVITY_MAP[act][0]
    if act.startswith('ASB'):
        return 'TURNO_AEROPUERTO'
    if act.startswith('HSB') or act.startswith('HB'):
        return 'TURNO_DOMICILIO'
    if act.startswith('SIM'):
        return 'CLASES_TIERRA'
    return 'OTRO'


def get_activity_label(act):
    if pd.isna(act):
        return 'Otro'
    act = str(act).strip().upper()
    if re.match(r'^LA\d+', act) or act == 'LA':
        return f'Vuelo {act}'
    return LABEL_MAP.get(act, act)


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
    try:
        return pd.to_datetime(s, format='%d%b%Y')
    except Exception:
        pass
    try:
        return pd.to_datetime(s)
    except Exception:
        return pd.NaT


def load_file(filepath):
    xl  = pd.ExcelFile(filepath)
    df  = pd.read_excel(filepath, sheet_name=xl.sheet_names[0])
    fname = os.path.basename(filepath).upper()

    tipo_rol = 'Publicado'
    if any(k in fname for k in ('EFECTUADO', 'EFECT', 'EF_', '_EF_')):
        tipo_rol = 'Efectuado'
    if 'tipo_rol' in df.columns and not df.empty:
        tipo_rol = df['tipo_rol'].iloc[0]

    if 'Nombre completo' not in df.columns:
        if 'First Name' in df.columns and 'Last Name' in df.columns:
            df['Nombre completo'] = (
                df['First Name'].fillna('') + ' ' + df['Last Name'].fillna('')
            ).str.strip()
        else:
            df['Nombre completo'] = df.get('Staff Num', '').astype(str)

    df['Str Dt']     = df['Str Dt'].apply(parse_str_dt)
    df['periodo']    = df['Str Dt'].dt.to_period('M').dt.to_timestamp()
    df['block_hours']= df['Block Time'].apply(timedelta_to_hours)
    df['act_type']   = df['Activity'].apply(classify_activity)
    df['tipo_rol']   = tipo_rol
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
    all_dfs = []
    for f in sorted(os.listdir(DATA_DIR)):
        if not f.endswith('.xlsx'):
            continue
        path = os.path.join(DATA_DIR, f)
        try:
            df = load_file(path)
            all_dfs.append(df)
            print(f"  Loaded: {f} -> {len(df)} rows, tipo_rol={df['tipo_rol'].iloc[0]}")
        except Exception as e:
            print(f"  ERROR loading {f}: {e}")
    if not all_dfs:
        return pd.DataFrame()
    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=['Staff Num', 'Str Dt', 'Activity', 'tipo_rol'], keep='last'
    )
    return combined


def compute_kpis(df):
    periods = sorted(df['periodo'].dropna().unique())
    output  = {
        'periods':         [str(p)[:7] for p in periods],
        'monthly':         {},
        'workers':         {},
        'activity_labels': LABEL_MAP,
    }

    for period in periods:
        period_key = str(period)[:7]
        period_df  = df[df['periodo'].dt.to_period('M') == pd.Period(period_key, 'M')]
        if period_df.empty:
            continue

        month_data = {}
        for tipo in ['Publicado', 'Efectuado']:
            tdf = period_df[period_df['tipo_rol'] == tipo]
            if tdf.empty:
                continue

            for rank in ['CCM', 'CC']:
                rdf = tdf[tdf['Rank'] == rank]
                if rdf.empty:
                    continue

                workers = rdf['Staff Num'].unique()
                active_workers = []
                for wid in workers:
                    wdf    = rdf[rdf['Staff Num'] == wid]
                    total  = wdf.shape[0]
                    absent = wdf[wdf['act_type'].isin(AUSENCIA_PROLONGADA)].shape[0]
                    if total > 0 and (absent / total) < 0.5:
                        active_workers.append(wid)

                ardf = rdf[rdf['Staff Num'].isin(active_workers)]

                fh_per_w   = ardf[ardf['act_type'] == 'VUELO'].groupby('Staff Num')['block_hours'].sum()
                fl_per_w   = ardf[ardf['act_type'] == 'VUELO'].groupby('Staff Num')['Activity'].count()
                duty_per_w = (
                    ardf[~ardf['act_type'].isin(
                        {'DIA_LIBRE','DIA_LIBRE_SOLICITADO','DIA_BLANCO',
                         'VACACIONES','LICENCIA_MEDICA','FUERA_VUELO','BLOQUE_LIBRE'}
                    )].groupby('Staff Num')['Str Dt'].nunique()
                )
                at_workers = ardf[ardf['act_type'] == 'TURNO_AEROPUERTO']['Staff Num'].unique()
                at_counts  = ardf[ardf['act_type'] == 'TURNO_AEROPUERTO'].groupby('Staff Num')['Activity'].count()
                ht_counts  = ardf[ardf['act_type'] == 'TURNO_DOMICILIO'].groupby('Staff Num')['Activity'].count()

                month_data[f'{tipo}_{rank}'] = {
                    'total_workers':              int(len(workers)),
                    'active_workers':             int(len(active_workers)),
                    'avg_flight_hours':           round(float(fh_per_w.mean())   if len(fh_per_w)   > 0 else 0, 2),
                    'avg_flights':                round(float(fl_per_w.mean())   if len(fl_per_w)   > 0 else 0, 2),
                    'avg_duty_days':              round(float(duty_per_w.mean()) if len(duty_per_w) > 0 else 0, 2),
                    'workers_with_airport_turns': int(len(at_workers)),
                    'avg_airport_turns':          round(float(at_counts.mean())  if len(at_counts)  > 0 else 0, 2),
                    'avg_home_turns':             round(float(ht_counts.mean())  if len(ht_counts)  > 0 else 0, 2),
                    'flight_hours_dist':          {str(k): round(float(v), 2) for k, v in fh_per_w.items()},
                    'airport_turns_dist':         {str(k): int(v) for k, v in at_counts.items()},
                }

        output['monthly'][period_key] = month_data

    for wid in df['Staff Num'].unique():
        wdf  = df[df['Staff Num'] == wid]
        name = wdf['Nombre completo'].iloc[0]
        rank = wdf['Rank'].iloc[0]
        worker_data = {'name': str(name), 'rank': str(rank), 'periods': {}}

        for period in periods:
            period_key = str(period)[:7]
            pwdf = wdf[wdf['periodo'].dt.to_period('M') == pd.Period(period_key, 'M')]
            if pwdf.empty:
                continue

            for tipo in ['Publicado', 'Efectuado']:
                tpwdf = pwdf[pwdf['tipo_rol'] == tipo]
                if tpwdf.empty:
                    continue

                timeline = [
                    {
                        'date':        str(row['Str Dt'])[:10] if not pd.isna(row['Str Dt']) else '',
                        'activity':    str(row['Activity']),
                        'label':       get_activity_label(row['Activity']),
                        'act_type':    str(row['act_type']),
                        'block_hours': round(float(row['block_hours']), 2),
                        'dep':         str(row['Dep Port']) if not pd.isna(row['Dep Port']) else '',
                        'arv':         str(row['Arv Port']) if not pd.isna(row['Arv Port']) else '',
                    }
                    for _, row in tpwdf.sort_values('Str Dt').iterrows()
                ]

                worker_data['periods'][f'{period_key}_{tipo}'] = {
                    'flight_hours':  round(float(tpwdf[tpwdf['act_type']=='VUELO']['block_hours'].sum()), 2),
                    'flight_count':  int((tpwdf['act_type']=='VUELO').sum()),
                    'airport_turns': int((tpwdf['act_type']=='TURNO_AEROPUERTO').sum()),
                    'home_turns':    int((tpwdf['act_type']=='TURNO_DOMICILIO').sum()),
                    'free_days':     int(tpwdf['act_type'].isin({'DIA_LIBRE','DIA_LIBRE_SOLICITADO'}).sum()),
                    'white_days':    int((tpwdf['act_type']=='DIA_BLANCO').sum()),
                    'vac_days':      int((tpwdf['act_type']=='VACACIONES').sum()),
                    'sick_days':     int((tpwdf['act_type']=='LICENCIA_MEDICA').sum()),
                    'oof_days':      int((tpwdf['act_type']=='FUERA_VUELO').sum()),
                    'reva':          int((tpwdf['act_type']=='REVA').sum()),
                    'clases':        int((tpwdf['act_type']=='CLASES_TIERRA').sum()),
                    'bloque_libre':  int((tpwdf['act_type']=='BLOQUE_LIBRE').sum()),
                    'lp':            int((tpwdf['act_type']=='LP').sum()),
                    'adm':           int((tpwdf['act_type']=='ADM').sum()),
                    'vusa':          int((tpwdf['act_type']=='VUSA').sum()),
                    'timeline':      timeline,
                }

        output['workers'][str(wid)] = worker_data

    return output


def build_workers_index(df):
    idx = {}
    for rank in ['CCM', 'CC']:
        rdf = df[df['Rank']==rank][['Staff Num','Nombre completo']].drop_duplicates('Staff Num')
        rdf = rdf.sort_values('Nombre completo')
        idx[rank] = [{'id': str(r['Staff Num']), 'name': str(r['Nombre completo'])} for _, r in rdf.iterrows()]
    return idx


def main():
    print("STCLE Parser - Loading data...")
    df = load_all_files()
    print(f"Total rows: {len(df)}")
    print(f"Periods: {sorted(df['periodo'].dropna().dt.to_period('M').unique())}")
    print(f"Workers: {df['Staff Num'].nunique()}")

    known = set(ACTIVITY_MAP.keys())
    unknown = set()
    for act in df['Activity'].dropna().unique():
        a = str(act).strip().upper()
        if not re.match(r'^LA\d+', a) and a not in known and a != 'LA':
            if not any(a.startswith(p) for p in ('ASB','HSB','HB','SIM')):
                unknown.add(a)
    if unknown:
        print(f"  Codigos sin clasificacion explicita (OTRO): {sorted(unknown)}")

    print("Computing KPIs...")
    kpis = compute_kpis(df)
    print("Building workers index...")
    kpis['workers_index'] = build_workers_index(df)

    out_path = os.path.join(OUTPUT_DIR, 'dashboard_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(kpis, f, ensure_ascii=False, default=str)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Output: {out_path} ({size_kb:.1f} KB)")
    print("Done!")


if __name__ == '__main__':
    main()
