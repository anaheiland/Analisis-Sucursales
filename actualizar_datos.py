#!/usr/bin/env python3
"""
=============================================================================
QTC DASHBOARD — SCRIPT DE ACTUALIZACIÓN SEMANAL
=============================================================================
Propósito : Lee los 5 CSV exportados desde Lark Base y genera qtc_data.json
            que alimenta el dashboard en tiempo real.
Frecuencia : Ejecutar cada lunes (o al subir nuevos CSVs)
Autor      : QTC Inteligencia Comercial
Versión    : 1.0
=============================================================================

REQUISITOS:
    pip install pandas

USO:
    python actualizar_datos.py
    python actualizar_datos.py --carpeta /ruta/a/mis/csvs

ARCHIVOS DE ENTRADA (exportar desde Lark Base cada semana):
    ├── KPI_Equipo_comercial.csv
    ├── Resultados.csv
    ├── Ventas.csv
    ├── Visitas_y_demostraciones.csv
    └── CRM.csv

ARCHIVO DE SALIDA:
    └── qtc_data.json   ← copiar junto al dashboard HTML

=============================================================================
"""

import pandas as pd
import json
import os
import sys
import argparse
from datetime import datetime

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────

# Mapeo de nombres de archivo. Ajusta si tus exportaciones tienen otro nombre.
ARCHIVOS = {
    "kpi":     "KPI_Equipo_comercial.csv",
    "res":     "Resultados.csv",
    "ventas":  "Ventas.csv",
    "visitas": "Visitas_y_demostraciones.csv",
    "crm":     "CRM.csv",
}

# ── UMBRALES PARA ALERTAS (editables por la jefatura) ──────────────────────
UMBRALES = {
    # KPI mínimo aceptable por ejecutivo (0–1)
    "kpi_rojo":   0.40,   # < 40% → alerta crítica
    "kpi_amarillo": 0.70, # < 70% → atención

    # Meses consecutivos sin ventas para disparar alerta
    "meses_sin_venta_critico": 2,
    "meses_sin_venta_atencion":1,

    # Tasa conversión CRM→Venta mínima esperada
    "conv_rojo":    5.0,   # < 5%  → crítico
    "conv_amarillo": 13.0, # < 13% → atención

    # Caída de KPI entre meses consecutivos (puntos porcentuales)
    "caida_kpi_critica":  40,  # ej: 100% → 60% = caída de 40pp
    "caida_kpi_atencion": 20,

    # CRM mínimo mensual esperado por sucursal
    "crm_minimo": 5,

    # Ventas potenciales altas (campo)
    "vp_alto": 12,
    "vp_medio":  6,
}

# ── LÓGICA PRINCIPAL ───────────────────────────────────────────────────────

def leer_csv(carpeta, clave):
    """Lee un CSV con manejo robusto de encoding."""
    path = os.path.join(carpeta, ARCHIVOS[clave])
    for enc in ["utf-8", "utf-8-sig", "latin-1"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"  ✓ {ARCHIVOS[clave]} ({len(df)} filas)")
            return df
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            print(f"  ✗ No encontrado: {path}")
            sys.exit(1)
    print(f"  ✗ No se pudo leer: {path}")
    sys.exit(1)


def procesar_resultados(df):
    """Limpia y estandariza el DataFrame de resultados."""
    col_map = {
        "Tienda": "tienda",
        "Año":    "anio",
        "Mes":    "mes",
        "Ventas": "ventas",
        "Meta-Ventas": "meta",
        "CRM":    "crm",
        "Reus":   "reus",
        "Prom. Tiempo Venta": "tiempo_venta",
        "Efectividad": "efectividad",
    }
    df = df.rename(columns=col_map)
    cols = [c for c in col_map.values() if c in df.columns]
    df = df[cols].copy()
    df["anio"] = pd.to_numeric(df.get("anio", 0), errors="coerce").fillna(0).astype(int)
    df["efectividad"] = (
        df.get("efectividad", pd.Series(dtype=float))
        .astype(str).str.replace("%", "").str.strip()
    )
    df["efectividad"] = pd.to_numeric(df["efectividad"], errors="coerce").fillna(0)
    df = df[df["anio"] > 0]          # excluir filas vacías
    df = df.fillna(0)
    return df


