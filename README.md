# 📊 STCLE Dashboard — Roles Tripulantes LanExpress

Dashboard interactivo para el **Sindicato de Tripulantes de Cabina de LanExpress (STCLE)**.  
Visualiza KPIs de roles publicados y efectuados para JSB (CCM) y TC (CC), con comparativas individuales y vista de calendario.

---

## 🗂 Estructura del Repositorio

```
stcle-dashboard/
├── data/                          ← Archivos Excel (sube aquí los nuevos meses)
│   ├── CABLU_Publicado_Sept25.xlsx
│   ├── Publicado_CABLU_OCT25_1.xlsx
│   ├── Publicado_CABLU_NOV25.xlsx
│   ├── Roles_Sindicatos_Ef_Nov_Pub_Dic25_CABLU.xlsx  ← Efectuado/Publicado diciembre
│   ├── CABLU_Publicado_ENE26.xlsx
│   └── Publicado_Sind_CabLU_FEB26.xlsx
├── src/
│   ├── parser.py                  ← Parser principal (lee data/, genera JSON)
│   ├── split_data.py              ← Divide el JSON en archivos livianos
│   ├── summary_data.json          ← Generado automáticamente
│   ├── distributions.json         ← Generado automáticamente
│   ├── logo_b64.txt               ← Logo STCLE en base64
│   └── workers/                   ← Un JSON por tripulante (generado automáticamente)
│       └── 1234.json
├── .github/
│   └── workflows/
│       └── process_data.yml       ← Workflow automático
├── index.html                     ← Dashboard web
└── README.md
```

---

## 🚀 Cómo subir un nuevo mes

### Rol Publicado
1. Nombra el archivo con el patrón: `Publicado_CABLU_ABR26.xlsx` (o similar)
2. Arrástralo a la carpeta `data/` en GitHub
3. Haz commit — el workflow se activa automáticamente
4. En ~1 minuto los datos aparecerán en el dashboard

### Rol Efectuado
1. Nombra el archivo con **EFECTUADO** o **Ef** en el nombre, ej: `Efectuado_CABLU_MAR26.xlsx`
2. Súbelo a `data/`
3. El sistema lo detecta automáticamente como tipo "Efectuado"
4. El dashboard mostrará el % de adherencia Publicado vs Efectuado

---

## 📋 Convención de Nombres de Archivos

| Tipo | Ejemplo | Detectado como |
|------|---------|----------------|
| Publicado | `Publicado_CABLU_MAR26.xlsx` | Publicado ✅ |
| Publicado | `CABLU_Publicado_ABR26.xlsx` | Publicado ✅ |
| Efectuado | `Efectuado_CABLU_MAR26.xlsx` | Efectuado ✅ |
| Efectuado | `Roles_Ef_ABR26_CABLU.xlsx` | Efectuado ✅ |
| Efectuado | `CABLU_EF_MAY26.xlsx` | Efectuado ✅ |

---

## 📊 KPIs del Dashboard

### Vista General (por cargo y mes)
- **Tripulantes en plantilla** / activos (excluye ausencias prolongadas)
- **Horas de vuelo promedio**
- **Tramos de vuelo promedio**
- **Días de servicio promedio**
- **Turnos en aeropuerto** — cuántos tripulantes los tienen, promedio
- **Turnos en domicilio promedio**
- **Adherencia al rol** — cuando hay datos de efectuado

### Vista Individual (tripulante seleccionado)
- Todos los KPIs anteriores + comparativa vs promedio del cargo
- **Percentil de horas de vuelo** dentro de su cargo
- **Calendario mensual** de actividades codificado por color
- **Evolución histórica** de horas de vuelo (todos los meses disponibles)
- Desglose: DO, B, Q, Vacaciones, Licencia, OOF, AS, HS, REVA, Clases, etc.

---

## 🏠 Ver el Dashboard Localmente

```bash
# Con Python (simple server)
python3 -m http.server 8000
# Luego abre: http://localhost:8000
```

---

## 🔧 Configuración del Repositorio para GitHub Pages

1. Ve a **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `root`
4. El dashboard estará en: `https://TU_ORG.github.io/stcle-dashboard/`

---

## 📂 Columnas Esperadas en los Excel

El parser acepta dos formatos:

### Formato A (archivos nuevos con sindicato/periodo)
`Staff Num | Nombre completo | Fleet | Company | departure_airport_code | Rank | Str Dt | Str Tm | End Dt | End Tm | Activity | Dep Port | Arv Port | Block Time | sindicato | periodo | tipo_rol`

### Formato B (archivo FEB26 con First/Last Name separados)
`Staff Num | National Id | First Name | Last Name | Company | Fleet | Base | Rank | ActRank | CI Dt | CI Tm | Str Dt | Str Tm | End Dt | End Tm | ... | Activity | ... | Block Time`

---

## 🎨 Codificación de Actividades

| Código | Tipo | Color |
|--------|------|-------|
| `LA###` | Vuelo | 🔵 Azul marino |
| `AS##` | Turno aeropuerto | 🟠 Naranja |
| `HS##` | Turno domicilio | 🟣 Púrpura |
| `B` | Día blanco | ⬜ Gris claro |
| `DO` | Día libre | 🟢 Verde claro |
| `DR` | Día libre solicitado | 💜 Lila |
| `VAC/VC` | Vacaciones | 🟡 Amarillo |
| `SICK/ME/MT` | Licencia médica | 🔴 Rojo claro |
| `OOF` | Fuera de vuelo | 🔵 Azul cielo |
| `Q` | Bloque libre quincena | 🟩 Verde |
| `RL1/RL3` | REVA | 🔷 Azul índigo |
| `CLA` | Clases en tierra | 🩵 Verde agua |
| `DH` | Dead-head | 🍑 Salmón |
| `VUSA` | Trámite visa USA | 🟡 Amarillo claro |

---

*Desarrollado para STCLE · Unidos por un bien común ✈*
