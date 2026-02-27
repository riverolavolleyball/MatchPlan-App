import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MatchPlan Pro", layout="wide", initial_sidebar_state="expanded")

# --- MOTOR DE LECTURA DVW (Extrae Nombres y Acciones) ---
def parse_dvw_with_names(file):
    file.seek(0)
    content = file.read().decode('latin-1')
    lines = content.split('\n')
    
    # Diccionarios para guardar información
    players_map = {'*': {}, 'a': {}} # * = Local, a = Visitante
    teams_map = {'*': "Equipo Local", 'a': "Equipo Visitante"}
    actions = []
    
    section = ""
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Identificar en qué sección del archivo estamos
        if line.startswith('[3TEAMS]'): section = "TEAMS"; continue
        if line.startswith('[3PLAYERS-H]'): section = "PLAYERS_H"; continue
        if line.startswith('[3PLAYERS-V]'): section = "PLAYERS_V"; continue
        if line.startswith('[3SCOUT]'): section = "SCOUT"; continue
        if line.startswith('['): section = "OTHER"; continue
        
        # Extraer Nombres de Equipos
        if section == "TEAMS":
            parts = line.split(';')
            if len(parts) > 0:
                if teams_map['*'] == "Equipo Local": teams_map['*'] = parts[0]
                else: teams_map['a'] = parts[0]
                
        # Extraer Nombres de Jugadoras Locales
        elif section == "PLAYERS_H":
            parts = line.split(';')
            if len(parts) >= 2:
                # parts[1] es el número, parts[2] suele ser el nombre
                num = parts[1].zfill(2) # Rellenar con 0 si es un dígito (ej. '4' -> '04')
                name = parts[2] if len(parts) > 2 else f"Jugadora {num}"
                players_map['*'][num] = name
                
        # Extraer Nombres de Jugadoras Visitantes
        elif section == "PLAYERS_V":
            parts = line.split(';')
            if len(parts) >= 2:
                num = parts[1].zfill(2)
                name = parts[2] if len(parts) > 2 else f"Jugadora {num}"
                players_map['a'][num] = name

        # Extraer Acciones de Juego (El Scout)
        elif section == "SCOUT":
            parts = line.split(';')
            code = parts[0]
            if len(code) >= 6 and code[0] in ['*', 'a'] and code[1:3].isdigit():
                team = code[0]
                player_num = code[1:3]
                skill = code[3]
                eval_mark = code[5]
                
                # Filtro: solo habilidades reales
                if skill in ['S', 'R', 'E', 'A', 'B', 'D', 'F'] and eval_mark in ['#', '+', '!', '-', '/', '=']:
                    actions.append({
                        'Match': file.name,
                        'Team_Code': team,
                        'Team_Name': teams_map[team],
                        'Player_Num': player_num,
                        'Player_Name': players_map[team].get(player_num, f"Jugadora {player_num}"),
                        'Skill': skill,
                        'Eval': eval_mark
                    })
                    
    return pd.DataFrame(actions), teams_map

# --- MOTOR DE CÁLCULO ESTADÍSTICO (Replicando el PDF) ---
def calculate_player_stats(df, team_code):
    df_team = df[df['Team_Code'] == team_code]
    if df_team.empty: return pd.DataFrame()
    
    stats = []
    players = df_team['Player_Name'].unique()
    
    for player in players:
        p_data = df_team[df_team['Player_Name'] == player]
        
        # Filtros por fundamento
        srv = p_data[p_data['Skill'] == 'S']
        rec = p_data[p_data['Skill'] == 'R']
        atk = p_data[p_data['Skill'] == 'A']
        blk = p_data[p_data['Skill'] == 'B']
        
        # --- CÁLCULOS ---
        # Saque
        s_tot = len(srv)
        s_err = len(srv[srv['Eval'] == '='])
        s_pts = len(srv[srv['Eval'] == '#'])
        
        # Recepción
        r_tot = len(rec)
        r_err = len(rec[rec['Eval'] == '='])
        r_pos = len(rec[rec['Eval'].isin(['#', '+'])])
        r_exc = len(rec[rec['Eval'] == '#'])
        r_pos_pct = (r_pos / r_tot * 100) if r_tot > 0 else 0
        r_exc_pct = (r_exc / r_tot * 100) if r_tot > 0 else 0
        
        # Ataque
        a_tot = len(atk)
        a_err = len(atk[atk['Eval'] == '='])
        a_blk = len(atk[atk['Eval'] == '/'])
        a_pts = len(atk[atk['Eval'] == '#'])
        a_eff_pct = (a_pts / a_tot * 100) if a_tot > 0 else 0
        
        # Bloqueo
        b_pts = len(blk[blk['Eval'] == '#'])
        
        # Puntos Totales y G-P (Ganados - Perdidos)
        tot_pts = s_pts + a_pts + b_pts
        tot_err = s_err + r_err + a_err + len(blk[blk['Eval'] == '='])
        g_p = tot_pts - tot_err
        
        # Si la jugadora no hizo nada, la saltamos
        if len(p_data) == 0: continue
            
        stats.append({
            'Jugadora': player,
            'Puntos Tot': tot_pts,
            'G-P': g_p,
            'Saque Tot': s_tot, 'Saque Err': s_err, 'Saque Pts': s_pts,
            'Rec Tot': r_tot, 'Rec Err': r_err, 'Rec Pos%': f"{r_pos_pct:.0f}%", 'Rec Exc%': f"{r_exc_pct:.0f}%",
            'Ataque Tot': a_tot, 'Ataque Err': a_err, 'Ataque Blq': a_blk, 'Ataque Pts': a_pts, 'Ataque Pts%': f"{a_eff_pct:.0f}%",
            'Bloqueo Pts': b_pts
        })
        
    df_stats = pd.DataFrame(stats)
    return df_stats.sort_values(by='Puntos Tot', ascending=False).reset_index(drop=True)

