import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MatchPlan Pro", layout="wide", initial_sidebar_state="expanded")

# --- MOTOR DE LECTURA DVW (Extracción Heurística de Nombres) ---
def parse_dvw_with_names(file):
    file.seek(0)
    content = file.read().decode('latin-1')
    lines = content.split('\n')
    
    players_map = {'*': {}, 'a': {}}
    teams_map = {'*': "Local", 'a': "Visitante"}
    actions = []
    
    section = ""
    team_line_count = 0
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Identificar secciones
        if line.startswith('[3TEAMS]'): section = "TEAMS"; team_line_count = 0; continue
        if line.startswith('[3PLAYERS-H]'): section = "PLAYERS_H"; continue
        if line.startswith('[3PLAYERS-V]'): section = "PLAYERS_V"; continue
        if line.startswith('[3SCOUT]'): section = "SCOUT"; continue
        if line.startswith('['): section = "OTHER"; continue
        
        # Extraer Nombres de Equipos Reales (Ignorando el ID)
        if section == "TEAMS":
            parts = line.split(';')
            if len(parts) > 1:
                # El nombre suele estar en la posición 1, el ID en la 0
                team_name = parts[1].strip() if parts[1].strip() else parts[0].strip()
                if team_line_count == 0: teams_map['*'] = team_name
                elif team_line_count == 1: teams_map['a'] = team_name
                team_line_count += 1
                
        # Extraer Jugadores/as (Ignorando IDs federativos)
        elif section in ["PLAYERS_H", "PLAYERS_V"]:
            parts = line.split(';')
            if len(parts) >= 4:
                try:
                    num = str(int(parts[1].strip()))
                    # Buscar el primer bloque de texto que contenga letras (el nombre real)
                    name = f"Jugador/a {num}"
                    for p in parts[3:]:
                        if any(c.isalpha() for c in p):
                            name = p.strip()
                            break
                    
                    if section == "PLAYERS_H":
                        players_map['*'][num] = f"{num}. {name}"
                    else:
                        players_map['a'][num] = f"{num}. {name}"
                except: pass

        # Extraer Acciones
        elif section == "SCOUT":
            parts = line.split(';')
            code = parts[0]
            if len(code) >= 6 and code[0] in ['*', 'a'] and code[1:3].strip().isdigit():
                team = code[0]
                player_num = str(int(code[1:3].strip()))
                skill = code[3]
                eval_mark = code[5]
                
                if skill in ['S', 'R', 'E', 'A', 'B', 'D', 'F'] and eval_mark in ['#', '+', '!', '-', '/', '=']:
                    actions.append({
                        'Partido': file.name,
                        'Equipo': teams_map[team],
                        'Jugador/a': players_map[team].get(player_num, f"{player_num}. Desconocido/a"),
                        'Skill': skill,
                        'Eval': eval_mark
                    })
                    
    return pd.DataFrame(actions)

