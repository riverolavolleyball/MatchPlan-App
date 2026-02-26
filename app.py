import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# --- CONFIGURACIÓN DE INTERFAZ PROFESIONAL ---
st.set_page_config(page_title="MatchPlan Pro | Analytics", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- DICCIONARIOS TÉCNICOS ---
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'F': 'Finta'}
RATINGS = {'#': 'Punto/Exc', '+': 'Positivo', '!': 'Excl!', '-': 'Negativo', '/': 'Pobre', '=': 'Error'}

# --- MOTOR DE CÁLCULO GEOESPACIAL ---
def get_coords(dv_coord):
    """Convierte coordenadas DV (0-100) a Metros (9x18)"""
    if not dv_coord or not str(dv_coord).isdigit(): return None, None
    c = int(dv_coord)
    x = (c % 100) * 0.09  # 0-100 -> 0-9m
    y = (c // 100) * 0.18 # 0-100 -> 0-18m
    return x, y

def draw_court(fig):
    """Dibuja las líneas oficiales de la FIVB"""
    # Perímetro y Red
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="white", width=3))
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="rgba(0, 255, 204, 0.8)", width=5))
    # Líneas de 3 metros (Zona de ataque)
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="white", width=1, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=12, x1=9, y1=12, line=dict(color="white", width=1, dash="dash"))
    return fig

# --- PARSER DE ALTA PRECISIÓN ---
def parse_match_data(content):
    scout_idx = next((i for i, l in enumerate(content) if "[3SCOUT]" in l or "[SCOUT]" in l), -1) + 1
    actions = []
    
    for line in content[scout_idx:]:
        p = line.split(';')
        if not p or len(p) < 15 or not p[0] or p[0][0] not in ['*', 'a']: continue
        
        c = p[0] # Código táctico
        if ">" in c or "z" in c or "P" in c: continue # Filtro de ruido
        
        x_in, y_in = get_coords(p[14]) if len(p) > 14 else (None, None)
        x_out, y_out = get_coords(p[15]) if len(p) > 15 else (None, None)
        
        actions.append({
            "Team": "Local" if c[0] == "*" else "Visitante",
            "Player": c[1:3],
            "Skill": SKILLS.get(c[3], "Otros"),
            "Effect": RATINGS.get(c[5], "Neutral"),
            "X_In": x_in, "Y_In": y_in,
            "X_Out": x_out, "Y_Out": y_out,
            "Set": p[11], "Score_H": p[9], "Score_V": p[10],
            "Phase": "K1" if "K1" in line else "K2"
        })
    return pd.DataFrame(actions)

# --- APP LAYOUT ---
st.title("🏐 MatchPlan Pro | Volley Vision 360")
file = st.file_uploader("Cargar archivo .dvw (Data Volley 4 Pro)", type=["dvw"])

if file:
    df = parse_match_data(file.read().decode('latin-1').splitlines())
    
    # KPIs SUPERIORES
    st.subheader("📊 Métricas de Eficiencia")
    col1, col2, col3, col4 = st.columns(4)
    
    attacks = df[df['Skill'] == 'Ataque']
    points = len(attacks[attacks['Effect'] == 'Punto/Exc'])
    errors = len(attacks[attacks['Effect'] == 'Error'])
    eff = (points - errors) / len(attacks) if len(attacks) > 0 else 0
    
    col1.metric("Eficiencia Ataque", f"{eff:.2f}")
    col2.metric("Puntos Ataque", points)
    col3.metric("Errores", errors)
    col4.metric("Acciones Totales", len(df))

    # FILTROS LATERALES
    st.sidebar.header("🕹️ Centro de Control")
    f_team = st.sidebar.selectbox("Seleccionar Equipo", df['Team'].unique())
    f_skill = st.sidebar.selectbox("Fundamento", df['Skill'].unique(), index=3) # Default: Ataque
    f_phase = st.sidebar.multiselect("Fase de Juego", ["K1", "K2"], default=["K1", "K2"])
    
    df_f = df[(df['Team'] == f_team) & (df['Skill'] == f_skill) & (df['Phase'].isin(f_phase))]

    # VISUALIZACIÓN REVOLUCIONARIA
    tab1, tab2, tab3 = st.tabs(["🔥 Mapa de Calor", "🏹 Shot Chart (Direcciones)", "📈 Data Table"])
    
    with tab1:
        st.subheader(f"Densidad de Impacto: {f_skill}")
        if not df_f['X_Out'].dropna().empty:
            fig_h = px.density_heatmap(df_f, x="X_Out", y="Y_Out", nbinsx=20, nbinsy=40,
                                     range_x=[0, 9], range_y=[0, 18], template="plotly_dark",
                                     color_continuous_scale="Viridis")
            fig_h = draw_court(fig_h)
            fig_h.update_layout(width=450, height=800)
            st.plotly_chart(fig_h, use_container_width=True)
        else:
            st.warning("El archivo no contiene coordenadas exactas para Mapa de Calor.")

    with tab2:
        st.subheader(f"Trayectorias de {f_skill}")
        fig_s = go.Figure()
        fig_s = draw_court(fig_s)
        
        # Dibujar flechas de cada acción
        for _, row in df_f.dropna(subset=['X_In', 'X_Out']).iterrows():
            color = "#00ffcc" if row['Effect'] == 'Punto/Exc' else "#ff4b4b" if row['Effect'] == 'Error' else "#808080"
            fig_s.add_trace(go.Scatter(x=[row['X_In'], row['X_Out']], y=[row['Y_In'], row['Y_Out']],
                                     mode='lines+markers', line=dict(color=color, width=1.5),
                                     marker=dict(size=4), hoverinfo='text', text=f"Jugador: {row['Player']}"))
            
        fig_s.update_layout(width=450, height=800, showlegend=False, template="plotly_dark",
                          xaxis=dict(range=[-1, 10]), yaxis=dict(range=[-1, 19]))
        st.plotly_chart(fig_s, use_container_width=True)

    with tab3:
        st.dataframe(df_f, use_container_width=True)
