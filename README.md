# QTC — Centro de Inteligencia Comercial
## Guía completa de despliegue y actualización semanal

---

## 📁 Estructura de archivos

```
qtc_dashboard/
├── dashboard.html          ← Dashboard principal (compartir este archivo)
├── qtc_data.json           ← Datos procesados (se regenera cada semana)
├── actualizar_datos.py     ← Script Python de actualización
│
├── KPI_Equipo_comercial.csv     ← Exportar desde Lark Base cada semana
├── Resultados.csv               ← Exportar desde Lark Base cada semana
├── Ventas.csv                   ← Exportar desde Lark Base cada semana
├── Visitas_y_demostraciones.csv ← Exportar desde Lark Base cada semana
└── CRM.csv                      ← Exportar desde Lark Base cada semana
```

---

## 🚀 Opciones de publicación (elegir una)

### OPCIÓN A — GitHub Pages (gratuito, recomendado)
> Cualquier persona con el link puede ver el dashboard actualizado.

1. Crear cuenta en https://github.com (gratis)
2. Crear repositorio nuevo → nombre: `qtc-dashboard`
3. Subir los archivos: `dashboard.html` y `qtc_data.json`
4. Ir a: Settings → Pages → Branch: main → Save
5. Tu URL pública será: `https://TU_USUARIO.github.io/qtc-dashboard/dashboard.html`
6. Cada semana: actualiza solo el archivo `qtc_data.json`

### OPCIÓN B — Netlify Drop (más fácil, 2 minutos)
1. Ir a https://app.netlify.com/drop
2. Arrastrar la carpeta `qtc_dashboard/` completa
3. Netlify genera una URL pública automáticamente
4. Para actualizar: volver a Netlify y arrastrar la carpeta nueva

### OPCIÓN C — Lark Docs (dentro del ecosistema Lark)
1. En Lark Docs → crear nueva página
2. Insertar bloque de código HTML
3. Pegar el contenido de `dashboard.html`
4. El JSON de datos debe estar en un almacenamiento accesible (Lark Drive)

### OPCIÓN D — Servidor propio / intranet
1. Copiar ambos archivos (`dashboard.html` y `qtc_data.json`) al servidor web
2. Servir desde Apache / Nginx / cualquier servidor HTTP
3. Asegurarse de que ambos archivos estén en el mismo directorio

---

## 🔄 Proceso de actualización semanal (cada lunes)

### Paso 1 — Exportar CSVs desde Lark Base
En cada tabla de Lark Base → botón Exportar → CSV:

| Tabla en Lark                    | Guardar como                    |
|----------------------------------|---------------------------------|
| KPI Equipo comercial             | `KPI_Equipo_comercial.csv`      |
| Resultados                       | `Resultados.csv`                |
| Ventas                           | `Ventas.csv`                    |
| Visitas y demostraciones         | `Visitas_y_demostraciones.csv`  |
| CRM                              | `CRM.csv`                       |

### Paso 2 — Ejecutar el script
```bash
# Instalar dependencias (solo la primera vez)
pip install pandas

# Ejecutar desde la carpeta del proyecto
python actualizar_datos.py

# O especificando ruta
python actualizar_datos.py --carpeta /Descargas/lark_export
```

### Paso 3 — Publicar el JSON actualizado
- **GitHub Pages**: subir `qtc_data.json` al repositorio (reemplaza el anterior)
- **Netlify**: arrastrar la carpeta completa nuevamente
- **Servidor**: copiar `qtc_data.json` al servidor

### ⏰ Automatización con tarea programada (opcional)
**Windows (Task Scheduler):**
```
Programa: python
Argumentos: C:\ruta\qtc_dashboard\actualizar_datos.py
Trigger: cada lunes a las 08:00
```

**Mac/Linux (cron):**
```bash
# Editar crontab
crontab -e

# Ejecutar cada lunes a las 8am
0 8 * * 1 python3 /ruta/qtc_dashboard/actualizar_datos.py
```

---

## 📊 Variables de alerta — definición completa

Las alertas se calculan automáticamente al ejecutar `actualizar_datos.py`.
Los umbrales son editables en la sección `UMBRALES` del script.

### 🔴 Alertas críticas (acción inmediata)

| Código | Variable                              | Condición de disparo                                      | Umbral por defecto |
|--------|---------------------------------------|-----------------------------------------------------------|--------------------|
| A1     | `tasa_conv_crm_venta`                 | Conversión CRM→Venta = 0% con CRM ≥ mínimo y demos > 0  | CRM mínimo: 5      |
| A2     | `ventas_mensuales_consecutivas_cero`  | N meses consecutivos sin ninguna venta cerrada            | 3 meses            |
| A3     | `kpi_ejecutivo_consecutivo_bajo`      | KPI ejecutivo bajo el mínimo por 2+ meses seguidos        | KPI < 40%          |
| A4     | `crm_mensual`                         | Sin ningún CRM registrado en el último mes                | = 0                |
| A5     | `caida_kpi_mensual_pp`                | Caída de KPI entre mes anterior y mes actual              | ≥ 40 puntos %      |