# --- MOTOR DE CÁLCULO ESTADÍSTICO ---
def calculate_player_stats(df):
    if df.empty: return pd.DataFrame()
    
    stats = []
    players = df['Jugador/a'].unique()
    
    t_s_tot = t_s_err = t_s_pts = 0
    t_r_tot = t_r_err = t_r_pos = t_r_exc = 0
    t_a_tot = t_a_err = t_a_blk = t_a_pts = 0
    t_b_pts = 0
    
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
        tot_err = s_err + r_err + a_err + len(blk[blk['Eval'] == '='])
        g_p = tot_pts - tot_err
        
        t_s_tot += s_tot; t_s_err += s_err; t_s_pts += s_pts
        t_r_tot += r_tot; t_r_err += r_err; t_r_pos += r_pos; t_r_exc += r_exc
        t_a_tot += a_tot; t_a_err += a_err; t_a_blk += a_blk; t_a_pts += a_pts
        t_b_pts += b_pts
        
        stats.append({
            'Jugador/a': player, 'Puntos Tot': tot_pts, 'G-P': g_p,
            'Saque Tot': s_tot, 'Saque Err': s_err, 'Saque Pts': s_pts,
            'Rec Tot': r_tot, 'Rec Err': r_err, 
            'Rec Pos%': round((r_pos / r_tot * 100), 0) if r_tot > 0 else 0, 
            'Rec Exc%': round((r_exc / r_tot * 100), 0) if r_tot > 0 else 0,
            'Ataque Tot': a_tot, 'Ataque Err': a_err, 'Ataque Blq': a_blk, 'Ataque Pts': a_pts, 
            'Ataque Pts%': round((a_pts / a_tot * 100), 0) if a_tot > 0 else 0,
            'Bloqueo Pts': b_pts
        })
        
    df_stats = pd.DataFrame(stats).sort_values(by='Puntos Tot', ascending=False)
    
    total_row = pd.DataFrame([{
        'Jugador/a': 'TOTAL EQUIPO',
        'Puntos Tot': t_s_pts + t_a_pts + t_b_pts,
        'G-P': (t_s_pts + t_a_pts + t_b_pts) - (t_s_err + t_r_err + t_a_err + t_a_blk),
        'Saque Tot': t_s_tot, 'Saque Err': t_s_err, 'Saque Pts': t_s_pts,
        'Rec Tot': t_r_tot, 'Rec Err': t_r_err,
        'Rec Pos%': round((t_r_pos / t_r_tot * 100), 0) if t_r_tot > 0 else 0,
        'Rec Exc%': round((t_r_exc / t_r_tot * 100), 0) if t_r_tot > 0 else 0,
        'Ataque Tot': t_a_tot, 'Ataque Err': t_a_err, 'Ataque Blq': t_a_blk, 'Ataque Pts': t_a_pts,
        'Ataque Pts%': round((t_a_pts / t_a_tot * 100), 0) if t_a_tot > 0 else 0,
        'Bloqueo Pts': t_b_pts
    }])
    
    return pd.concat([df_stats, total_row], ignore_index=True)

# --- INTERFAZ PRINCIPAL ---
st.sidebar.title("🏐 MatchPlan Pro")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader("Sube tus archivos .dvw", type=['dvw'], accept_multiple_files=True)

