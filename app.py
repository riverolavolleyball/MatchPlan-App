import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO ---
st.set_page_config(page_title="MatchPlan Pro", layout="wide", initial_sidebar_state="expanded")

# Inyección de CSS (Tipografía profesional y limpieza de interfaz)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3 {
        font-weight: 600 !important;
        letter-spacing: -0.5px;
    }
    .stExpander {
        border: 1px solid rgba(128,128,128,0.2) !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- MOTOR DE LECTURA DVW ---
def parse_dvw_with_names(file):
    file.seek(0)
    content = file.read().decode('latin-1')
    lines = content.split('\n')
    
    players_map = {'*': {}, 'a': {}}
    teams_map = {'*': "Local", 'a': "Visitante"}
    actions = []
    section = ""
    team_line_count = 0
    current_set = 1
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.startswith('[3TEAMS]'): section = "TEAMS"; team_line_count = 0; continue
        if line.startswith('[3PLAYERS-H]'): section = "PLAYERS_H"; continue
        if line.startswith('[3PLAYERS-V]'): section = "PLAYERS_V"; continue
        if line.startswith('[3SCOUT]'): section = "SCOUT"; continue
        if line.startswith('['): section = "OTHER"; continue
        
        if section == "TEAMS":
            parts = line.split(';')
            if len(parts) > 1:
                team_name = parts[1].strip() if parts[1].strip() else parts[0].strip()
                if team_line_count == 0: teams_map['*'] = team_name
                elif team_line_count == 1: teams_map['a'] = team_name
                team_line_count += 1
                
        elif section in ["PLAYERS_H", "PLAYERS_V"]:
            parts = line.split(';')
            if len(parts) >= 4:
                try:
                    num = str(int(parts[1].strip()))
                    name = f"Jugador/a {num}"
                    for p in parts[3:]:
                        if any(c.isalpha() for c in p):
                            name = p.strip()
                            break
                    if section == "PLAYERS_H": players_map['*'][num] = f"{num}. {name}"
                    else: players_map['a'][num] = f"{num}. {name}"
                except: pass

        elif section == "SCOUT":
            parts = line.split(';')
            code = parts[0]
            
            if 'set' in code.lower() and len(code) <= 8:
                match = re.search(r'[1-5]', code)
                if match: current_set = int(match.group())
                continue

            if len(code) >= 6 and code[0] in ['*', 'a'] and code[1:3].strip().isdigit():
                team = code[0]
                player_num = str(int(code[1:3].strip()))
                skill = code[3]
                eval_mark = code[5]
                
                if skill in ['S', 'R', 'E', 'A', 'B', 'D', 'F'] and eval_mark in ['#', '+', '!', '-', '/', '=']:
                    actions.append({
                        'Partido': file.name, 'Set': f"Set {current_set}",
                        'Equipo': teams_map[team], 'Jugador/a': players_map[team].get(player_num, f"{player_num}. Desconocido/a"),
                        'Skill': skill, 'Eval': eval_mark
                    })
                    
    return pd.DataFrame(actions)

# --- MOTOR DE CÁLCULO ESTADÍSTICO ---
def calculate_player_stats(df):
    if df.empty: return pd.DataFrame()
    stats = []
    players = df['Jugador/a'].unique()
    
    t_s_tot = t_s_err = t_s_pts = t_r_tot = t_r_err = t_r_pos = t_r_exc = 0
    t_a_tot = t_a_err = t_a_blk = t_a_pts = t_b_pts = 0
    
    for player in players:
        p_data = df[df['Jugador/a'] == player]
        srv = p_data[p_data['Skill'] == 'S']
        rec = p_data[p_data['Skill'] == 'R']
        atk = p_data[p_data['Skill'] == 'A']
        blk = p_data[p_data['Skill'] == 'B']
        
        s_tot = len(srv); s_err = len(srv[srv['Eval'] == '=']); s_pts = len(srv[srv['Eval'] == '#'])
        r_tot = len(rec); r_err = len(rec[rec['Eval'] == '='])
        r_pos = len(rec[rec['Eval'].isin(['#', '+'])]); r_exc = len(rec[rec['Eval'] == '#'])
        a_tot = len(atk); a_err = len(atk[atk['Eval'] == '='])
        a_blk = len(atk[atk['Eval'] == '/']); a_pts = len(atk[atk['Eval'] == '#'])
        b_pts = len(blk[blk['Eval'] == '#'])
        
        tot_pts = s_pts + a_pts + b_pts
        tot_err = s_err + r_err + a_err + a_blk
        
        t_s_tot += s_tot; t_s_err += s_err; t_s_pts += s_pts
        t_r_tot += r_tot; t_r_err += r_err; t_r_pos += r_pos; t_r_exc += r_exc
        t_a_tot += a_tot; t_a_err += a_err; t_a_blk += a_blk; t_a_pts += a_pts
        t_b_pts += b_pts
        
        stats.append({
            'Jugador/a': player, 'Puntos Propios': tot_pts, 'Balance G-P': (tot_pts - tot_err),
            'Errores Totales': tot_err, 
            'Saque Tot': s_tot, 'Saque Err': s_err, 'Aces': s_pts,
            'Rec Tot': r_tot, 'Rec Err': r_err, 
            'Rec Pos%': round((r_pos / r_tot * 100), 0) if r_tot > 0 else 0, 
            'Rec Exc%': round((r_exc / r_tot * 100), 0) if r_tot > 0 else 0,
            'Ataque Tot': a_tot, 'Ataque Err': a_err, 'Ataque Blq': a_blk, 'Ataque Pts': a_pts, 
            'Ataque Pts%': round((a_pts / a_tot * 100), 0) if a_tot > 0 else 0,
            'Ataque Eff%': round(((a_pts - a_err - a_blk) / a_tot * 100), 0) if a_tot > 0 else 0,
            'Bloqueos': b_pts
        })
        
    df_stats = pd.DataFrame(stats).sort_values(by='Puntos Propios', ascending=False)
    
    t_tot_err = t_s_err + t_r_err + t_a_err + t_a_blk
    total_row = pd.DataFrame([{
        'Jugador/a': 'TOTAL EQUIPO', 'Puntos Propios': t_s_pts + t_a_pts + t_b_pts,
        'Balance G-P': (t_s_pts + t_a_pts + t_b_pts) - t_tot_err,
        'Errores Totales': t_tot_err,
        'Saque Tot': t_s_tot, 'Saque Err': t_s_err, 'Aces': t_s_pts,
        'Rec Tot': t_r_tot, 'Rec Err': t_r_err,
        'Rec Pos%': round((t_r_pos / t_r_tot * 100), 0) if t_r_tot > 0 else 0,
        'Rec Exc%': round((t_r_exc / t_r_tot * 100), 0) if t_r_tot > 0 else 0,
        'Ataque Tot': t_a_tot, 'Ataque Err': t_a_err, 'Ataque Blq': t_a_blk, 'Ataque Pts': t_a_pts,
        'Ataque Pts%': round((t_a_pts / t_a_tot * 100), 0) if t_a_tot > 0 else 0,
        'Ataque Eff%': round(((t_a_pts - t_a_err - t_a_blk) / t_a_tot * 100), 0) if t_a_tot > 0 else 0,
        'Bloqueos': t_b_pts
    }])
    
    return pd.concat([df_stats, total_row], ignore_index=True)

# --- GENERADOR GRÁFICO TORNADO UNIFICADO (H2H) ---
def plot_unified_tornado(kpis_e1, kpis_e2, name1, name2, is_team=False):
    if is_team:
        categories = ['Puntos Totales', 'Puntos Propios', 'Aces', 'Bloqueos', 'Ataque Pts%', 'Ataque Eff%', 'Rec Pos%', 'Rec Exc%']
    else:
        categories = ['Puntos Propios', 'Aces', 'Bloqueos', 'Ataque Pts%', 'Ataque Eff%', 'Rec Pos%', 'Rec Exc%']
        
    categories.reverse() 
    
    val1 = [-kpis_e1.get(c, 0) for c in categories]
    val2 = [kpis_e2.get(c, 0) for c in categories] 
    
    text_val1 = [f"{abs(v)}%" if "%" in c else str(abs(v)) for v, c in zip(val1, categories)]
    text_val2 = [f"{v}%" if "%" in c else str(v) for v, c in zip(val2, categories)]

    fig = go.Figure()
    # Uso de colores corporativos neutros (Azul Slate y Rojo Coral)
    fig.add_trace(go.Bar(y=categories, x=val1, name=name1, orientation='h', marker_color='#3b82f6', text=text_val1, textposition='outside', hoverinfo='none'))
    fig.add_trace(go.Bar(y=categories, x=val2, name=name2, orientation='h', marker_color='#ef4444', text=text_val2, textposition='outside', hoverinfo='none'))
    
    fig.update_layout(
        barmode='relative',
        title=dict(text=f"Comparativa de Rendimiento: {name1} vs {name2}", font=dict(size=18)),
        bargap=0.25,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(showticklabels=False, title="", showgrid=False, zeroline=True, zerolinecolor='rgba(128,128,128,0.3)'),
        yaxis=dict(title="", tickfont=dict(size=13))
    )
    return fig

# --- LEYENDA TÉCNICA ---
def show_metric_legend(is_team=False):
    st.markdown("---")
    st.markdown("#### Glosario de Métricas")
    legend_md = ""
    if is_team:
        legend_md += "- **Puntos Totales:** Puntos generados por mérito propio sumados a los errores directos cometidos por el equipo rival.\n"
    
    legend_md += """
- **Puntos Propios:** Suma exclusiva de Ataques convertidos, Bloqueos y Saques Directos (Aces).
- **Aces / Bloqueos:** Acciones desde el saque o en la red que resultan en punto directo y finalizan el rally.
- **Ataque Pts% (Eficacia):** Porcentaje absoluto de ataques que terminan en punto.
- **Ataque Eff% (Eficiencia):** Rentabilidad del ataque calculada como `(Puntos - Errores - Bloqueados) / Total de Ataques`.
- **Rec Pos% (Positiva):** Porcentaje de recepciones operativas (`#` y `+`) que permiten estructurar el side-out.
- **Rec Exc% (Excelente):** Porcentaje de recepciones perfectas (`#`) que garantizan al colocador todas las opciones de distribución.
    """
    st.caption(legend_md)

# --- MENÚ LATERAL Y NAVEGACIÓN ---
st.sidebar.title("MatchPlan Pro")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader("Cargar archivos fuente (.dvw)", type=['dvw'], accept_multiple_files=True)

if uploaded_files:
    all_actions = []
    for file in uploaded_files:
        all_actions.append(parse_dvw_with_names(file))
    df_master = pd.concat(all_actions, ignore_index=True)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Módulos de Análisis")
    menu = st.sidebar.radio("Navegación", ["Informe Interactivo", "Cara a Cara (H2H)"], label_visibility="collapsed")
    
    if menu == "Informe Interactivo":
        st.header("Resumen del Partido")
        
        with st.expander("Panel de Filtros Globales", expanded=True):
            col_f1, col_fset, col_f2, col_f3 = st.columns(4)
            df_filtrado = df_master[df_master['Partido'].isin(col_f1.multiselect("Partido(s):", df_master['Partido'].unique(), default=df_master['Partido'].unique()))]
            if not df_filtrado.empty: df_filtrado = df_filtrado[df_filtrado['Set'].isin(col_fset.multiselect("Set(s):", sorted(df_filtrado['Set'].unique()), default=sorted(df_filtrado['Set'].unique())))]
            if not df_filtrado.empty: equipo_sel = col_f2.selectbox("Equipo:", df_filtrado['Equipo'].unique())
            if not df_filtrado.empty: df_filtrado = df_filtrado[(df_filtrado['Equipo'] == equipo_sel) & (df_filtrado['Jugador/a'].isin(col_f3.multiselect("Jugador/a(s):", df_filtrado[df_filtrado['Equipo'] == equipo_sel]['Jugador/a'].unique(), default=df_filtrado[df_filtrado['Equipo'] == equipo_sel]['Jugador/a'].unique())))]

        if df_filtrado.empty:
            st.warning("Ausencia de datos para los parámetros seleccionados.")
        else:
            df_resumen = calculate_player_stats(df_filtrado)
            st.subheader(f"Estadísticas Generales: {equipo_sel}")
            
            # --- TABLA TAMAÑO COMPLETO SIN SCROLL ---
            cols_to_show = [c for c in df_resumen.columns if c != 'Errores Totales']
            df_display = df_resumen[cols_to_show]
            
            # Cálculo dinámico de altura para eliminar barras de desplazamiento (aprox 36px por fila + cabecera)
            table_height = int((len(df_display) + 1) * 36)
            
            st.dataframe(
                df_display.style.format({'Rec Pos%': '{:.0f}%', 'Rec Exc%': '{:.0f}%', 'Ataque Pts%': '{:.0f}%', 'Ataque Eff%': '{:.0f}%'})
                .apply(lambda x: ['background: rgba(128, 128, 128, 0.1); font-weight: bold;' if x.name == df_display.index[-1] else '' for i in x], axis=1), 
                use_container_width=True, 
                hide_index=True,
                height=table_height
            )

            st.markdown("---")
            st.subheader("Dashboard Analítico")
            df_graficos = df_resumen[df_resumen['Jugador/a'] != 'TOTAL EQUIPO']
            
            if not df_graficos.empty:
                c1, c2 = st.columns(2)
                with c1:
                    fig_pts = px.bar(df_graficos[df_graficos['Puntos Propios'] > 0].sort_values(by='Puntos Propios'), x='Puntos Propios', y='Jugador/a', orientation='h', title="Carga Ofensiva (Puntos Propios)", text='Puntos Propios')
                    fig_pts.update_traces(textposition='outside', marker_color='#3b82f6')
                    fig_pts.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0), xaxis=dict(showgrid=False))
                    st.plotly_chart(fig_pts, use_container_width=True, theme="streamlit")
                with c2:
                    df_gp = df_graficos.sort_values(by='Balance G-P')
                    fig_gp = px.bar(df_gp, x='Balance G-P', y='Jugador/a', orientation='h', color=df_gp['Balance G-P']>=0, title="Rentabilidad Neta (Puntos vs Errores)", text='Balance G-P', color_discrete_map={True: '#10b981', False: '#ef4444'})
                    fig_gp.update_traces(textposition='outside')
                    fig_gp.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0), xaxis=dict(showgrid=False))
                    st.plotly_chart(fig_gp, use_container_width=True, theme="streamlit")

                c3, c4 = st.columns(2)
                with c3:
                    totales_pts = [df_graficos['Ataque Pts'].sum(), df_graficos['Bloqueos'].sum(), df_graficos['Aces'].sum()]
                    if sum(totales_pts) > 0:
                        fig_pie_pts = px.pie(values=totales_pts, names=['Ataque', 'Bloqueo', 'Aces'], hole=0.45, title="Distribución de Puntos Propios", color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b'])
                        fig_pie_pts.update_traces(textposition='inside', textinfo='percent+label')
                        fig_pie_pts.update_layout(margin=dict(l=0, r=0, t=40, b=0))
                        st.plotly_chart(fig_pie_pts, use_container_width=True, theme="streamlit")
                with c4:
                    totales_err = [df_graficos['Ataque Err'].sum(), df_graficos['Saque Err'].sum(), df_graficos['Rec Err'].sum()]
                    if sum(totales_err) > 0:
                        fig_pie_err = px.pie(values=totales_err, names=['Ataque', 'Saque', 'Recepción'], hole=0.45, title="Distribución de Errores No Forzados", color_discrete_sequence=['#ef4444', '#f59e0b', '#8b5cf6'])
                        fig_pie_err.update_traces(textposition='inside', textinfo='percent+label')
                        fig_pie_err.update_layout(margin=dict(l=0, r=0, t=40, b=0))
                        st.plotly_chart(fig_pie_err, use_container_width=True, theme="streamlit")

    elif menu == "Cara a Cara (H2H)":
        st.header("Análisis Comparativo (H2H)")
        tipo_h2h = st.radio("Dimensión de Análisis:", ["Equipos", "Jugadores/as"], horizontal=True)
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        if tipo_h2h == "Equipos":
            equipos_disp = df_master['Equipo'].unique().tolist()
            if len(equipos_disp) >= 2:
                e1 = c1.selectbox("Entidad Referencia:", equipos_disp, index=0)
                e2 = c2.selectbox("Entidad Oponente:", equipos_disp, index=1)
                
                s1 = calculate_player_stats(df_master[df_master['Equipo'] == e1])
                s2 = calculate_player_stats(df_master[df_master['Equipo'] == e2])
                stats_e1 = s1.iloc[-1].to_dict() if not s1.empty else {}
                stats_e2 = s2.iloc[-1].to_dict() if not s2.empty else {}
                
                if stats_e1 and stats_e2:
                    stats_e1['Puntos Totales'] = stats_e1['Puntos Propios'] + stats_e2.get('Errores Totales', 0)
                    stats_e2['Puntos Totales'] = stats_e2['Puntos Propios'] + stats_e1.get('Errores Totales', 0)
                    
                    st.plotly_chart(plot_unified_tornado(stats_e1, stats_e2, e1, e2, is_team=True), use_container_width=True, theme="streamlit")
                    show_metric_legend(is_team=True)
                    
                    st.subheader("Matriz de Datos")
                    df_comp = pd.DataFrame([stats_e1, stats_e2]).set_index('Jugador/a')[['Puntos Totales', 'Puntos Propios', 'Aces', 'Bloqueos', 'Ataque Pts%', 'Ataque Eff%', 'Rec Pos%', 'Rec Exc%']]
                    df_comp.index.name = "Equipo"
                    st.dataframe(df_comp.style.format("{:.0f}"), use_container_width=True)
        
        elif tipo_h2h == "Jugadores/as":
            jugs_disp = sorted(df_master['Jugador/a'].unique().tolist())
            if len(jugs_disp) >= 2:
                j1 = c1.selectbox("Jugador/a Referencia:", jugs_disp, index=0)
                j2 = c2.selectbox("Jugador/a Oponente:", jugs_disp, index=1)
                
                s1 = calculate_player_stats(df_master[df_master['Jugador/a'] == j1])
                s2 = calculate_player_stats(df_master[df_master['Jugador/a'] == j2])
                stats_j1 = s1.iloc[0].to_dict() if len(s1) > 1 else {}
                stats_j2 = s2.iloc[0].to_dict() if len(s2) > 1 else {}
                
                if stats_j1 and stats_j2:
                    st.plotly_chart(plot_unified_tornado(stats_j1, stats_j2, j1, j2, is_team=False), use_container_width=True, theme="streamlit")
                    show_metric_legend(is_team=False)
                    
                    st.subheader("Matriz de Datos")
                    df_comp = pd.DataFrame([stats_j1, stats_j2]).set_index('Jugador/a')[['Puntos Propios', 'Aces', 'Bloqueos', 'Ataque Pts%', 'Ataque Eff%', 'Rec Pos%', 'Rec Exc%']]
                    st.dataframe(df_comp.style.format("{:.0f}"), use_container_width=True)

else:
    st.info("Sistema a la espera. Inserte el archivo fuente de Data Volley (.dvw) en el panel lateral para iniciar el procesamiento.")
