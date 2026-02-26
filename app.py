import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 1. ESTILO PROFESIONAL (UX/UI)
st.set_page_config(page_title="MatchPlan Pro | Analytics", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0b0d11; color: #e0e6ed; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏐 MatchPlan Pro | Powered by Volley Vision 360")

# 2. MOTOR DE TRADUCCIÓN Y CÁLCULO
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'F': 'Finta'}
RATINGS = {'#': 'Punto/Perfecto', '+': 'Positivo', '!': 'Exclamación', '-': 'Negativo', '/': 'Pobre', '=': 'Error'}

def dv_to_coords(val):
    """Convierte coordenadas DV4 (ej. 5171) a metros reales"""
    if not val or not str(val).isdigit(): return None, None
    v = int(val)
    # X: 0-100 -> 0-9m | Y: 0-100 -> 0-18m
    x = (v % 100) * 0.09
    y = (v // 100) * 0.18
    return x, y

def parse_dv_pro(content):
    """Lógica de extracción de datos limpios"""
    try:
        scout_idx = next(i for i, l in enumerate(content) if "[3SCOUT]" in l) + 1
    except StopIteration: return pd.DataFrame()

    rows = []
    for line in content[scout_idx:]:
        p = line.split(';')
        if len(p) < 15: continue
        
        c = p[0]
        # Filtro estricto: Debe ser acción táctica válida (* o a, número, skill)
        if len(c) < 6 or c[0] not in ['*', 'a'] or not c[1:3].isdigit() or c[3] not in SKILLS:
            continue
            
        x_in, y_in = dv_to_coords(p[14])
        x_out, y_out = dv_to_coords(p[15])

        rows.append({
            "Equipo": "Local" if c[0] == "*" else "Visitante",
            "Dorsal": c[1:3],
            "Accion": SKILLS[c[3]],
            "Calidad": RATINGS.get(c[5], "Continuidad"),
            "X_In": x_in, "Y_In": y_in, "X_Out": x_out, "Y_Out": y_out,
            "Set": p[11],
            "Fase": "K1" if "K1" in line else "K2",
            "Puntos": f"{p[9]}-{p[10]}"
        })
    return pd.DataFrame(rows)

def draw_pro_court(fig):
    """Dibuja la pista estilo untan.gl"""
    # Perímetro
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="#ffffff", width=2))
    # Red (Centro)
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#00ffcc", width=4))
    # Líneas de 3 metros
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="#555", width=1, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=12, x1=9, y1=12, line=dict(color="#555", width=1, dash="dash"))
    
    fig.update_layout(
        xaxis=dict(range=[-0.5, 9.5], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-0.5, 18.5], showgrid=False, zeroline=False, showticklabels=False),
        template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10)
    )
    return fig

# 3. CARGA DE ARCHIVO
file = st.file_uploader("Sube tu archivo .dvw de Data Volley 4 Pro", type=["dvw"])

if file:
    df = parse_dv_pro(file.read().decode('latin-1').splitlines())
    
    if not df.empty:
        # SIDEBAR: CENTRO DE CONTROL
        st.sidebar.header("🕹️ Filtros de Análisis")
        f_team = st.sidebar.selectbox("Seleccionar Equipo", df['Equipo'].unique())
        f_skill = st.sidebar.selectbox("Fundamento", df['Accion'].unique(), index=list(df['Accion'].unique()).index('Ataque'))
        players = st.sidebar.multiselect("Jugadores", df[df['Equipo'] == f_team]['Dorsal'].unique(), default=df[df['Equipo'] == f_team]['Dorsal'].unique())
        
        df_f = df[(df['Equipo'] == f_team) & (df['Accion'] == f_skill) & (df['Dorsal'].isin(players))]

        # DASHBOARD DE KPIs
        st.subheader("📊 Métricas de Rendimiento")
        c1, c2, c3, c4 = st.columns(4)
        
        total = len(df_f)
        puntos = len(df_f[df_f['Calidad'] == 'Punto/Perfecto'])
        errores = len(df_f[df_f['Calidad'] == 'Error'])
        eff = (puntos - errores) / total if total > 0 else 0
        success = (puntos / total * 100) if total > 0 else 0

        c1.metric("Volumen", total)
        c2.metric("Eficiencia (EFF)", f"{eff:.2f}")
        c3.metric("Éxito (Success %)", f"{success:.1f}%")
        c4.metric("Errores", errores)

        # PESTAÑAS DE VISUALIZACIÓN
        t1, t2, t3 = st.tabs(["🔥 Mapa de Calor", "🏹 Direcciones de Ataque", "📋 Listado de Jugadores"])

        with t1:
            st.write("Densidad de impactos en campo contrario")
            if not df_f['X_Out'].dropna().empty:
                fig_h = px.density_heatmap(df_f, x="X_Out", y="Y_Out", nbinsx=15, nbinsy=30, 
                                         range_x=[0, 9], range_y=[0, 18], color_continuous_scale="Inferno")
                fig_h = draw_pro_court(fig_h)
                st.plotly_chart(fig_h, use_container_width=True)

        with t2:
            st.write("Trayectorias reales desde origen a destino")
            fig_s = go.Figure()
            fig_s = draw_pro_court(fig_s)
            
            for _, r in df_f.dropna(subset=['X_In', 'X_Out']).iterrows():
                color = "#00ffcc" if r['Calidad'] == 'Punto/Perfecto' else "#ff4b4b" if r['Calidad'] == 'Error' else "#888888"
                fig_s.add_trace(go.Scatter(x=[r['X_In'], r['X_Out']], y=[r['Y_In'], r['Y_Out']],
                                         mode='lines+markers', line=dict(color=color, width=1.5),
                                         marker=dict(size=4), hoverinfo='text', 
                                         text=f"Jugador: {r['Dorsal']} | Marcador: {r['Puntos']}"))
            st.plotly_chart(fig_s, use_container_width=True)

        with t3:
            # Resumen por jugador
            player_stats = df_f.groupby('Dorsal').size().reset_index(name='Total')
            st.dataframe(df_f[['Dorsal', 'Accion', 'Calidad', 'Puntos', 'Fase']], use_container_width=True)

    else:
        st.warning("No se encontraron acciones tácticas válidas en este archivo.")