### 🟡 Alertas de atención (oportunidad)

| Código | Variable                   | Condición de disparo                                          | Umbral por defecto |
|--------|----------------------------|---------------------------------------------------------------|--------------------|
| B1     | `ventas_potenciales_campo` | Ventas potenciales detectadas en campo sin capitalizar        | VP ≥ 12 unidades   |
| B2     | `caida_kpi_mensual_pp`     | Caída moderada de KPI entre meses                            | 20–39 puntos %     |
| B3     | `tasa_conv_crm_venta`      | Conversión CRM→Venta baja pero no nula                       | Entre 5% y 15%     |
| B4     | `ventas_mensuales_consecutivas_cero` | Meses sin ventas (no llega a crítico)               | 2 meses            |
| B5     | `tasa_demo_venta`          | Demostraciones altas pero pocas ventas resultantes           | Demos≥10 y <10%    |

### Cómo ajustar los umbrales
Editar el diccionario `UMBRALES` en `actualizar_datos.py`:
```python
UMBRALES = {
    "kpi_rojo":                    0.40,  # KPI mínimo ejecutivo (0–1)
    "kpi_amarillo":                0.70,
    "meses_sin_venta_critico":     3,     # meses consecutivos
    "meses_sin_venta_atencion":    2,
    "conv_rojo":                   5.0,   # % conversión CRM→Venta
    "conv_amarillo":               15.0,
    "caida_kpi_critica":           40,    # puntos porcentuales de caída
    "caida_kpi_atencion":          20,
    "crm_minimo":                  5,     # CRM mínimo mensual esperado
    "vp_alto":                     12,    # ventas potenciales "alto"
    "vp_medio":                    6,
}
```

---

## 📈 Variables de inteligencia de mercado — definición

Estas variables se extraen automáticamente de los CSVs y se muestran en la pestaña "Inteligencia de mercado".

| Variable               | Fuente (archivo → columna)                                              | Descripción                                       |
|------------------------|-------------------------------------------------------------------------|---------------------------------------------------|
| `perfil_cliente`       | CRM.csv → `Perfil de cliente`                                           | Tipo de empresa/persona (Agricultor, Fumigador…)  |
| `interes_dron`         | CRM.csv → `¿En que dron está interesado?`                               | Modelo declarado de interés en CRM                |
| `tipo_pago`            | CRM.csv → `Tipo de pago`                                                | Preferencia de pago declarada en CRM              |
| `procedencia_cliente`  | CRM.csv → `Procedencia del cliente`                                     | Canal de entrada (Ruta de campo, Referido…)       |
| `cultivos`             | CRM.csv → `Datos de cultivo`                                            | Tipos de cultivo de los prospectos                |
| `hectareas_promedio`   | CRM.csv → `Hectareas` agrupado por Tienda                               | Superficie agrícola promedio del cliente          |
| `roi_meses`            | Visitas.csv → `Cuántos meses se estima a recuperar la inversión`        | Percepción de ROI declarada en campo              |
| `intencion_compra`     | Visitas.csv → `¿Está interesado en comprar un dron agrícola?`           | Intención de compra del prospecto visitado        |
| `limitantes_compra`    | Visitas.csv → `Limitantes de compras del dron`                          | Barreras de compra declaradas en campo            |
| `uso_dron`             | Ventas.csv → `Uso`                                                      | Finalidad de uso del dron comprado                |
| `segmento_venta`       | Ventas.csv → `Segmento`                                                 | Venta directa vs subdealer                        |
| `financiamiento`       | Ventas.csv → `Financiamiento`                                           | Tipo de financiamiento en ventas cerradas         |

---

## 🔧 Solución de problemas frecuentes

**"No se encontró qtc_data.json"**
→ Asegúrate de que `dashboard.html` y `qtc_data.json` están en la misma carpeta
→ Si usas GitHub Pages, ambos archivos deben estar en el repositorio

**"Error de encoding en CSV"**
→ Al exportar desde Lark, elegir codificación UTF-8
→ El script intenta UTF-8, UTF-8-BOM y Latin-1 automáticamente

**Los gráficos no cargan**
→ Verifica conexión a internet (Chart.js se carga desde CDN)
→ O descarga Chart.js y referenciarlo localmente

**Nombre de columnas cambiaron en Lark**
→ Actualizar el diccionario `col_map` en la función correspondiente de `actualizar_datos.py`

---

## 📞 Soporte
Para preguntas sobre la configuración o actualización del dashboard, contactar al área de sistemas o al responsable de la exportación de Lark Base.