if uploaded_files:
    all_actions = []
    for file in uploaded_files:
        df_actions = parse_dvw_with_names(file)
        all_actions.append(df_actions)
        
    df_master = pd.concat(all_actions, ignore_index=True)
    
    menu = st.sidebar.radio("Herramientas", ["1. Informe Interactivo"])
    
    if menu == "1. Informe Interactivo":
        st.title("📊 Resumen del Partido")
        
        # --- PANEL DE FILTROS INTERACTIVOS ---
        with st.expander("🛠️ Panel de Filtros (Partidos, Equipos y Jugadores/as)", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            
            # Filtro 1: Partido(s)
            lista_partidos = df_master['Partido'].unique().tolist()
            partidos_seleccionados = col_f1.multiselect("1. Selecciona Partido(s):", lista_partidos, default=lista_partidos)
            
            df_filtrado = df_master[df_master['Partido'].isin(partidos_seleccionados)]
            
            # Filtro 2: Equipo
            if not df_filtrado.empty:
                lista_equipos = df_filtrado['Equipo'].unique().tolist()
                equipo_seleccionado = col_f2.selectbox("2. Selecciona Equipo:", lista_equipos)
                df_filtrado = df_filtrado[df_filtrado['Equipo'] == equipo_seleccionado]
            
            # Filtro 3: Jugadores/as
            if not df_filtrado.empty:
                lista_jugadores = df_filtrado['Jugador/a'].unique().tolist()
                jugadores_seleccionados = col_f3.multiselect("3. Selecciona Jugador/a(s):", lista_jugadores, default=lista_jugadores)
                df_filtrado = df_filtrado[df_filtrado['Jugador/a'].isin(jugadores_seleccionados)]

        # --- RENDERIZADO DE DATOS ---
        if df_filtrado.empty:
            st.warning("No hay datos para los filtros seleccionados.")
        else:
            df_resumen = calculate_player_stats(df_filtrado)
            
            st.subheader(f"Estadísticas: {equipo_seleccionado}")
            
            st.dataframe(
                df_resumen.style.format({
                    'Rec Pos%': '{:.0f}%', 
                    'Rec Exc%': '{:.0f}%', 
                    'Ataque Pts%': '{:.0f}%'
                }).apply(lambda x: ['background: #e6f2ff' if x.name == df_resumen.index[-1] else '' for i in x], axis=1), 
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("📈 Dashboard Visual")
            
            df_graficos = df_resumen[df_resumen['Jugador/a'] != 'TOTAL EQUIPO'].copy()
            
            if not df_graficos.empty:
                # FILA 1: Puntos y Balance G-P
                c1, c2 = st.columns(2)
                
                with c1:
                    df_pts = df_graficos[df_graficos['Puntos Tot'] > 0].sort_values(by='Puntos Tot', ascending=True)
                    if not df_pts.empty:
                        fig_pts = px.bar(df_pts, x='Puntos Tot', y='Jugador/a', orientation='h', 
                                         title="Máximos/as Anotadores/as", text='Puntos Tot', color='Puntos Tot')
                        fig_pts.update_traces(textposition='outside')
                        fig_pts.update_layout(showlegend=False)
                        st.plotly_chart(fig_pts, use_container_width=True)
                        
                with c2:
                    df_gp = df_graficos.sort_values(by='G-P', ascending=True)
                    df_gp['Color'] = df_gp['G-P'].apply(lambda x: 'Positivo' if x >= 0 else 'Negativo')
                    fig_gp = px.bar(df_gp, x='G-P', y='Jugador/a', orientation='h', color='Color',
                                    title="Balance Global (Puntos Ganados vs Errores)", text='G-P',
                                    color_discrete_map={'Positivo': '#2ca02c', 'Negativo': '#d62728'})
                    fig_gp.update_traces(textposition='outside')
                    fig_gp.update_layout(showlegend=False)
                    st.plotly_chart(fig_gp, use_container_width=True)

                # FILA 2: Origen de Puntos y Origen de Errores
                c3, c4 = st.columns(2)
                
                with c3:
                    tot_saque_pts = df_graficos['Saque Pts'].sum()
                    tot_ataque_pts = df_graficos['Ataque Pts'].sum()
                    tot_bloqueo_pts = df_graficos['Bloqueo Pts'].sum()
                    
                    if (tot_saque_pts + tot_ataque_pts + tot_bloqueo_pts) > 0:
                        df_dist_pts = pd.DataFrame({
                            'Fundamento': ['Ataque', 'Bloqueo', 'Saque (Aces)'],
                            'Volumen': [tot_ataque_pts, tot_bloqueo_pts, tot_saque_pts]
                        })
                        fig_pie_pts = px.pie(df_dist_pts, values='Volumen', names='Fundamento', hole=0.4, 
                                         title="🟢 Origen de los Puntos Generados",
                                         color_discrete_sequence=px.colors.qualitative.Pastel)
                        fig_pie_pts.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_pie_pts, use_container_width=True)

                with c4:
                    tot_saque_err = df_graficos['Saque Err'].sum()
                    tot_ataque_err = df_graficos['Ataque Err'].sum()
                    tot_rec_err = df_graficos['Rec Err'].sum()
                    
                    if (tot_saque_err + tot_ataque_err + tot_rec_err) > 0:
                        df_dist_err = pd.DataFrame({
                            'Fundamento': ['Ataque (Fallos)', 'Saque (Fallos)', 'Recepción (Fallos)'],
                            'Volumen': [tot_ataque_err, tot_saque_err, tot_rec_err]
                        })
                        fig_pie_err = px.pie(df_dist_err, values='Volumen', names='Fundamento', hole=0.4, 
                                         title="🔴 Origen de los Errores Cometidos",
                                         color_discrete_sequence=px.colors.qualitative.Set2)
                        fig_pie_err.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_pie_err, use_container_width=True)
                        
                # FILA 3: Recepción
                df_rec = df_graficos[df_graficos['Rec Tot'] > 0]
                if not df_rec.empty:
                    fig_rec = px.scatter(df_rec, x='Rec Tot', y='Rec Pos%', size='Rec Tot', color='Jugador/a',
                                         title="Volumen vs Eficacia en Recepción (Tamaño = Recepciones Totales)",
                                         hover_name='Jugador/a', text='Jugador/a')
                    fig_rec.update_traces(textposition='top center')
                    fig_rec.add_hline(y=50, line_dash="dot", annotation_text="Meta 50%")
                    st.plotly_chart(fig_rec, use_container_width=True)
else:
    st.info("👋 Sube un archivo de Data Volley (.dvw) en el menú lateral para empezar.")
