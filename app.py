import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# Configuración de estilo ejecutivo
st.set_page_config(page_title="MatchPlan App", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_name_with_ Harris=True)

st.title("🏐 MatchPlan App - Inteligencia Táctica")

# Diccionarios de traducción Data Volley
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'E': 'Colocación', 'F': 'Finta'}
RATINGS = {'#': 'Punto/Excelente', '+': 'Positiva', '!': 'Exclamación', '-': 'Negativa', '/': 'Pobre', '=': 'Error'}

def parse_dv_line(line):
    """Extrae datos tácticos de una línea de scout de DV4"""
    # Dividir por punto y coma para aislar el código táctico del metadato
    parts = line.split(';')
    code = parts[0]
    
    # Filtro: debe empezar por * o a y tener longitud mínima
    if not code or code[0] not in ['*', 'a'] or len(code) < 5:
        return None
    
    try:
        team = "Local" if code[0] == "*" else "Visitante"
        player = code[1:3]
        skill = SKILLS.get(code[3], "Otros")
        rating = RATINGS.get(code[5], "Neutral")
        
        # Extracción de Zonas (Posiciones 14-15 inicio, 16-17 fin en el string de DV)
        # En tu archivo: *01SQ=~~~95~~~L -> Zona fin es 9, subzona 5
        start_zone = code[13:14] if len(code) > 13 and code[13].isdigit() else None
        end_zone = code[14:15] if len(code) > 14 and code[14].isdigit() else None
        
        return {
            "Equipo": team,
            "Jugador": player,
            "Fundamento": skill,
            "Calidad": rating,
            "Zona_In": start_zone,
            "Zona_Out": end_zone,
            "Hora_Relativa": parts[8] if len(parts) > 8 else "",
            "Score": f"{parts[9]}-{parts[10]}" if len(parts) > 10 else "0-0",
            "Full_Code": code
        }
    except:
        return None

# Lógica de carga
uploaded_file = st.file_uploader("Sube tu archivo .dvw de Data Volley 4", type=["dvw"])

if uploaded_file:
    content = uploaded_file.read().decode('latin-1').splitlines()
    
    # Localizar sección [3SCOUT] o [SCOUT]
    start_idx = -1
    for i, line in enumerate(content):
        if "[3SCOUT]" in line or "[SCOUT]" in line:
            start_idx = i + 1
            break
    
    if start_idx != -1:
        data = [parse_dv_line(l) for l in content[start_idx:]]
        df = pd.DataFrame([d for d in data if d is not None])
        
        # --- DASHBOARD ---
        st.subheader("📊 Análisis de Rendimiento")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Acciones Totales", len(df))
        c2.metric("Ataques", len(df[df['Fundamento'] == 'Ata
