import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# 1. Configuración de la página y Estilo Visual (MatchPlan Dark Mode)
st.set_page_config(page_title="MatchPlan App", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    div[data-testid="stMetricValue"] { color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏐 MatchPlan App - v4.5")

# 2. Diccionarios de Traducción de Data Volley
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'F': 'Finta'}
RATINGS = {'#': 'Perfecto/Punto', '+': 'Positivo', '!': 'Exclamación', '-': 'Negativo', '/': 'Pobre', '=': 'Error'}

def parse_dv_line(line):
    """Parser optimizado para códigos de Data Volley 4 Professional"""
    if not line or len(line) < 10 or not line[0] in ['*', 'a']:
        return None
    
    # Separamos el código táctico de los metadatos (tiempo, marcador, etc.)
    parts = line.split(';')
    code = parts[0]
    
    try:
        # Extracción por posición fija (Estándar DV)
        # * 01 S Q = ~~~ 9 5
        # 0 12 3 4 5 678 9 10
        team = "Local (*)" if code[0] == "*" else "Visitante (a)"
        player = code[1:3]
        skill = SKILLS.get(code[3], "Otros")
        rating = RATINGS.get(code[5], "Neutral")
        
        # Zonas (índices 9 y 10 en la cadena)
        z_in = code[9] if len(code) > 9 and code[9].isdigit() else "0"
        z_out = code[10] if len(code) > 10 and code[10].isdigit() else "0"
        
        return {
            "Equipo": team, "Jugador": player, "Fundamento": skill, 
            "Calidad": rating, "Z_In": z_in, "Z_Out": z_out,
            "Score": f"{parts[9]}-{parts[10]}" if len(parts) > 10 else "0-0",
            "Código": code
        }
    except:
        return None

# 3. Interfaz de Usuario
uploaded_file = st.file_uploader("Sube tu archivo .dvw", type=["dvw"])

if uploaded_file:
    # Lectura del archivo
    content = uploaded_file.read().decode('latin-1', errors='ignore').splitlines()
    
    # Localizar sección [3SCOUT]
    start_idx = -1
    for i, line in enumerate(content):
        if "[3SCOUT]" in line:
            start_idx = i + 1
            break
    
    if start_idx != -1:
        # Procesar líneas de scouting
        scout_data = [parse_dv_line(l) for l in content[start_idx:]]
        df = pd.DataFrame([d for d in scout_data if d is not None])
        
        # 4. Dashboard de Métricas (Aquí estaba el error anterior)
        st.subheader("📊 Resumen Táctico")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Acciones", len(df))
        m2.metric("Ataques", len(df[df['Fundamento'] == 'Ataque']))
        m3.metric("Puntos", len(df[df['Calidad'] == 'Perfecto/Punto']))
        m4.metric("Errores", len(df[df['Calidad'] == 'Error']))
        
        # 5. Filtros Dinámicos
        st.sidebar.header("Match Plan Filters")
        sel_team = st.sidebar.selectbox("Seleccionar Equipo", df['Equipo'].unique())
        sel_skill = st.sidebar.multiselect("Filtrar Acción", df['Fundamento'].unique(), default=['Ataque', 'Saque'])
        
        df_view = df[(df['Equipo'] == sel_team) & (df['Fundamento'].isin(sel_skill))]
        
        # 6. Tabla de Datos
        st.dataframe(df_view, use_container_width=True)
        
        # 7. Mini Mapa de Direcciones (Simple)
        st.subheader("📍 Mapa de Zonas (Z_In vs Z_Out)")
        fig = go.Figure(data=go.Scatter(
            x=df_view['Z_In'], y=df_view['Z_Out'],
            mode='markers',
            marker=dict(size=12, color='#00ffcc', opacity=0.6),
            text=df_view['Jugador']
        ))
        fig.update_layout(title="Distribución de Zonas", xaxis_title="Zona Inicio", yaxis_title="Zona Fin", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("No se detectó la etiqueta [3SCOUT] en el archivo.")
