import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(page_title="MatchPlan App", layout="wide")
st.title("🏐 MatchPlan App - Panel Analítico Base")

# Módulo de carga de archivos
uploaded_file = st.file_uploader("Cargar archivo Data Volley (.dvw)", type=["dvw"])

if uploaded_file is not None:
    # Decodificación del archivo de texto
    content = uploaded_file.read().decode('utf-8', errors='ignore').splitlines()
    
    # Aislamiento de la sección operativa
    try:
        scout_idx = content.index('[SCOUT]') + 1
        scout_lines = content[scout_idx:]
    except ValueError:
        st.error("Error crítico: No se ha detectado la etiqueta [SCOUT] en el archivo.")
        st.stop()
        
    # Motor de Parseo (Traducción de códigos)
    parsed_data = []
    # Expresión regular para aislar: Equipo, Jugador, Fundamento, Evaluación
    pattern = re.compile(r'^([*a])(..)([SREAFDB])([-+#=!/])')
    
    for line in scout_lines:
        line = line.strip()
        if not line: continue
        
        match = pattern.match(line)
        if match:
            equipo = "Local (*)" if match.group(1) == "*" else "Visitante (a)"
            jugador = match.group(2)
            fundamento = match.group(3)
            evaluacion = match.group(4)
            parsed_data.append([equipo, jugador, fundamento, evaluacion, line])
            
    # Estructuración de datos
    df = pd.DataFrame(parsed_data, columns=["Equipo", "Jugador", "Fundamento", "Evaluación", "Código Raw"])
    
    # Panel de KPIs Ejecutivos
    st.subheader("Métricas Generales del Archivo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Acciones Registradas", len(df))
    col2.metric("Ataques (A)", len(df[df["Fundamento"] == "A"]))
    col3.metric("Recepciones (R)", len(df[df["Fundamento"] == "R"]))
    
    # Visualización de la Base de Datos
    st.subheader("Tabla de Datos Estructurada")
    st.dataframe(df, use_container_width=True)
else:
    st.info("A la espera de un archivo .dvw para iniciar el procesamiento.")