def procesar_kpi(df):
    """Limpia KPI de ejecutivos."""
    col_map = {
        "Tienda":                           "tienda",
        "Ejecutivo comercial":              "ejecutivo",
        "Fecha":                            "fecha",
        "Academy":                          "academy",
        "Demostraciones x Ejecutivo":       "demos",
        "Meta Demostraciones X ejecutivo":  "meta_demos",
        "Reunión con cliente X Ejecutivo":  "reus",
        "Meta de reuniones":                "meta_reus",
        "Clientes nuevos X Ejecutivo":      "clientes_nuevos",
        "Meta de clientes nuevos":          "meta_clientes",
        "Ventas por Ejecutivo":             "ventas",
        "Meta de Ventas por Ejecutivo":     "meta_ventas",
        "KPI":                              "kpi",
        "KPI 2":                            "kpi2",
    }
    df = df.rename(columns=col_map)
    cols = [c for c in col_map.values() if c in df.columns]
    df = df[cols].copy()
    df["kpi"] = pd.to_numeric(df.get("kpi", 0), errors="coerce").fillna(0)
    df = df[df["fecha"].notna() & (df["fecha"].astype(str).str.len() >= 7)]
    df = df.fillna(0)
    return df


def procesar_funnel(crm_df, visitas_df):
    """Construye tabla de funnel CRM → Demo → Venta + ventas potenciales."""
    crm_auth = crm_df[crm_df.get("Aprobación", pd.Series("")) == "AUTORIZADO"].copy()
    funnel = crm_auth.groupby(["Tienda", "Estado"]).size().unstack(fill_value=0).reset_index()
    funnel.columns.name = None
    # Asegurar columnas mínimas
    for col in ["CRM", "Demostracion", "Ventas"]:
        if col not in funnel.columns:
            funnel[col] = 0
    funnel = funnel[["Tienda"] + [c for c in ["CRM", "Demostracion", "Ventas"] if c in funnel.columns]]

    vp = visitas_df.groupby("Tienda")["Ventas Potenciales"].sum().reset_index()
    vp.columns = ["Tienda", "ventas_potenciales"]
    funnel = funnel.merge(vp, on="Tienda", how="left").fillna(0)
    return funnel


