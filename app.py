import streamlit as st
import pandas as pd
import re

# Configuración visual de la página
st.set_page_config(page_title="MatchPlan App", layout="wide")
st.title("🏐 MatchPlan App - Panel Analítico")

# Carga del archivo
uploaded_file = st.file_uploader("Cargar archivo Data Volley (.dvw)", type=["dvw"])

if uploaded_file is not None:
    # --- CORRECCIÓN 1: Lectura más robusta (Latin-1 para Windows) ---
    try:
        # DataVolley suele usar codificación 'latin-1' o 'cp1252'
        bytes_data = uploaded_file.read()
        content = bytes_data.decode('latin-1')
    except UnicodeDecodeError:
        # Si falla, probamos utf-8 ignorando errores
        content = bytes_data.decode('utf-8', errors='ignore')
    
    lines = content.splitlines()
    
    # --- CORRECCIÓN 2: Búsqueda flexible de la sección SCOUT ---
    scout_index = -1
    for i, line in enumerate(lines):
        # Buscamos cualquier variante: [SCOUT], [3SCOUT], etc.
        if "SCOUT]" in line:
            scout_index = i + 1
            st.success(f"✅ Sección de datos encontrada en la línea {i+1}: {line}")
            break
            
    if scout_index == -1:
        st.error("Error crítico: No se encuentra la etiqueta [SCOUT].")
        st.warning("Muestra de las primeras 5 líneas del archivo para depurar:")
        st.code("\n".join(lines[:5]))
        st.stop()

    # Procesamiento de datos
    raw_data = []
    # Regex ajustado para capturar código completo
    for line in lines[scout_index:]:
        line = line.strip()
        if not line: continue
        
        # Separamos los componentes básicos por posición (sintaxis DV)
        # Un código típico es: *05P+H#...
        try:
            # Si la línea es muy corta, la saltamos (comentarios o basura)
            if len(line) < 5: continue
            
            equipo = line[0] # * o a
            numero = line[1:3] # 05
            fundamento = line[3] # P, A, S...
            evaluacion = line[5] # +, -, #, =
            
            # Traducción básica
            equipo_nombre = "Mío (*)" if equipo == "*" else "Rival (a)"
            
            raw_data.append({
                "Equipo": equipo_nombre,
                "Número": numero,
                "Fundamento": fundamento,
                "Evaluación": evaluacion,
                "Código Completo": line
            })
        except Exception as e:
            continue # Si una línea falla, seguimos con la siguiente

    if raw_data:
        df = pd.DataFrame(raw_data)
        
        # --- VISUALIZACIÓN ---
        
        # Métricas (Tarjetas superiores)
        st.markdown("### 📊 Resumen del Partido")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Acciones", len(df))
        kpi2.metric("Ataques Totales", len(df[df['Fundamento'] == 'A']))
        kpi3.metric("Errores Totales", len(df[df['Evaluación'] == '=']))

        # Tabla de datos
        st.markdown("### 📝 Datos Extraídos")
        st.dataframe(df, use_container_width=True)
        
    else:
        st.warning("Se encontró la sección SCOUT pero no se pudieron extraer datos válidos.")

else:
    st.info("Sube tu archivo .dvw para comenzar.")
