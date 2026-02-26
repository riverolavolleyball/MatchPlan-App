import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# 1. CONFIGURACIÓN CORPORATIVA (RIVEROLA VOLLEYBALL)
# ==========================================
st.set_page_config(page_title="MatchPlan | Riverola Volleyball", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; color: #1e293b; font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    [data-testid="stSidebar"] { background-color: #1e293b; color: white; }
    h1, h2, h3 { color: #0f172a; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 2px solid #e2e8f0; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; color: #64748b; font-weight: 600; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #2563eb; border-bottom: 3px solid #2563eb; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>🏐 MatchPlan Analytics</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748b; font-size: 1.1rem; font-weight: 500;'>Powered by Riverola Volleyball | Tactical Intelligence</p>", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE PROCESAMIENTO TÁCTICO
# ==========================================
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa'}
RATINGS = {'#': 'Punto / Perfecto', '+': 'Positivo', '!': 'Exclamación', '-': 'Negativo', '/': 'Pobre', '=': 'Error'}

@st.cache_data
def procesar_scouting(lineas):
    try:
        scout_idx = next(i for i, l in enumerate(lineas) if "[3SCOUT]" in l) + 1
    except StopIteration:
        return pd.DataFrame()

    datos = []
    for i, line in enumerate(lineas[scout_idx:]):
        p = line.split(';')
        if len(p) < 11: continue
        c = p[0]
        
        if len(c) < 6 or c[0] not in ['*', 'a'] or not c[1:3].isdigit() or c[3] not in SKILLS:
            continue
            
        z_in = c[9] if len(c) > 9 and c[9].isdigit() else "Desc"
        z_out = c[10] if len(c) > 10 and c[10].isdigit() else "Desc"
        
        # Clasificación de Fases
        fase = "Transición (K2)"
        if "K1" in line: fase = "Side-Out (K1)"
        
        datos.append({
            "Equipo": "Local" if c[0] == "*" else "Visitante",
            "Dorsal": c[1:3],
            "Fundamento": SKILLS[c[3]],
            "Calidad": RATINGS.get(c[5], "Continuidad"),
            "Z_Origen": z_in,
            "Z_Destino": z_out,
            "Fase": fase
        })
        
    return pd.DataFrame(datos)

def dibujar_pista_tactica(fig):
    """Pista limpia y minimalista para análisis claro"""
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="#1e293b", width=2))
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#2563eb", width=4)) # Red
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="#cbd5e1", width=2, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=12, x1=9, y1=12, line=dict(color="#cbd5e1", width=2, dash="dash"))
    
    # Etiquetas de zonas (Campo rival)
    zonas_rivales = {1: (1.5, 16.5), 2: (1.5, 10.5), 3: (4.5, 10.5), 4: (7.5, 10.5), 5: (7.5, 16.5), 6: (4.5, 16.5)}
    for z, coords in zonas_rivales.items():
        fig.add_annotation(x=coords[0], y=coords[1], text=f"Z{z}", showarrow=False, font=dict(color="#94a3b8", size=16))

    fig.update_layout(xaxis=dict(range=[-0.5, 9.5], visible=False), yaxis=dict(range=[-0.5, 18.5], visible=False),
                      plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
    return fig

# ==========================================
# 3. INTERFAZ Y DASHBOARD EJECUTIVO
# ==========================================
archivo = st.file_uploader("📥 Cargar archivo DVW (Data Volley 4)", type=["dvw"])

if archivo:
    df = procesar_scouting(archivo.read().decode('latin-1').splitlines())
    
    if not df.empty:
        # --- FILTROS DE MATCH PLAN ---
        st.sidebar.markdown("### 🎯 Configuración del Match Plan")
        equipo_sel = st.sidebar.selectbox("Seleccionar Equipo a Analizar", df['Equipo'].unique())
        
        df_equipo = df[df['Equipo'] == equipo_sel]
        
        # --- TABS DE ANÁLISIS TÁCTICO ---
        tab1, tab2, tab3 = st.tabs(["⚔️ Tendencias de Ataque", "🎯 Análisis de Saque", "📊 Rendimiento de Recepción"])

        # TAB 1: ATAQUE Y COLOCACIÓN
        with tab1:
            st.markdown(f"### Análisis de Ataque - {equipo_sel}")
            df_ataque = df_equipo[df_equipo['Fundamento'] == 'Ataque']
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("**Distribución por Zonas de Origen (Tendencia del Colocador)**")
                distribucion = df_ataque['Z_Origen'].value_counts(normalize=True) * 100
                st.dataframe(distribucion.round(1).astype(str) + '%', use_container_width=True)
                
                st.markdown("**Eficiencia por Fase**")
                for fase in ["Side-Out (K1)", "Transición (K2)"]:
                    df_fase = df_ataque[df_ataque['Fase'] == fase]
                    if not df_fase.empty:
                        eff = (len(df_fase[df_fase['Calidad'] == 'Punto / Perfecto']) - len(df_fase[df_fase['Calidad'] == 'Error'])) / len(df_fase) * 100
                        st.metric(f"EFF % - {fase}", f"{eff:.1f}%")

            with col2:
                st.markdown("**Eficacia de los Atacantes Principales**")
                ataques_resumen = df_ataque.groupby('Dorsal').agg(
                    Volumen=('Calidad', 'count'),
                    Puntos=('Calidad', lambda x: (x == 'Punto / Perfecto').sum()),
                    Errores=('Calidad', lambda x: (x == 'Error').sum())
                ).reset_index()
                ataques_resumen['EFF %'] = ((ataques_resumen['Puntos'] - ataques_resumen['Errores']) / ataques_resumen['Volumen'] * 100).round(1)
                ataques_resumen = ataques_resumen[ataques_resumen['Volumen'] > 2].sort_values(by='Volumen', ascending=False)
                st.dataframe(ataques_resumen, use_container_width=True, hide_index=True)

        # TAB 2: SAQUE
        with tab2:
            st.markdown(f"### Presión de Saque - {equipo_sel}")
            df_saque = df_equipo[df_equipo['Fundamento'] == 'Saque']
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Saques", len(df_saque))
            c2.metric("Aces (#)", len(df_saque[df_saque['Calidad'] == 'Punto / Perfecto']))
            c3.metric("Errores de Saque (=)", len(df_saque[df_saque['Calidad'] == 'Error']))
            
            st.markdown("**Destinos de Saque Frecuentes (Zonas Rivales)**")
            destinos = df_saque[df_saque['Z_Destino'] != 'Desc']['Z_Destino'].value_counts(normalize=True).head(5) * 100
            st.bar_chart(destinos)

            st.markdown("**Rendimiento por Sacador**")
            saque_resumen = df_saque.groupby('Dorsal').agg(
                Intentos=('Calidad', 'count'),
                Aces=('Calidad', lambda x: (x == 'Punto / Perfecto').sum()),
                Errores=('Calidad', lambda x: (x == 'Error').sum())
            ).reset_index().sort_values(by='Intentos', ascending=False)
            st.dataframe(saque_resumen, use_container_width=True, hide_index=True)

        # TAB 3: RECEPCIÓN
        with tab3:
            st.markdown(f"### Estabilidad en Recepción - {equipo_sel}")
            df_rec = df_equipo[df_equipo['Fundamento'] == 'Recepción']
            
            if not df_rec.empty:
                positivas = len(df_rec[df_rec['Calidad'].isin(['Punto / Perfecto', 'Positivo'])])
                porcentaje_pos = (positivas / len(df_rec)) * 100
                
                st.metric("Recepción Perfecta/Positiva (# / +)", f"{porcentaje_pos:.1f}%")
                
                st.markdown("**Carga de Recepción por Jugador**")
                rec_resumen = df_rec.groupby('Dorsal').agg(
                    Total=('Calidad', 'count'),
                    Perfectas=('Calidad', lambda x: (x == 'Punto / Perfecto').sum()),
                    Errores=('Calidad', lambda x: (x == 'Error').sum())
                ).reset_index()
                rec_resumen['% Perfecta'] = (rec_resumen['Perfectas'] / rec_resumen['Total'] * 100).round(1)
                st.dataframe(rec_resumen.sort_values(by='Total', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos de recepción para el equipo seleccionado.")
    else:
        st.error("No se han encontrado datos procesables.")
