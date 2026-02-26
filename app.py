import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- CONFIGURACIÓN DE INTERFAZ DE ÉLITE ---
st.set_page_config(page_title="MatchPlan Pro | Analytics", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; }
    div[data-testid="stExpander"] { background-color: #161b22; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- DICCIONARIOS TÉCNICOS ---
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'F': 'Finta'}
RATINGS = {'#': 'Punto/Exc', '+': 'Positivo', '!': 'Excl!', '-': 'Negativo', '/': 'Pobre', '=': 'Error'}

# --- MOTOR GEOESPACIAL Y DE DIBUJO ---
def get_coords(dv_coord):
    """Traduce coordenadas DV4 a metros reales de pista (9x18m)"""
    if not dv_coord or not str(dv_coord).isdigit(): return None, None
    c = int(dv_coord)
    # DV usa escala 0-100 para cada eje del campo
    x = (c % 100) * 0.09
    y = (c // 100) * 0.18
    return x, y

def draw_voley_court(fig):
    """Dibuja líneas reglamentarias FIVB sobre Plotly"""
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="white", width=3))
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#00ffcc", width=4)) # Red
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="white", width=1, dash="dash")) # 3m
    fig.add_shape(type="line", x0=0, y0=12, x1=9, y1=12, line=dict(color="white", width=1, dash="dash")) # 3m
    fig.update_layout(xaxis=dict(range=[-0.5, 9.5], showgrid=False, zeroline=False, showticklabels=False),
                      yaxis=dict(range=[-0.5, 18.5], showgrid=False, zeroline=False, showticklabels=False),
                      margin=dict(l=0, r=0, t=30, b=0), template="plotly_dark")
    return fig

# --- PARSER PROFESIONAL DE DATOS ---
def parse_match_pro(content):
    try:
        scout_idx = next(i for i, l in enumerate(content) if "[3SCOUT]" in l) + 1
    except StopIteration: return pd.DataFrame()
    
    actions = []
    current_set = "1"
    
    for line in content[scout_idx:]:
        p = line.split(';')
        if not p or len(p) < 5: continue
        
        code = p[0]
        # Filtro estricto: solo líneas que midan al menos 6 caracteres y sean acciones (no rotaciones)
        if len(code) < 6 or code[0] not in ['*', 'a'] or not code[1:3].isdigit():
            continue
            
        skill_key = code[3]
        if skill_key not in SKILLS: continue
        
        x_in, y_in = get_coords(p[14]) if len(p) > 14 else (None, None)
        x_out, y_out = get_coords(p[15]) if len(p) > 15 else (None, None)
        
        actions.append({
            "Equipo": "Local" if code[0] == "*" else "Visitante",
            "Jugador": code[1:3],
            "Acción": SKILLS[skill_key],
            "Efecto": RATINGS.get(code[5], "Continuidad"),
            "X_In": x_in, "Y_In": y_in, "X_Out": x_out, "Y_Out": y_out,
            "Set": p[11] if len(p) > 11 else current_set,
            "Fase": "K1" if "K1" in line else "K2",
            "Full": code
        })
    return pd.DataFrame(actions)

# --- APP LAYOUT ---
st.title("🏐 MatchPlan Pro | Advanced Scouting")
uploaded = st.file_uploader("Cargar archivo .dvw", type=["dvw"])

if uploaded:
    raw_content = uploaded.read().decode('latin-1').splitlines()
    df = parse_match_pro(raw_content)
    
    if not df.empty:
        # 1. KPIs de Élite
        st.subheader("📊 Análisis de Eficiencia (EFF)")
        attacks = df[df['Acción'] == 'Ataque']
        puntos = len(attacks[attacks['Efecto'] == 'Punto/Exc'])
        errores = len(attacks[attacks['Efecto'] == 'Error'])
        eff = (puntos - errores) / len(attacks) if len(attacks) > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Eficiencia Ataque", f"{eff:.2f}")
        c2.metric("Puntos Ganados", puntos)
        c3.metric("Errores No Forzados", errores)
        c4.metric("Carga de Juego", f"{len(df)} acc.")

        # 2. Centro de Control (Sidebar)
        st.sidebar.header("🎯 Filtros Tácticos")
        f_team = st.sidebar.selectbox("Equipo", df['Equipo'].unique())
        f_skill = st.sidebar.selectbox("Fundamento", df['Acción'].unique(), index=list(df['Acción'].unique()).index('Ataque') if 'Ataque' in df['Acción'].unique() else 0)
        f_player = st.sidebar.multiselect("Jugadores", df[df['Equipo'] == f_team]['Jugador'].unique(), default=df[df['Equipo'] == f_team]['Jugador'].unique())
        
        df_f = df[(df['Equipo'] == f_team) & (df['Acción'] == f_skill) & (df['Jugador'].isin(f_player))]

        # 3. Visualizaciones Revolucionarias
        t1, t2, t3 = st.tabs(["🔥 Mapa de Calor", "🏹 Trayectorias", "📋 Data Raw"])
        
        with t1:
            if not df_f['X_Out'].dropna().empty:
                fig_h = px.density_heatmap(df_f, x="X_Out", y="Y_Out", nbinsx=15, nbinsy=30,
                                         range_x=[0, 9], range_y=[0, 18], color_continuous_scale="Hot")
                fig_h = draw_voley_court(fig_h)
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("No hay suficientes coordenadas exactas en este archivo para el Mapa de Calor.")

        with t2:
            fig_s = go.Figure()
            fig_s = draw_voley_court(fig_s)
            for _, r in df_f.dropna(subset=['X_In', 'X_Out']).iterrows():
                color = "#00ffcc" if r['Efecto'] == 'Punto/Exc' else "#ff4b4b" if r['Efecto'] == 'Error' else "#888"
                fig_s.add_trace(go.Scatter(x=[r['X_In'], r['X_Out']], y=[r['Y_In'], r['Y_Out']],
                                         mode='lines+markers', line=dict(color=color, width=1.5),
                                         marker=dict(size=4), hoverinfo='text', text=f"J:{r['Jugador']} - {r['Efecto']}"))
            st.plotly_chart(fig_s, use_container_width=True)

        with t3:
            st.dataframe(df_f, use_container_width=True)
    else:
        st.warning("El archivo se leyó pero no se encontraron acciones tácticas válidas. Revisa el formato.")
