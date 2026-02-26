import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import random
import re

# ==========================================
# 1. CONFIGURACIÓN DEL SISTEMA Y UI
# ==========================================
st.set_page_config(page_title="MatchPlan Suite | Riverola Volleyball", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
    :root { --bg-color: #0f172a; --panel-bg: #1e293b; --text-main: #f8fafc; --accent: #3b82f6; }
    .main { background-color: var(--bg-color); color: var(--text-main); font-family: 'Inter', sans-serif; }
    .stMetric { background-color: var(--panel-bg); border: 1px solid #334155; border-left: 4px solid var(--accent); padding: 1rem; border-radius: 0.5rem; }
    [data-testid="stSidebar"] { background-color: #020617; border-right: 1px solid #1e293b; }
    h1, h2, h3, h4 { color: #f1f5f9; font-weight: 700; letter-spacing: -0.025em; }
    .stDataFrame { border: 1px solid #334155; border-radius: 0.5rem; }
    hr { border-color: #334155; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTES TÉCNICAS (DATA VOLLEY 4 PRO)
# ==========================================
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'F': 'Finta'}
RATINGS = {'#': 'Perfecto', '+': 'Positivo', '!': 'Exclamación', '-': 'Negativo', '/': 'Pobre', '=': 'Error'}
ZONAS_ATAQUE = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

# ==========================================
# 3. MOTOR GEOESPACIAL AVANZADO (JITTER ENGINE)
# ==========================================
def traducir_coordenadas_fivb(exact_str, zone_str, is_start):
    """
    Motor de renderizado espacial. 
    Prioridad 1: Coordenada X,Y exacta (Clic del Scouter).
    Prioridad 2: Cálculo matemático sobre el centro de la zona + Jitter gaussiano.
    """
    if exact_str and str(exact_str).isdigit() and int(exact_str) > 0:
        val = int(exact_str)
        return (val % 100) * 0.09, (val // 100) * 0.18
    
    if not zone_str or not str(zone_str).isdigit() or zone_char == '0':
        return None, None
        
    z = int(zone_str)
    # Matriz de centros de zona
    if is_start:
        x_map = {1: 7.5, 2: 7.5, 3: 4.5, 4: 1.5, 5: 1.5, 6: 4.5, 7: 1.5, 8: 4.5, 9: 7.5}
        y_map = {1: 1.5, 2: 7.5, 3: 7.5, 4: 7.5, 5: 1.5, 6: 1.5, 7: -0.5, 8: -0.5, 9: -0.5}
    else:
        x_map = {1: 1.5, 2: 1.5, 3: 4.5, 4: 7.5, 5: 7.5, 6: 4.5, 7: 7.5, 8: 4.5, 9: 1.5}
        y_map = {1: 16.5, 2: 10.5, 3: 10.5, 4: 10.5, 5: 16.5, 6: 16.5, 7: 18.5, 8: 18.5, 9: 18.5}
        
    if z in x_map:
        # Distribución normal para simular impacto orgánico
        return np.random.normal(x_map[z], 0.4), np.random.normal(y_map[z], 0.4)
    return None, None

# ==========================================
# 4. PARSER DE DATOS (DATA CLEANING & FEATURE ENGINEERING)
# ==========================================
@st.cache_data(show_spinner="Procesando matriz de datos...")
def parsear_archivos_dvw(archivos):
    master_data = []
    
    for archivo in archivos:
        archivo.seek(0)
        lineas = archivo.read().decode('latin-1', errors='ignore').splitlines()
        
        try:
            scout_start = next(i for i, l in enumerate(lineas) if "[3SCOUT]" in l) + 1
            teams_start = next(i for i, l in enumerate(lineas) if "[3TEAMS]" in l) + 1
            eq_local = lineas[teams_start].strip()
            eq_visitante = lineas[teams_start+1].strip()
        except:
            continue

        # Memoria de estado para análisis relacional
        memoria_recepcion = "Sin Recepción"
        
        for num_linea, linea in enumerate(lineas[scout_start:]):
            p = linea.split(';')
            if len(p) < 11: continue
            
            codigo = p[0]
            if len(codigo) < 6 or codigo[0] not in ['*', 'a'] or not codigo[1:3].isdigit(): continue
            if codigo[3] not in SKILLS: continue

            equipo = eq_local if codigo[0] == "*" else eq_visitante
            rival = eq_visitante if codigo[0] == "*" else eq_local
            dorsal = codigo[1:3]
            fundamento = SKILLS[codigo[3]]
            calidad = RATINGS.get(codigo[5], "Continuidad")
            
            # Lógica relacional (Pase -> Colocación -> Ataque)
            if fundamento == 'Recepción': memoria_recepcion = calidad
            elif fundamento == 'Saque': memoria_recepcion = "Sin Recepción"

            z_ini = codigo[9] if len(codigo) > 9 and codigo[9].isdigit() else "N/A"
            z_fin = codigo[10] if len(codigo) > 10 and codigo[10].isdigit() else "N/A"
            
            x_in, y_in = traducir_coordenadas_fivb(p[14] if len(p) > 14 else None, z_ini, True)
            x_out, y_out = traducir_coordenadas_fivb(p[15] if len(p) > 15 else None, z_fin, False)

            # Clasificación Avanzada K1/K2
            fase = "Side-Out (K1)" if "K1" in linea else "Transición (K2)"
            if fundamento == 'Saque': fase = "Saque (BP)"
            elif fundamento == 'Recepción': fase = "Side-Out (K1)"

            master_data.append({
                "ID_Accion": f"{eq_local[:3]}-{num_linea}",
                "Partido": f"{eq_local} vs {eq_visitante}",
                "Set": p[11] if len(p) > 11 else "1",
                "Marcador": f"{p[9]}-{p[10]}",
                "Equipo": equipo,
                "Rival": rival,
                "Dorsal": dorsal,
                "Fundamento": fundamento,
                "Calidad": calidad,
                "Z_Origen": z_ini,
                "Z_Destino": z_fin,
                "X_In": x_in, "Y_In": y_in, "X_Out": x_out, "Y_Out": y_out,
                "Fase": fase,
                "Calidad_Pase_Previo": memoria_recepcion if fundamento in ['Colocación', 'Ataque'] else "N/A"
            })
            
    return pd.DataFrame(master_data)

# ==========================================
# 5. RENDERIZADO VISUAL (CANVAS FIVB)
# ==========================================
def renderizar_cancha_fivb(opacidad_fondo=1.0):
    fig = go.Figure()
    # Pista Base
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, fillcolor=f"rgba(209, 142, 84, {opacidad_fondo})", line=dict(color="#ffffff", width=2))
    # Red
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#ef4444", width=5))
    # Líneas de 3 metros
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="#ffffff", width=2))
    fig.add_shape(type="line", x0=0, y0=12, x1=9, y1=12, line=dict(color="#ffffff", width=2))
    
    fig.update_layout(
        xaxis=dict(range=[-1, 10], visible=False),
        yaxis=dict(range=[-1, 19], visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=10)
    )
    return fig

# ==========================================
# 6. ESTRUCTURA DE LA APLICACIÓN (UI)
# ==========================================
st.sidebar.markdown("## 🏐 Riverola Volleyball")
st.sidebar.markdown("<p style='color: #64748b; font-size: 0.8rem;'>TACTICAL INTELLIGENCE SUITE</p>", unsafe_allow_html=True)
st.sidebar.divider()

modo_app = st.sidebar.radio("MÓDULOS DE ANÁLISIS", [
    "📁 1. Data Validator (Raw Data)",
    "🧠 2. Setter Distribution (K1)",
    "🏹 3. Attack Analytics",
    "🎯 4. Serve & Pass Evaluation",
    "⚔️ 5. Teams Matchup (H2H)"
])

archivos_upload = st.sidebar.file_uploader("Subir archivos de scouting (.dvw)", type=["dvw"], accept_multiple_files=True)

if archivos_upload:
    df = parsear_archivos_dvw(archivos_upload)
    
    if not df.empty:
        st.sidebar.divider()
        equipo_target = st.sidebar.selectbox("🎯 EQUIPO A ANALIZAR", df['Equipo'].unique())
        df_target = df[df['Equipo'] == equipo_target]

        # ---------------------------------------------------------
        # MÓDULO 1: DATA VALIDATOR (DB & Limpieza)
        # ---------------------------------------------------------
        if "Validator" in modo_app:
            st.markdown(f"## 📁 Base de Datos Consolidada: {equipo_target}")
            st.markdown("Inspección de la estructura de datos en bruto y volumetría global.")
            
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Volumen Total", len(df_target))
            kpi2.metric("Ataques (Total)", len(df_target[df_target['Fundamento'] == 'Ataque']))
            kpi3.metric("Recepciones (Total)", len(df_target[df_target['Fundamento'] == 'Recepción']))
            kpi4.metric("Sets Analizados", df_target['Set'].nunique())

            st.dataframe(df_target.drop(columns=['ID_Accion', 'X_In', 'Y_In', 'X_Out', 'Y_Out']), use_container_width=True, height=500)

        # ---------------------------------------------------------
        # MÓDULO 2: SETTER DISTRIBUTION (Colocador)
        # ---------------------------------------------------------
        elif "Distribution" in modo_app:
            st.markdown(f"## 🧠 Patrones de Distribución: {equipo_target}")
            st.markdown("Análisis condicionado de las decisiones del colocador en función de la calidad del primer toque.")
            
            df_k1 = df_target[(df_target['Fundamento'] == 'Ataque') & (df_target['Fase'] == 'Side-Out (K1)')]
            
            if not df_k1.empty:
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.markdown("### % Distribución según Calidad de Pase")
                    tabla_dist = pd.crosstab(df_k1['Calidad_Pase_Previo'], df_k1['Z_Origen'], normalize='index') * 100
                    st.dataframe(tabla_dist.round(1).astype(str) + '%', use_container_width=True)
                
                with col_b:
                    st.markdown("### Mapa de Calor de Colocación (Zonas de Origen)")
                    fig_heat_setter = px.density_heatmap(df_k1, x="X_In", y="Y_In", nbinsx=15, nbinsy=15, 
                                                         range_x=[0,9], range_y=[0,9], color_continuous_scale="Viridis")
                    fig_heat_setter.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_heat_setter, use_container_width=True)
            else:
                st.info("No hay datos de ataque en K1 para este equipo.")

        # ---------------------------------------------------------
        # MÓDULO 3: ATTACK ANALYTICS (Táctica Ofensiva)
        # ---------------------------------------------------------
        elif "Attack" in modo_app:
            st.markdown(f"## 🏹 Attack Analytics: {equipo_target}")
            
            df_atk = df_target[df_target['Fundamento'] == 'Ataque']
            
            # Filtros Secundarios
            f_col1, f_col2, f_col3 = st.columns(3)
            filtro_fase = f_col1.selectbox("Fase de Juego", ["Todas"] + list(df_atk['Fase'].unique()))
            filtro_dorsal = f_col2.selectbox("Dorsal", ["Todos"] + list(df_atk['Dorsal'].unique()))
            filtro_zona = f_col3.selectbox("Zona de Origen", ["Todas"] + sorted([z for z in df_atk['Z_Origen'].unique() if z != 'N/A']))

            # Aplicar Filtros
            if filtro_fase != "Todas": df_atk = df_atk[df_atk['Fase'] == filtro_fase]
            if filtro_dorsal != "Todos": df_atk = df_atk[df_atk['Dorsal'] == filtro_dorsal]
            if filtro_zona != "Todas": df_atk = df_atk[df_atk['Z_Origen'] == filtro_zona]

            # KPIs Avanzados
            st.markdown("### Rendimiento Ofensivo")
            m1, m2, m3, m4 = st.columns(4)
            intentos = len(df_atk)
            pts = len(df_atk[df_atk['Calidad'] == 'Perfecto'])
            err = len(df_atk[df_atk['Calidad'] == 'Error'])
            blk = len(df_atk[df_atk['Calidad'] == 'Negativo']) # Bola bloqueada suele marcarse así o con /
            eff = ((pts - err - blk) / intentos * 100) if intentos > 0 else 0
            
            m1.metric("Intentos (N)", intentos)
            m2.metric("Kill % (Puntos)", f"{(pts/intentos*100):.1f}%" if intentos > 0 else "0%")
            m3.metric("Error/Block %", f"{((err+blk)/intentos*100):.1f}%" if intentos > 0 else "0%")
            m4.metric("Eficiencia Pura (EFF)", f"{eff:.1f}%")

            # Visualización Espacial
            v1, v2 = st.columns([1, 1])
            with v1:
                st.markdown("#### Shot Chart (Vectores Físicos)")
                fig_shot = renderizar_cancha_fivb(opacidad_fondo=0.1)
                for _, r in df_atk.dropna(subset=['X_In', 'X_Out']).iterrows():
                    color = "#10b981" if r['Calidad'] == 'Perfecto' else "#ef4444" if r['Calidad'] == 'Error' else "#94a3b8"
                    fig_shot.add_trace(go.Scatter(x=[r['X_In'], r['X_Out']], y=[r['Y_In'], r['Y_Out']],
                                                 mode='lines+markers', line=dict(color=color, width=2.5),
                                                 marker=dict(size=6, symbol='circle'), 
                                                 hoverinfo='text', text=f"Dorsal {r['Dorsal']} | Res: {r['Calidad']}"))
                fig_shot.update_layout(height=650, showlegend=False)
                st.plotly_chart(fig_shot, use_container_width=True)
            
            with v2:
                st.markdown("#### Impact Heatmap (Densidad de Destinos)")
                if not df_atk['X_Out'].dropna().empty:
                    fig_dense = px.density_contour(df_atk, x="X_Out", y="Y_Out", range_x=[0,9], range_y=[0,18], 
                                                   color_discrete_sequence=['#3b82f6'])
                    fig_dense.update_traces(contours_coloring="fill", contours_showlabels=True)
                    fig_dense.update_layout(height=650, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                            xaxis=dict(visible=False), yaxis=dict(visible=False))
                    # Añadir líneas de pista sobre el contorno
                    fig_dense.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="#ffffff", width=2))
                    fig_dense.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#ffffff", width=4))
                    st.plotly_chart(fig_dense, use_container_width=True)

        # ---------------------------------------------------------
        # MÓDULO 4: SERVE & PASS (Saque y Recepción)
        # ---------------------------------------------------------
        elif "Serve" in modo_app:
            st.markdown(f"## 🎯 Serve & Pass Evaluation: {equipo_target}")
            
            df_saq = df_target[df_target['Fundamento'] == 'Saque']
            df_rec = df_target[df_target['Fundamento'] == 'Recepción']

            col_s, col_r = st.columns(2)
            
            # BLOQUE SAQUE
            with col_s:
                st.markdown("### Rendimiento en Saque (BP)")
                total_s = len(df_saq)
                aces = len(df_saq[df_saq['Calidad'] == 'Perfecto'])
                err_s = len(df_saq[df_saq['Calidad'] == 'Error'])
                
                sm1, sm2, sm3 = st.columns(3)
                sm1.metric("Total Saques", total_s)
                sm2.metric("Aces (#)", aces)
                sm3.metric("Errores (=)", err_s)

                st.markdown("#### Mapa de Zonas de Impacto de Saque")
                fig_saq_map = renderizar_cancha_fivb(opacidad_fondo=0.1)
                for _, r in df_saq.dropna(subset=['X_Out']).iterrows():
                    color = "#10b981" if r['Calidad'] == 'Perfecto' else "#ef4444" if r['Calidad'] == 'Error' else "#f59e0b"
                    fig_saq_map.add_trace(go.Scatter(x=[r['X_Out']], y=[r['Y_Out']], mode='markers',
                                                     marker=dict(color=color, size=10), hoverinfo='text', 
                                                     text=f"Dorsal {r['Dorsal']} | {r['Calidad']}"))
                fig_saq_map.update_layout(height=500, showlegend=False)
                st.plotly_chart(fig_saq_map, use_container_width=True)

            # BLOQUE RECEPCIÓN
            with col_r:
                st.markdown("### Estabilidad en Recepción (K1)")
                total_r = len(df_rec)
                perf_r = len(df_rec[df_rec['Calidad'] == 'Perfecto'])
                pos_r = len(df_rec[df_rec['Calidad'] == 'Positivo'])
                err_r = len(df_rec[df_rec['Calidad'] == 'Error'])
                
                rm1, rm2, rm3 = st.columns(3)
                rm1.metric("Volumen Rec.", total_r)
                rm2.metric("Pase Perfecto (#)", f"{(perf_r/total_r*100):.1f}%" if total_r > 0 else "0%")
                rm3.metric("Eficiencia Positiva", f"{((perf_r+pos_r-err_r)/total_r*100):.1f}%" if total_r > 0 else "0%")

                st.markdown("#### Carga de Recepción por Jugador")
                rec_stats = df_rec.groupby('Dorsal').agg(
                    Total=('Calidad', 'count'),
                    Perfectas=('Calidad', lambda x: (x == 'Perfecto').sum()),
                    Errores=('Calidad', lambda x: (x == 'Error').sum())
                ).reset_index()
                rec_stats['% Perfecto'] = (rec_stats['Perfectas'] / rec_stats['Total'] * 100).round(1)
                st.dataframe(rec_stats.sort_values(by='Total', ascending=False), use_container_width=True, hide_index=True)

        # ---------------------------------------------------------
        # MÓDULO 5: TEAMS MATCHUP (H2H)
        # ---------------------------------------------------------
        elif "Matchup" in modo_app:
            st.markdown("## ⚔️ Teams Matchup (Comparativa Directa)")
            rival_target = df_target['Rival'].iloc[0] if not df_target.empty else "Rival"
            
            def extraer_kpis_avanzados(dataset):
                atk = dataset[dataset['Fundamento'] == 'Ataque']
                rec = dataset[dataset['Fundamento'] == 'Recepción']
                saq = dataset[dataset['Fundamento'] == 'Saque']
                blk = dataset[dataset['Fundamento'] == 'Bloqueo']
                
                # Fórmulas FIBA/FIVB estándar
                eff_atk = ((len(atk[atk['Calidad'] == 'Perfecto']) - len(atk[atk['Calidad'] == 'Error'])) / len(atk) * 100) if len(atk) > 0 else 0
                kill_pct = (len(atk[atk['Calidad'] == 'Perfecto']) / len(atk) * 100) if len(atk) > 0 else 0
                rec_perf = (len(rec[rec['Calidad'] == 'Perfecto']) / len(rec) * 100) if len(rec) > 0 else 0
                aces_ps = len(saq[saq['Calidad'] == 'Perfecto']) / dataset['Set'].nunique() if dataset['Set'].nunique() > 0 else 0
                blk_ps = len(blk[blk['Calidad'] == 'Perfecto']) / dataset['Set'].nunique() if dataset['Set'].nunique() > 0 else 0
                
                return {"EFF Ataque %": eff_atk, "Kill %": kill_pct, "Rec Perfecta %": rec_perf, "Aces / Set": aces_ps, "Blocks / Set": blk_ps}

            kpis_eq1 = extraer_kpis_avanzados(df[df['Equipo'] == equipo_target])
            kpis_eq2 = extraer_kpis_avanzados(df[df['Equipo'] == rival_target])

            df_comp = pd.DataFrame({
                "Métrica": list(kpis_eq1.keys()),
                equipo_target: [round(v, 2) for v in kpis_eq1.values()],
                rival_target: [round(v, 2) for v in kpis_eq2.values()]
            })

            col_t, col_r = st.columns([1, 1.5])
            with col_t:
                st.markdown("### Balance Cuantitativo")
                st.dataframe(df_comp, use_container_width=True, hide_index=True)
            
            with col_r:
                st.markdown("### Radar de Dominio")
                # Escalado interno para visualización en radar (Aces y Blocks se multiplican para verse en el eje 0-100)
                categorias = ['EFF Ataque %', 'Kill %', 'Rec Perfecta %']
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=[kpis_eq1[c] for c in categorias], theta=categorias, fill='toself', name=equipo_target, line_color='#3b82f6'))
                fig_radar.add_trace(go.Scatterpolar(r=[kpis_eq2[c] for c in categorias], theta=categorias, fill='toself', name=rival_target, line_color='#ef4444'))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 70])),
                                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
                st.plotly_chart(fig_radar, use_container_width=True)

    else:
        st.error("Error crítico: No se ha podido extraer la matriz de datos del archivo.")
else:
    st.info("Despliegue inicial de Riverola Volleyball Analytics completado. A la espera de carga de archivos (.dvw) en el panel lateral.")