def generar_alertas(res_df, kpi_df, funnel_df):
    """
    ─────────────────────────────────────────────────────────────────────────
    VARIABLES DE ALERTA — DEFINICIÓN COMPLETA
    ─────────────────────────────────────────────────────────────────────────
    NIVEL ROJO (acción inmediata):
      A1 — Tasa de conversión CRM→Venta = 0% con CRM > 0 y demos > 0
      A2 — N meses consecutivos sin ventas (umbral: meses_sin_venta_critico)
      A3 — KPI ejecutivo < kpi_rojo por 2+ meses consecutivos
      A4 — CRM mensual = 0 (inactividad total)
      A5 — Caída de KPI ≥ caida_kpi_critica pp entre último y penúltimo mes

    NIVEL ÁMBAR (oportunidad / atención):
      B1 — Ventas potenciales en campo ≥ vp_alto pero conv < conv_amarillo
      B2 — KPI cayó ≥ caida_kpi_atencion pp (no llega a crítico)
      B3 — Tasa conversión entre conv_rojo y conv_amarillo
      B4 — N meses consecutivos sin ventas (umbral: meses_sin_venta_atencion)
      B5 — Sucursal con demos altas pero sin cierres (ratio demo→venta < 10%)
    ─────────────────────────────────────────────────────────────────────────
    """
    alertas = {"rojas": [], "ambar": []}
    T = UMBRALES
    anio_max = res_df["anio"].max() if len(res_df) else 2026

    # — Calcular conversiones por tienda —
    conv = {}
    for t, g in funnel_df.groupby("Tienda"):
        crm   = g["CRM"].sum()
        demo  = g.get("Demostracion", pd.Series([0])).sum()
        venta = g["Ventas"].sum()
        conv[t] = {
            "crm": int(crm),
            "demo": int(demo),
            "venta": int(venta),
            "tasa_conv": round(venta / crm * 100, 1) if crm > 0 else 0,
            "tasa_demo_venta": round(venta / demo * 100, 1) if demo > 0 else 0,
            "vp": float(g.get("ventas_potenciales", pd.Series([0])).sum()),
        }

    # — Analizar KPI por ejecutivo —
    exec_kpi = {}
    for e, g in kpi_df.groupby(["ejecutivo", "tienda"]):
        g_sorted = g.sort_values("fecha")
        kpis     = g_sorted["kpi"].tolist()
        fechas   = g_sorted["fecha"].tolist()
        exec_kpi[e] = {"kpis": kpis, "fechas": fechas, "tienda": e[1]}

    # — Analizar ventas mensuales por tienda (año corriente) —
    res_curr = res_df[res_df["anio"] == anio_max]
    MESES_ORD = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"]

    for tienda, g in res_curr.groupby("tienda"):
        g_sorted = g.sort_values("mes", key=lambda s: s.map(
            {m: i for i, m in enumerate(MESES_ORD)}
        ))
        ventas_mes = g_sorted["ventas"].tolist()
        crm_mes    = g_sorted["crm"].tolist()
        d_conv     = conv.get(tienda, {})

        # A1 — Conversión cero con actividad
        if d_conv.get("tasa_conv", 0) == 0 and d_conv.get("crm", 0) >= T["crm_minimo"] and d_conv.get("demo", 0) > 0:
            alertas["rojas"].append({
                "tipo": "A1", "tienda": tienda,
                "titulo": f"{tienda} — Conversión 0% con {d_conv['crm']} CRM y {d_conv['demo']} demos",
                "detalle": "Alta actividad sin cierres. Revisar proceso de cotización y seguimiento post-demo.",
                "kpi_variable": "tasa_conv_crm_venta",
                "valor": 0,
            })

        # A2 — Meses consecutivos sin ventas
        consecutivos = 0
        for v in reversed(ventas_mes):
            if v == 0:
                consecutivos += 1
            else:
                break
        if consecutivos >= T["meses_sin_venta_critico"]:
            alertas["rojas"].append({
                "tipo": "A2", "tienda": tienda,
                "titulo": f"{tienda} — {consecutivos} meses consecutivos sin ventas",
                "detalle": f"Revisar estrategia de territorio y perfil del ejecutivo.",
                "kpi_variable": "ventas_mensuales_consecutivas_cero",
                "valor": consecutivos,
            })
        elif consecutivos >= T["meses_sin_venta_atencion"]:
            alertas["ambar"].append({
                "tipo": "B4", "tienda": tienda,
                "titulo": f"{tienda} — {consecutivos} meses sin ventas",
                "detalle": "Tendencia preocupante. Revisar actividad del ejecutivo.",
                "kpi_variable": "ventas_mensuales_consecutivas_cero",
                "valor": consecutivos,
            })

        # A4 — CRM mensual = 0 en último mes
        if crm_mes and crm_mes[-1] == 0:
            alertas["rojas"].append({
                "tipo": "A4", "tienda": tienda,
                "titulo": f"{tienda} — Sin registro CRM en el último mes",
                "detalle": "Inactividad total en prospección. Verificar si el ejecutivo está activo.",
                "kpi_variable": "crm_mensual",
                "valor": 0,
            })

        # B1 — Ventas potenciales altas sin conversión
        vp = d_conv.get("vp", 0)
        if vp >= T["vp_alto"] and d_conv.get("tasa_conv", 0) < T["conv_amarillo"]:
            alertas["ambar"].append({
                "tipo": "B1", "tienda": tienda,
                "titulo": f"{tienda} — {int(vp)} ventas potenciales sin capitalizar",
                "detalle": f"Conversión actual: {d_conv.get('tasa_conv',0)}%. Alto potencial de campo no convertido. Soporte de cierre recomendado.",
                "kpi_variable": "ventas_potenciales_campo",
                "valor": vp,
            })

        # B3 — Conversión baja
        tasa = d_conv.get("tasa_conv", None)
        if tasa is not None and T["conv_rojo"] <= tasa < T["conv_amarillo"]:
            alertas["ambar"].append({
                "tipo": "B3", "tienda": tienda,
                "titulo": f"{tienda} — Conversión CRM→Venta baja: {tasa}%",
                "detalle": "Por debajo del umbral saludable (15%). Capacitación en cierre recomendada.",
                "kpi_variable": "tasa_conv_crm_venta",
                "valor": tasa,
            })

        # B5 — Demos altas, ventas mínimas
        demo_venta_r = d_conv.get("tasa_demo_venta", 0)
        if d_conv.get("demo", 0) >= 10 and demo_venta_r < 10:
            alertas["ambar"].append({
                "tipo": "B5", "tienda": tienda,
                "titulo": f"{tienda} — {d_conv['demo']} demos con ratio demo→venta {demo_venta_r}%",
                "detalle": "Las demostraciones no se traducen en ventas. Revisar calidad de las demos y perfil del prospecto.",
                "kpi_variable": "tasa_demo_venta",
                "valor": demo_venta_r,
            })

    # — Alertas por ejecutivo (A3, A5, B2) —
    for (ejecutivo, tienda), datos in exec_kpi.items():
        if not ejecutivo or ejecutivo == 0:
            continue
        kpis = datos["kpis"]
        if len(kpis) < 2:
            continue
        ultimo    = kpis[-1] * 100
        penultimo = kpis[-2] * 100
        caida     = penultimo - ultimo

        # A5 — Caída crítica de KPI
        if caida >= T["caida_kpi_critica"]:
            alertas["rojas"].append({
                "tipo": "A5", "tienda": tienda, "ejecutivo": str(ejecutivo),
                "titulo": f"{tienda} ({ejecutivo}) — Caída de KPI: {penultimo:.0f}% → {ultimo:.0f}%",
                "detalle": f"Caída de {caida:.0f} pp en un mes. Identificar causa: ausencia, cambio de territorio o competencia.",
                "kpi_variable": "caida_kpi_mensual_pp",
                "valor": caida,
            })

        # B2 — Caída moderada
        elif caida >= T["caida_kpi_atencion"]:
            alertas["ambar"].append({
                "tipo": "B2", "tienda": tienda, "ejecutivo": str(ejecutivo),
                "titulo": f"{tienda} ({ejecutivo}) — KPI bajó {caida:.0f} pp este mes",
                "detalle": f"De {penultimo:.0f}% a {ultimo:.0f}%. Monitorear de cerca.",
                "kpi_variable": "caida_kpi_mensual_pp",
                "valor": caida,
            })

        # A3 — KPI bajo sostenido (últimos 2 meses)
        if len(kpis) >= 2 and all(k < T["kpi_rojo"] for k in kpis[-2:]):
            alertas["rojas"].append({
                "tipo": "A3", "tienda": tienda, "ejecutivo": str(ejecutivo),
                "titulo": f"{ejecutivo} ({tienda}) — KPI bajo 2+ meses consecutivos",
                "detalle": f"KPI promedio últimos meses: {sum(kpis[-2:])/2*100:.0f}%. Evaluación de desempeño urgente.",
                "kpi_variable": "kpi_ejecutivo_consecutivo_bajo",
                "valor": round(sum(kpis[-2:]) / 2 * 100, 1),
            })

    # Eliminar duplicados
    for nivel in ["rojas", "ambar"]:
        seen = set()
        uniq = []
        for a in alertas[nivel]:
            key = (a["tipo"], a.get("tienda",""), a.get("ejecutivo",""))
            if key not in seen:
                seen.add(key)
                uniq.append(a)
        alertas[nivel] = uniq

    return alertas


