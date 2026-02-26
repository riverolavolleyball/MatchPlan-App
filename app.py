import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import random

# ==========================================
# 1. CONFIGURACIÓN DEL ECOSISTEMA
# ==========================================
st.set_page_config(page_title="MatchPlan Suite | Riverola Volleyball", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; color: #1e293b; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0f172a; color: #ffffff; }
    h1, h2, h3 { color: #0f172a; font-weight: 700; }
    .stMetric { background-color: white; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb; padding: 15px; border-radius: 6px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR CORE DE DATAVOLLEY 4 PRO
# ==========================================
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'F': 'Finta'}
RATINGS = {'#': 'Perfecto (#)', '+': 'Positivo (+)', '!': 'Exclamación (!)', '-': 'Negativo (-)', '/': 'Pobre (/)', '=': 'Error (=)'}

def extraer_coordenadas(exact_val, zone_char, is_start):
    if exact_val and str(exact_val).isdigit() and int(exact_val) > 0:
        val = int(exact_val)
        return (val % 100) * 0.09, (val // 100) * 0.18
    if not zone_char or not zone_char.isdigit() or zone_char == '0': return None, None
    z = int(zone_char)
    if is_start: 
        x_m = {1: 7.5, 2: 7.5, 3: 4.5, 4: 1.5, 5: 1.5, 6: 4.5, 7: 1.5, 8: 4.5, 9: 7.5}
        y_m = {1: 1.5, 2: 7.5, 3: 7.5, 4: 7.5, 5: 1.5, 6: 1.5, 7: -0.5, 8: -0.5, 9: -0.5}
    else: 
        x_m = {1: 1.5, 2: 1.5, 3: 4.5, 4: 7.5, 5: 7.5, 6: 4.5, 7: 7.5, 8: 4.5, 9: 1.5}
        y_m = {1: 16.5, 2: 10.5, 3: 10.5, 4: 10.5, 5: 16.5, 6: 16.5, 7: 18.5, 8: 18.5, 9: 18.5}
    if z in x_m: return x_m[z] + random.uniform(-0.6, 0.6), y_m[z] + random.uniform(-0.6, 0.6)
    return None, None

@st.cache_data
def procesar_archivos(archivos):
    todos_datos = []
    for archivo in archivos:
        contenido = archivo.read().decode('latin-1').splitlines()
        try: scout_idx = next(i for i, l in enumerate(contenido) if "[3SCOUT]" in l) + 1
        except: continue

        equipo_local, equipo_vis = "Local", "Visitante"
        for i, l in enumerate(contenido):
            if "[3TEAMS]" in l:
                equipo_local, equipo_vis = contenido[i+1].strip(), contenido[i+2].strip()
                break

        rec_calidad_memoria = "No K1"
        for line in contenido[scout_idx:]:
            p = line.split(';')
            if len(p) < 11: continue
            c = p[0]
            if len(c) < 6 or c[0] not in ['*', 'a'] or not c[1:3].isdigit() or c[3] not in SKILLS: continue

            accion = SKILLS[c[3]]
            calidad = RATINGS.get(c[5], "Continuidad")
            
            if accion == 'Recepción': rec_calidad_memoria = calidad
            elif accion == 'Saque': rec_calidad_memoria = "No K1"

            z_in = c[9] if len(c) > 9 and c[9] != '~' else "N/A"
            z_out = c[10] if len(c) > 10 and c[10] != '~' else "N/A"
            x_in, y_in = extraer_coordenadas(p[14] if len(p) > 14 else None, z_in, True)
            x_out, y_out = extraer_coordenadas(p[15] if len(p) > 15 else None, z_out, False)

            todos_datos.append({
                "Partido": f"{equipo_local} vs {equipo_vis}",
                "Equipo": equipo_local if c[0] == "*" else equipo_vis,
                "Rival": equipo_vis if c[0] == "*" else equipo_local,
                "Dorsal": c[1:3],
                "Accion": accion,
                "Calidad": calidad,
                "Z_Ini": z_in, "Z_Fin": z_out,
                "X_In": x_in, "Y_In": y_in, "X_Out": x_out, "Y_Out": y_out,
                "Fase": "Side-Out (K1)" if "K1" in line else "Transición (K2)",
                "Rec_Previa": rec_calidad_memoria if accion in ['Ataque', 'Colocación'] and "K1" in line else "-"
            })
    return pd.DataFrame(todos_datos)

def dibujar_pista_fivb():
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="#1e293b", width=2))
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#2563eb", width=4)) 
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="#94a3b8", width=2, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=12, x1=9, y1=12, line=dict(color="#94a3b8", width=2, dash="dash"))
    fig.update_layout(xaxis=dict(range=[-0.5, 9.5], visible=False), yaxis=dict(range=[-0.5, 18.5], visible=False),
                      plot_bgcolor="white", margin=dict(l=0, r=0, t=10, b=10))
    return fig

