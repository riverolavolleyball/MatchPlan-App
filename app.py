import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MatchPlan Pro", layout="wide", initial_sidebar_state="expanded")

# --- MOTOR DE LECTURA DVW (Heurística de Nombres y Sets) ---
def parse_dvw_with_names(file):
    file.seek(0)
    content = file.read().decode('latin-1')
    lines = content.split('\n')
    
    players_map = {'*': {}, 'a': {}}
    teams_map = {'*': "Local", 'a': "Visitante"}
    actions = []
    
    section = ""
    team_line_count = 0
    current_set = 1 # Por defecto iniciamos en el Set 1
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Identificar secciones
        if line.startswith('[3TEAMS]'): section = "TEAMS"; team_line_count = 0; continue
        if line.startswith('[3PLAYERS-H]'): section = "PLAYERS_H"; continue
        if line.startswith('[3PLAYERS-V]'): section = "PLAYERS_V"; continue
        if line.startswith('[3SCOUT]'): section = "SCOUT"; continue
        if line.startswith('['): section = "OTHER"; continue
        
        # Extraer Nombres de Equipos
        if section == "TEAMS":
            parts = line.split(';')
            if len(parts) > 1:
                team_name = parts[1].strip() if parts[1].strip() else parts[0].strip()
                if team_line_count == 0: teams_map['*'] = team_name
                elif team_line_count == 1: teams_map['a'] = team_name
                team_line_count += 1
                
        # Extraer Jugadores/as
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

        # Extraer Acciones y Sets
        elif section == "SCOUT":
            parts = line.split(';')
            code = parts[0]
            
            # Detección de cambio de Set (Ej. *01set, **1set, a02set)
            if 'set' in code.lower() and ('*' in code or 'a' in code):
                match = re.search(r'\d+', code)
                if match:
                    current_set = int(match.group())
                continue

            if len(code) >= 6 and code[0] in ['*', 'a'] and code[1:3].strip().isdigit():
                team = code[0]
                player_num = str(int(code[1:3].strip()))
                skill = code[3]
                eval_mark = code[5]
                
                if skill in ['S', 'R', 'E', 'A', 'B', 'D', 'F'] and eval_mark in ['#', '+', '!', '-', '/', '=']:
                    actions.append({
                        'Partido': file.name,
                        'Set': f"Set {current_set}",
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
            'Ataque Eff%': round(((a_pts - a_err - a_blk) / a_tot * 100), 0) if a_tot > 0 else 0,
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
        'Ataque Eff%': round(((t_a_pts - t_a_err - t_a_blk) / t_a_tot * 100), 0) if t_a_tot > 0 else 0,
        'Bloqueo Pts': t_b_pts
    }])
    
    return pd.concat([df_stats, total_row], ignore_index=True)

