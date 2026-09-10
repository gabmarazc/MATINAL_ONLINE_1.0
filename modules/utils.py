# modules/utils.py
import pandas as pd
import unicodedata

def parsear_fecha_robusta(serie):
    """Estandariza parseo de fechas considerando formatos ISO, DD/MM/YYYY y genérico sin advertencias."""
    if serie is None or (isinstance(serie, pd.Series) and serie.empty):
        return pd.Series(dtype="datetime64[ns]")
    if not isinstance(serie, pd.Series):
        serie = pd.Series([serie])
    s = serie.astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
    
    dt_iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dt_lat = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    dt_gen = pd.to_datetime(s, errors="coerce")
    
    return dt_iso.combine_first(dt_lat).combine_first(dt_gen)

def extraer_dia_de_ruta(val):
    """Extrae y normaliza el día de visita a partir del texto de la ruta."""
    if pd.isna(val):
        return "SIN DÍA"
    nfkd = unicodedata.normalize('NFKD', str(val))
    val_clean = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    
    if "LUN" in val_clean: return "LUNES"
    if "MAR" in val_clean: return "MARTES"
    if "MIE" in val_clean: return "MIERCOLES"
    if "JUE" in val_clean: return "JUEVES"
    if "VIE" in val_clean: return "VIERNES"
    if "SAB" in val_clean: return "SABADO"
    if "DOM" in val_clean: return "DOMINGO"
    return "SIN DÍA"

def extraer_dia_de_ruta_vectorial(serie):
    """Normalización y extracción vectorial rápida de días de visita sin bucles en Python."""
    if serie is None or (isinstance(serie, pd.Series) and serie.empty):
        return pd.Series(dtype="object")
    s_upper = serie.astype(str).str.upper()
    dias_map = pd.Series("SIN DÍA", index=serie.index)
    dias_map[s_upper.str.contains("LUN", na=False)] = "LUNES"
    dias_map[s_upper.str.contains("MAR", na=False)] = "MARTES"
    dias_map[s_upper.str.contains("MIE", na=False)] = "MIERCOLES"
    dias_map[s_upper.str.contains("JUE", na=False)] = "JUEVES"
    dias_map[s_upper.str.contains("VIE", na=False)] = "VIERNES"
    dias_map[s_upper.str.contains("SAB", na=False)] = "SABADO"
    dias_map[s_upper.str.contains("DOM", na=False)] = "DOMINGO"
    return dias_map

def tarjeta_metrica_html(label, valor, border_color="#475569", font_val="1.4rem", font_lbl="0.75rem"):
    """Genera contenedores HTML unificados para tarjetas de métricas."""
    return f"""
    <div style="
        background-color: #1e293b;
        border: 2px solid {border_color};
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 8px;
    ">
        <div style="font-size: {font_lbl}; color: #94a3b8; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">{label}</div>
        <div style="font-size: {font_val}; color: #f8fafc; font-weight: 700;">{valor}</div>
    </div>
    """