def procesar_mercado(crm_df, visitas_df, ventas_df):
    """
    ─────────────────────────────────────────────────────────────────────────
    VARIABLES DE INTELIGENCIA DE MERCADO — DEFINICIÓN
    ─────────────────────────────────────────────────────────────────────────
    perfil_cliente       : Tipo de empresa/persona del CRM (Agricultor, etc.)
    interes_dron         : Modelo de interés declarado en el CRM
    tipo_pago            : Forma de pago preferida declarada en el CRM
    procedencia_cliente  : Canal por el que llegó el cliente a QTC
    cultivos             : Tipos de cultivo de los prospectos
    hectareas_promedio   : Superficie agrícola promedio por sucursal (del CRM)
    roi_meses            : Meses estimados de recuperación de inversión (campo)
    intencion_compra     : Respuesta a "¿Interesado en comprar?" (visitas campo)
    limitantes_compra    : Barreras declaradas por el prospecto en campo
    uso_dron             : Para qué usará el dron (venta, servicio, propio)
    segmento_venta       : Venta directa vs subdealer
    financiamiento       : Tipo de financiamiento en ventas cerradas
    ─────────────────────────────────────────────────────────────────────────
    """
    def vc(series, top=None):
        vc = series.dropna().value_counts()
        if top:
            vc = vc.head(top)
        return vc.to_dict()

    return {
        "perfil_cliente":      vc(crm_df.get("Perfil de cliente", pd.Series())),
        "interes_dron":        vc(crm_df.get("¿En que dron está interesado?", pd.Series()), top=8),
        "tipo_pago":           vc(crm_df.get("Tipo de pago", pd.Series())),
        "procedencia_cliente": vc(crm_df.get("Procedencia del cliente", pd.Series())),
        "cultivos":            vc(crm_df.get("Datos de cultivo", pd.Series()), top=8),
        "hectareas_promedio":  crm_df.groupby("Tienda")["Hectareas"].mean().round(0).dropna().to_dict()
                               if "Hectareas" in crm_df.columns else {},
        "roi_meses":           vc(visitas_df.get("Cuántos meses se estima a recuperar la inversión", pd.Series()), top=8),
        "intencion_compra":    vc(visitas_df.get("¿Está interesado en comprar un dron agrícola?", pd.Series())),
        "limitantes_compra":   vc(visitas_df.get("Limitantes de compras del dron", pd.Series()), top=8),
        "uso_dron":            vc(ventas_df.get("Uso", pd.Series())),
        "segmento_venta":      vc(ventas_df.get("Segmento", pd.Series())),
        "financiamiento":      vc(ventas_df.get("Financiamiento", pd.Series())),
    }