# ==========================================
# 3. INTERFAZ: SELECTOR DE APPS (MENU LATERAL)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Volleyball_icon.svg/200px-Volleyball_icon.svg.png", width=60)
st.sidebar.title("MatchPlan Suite")

app_activa = st.sidebar.radio("Navegador de Apps:", [
    "📁 File Validator",
    "🧠 Set Distribution",
    "🏹 Attack Charts",
    "⚔️ Teams Matchup",
    "🛡️ Defensive Analysis",
    "📈 League Leaderboards"
])

archivos = st.sidebar.file_uploader("📥 Cargar DVW", type=["dvw"], accept_multiple_files=True)

if archivos:
    df = procesar_archivos(archivos)
    
    if not df.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**⚙️ Filtro de Contexto**")
        equipo_sel = st.sidebar.selectbox("Analizar Equipo", df['Equipo'].unique())
        df_eq = df[df['Equipo'] == equipo_sel]

        # ---------------------------------------------------------
        # APP 1: FILE VALIDATOR
        # ---------------------------------------------------------
        if "Validator" in app_activa:
            st.header(f"📁 Validador de Datos: {equipo_sel}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Partidos Procesados", df_eq['Partido'].nunique())
            c2.metric("Total Acciones", len(df_eq))
            c3.metric("Volumen de Ataque", len(df_eq[df_eq['Accion'] == 'Ataque']))
            st.dataframe(df_eq[['Partido', 'Fase', 'Dorsal', 'Accion', 'Calidad', 'Z_Ini', 'Z_Fin']], use_container_width=True)

        # ---------------------------------------------------------
        # APP 2: SET DISTRIBUTION
        # ---------------------------------------------------------
        elif "Distribution" in app_activa:
            st.header(f"🧠 Set Distribution Analysis: {equipo_sel}")
            df_k1 = df_eq[(df_eq['Accion'] == 'Ataque') & (df_eq['Fase'] == 'Side-Out (K1)')]
            if not df_k1.empty:
                crosstab = pd.crosstab(df_k1['Rec_Previa'], df_k1['Z_Ini'], normalize='index') * 100
                st.write("**Distribución Ofensiva % (Por dónde se ataca según el pase)**")
                st.dataframe(crosstab.round(1).astype(str) + '%', use_container_width=True)
                fig_bar = px.histogram(df_k1, x="Rec_Previa", color="Z_Ini", barmode="group",
                                       color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.warning("Datos insuficientes de Side-Out.")

        # ---------------------------------------------------------
        # APP 3: ATTACK CHARTS
        # ---------------------------------------------------------
        elif "Attack" in app_activa:
            st.header(f"🏹 Attack Charts: {equipo_sel}")
            df_ataque = df_eq[df_eq['Accion'] == 'Ataque']
            jugador_sel = st.selectbox("Filtrar Atacante", ["Todo el Equipo"] + list(df_ataque['Dorsal'].unique()))
            if jugador_sel != "Todo el Equipo": df_ataque = df_ataque[df_ataque['Dorsal'] == jugador_sel]

            col1, col2 = st.columns([2, 1])
            with col1:
                fig_pista = dibujar_pista_fivb()
                for _, r in df_ataque.dropna(subset=['X_In', 'X_Out']).iterrows():
                    color = "#10b981" if "Perfecto" in r['Calidad'] else "#ef4444" if "Error" in r['Calidad'] else "#94a3b8"
                    fig_pista.add_trace(go.Scatter(x=[r['X_In'], r['X_Out']], y=[r['Y_In'], r['Y_Out']],
                                                 mode='lines+markers', line=dict(color=color, width=2),
                                                 marker=dict(size=4), hoverinfo='text', 
                                                 text=f"Calidad: {r['Calidad']}"))
                fig_pista.update_layout(width=500, height=800, showlegend=False)
                st.plotly_chart(fig_pista)
            with col2:
                puntos = len(df_ataque[df_ataque['Calidad'] == 'Perfecto (#)'])
                errores = len(df_ataque[df_ataque['Calidad'] == 'Error (=)'])
                eff = ((puntos - errores) / len(df_ataque) * 100) if len(df_ataque) > 0 else 0
                st.metric("Total Ataques", len(df_ataque))
                st.metric("Eficiencia Neta", f"{eff:.1f}%")

        # ---------------------------------------------------------
        # APP 4: TEAMS MATCHUP (NUEVA FASE)
        # ---------------------------------------------------------
        elif "Matchup" in app_activa:
            st.header("⚔️ Teams Matchup: Comparativa Directa")
            st.markdown("Comparación de KPIs críticos entre el equipo analizado y su rival directo en el archivo.")
            
            # Identificar al rival (asumiendo análisis de 1 partido para simplificar la vista directa)
            rival_sel = df_eq['Rival'].iloc[0] if not df_eq.empty else "Rival"
            
            # Función interna para calcular KPIs
            def calcular_kpis(data_equipo):
                kpis = {}
                # Ataque K1
                ataques_k1 = data_equipo[(data_equipo['Accion'] == 'Ataque') & (data_equipo['Fase'] == 'Side-Out (K1)')]
                kpis['EFF K1 %'] = ((len(ataques_k1[ataques_k1['Calidad'] == 'Perfecto (#)']) - len(ataques_k1[ataques_k1['Calidad'] == 'Error (=)'])) / len(ataques_k1) * 100) if len(ataques_k1) > 0 else 0
                # Ataque K2
                ataques_k2 = data_equipo[(data_equipo['Accion'] == 'Ataque') & (data_equipo['Fase'] == 'Transición (K2)')]
                kpis['EFF K2 %'] = ((len(ataques_k2[ataques_k2['Calidad'] == 'Perfecto (#)']) - len(ataques_k2[ataques_k2['Calidad'] == 'Error (=)'])) / len(ataques_k2) * 100) if len(ataques_k2) > 0 else 0
                # Recepción Positiva/Perfecta
                reps = data_equipo[data_equipo['Accion'] == 'Recepción']
                kpis['Rec Positiva %'] = (len(reps[reps['Calidad'].isin(['Perfecto (#)', 'Positivo (+)', 'Exclamación (!)'])])) / len(reps) * 100 if len(reps) > 0 else 0
                # Puntos de Bloqueo Absolutos
                kpis['Puntos Bloqueo'] = len(data_equipo[(data_equipo['Accion'] == 'Bloqueo') & (data_equipo['Calidad'] == 'Perfecto (#)')])
                # Aces
                kpis['Aces'] = len(data_equipo[(data_equipo['Accion'] == 'Saque') & (data_equipo['Calidad'] == 'Perfecto (#)')])
                return kpis

            kpis_eq1 = calcular_kpis(df[df['Equipo'] == equipo_sel])
            kpis_eq2 = calcular_kpis(df[df['Equipo'] == rival_sel])

            # Construcción de la tabla comparativa
            df_matchup = pd.DataFrame({
                "KPI": list(kpis_eq1.keys()),
                equipo_sel: [round(v, 1) for v in kpis_eq1.values()],
                rival_sel: [round(v, 1) for v in kpis_eq2.values()]
            })

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Tabla de Rendimiento Cruzado**")
                st.dataframe(df_matchup, use_container_width=True, hide_index=True)
                
            with col_b:
                st.markdown("**Radar Táctico (Balance de Fuerzas)**")
                # Filtrar métricas porcentuales para el radar para no desescalar con valores absolutos
                categorias = ['EFF K1 %', 'EFF K2 %', 'Rec Positiva %']
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=[kpis_eq1[c] for c in categorias], theta=categorias, fill='toself', name=equipo_sel, line_color='#2563eb'
                ))
                fig_radar.add_trace(go.Scatterpolar(
                    r=[kpis_eq2[c] for c in categorias], theta=categorias, fill='toself', name=rival_sel, line_color='#ef4444'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, margin=dict(l=40, r=40, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)

        # ---------------------------------------------------------
        # APPS EN DESARROLLO
        # ---------------------------------------------------------
        elif "Defensive" in app_activa or "Leaderboards" in app_activa:
            st.header(f"🛠️ Módulo en Construcción: {app_activa}")
            st.info("Estructura base lista. Pendiente programación lógica.")
            
    else:
        st.error("No se han extraído datos válidos.")
else:
    st.info("👈 Sube archivos .dvw en el menú lateral para iniciar la Suite de Riverola Volleyball.")