# --- INTERFAZ PRINCIPAL ---
st.sidebar.title("🏐 MatchPlan Pro")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader("Sube tus archivos .dvw", type=['dvw'], accept_multiple_files=True)

if uploaded_files:
    all_actions = []
    teams_dict = {}
    
    for file in uploaded_files:
        df_actions, t_map = parse_dvw_with_names(file)
        all_actions.append(df_actions)
        teams_dict = t_map # Nos quedamos con los nombres del último archivo para los botones
        
    df_master = pd.concat(all_actions, ignore_index=True)
    
    # Menú Modular
    menu = st.sidebar.radio("Herramientas", ["1. Informe Interactivo"])
    
    if menu == "1. Informe Interactivo":
        st.title("📊 Resumen del Partido")
        st.markdown("Tabla estadística calculada a partir de los datos brutos del `.dvw` y visualizaciones clave.")
        
        # Selector de Equipo a analizar
        equipo_seleccionado = st.radio("Selecciona el equipo a analizar:", 
                                       options=['*', 'a'], 
                                       format_func=lambda x: teams_dict.get(x, "Desconocido"),
                                       horizontal=True)
        
        nombre_equipo = teams_dict.get(equipo_seleccionado, "Equipo")
        
        # 1. TABLA ESTADÍSTICA ESTILO PDF
        st.subheader(f"Estadísticas Individuales: {nombre_equipo}")
        df_resumen = calculate_player_stats(df_master, equipo_seleccionado)
        
        # Mostramos la tabla interactiva (se puede ordenar al hacer clic en las columnas)
        st.dataframe(df_resumen, use_container_width=True)
        
        st.markdown("---")
        
        # 2. DASHBOARD VISUAL E INTERACTIVO
        st.subheader("📈 Dashboard Visual")
        
        if not df_resumen.empty:
            c1, c2 = st.columns(2)
            
            # Gráfica 1: Máximas Puntuadoras (Barras horizontales)
            with c1:
                df_pts = df_resumen[df_resumen['Puntos Tot'] > 0].sort_values(by='Puntos Tot', ascending=True)
                fig_pts = px.bar(df_pts, x='Puntos Tot', y='Jugadora', orientation='h', 
                                 title="Máximas Anotadoras (Puntos Totales)",
                                 text='Puntos Tot', color='Puntos Tot', color_continuous_scale='Blues')
                fig_pts.update_layout(showlegend=False)
                st.plotly_chart(fig_pts, use_container_width=True)
                
            # Gráfica 2: Rendimiento en Recepción (Gráfica de dispersión o Burbujas)
            with c2:
                # Limpiamos el % para poder graficarlo como número
                df_rec = df_resumen[df_resumen['Rec Tot'] > 0].copy()
                df_rec['Rec Pos N'] = df_rec['Rec Pos%'].str.replace('%','').astype(float)
                
                fig_rec = px.scatter(df_rec, x='Rec Tot', y='Rec Pos N', size='Rec Tot', color='Jugadora',
                                     title="Volumen vs Eficacia en Recepción",
                                     labels={'Rec Tot': "Volumen (Total Recepciones)", 'Rec Pos N': "% Recepción Positiva"},
                                     hover_name='Jugadora')
                # Añadimos una línea de referencia (ej. 50% de positiva)
                fig_rec.add_hline(y=50, line_dash="dot", annotation_text="Meta 50%", annotation_position="bottom right")
                st.plotly_chart(fig_rec, use_container_width=True)

            c3, c4 = st.columns(2)
            
            # Gráfica 3: Balance Ganados/Perdidos (Semáforo de barras)
            with c3:
                df_gp = df_resumen.sort_values(by='G-P', ascending=True)
                # Color condicional: verde si es positivo, rojo si es negativo
                df_gp['Color'] = df_gp['G-P'].apply(lambda x: 'Positivo' if x >= 0 else 'Negativo')
                fig_gp = px.bar(df_gp, x='G-P', y='Jugadora', orientation='h', color='Color',
                                title="Balance Ganados - Perdidos (G-P)",
                                color_discrete_map={'Positivo': '#2ca02c', 'Negativo': '#d62728'})
                st.plotly_chart(fig_gp, use_container_width=True)
                
            # Gráfica 4: Distribución de Puntos del Equipo (Gráfico de Pastel / Donut)
            with c4:
                # Sumamos los totales de las columnas del dataframe
                tot_saque = df_resumen['Saque Pts'].sum()
                tot_ataque = df_resumen['Ataque Pts'].sum()
                tot_bloqueo = df_resumen['Bloqueo Pts'].sum()
                
                df_dist = pd.DataFrame({
                    'Fundamento': ['Ataque', 'Bloqueo', 'Saque (Aces)'],
                    'Puntos': [tot_ataque, tot_bloqueo, tot_saque]
                })
                
                fig_pie = px.pie(df_dist, values='Puntos', names='Fundamento', hole=0.4, 
                                 title="Origen de los Puntos del Equipo",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
                st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.info("👋 ¡Hola! Sube un archivo de Data Volley (.dvw) en el menú lateral para generar el informe interactivo.")