# --- GENERADOR GRÁFICO TORNADO (H2H) ---
def plot_tornado(kpis_e1, kpis_e2, name1, name2):
    categories = ['Ataque Pts%', 'Ataque Eff%', 'Rec Pos%', 'Rec Exc%', 'Saque Pts (Aces)', 'Bloqueo Pts']
    
    val1 = [kpis_e1.get(c, 0) for c in categories]
    val2 = [-kpis_e2.get(c, 0) for c in categories] # Negativo para invertir la barra
    
    fig = go.Figure()
    fig.add_trace(go.Bar(y=categories, x=val1, name=name1, orientation='h', marker_color='#1f77b4', text=val1, textposition='outside'))
    fig.add_trace(go.Bar(y=categories, x=val2, name=name2, orientation='h', marker_color='#ff7f0e', text=[abs(v) for v in val2], textposition='outside'))
    
    fig.update_layout(
        barmode='relative',
        title=f"Comparativa Global: {name1} vs {name2}",
        yaxis_autorange="reversed",
        bargap=0.2,
        xaxis=dict(tickvals=[-100, -50, 0, 50, 100], ticktext=['100', '50', '0', '50', '100'], title="Métricas / Porcentajes")
    )
    return fig

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
    
    menu = st.sidebar.radio("Herramientas", ["1. Informe Interactivo", "2. Cara a Cara (H2H)"])
    
    # ==========================================
    # MÓDULO 1: INFORME INTERACTIVO
    # ==========================================
    if menu == "1. Informe Interactivo":
        st.title("📊 Resumen del Partido")
        
        with st.expander("🛠️ Panel de Filtros (Partidos, Sets, Equipos y Jugadores/as)", expanded=True):
            col_f1, col_fset, col_f2, col_f3 = st.columns(4)
            
            lista_partidos = df_master['Partido'].unique().tolist()
            partidos_sel = col_f1.multiselect("1. Partido(s):", lista_partidos, default=lista_partidos)
            df_filtrado = df_master[df_master['Partido'].isin(partidos_sel)]
            
            # NUEVO FILTRO: SETS
            if not df_filtrado.empty:
                lista_sets = sorted(df_filtrado['Set'].unique().tolist())
                sets_sel = col_fset.multiselect("2. Set(s):", lista_sets, default=lista_sets)
                df_filtrado = df_filtrado[df_filtrado['Set'].isin(sets_sel)]
            
            if not df_filtrado.empty:
                lista_equipos = df_filtrado['Equipo'].unique().tolist()
                equipo_sel = col_f2.selectbox("3. Equipo:", lista_equipos)
                df_filtrado = df_filtrado[df_filtrado['Equipo'] == equipo_sel]
            
            if not df_filtrado.empty:
                lista_jugadores = df_filtrado['Jugador/a'].unique().tolist()
                jugadores_sel = col_f3.multiselect("4. Jugador/a(s):", lista_jugadores, default=lista_jugadores)
                df_filtrado = df_filtrado[df_filtrado['Jugador/a'].isin(jugadores_sel)]

        if df_filtrado.empty:
            st.warning("No hay datos para los filtros seleccionados.")
        else:
            df_resumen = calculate_player_stats(df_filtrado)
            st.subheader(f"Estadísticas: {equipo_sel}")
            st.dataframe(
                df_resumen.style.format({'Rec Pos%': '{:.0f}%', 'Rec Exc%': '{:.0f}%', 'Ataque Pts%': '{:.0f}%', 'Ataque Eff%': '{:.0f}%'})
                .apply(lambda x: ['background: #e6f2ff' if x.name == df_resumen.index[-1] else '' for i in x], axis=1), 
                use_container_width=True
            )

    # ==========================================
    # MÓDULO 2: CARA A CARA (H2H)
    # ==========================================
    elif menu == "2. Cara a Cara (H2H)":
        st.title("⚔️ Cara a Cara (H2H)")
        st.markdown("Comparativa directa de rendimiento. Selecciona si quieres enfrentar Equipos o Jugadores individuales.")
        
        tipo_h2h = st.radio("Nivel de Comparación:", ["Equipos", "Jugadores/as"], horizontal=True)
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        
        if tipo_h2h == "Equipos":
            equipos_disp = df_master['Equipo'].unique().tolist()
            if len(equipos_disp) >= 2:
                e1 = c1.selectbox("Entidad 1 (Izquierda):", equipos_disp, index=0)
                e2 = c2.selectbox("Entidad 2 (Derecha):", equipos_disp, index=1)
                
                df_e1 = df_master[df_master['Equipo'] == e1]
                df_e2 = df_master[df_master['Equipo'] == e2]
                
                stats_e1 = calculate_player_stats(df_e1).iloc[-1].to_dict() # Cogemos la fila TOTAL EQUIPO
                stats_e2 = calculate_player_stats(df_e2).iloc[-1].to_dict()
                
                st.plotly_chart(plot_tornado(stats_e1, stats_e2, e1, e2), use_container_width=True)
            else:
                st.warning("Se necesitan al menos 2 equipos en los datos para comparar.")
                
        elif tipo_h2h == "Jugadores/as":
            jugs_disp = sorted(df_master['Jugador/a'].unique().tolist())
            if len(jugs_disp) >= 2:
                j1 = c1.selectbox("Entidad 1 (Izquierda):", jugs_disp, index=0)
                j2 = c2.selectbox("Entidad 2 (Derecha):", jugs_disp, index=1)
                
                df_j1 = df_master[df_master['Jugador/a'] == j1]
                df_j2 = df_master[df_master['Jugador/a'] == j2]
                
                # Calcular stats y coger la primera fila (única de ese jugador)
                s1 = calculate_player_stats(df_j1)
                s2 = calculate_player_stats(df_j2)
                
                stats_j1 = s1.iloc[0].to_dict() if len(s1) > 1 else {}
                stats_j2 = s2.iloc[0].to_dict() if len(s2) > 1 else {}
                
                if stats_j1 and stats_j2:
                    st.plotly_chart(plot_tornado(stats_j1, stats_j2, j1, j2), use_container_width=True)
                else:
                    st.info("No hay datos suficientes de los jugadores seleccionados para generar la comparativa.")
            else:
                st.warning("Se necesitan al menos 2 jugadores/as en los datos para comparar.")
                
else:
    st.info("👋 Sube un archivo de Data Volley (.dvw) en el menú lateral para empezar.")