def main():
    parser = argparse.ArgumentParser(description="Actualiza qtc_data.json para el dashboard QTC")
    parser.add_argument("--carpeta", default=".", help="Carpeta con los CSVs (default: carpeta actual)")
    parser.add_argument("--salida",  default="qtc_data.json", help="Nombre del JSON de salida")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  QTC DASHBOARD — ACTUALIZACIÓN DE DATOS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print(f"\n📂 Leyendo CSVs desde: {os.path.abspath(args.carpeta)}\n")

    kpi_df     = leer_csv(args.carpeta, "kpi")
    res_df     = leer_csv(args.carpeta, "res")
    ventas_df  = leer_csv(args.carpeta, "ventas")
    visitas_df = leer_csv(args.carpeta, "visitas")
    crm_df     = leer_csv(args.carpeta, "crm")

    print("\n⚙️  Procesando datos...")
    res_clean  = procesar_resultados(res_df)
    kpi_clean  = procesar_kpi(kpi_df)
    funnel_df  = procesar_funnel(crm_df, visitas_df)
    alertas    = generar_alertas(res_clean, kpi_clean, funnel_df)
    mercado    = procesar_mercado(crm_df, visitas_df, ventas_df)

    output = {
        "last_update":    datetime.now().strftime("%Y-%m-%d"),
        "umbrales":       UMBRALES,
        "resultados":     json.loads(res_clean.to_json(orient="records")),
        "kpi_ejecutivos": json.loads(kpi_clean.to_json(orient="records")),
        "funnel":         json.loads(funnel_df.to_json(orient="records")),
        "alertas":        alertas,
        "mercado":        mercado,
    }

    salida_path = os.path.join(args.carpeta, args.salida)
    with open(salida_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Archivo generado: {os.path.abspath(salida_path)}")
    print(f"   Resultados:    {len(output['resultados'])} filas")
    print(f"   KPI ejecutivos:{len(output['kpi_ejecutivos'])} registros")
    print(f"   Funnel:        {len(output['funnel'])} sucursales")
    print(f"   Alertas rojas: {len(alertas['rojas'])}")
    print(f"   Alertas ámbar: {len(alertas['ambar'])}")
    print("\n📋 PRÓXIMO PASO: Coloca qtc_data.json en la misma carpeta que el dashboard HTML.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
