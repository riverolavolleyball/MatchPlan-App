import streamlit as st
import pandas as pd
import re

# Configuración visual de la página
st.set_page_config(page_title="MatchPlan App", layout="wide")
st.title("🏐 MatchPlan App - Panel Analítico Base")

# Carga del archivo
uploaded_file = st.file_uploader("Cargar archivo Data Volley (.dvw)", type=["dvw"])

if uploaded_file is not None:
    # Decodificación adaptada para Windows/DataVolley
    try:
        bytes_data = uploaded_file.read()
        content = bytes_data.decode('latin-1')
    except UnicodeDecodeError:
        content = bytes_data.decode('utf-8', errors='ignore')
    
    lines = content.splitlines()
    
    # Buscar la sección EXACTA de las jugadas
    scout_index = -1
    for i, line in enumerate(lines):
        if line.strip() in ["[SCOUT]", "[3SCOUT]"]:
            scout_index = i + 1
            st.success(f"✅ Sección de acciones tácticas encontrada en la línea {i+1}: {line.strip()}")
            break
            
    if scout_index == -1:
        st.error("Error: No se encontró la etiqueta de inicio de datos [3SCOUT].")
        st.stop()

    # Procesamiento con FILTRO ESTRICTO (Regex)
    raw_data = []
    
    # Expresión regular:
    # ^([*a])          -> * (Local) o a (Visitante)
    # (..)             -> Número de jugador (ej. 05, 12)
    # ([SREAFDB])      -> Fundamento (Saque, Recepción, Colocación(E), Ataque, Finta, Defensa, Bloqueo)
    # ([-+#=!/])       -> Evaluación
    pattern = re.compile(r'^([*a])(..)([SREAFDB])([-+#=!/])')
    
    for line in lines[scout_index:]:
        line = line.strip()
        if not line: continue
        
        match = pattern.match(line)
        if match:
            equipo_nombre = "Local (*)" if match.group(1) == "*" else "Visitante (a)"
            numero = match.group(2)
            fundamento = match.group(3)
            evaluacion = match.group(4)
            
            raw_data.append({
                "Equipo": equipo_nombre,
                "Número": numero,
                "Fundamento": fundamento,
                "Evaluación": evaluacion,
                "Código Completo": line
            })

    if raw_data:
        df = pd.DataFrame(raw_data)
        
        # --- VISUALIZACIÓN ---
        st.markdown("### 📊 Resumen de Acciones Extraídas")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Acciones (Limpias)", len(df))
        kpi2.metric("Total Ataques (A)", len(df[df['Fundamento'] == 'A']))
        kpi3.metric("Total Saques (S)", len(df[df['Fundamento'] == 'S']))

        st.markdown("### 📝 Base de Datos Táctica")
        st.dataframe(df, use_container_width=True)
        
    else:
        st.warning("Se encontró la sección de datos, pero el filtro no ha detectado ninguna acción con el formato táctico correcto.")

else:
    st.info("Sube tu archivo .dvw para comenzar.")
