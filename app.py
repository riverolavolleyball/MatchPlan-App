import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io
import tempfile
from fpdf import FPDF
import plotly.io as pio

# --- 1. CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="MatchPlan Pro | Volley Vision 360", layout="wide", initial_sidebar_state="expanded")

if 'df_master' not in st.session_state:
    st.session_state.df_master = pd.DataFrame()

# --- 2. MOTOR GEOSPACIAL (100x100 GRID & FALLBACK) ---
ZONE_CENTERS = {
    '1': (7.5, 1.5), '2': (7.5, 7.5), '3': (4.5, 7.5), 
    '4': (1.5, 7.5), '5': (1.5, 1.5), '6': (4.5, 1.5),
    '7': (1.5, 4.5), '8': (4.5, 4.5), '9': (7.5, 4.5)
}

def get_coordinates(exact_coord, zone, is_end=False):
    if exact_coord and exact_coord.isdigit() and len(exact_coord) >= 4:
        val = int(exact_coord[:4])
        x = (val % 100) * 0.09
        y = (val // 100) * 0.18
        if is_end: y = 18 - y 
        return x, y
    elif zone in ZONE_CENTERS:
        base_x, base_y = ZONE_CENTERS[zone]
        if is_end: base_y = 18 - base_y
        return np.random.normal(base_x, 0.4), np.random.normal(base_y, 0.4)
    return None, None

# --- 3. MOTOR DE PARSEO DVW ---
def parse_dvw(file):
    file.seek(0)
    content = file.read().decode('latin-1')
    lines = content.split('\n')
    
    data = []
    in_scout = False
    current_home_rot = None
    current_away_rot = None
    
    for line in lines:
        line = line.strip()
        if '[3DATAVOLLEYSCOUT]' in line or '[3SCOUT]' in line:
            in_scout = True
            continue
        if not in_scout or not line:
            continue
            
        if line.startswith('*z') and len(line) >= 3 and line[2].isdigit():
            current_home_rot = f"R{line[2]}"
            continue
        if line.startswith('az') and len(line) >= 3 and line[2].isdigit():
            current_away_rot = f"R{line[2]}"
            continue
            
        parts = line.split(';')
        code = parts[0]
        
        if len(code) >= 6 and code[0] in ['*', 'a'] and code[1:3].isdigit():
            team = code[0]
            player = code[1:3]
            skill = code[3]
            eval_mark = code[5]
            start_zone = code[9] if len(code) > 9 else None
            end_zone = code[10] if len(code) > 10 else None
            
            start_coord = parts[14] if len(parts) > 14 else ""
            end_coord = parts[15] if len(parts) > 15 else ""
            
            start_x, start_y = get_coordinates(start_coord, start_zone, is_end=False)
            end_x, end_y = get_coordinates(end_coord, end_zone, is_end=True)
            
            phase = "Side-Out (K1)" if "K1" in line else "Transition (K2)"
            rotation = current_home_rot if team == '*' else current_away_rot
            
            video_time = None
            if len(parts) > 13:
                try:
                    video_time = float(parts[13])
                except ValueError:
                    video_time = None
            
            data.append({
                'Code': code, 'Team': team, 'Player': player, 'Skill': skill, 'Eval': eval_mark,
                'Start_Zone': start_zone, 'End_Zone': end_zone,
                'Start_X': start_x, 'Start_Y': start_y, 'End_X': end_x, 'End_Y': end_y,
                'Phase': phase, 'Rotation': rotation, 'Video_Time': video_time
            })
            
    df = pd.DataFrame(data)
    
    if not df.empty:
        df['Previous_Pass'] = None
        last_rec = None
        for idx, row in df.iterrows():
            if row['Skill'] == 'R':
                last_rec = row['Eval']
            if row['Skill'] == 'A' and row['Phase'] == 'Side-Out (K1)':
                df.at[idx, 'Previous_Pass'] = last_rec
                
    return df

# --- 4. RENDERIZADO DE PISTA (FIVB) ---
def draw_court(fig):
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="white", width=2), fillcolor="#e08b5e", layer="below")
    fig.add_shape(type="rect", x0=0, y0=6, x1=9, y1=12, line=dict(color="white", width=2), fillcolor="#d4aa7d", layer="below")
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="white", width=4), layer="below")
    fig.update_xaxes(range=[-1, 10], showgrid=False, visible=False)
    fig.update_yaxes(range=[-1, 19], showgrid=False, visible=False)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0))
    return fig

# --- 5. UI Y NAVEGACIÓN LATERAL ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Volleyball_icon.svg/2048px-Volleyball_icon.svg.png", width=50)
st.sidebar.title("MatchPlan Pro")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader("Cargar archivos .dvw", type=['dvw'], accept_multiple_files=True)

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        df_parsed = parse_dvw(file)
        df_parsed['Match'] = file.name 
        dfs.append(df_parsed)
    if dfs:
        st.session_state.df_master = pd.concat(dfs, ignore_index=True)

menu = st.sidebar.radio("Módulos de Análisis", [
    "1. Validador de Datos", 
    "2. Distribución K1 (Colocador)", 
    "3. Mapas de Ataque", 
    "4. Presión de Saque y Recepción", 
    "5. Cara a Cara (H2H)",
    "6. Dossier PDF (Cuerpo Técnico)",
    "7. Sincronización de Vídeo"
])

# --- 6. FILTRADO GLOBAL ---
df_master = st.session_state.df_master

if df_master.empty:
    st.info("A la espera de carga de archivos .dvw. Sube los archivos en el menú lateral para iniciar el análisis.")
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtros Globales")
    
    lista_partidos = ["Todos"] + list(df_master['Match'].unique())
    partido_seleccionado = st.sidebar.selectbox("Partido / Archivo", lista_partidos)
    
    if partido_seleccionado != "Todos":
        df = df_master[df_master['Match'] == partido_seleccionado].copy()
    else:
        df = df_master.copy()

    # --- MÓDULO 1: VALIDADOR DE DATOS ---
    if menu == "1. Validador de Datos":
        st.header("1. Consolidación y Calidad del Dato")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Acciones Totales", len(df))
        c2.metric("Ataques Registrados", len(df[df['Skill'] == 'A']))
        c3.metric("Saques Registrados", len(df[df['Skill'] == 'S']))
        c4.metric("Archivos Consolidados", df['Match'].nunique())
        
        st.dataframe(df.head(100), use_container_width=True)
        
        st.markdown("### Exportación de Datos")
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar DataFrame (CSV)",
            data=csv_data,
            file_name=f"volley_vision_data_{partido_seleccionado}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # --- MÓDULO 2: DISTRIBUCIÓN K1 ---
    elif menu == "2. Distribución K1 (Colocador)":
        st.header("2. Tendencias de Distribución (Side-Out K1)")
        
        rotations_list = ["Todas", "R1", "R2", "R3", "R4", "R5", "R6"]
        selected_rot = st.sidebar.selectbox("Filtro de Rotación (Colocador)", rotations_list)
        
        df_k1 = df[(df['Skill'] == 'A') & (df['Phase'] == 'Side-Out (K1)') & (df['Previous_Pass'].notna())].copy()
        
        if selected_rot != "Todas":
            df_k1 = df_k1[df_k1['Rotation'] == selected_rot]
            st.write(f"**Mostrando datos para: {selected_rot}**")
        
        if not df_k1.empty:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("Distribución (%)")
                crosstab = pd.crosstab(df_k1['Previous_Pass'], df_k1['Start_Zone'], normalize='index') * 100
                st.dataframe(crosstab.style.format("{:.1f}%"), use_container_width=True)
            
            with c2:
                fig = px.bar(df_k1, x="Previous_Pass", color="Start_Zone", barmode="group",
                             title="Ataques Absolutos por Calidad de Pase y Zona",
                             category_orders={"Previous_Pass": ["#", "+", "!", "-", "/", "="]},
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Datos K1 insuficientes para generar la distribución.")

        # Motor Predictivo
        st.markdown("---")
        st.subheader("Motor Predictivo de Distribución")
        st.markdown("**Calculadora de Probabilidades:** Estima el destino del ataque rival según el contexto actual de juego.")
        
        c_pred1, c_pred2 = st.columns(2)
        with c_pred1:
            pred_rot = st.selectbox("Contexto: Rotación del Rival", ["R1", "R2", "R3", "R4", "R5", "R6"])
        with c_pred2:
            pred_pass = st.selectbox("Contexto: Calidad del Pase", ["#", "+", "!", "-", "/", "="])
            
        df_pred = df[(df['Skill'] == 'A') & (df['Phase'] == 'Side-Out (K1)')]
        df_pred = df_pred[(df_pred['Rotation'] == pred_rot) & (df_pred['Previous_Pass'] == pred_pass)]
        
        if not df_pred.empty:
            prob_dist = df_pred['Start_Zone'].value_counts(normalize=True) * 100
            st.markdown(f"**Probabilidad de Destino de Colocación (Basado en {len(df_pred)} situaciones idénticas):**")
            
            cols_prob = st.columns(len(prob_dist))
            for i, (zona, prob) in enumerate(prob_dist.items()):
                with cols_prob[i]:
                    st.metric(label=f"Ataque por Zona {zona}", value=f"{prob:.1f}%")
                    st.progress(int(prob) / 100)
        else:
            st.info("No existe histórico estadístico suficiente para esta combinación exacta de Rotación y Pase.")

    # --- MÓDULO 3: MAPAS DE ATAQUE ---
    elif menu == "3. Mapas de Ataque":
        st.header("3. Shot Charts & Densidad")
        players = sorted(df[(df['Skill'] == 'A')]['Player'].dropna().unique())
        selected_player = st.sidebar.selectbox("Filtrar Jugador (Ataque)", ["Todos"] + list(players))
        
        df_attack = df[df['Skill'] == 'A'].copy()
        if selected_player != "Todos":
            df_attack = df_attack[df_attack['Player'] == selected_player]
            
        pts = len(df_attack[df_attack['Eval'] == '#'])
        err = len(df_attack[df_attack['Eval'] == '='])
        total = len(df_attack)
        eff = ((pts - err) / total * 100) if total > 0 else 0
        
        st.metric(f"Eficiencia de Ataque (EFF%) - {selected_player}", f"{eff:.1f}%", f"{pts} Pts | {err} Err | {total} Tot")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Vectores de Ataque")
            fig_vec = go.Figure()
            draw_court(fig_vec)
            for _, row in df_attack.dropna(subset=['Start_X', 'Start_Y', 'End_X', 'End_Y']).iterrows():
                color = "#2ca02c" if row['Eval'] == '#' else "#d62728" if row['Eval'] == '=' else "#7f7f7f"
                fig_vec.add_trace(go.Scatter(x=[row['Start_X'], row['End_X']], y=[row['Start_Y'], row['End_Y']],
                                             mode='lines+markers', line=dict(color=color, width=2),
                                             marker=dict(size=[0, 5], color=color), showlegend=False))
            st.plotly_chart(fig_vec, use_container_width=True)

        with c2:
            st.subheader("Heatmap de Destino")
            fig_heat = go.Figure()
            draw_court(fig_heat)
            df_heat = df_attack.dropna(subset=['End_X', 'End_Y'])
            if not df_heat.empty:
                fig_heat.add_trace(go.Histogram2dContour(x=df_heat['End_X'], y=df_heat['End_Y'], 
                                                         colorscale="YlOrRd", opacity=0.6, showscale=False))
            st.plotly_chart(fig_heat, use_container_width=True)

    # --- MÓDULO 4: PRESIÓN DE SAQUE Y RECEPCIÓN ---
    elif menu == "4. Presión de Saque y Recepción":
        st.header("4. Rendimiento Saque / Recepción")
        df_serve = df[df['Skill'] == 'S']
        df_rec = df[df['Skill'] == 'R']
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Métricas de Saque")
            aces = len(df_serve[df_serve['Eval'] == '#'])
            s_err = len(df_serve[df_serve['Eval'] == '='])
            st.metric("Total Aces", aces)
            st.metric("Total Errores Saque", s_err)
            
            fig_s = px.histogram(df_serve.dropna(subset=['End_Zone']), x='End_Zone', 
                                 title="Destino de Saque (Zonas 1-9)", color_discrete_sequence=['#1f77b4'])
            st.plotly_chart(fig_s, use_container_width=True)

        with c2:
            st.subheader("Estabilidad en Recepción")
            perfect = len(df_rec[df_rec['Eval'] == '#'])
            positive = len(df_rec[df_rec['Eval'] == '+'])
            total_rec = len(df_rec)
            r_eff = ((perfect + positive) / total_rec * 100) if total_rec > 0 else 0
            st.metric("Recepción Perfecta/Positiva (#/+)", f"{r_eff:.1f}%", f"{perfect + positive} de {total_rec}")
            
            fig_r = px.pie(df_rec, names='Eval', title="Calidad de Pase Global", hole=0.4,
                           color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_r, use_container_width=True)

    # --- MÓDULO 5: CARA A CARA (H2H) ---
    elif menu == "5. Cara a Cara (H2H)":
        st.header("5. Comparativa Directa (H2H Radar)")
        
        def calc_kpis(team_code):
            team_df = df[df['Team'] == team_code]
            att = team_df[team_df['Skill'] == 'A']
            k1_att = att[att['Phase'] == 'Side-Out (K1)']
            k2_att = att[att['Phase'] == 'Transition (K2)']
            rec = team_df[team_df['Skill'] == 'R']
            srv = team_df[team_df['Skill'] == 'S']
            
            def eff(d):
                t = len(d)
                return ((len(d[d['Eval'] == '#']) - len(d[d['Eval'] == '='])) / t * 100) if t > 0 else 0
            
            pos_rec = ((len(rec[rec['Eval'] == '#']) + len(rec[rec['Eval'] == '+'])) / len(rec) * 100) if len(rec) > 0 else 0
            
            return {
                "ATT_EFF": eff(att),
                "K1_EFF": eff(k1_att),
                "K2_EFF": eff(k2_att),
                "REC_POS": pos_rec,
                "ACES": len(srv[srv['Eval'] == '#'])
            }

        kpis_home = calc_kpis('*')
        kpis_away = calc_kpis('a')
        
        categories = ['EFF% Total', 'EFF% K1', 'EFF% K2', 'REC Positiva %', 'Aces Absolutos']
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=list(kpis_home.values()), theta=categories, fill='toself', name='Local (*)'))
        fig_radar.add_trace(go.Scatterpolar(r=list(kpis_away.values()), theta=categories, fill='toself', name='Visitante (a)'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 80])), showlegend=True)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Tabla de KPIs")
            df_comp = pd.DataFrame([kpis_home, kpis_away], index=["Local (*)", "Visitante (a)"]).T
            st.dataframe(df_comp.style.format("{:.1f}"), use_container_width=True)
        with c2:
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- MÓDULO 6: DOSSIER PDF ---
    elif menu == "6. Dossier PDF (Cuerpo Técnico)":
        st.header("6. Generación de Dossier Técnico")
        st.write("Genera un reporte ejecutivo en PDF con los KPIs globales y gráficos clave del partido seleccionado.")
        
        if st.button("Generar Dossier PDF", type="primary"):
            with st.spinner("Compilando gráficos y renderizando PDF..."):
                df_serve = df[df['Skill'] == 'S']
                fig_s = px.histogram(df_serve.dropna(subset=['End_Zone']), x='End_Zone', title="Destino de Saque")
                
                df_rec = df[df['Skill'] == 'R']
                fig_r = px.pie(df_rec, names='Eval', title="Calidad de Pase Global")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_s, \
                     tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_r:
                    
                    pio.write_image(fig_s, tmp_s.name, format="png", engine="kaleido")
                    pio.write_image(fig_r, tmp_r.name, format="png", engine="kaleido")

                    class PDF(FPDF):
                        def header(self):
                            self.set_font("helvetica", "B", 16)
                            self.cell(0, 10, "MatchPlan Pro | Dossier Técnico", align="C", ln=True)
                            self.set_font("helvetica", "I", 10)
                            self.cell(0, 10, f"Partido/Filtro: {partido_seleccionado}", align="C", ln=True)
                            self.ln(5)
                        def footer(self):
                            self.set_y(-15)
                            self.set_font("helvetica", "I", 8)
                            self.cell(0, 10, f"Página {self.page_no()} - Volley Vision 360", align="C")

                    pdf = PDF()
                    pdf.add_page()
                    
                    pdf.set_font("helvetica", "B", 14)
                    pdf.cell(0, 10, "1. Resumen de Acciones", ln=True)
                    pdf.set_font("helvetica", "", 12)
                    pdf.cell(0, 8, f"Acciones Totales: {len(df)}", ln=True)
                    pdf.cell(0, 8, f"Ataques Registrados: {len(df[df['Skill'] == 'A'])}", ln=True)
                    pdf.cell(0, 8, f"Saques Registrados: {len(df_serve)}", ln=True)
                    pdf.ln(10)

                    pdf.set_font("helvetica", "B", 14)
                    pdf.cell(0, 10, "2. Análisis de Saque y Recepción", ln=True)
                    pdf.image(tmp_s.name, x=10, w=90)
                    pdf.image(tmp_r.name, x=110, y=pdf.get_y() - 65, w=90)
                    
                    pdf_output = pdf.output(dest="S").encode("latin-1")

                st.success("¡Dossier generado con éxito!")
                st.download_button(
                    label="📥 Descargar Dossier (PDF)",
                    data=pdf_output,
                    file_name=f"MatchPlan_Dossier_{partido_seleccionado}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # --- MÓDULO 7: SINCRONIZACIÓN DE VÍDEO ---
    elif menu == "7. Sincronización de Vídeo":
        st.header("7. Sincronizador de Vídeo a Corte")
        st.markdown("**Análisis visual interactivo:** Filtra la jugada y visualiza el momento exacto.")
        
        video_file = st.file_uploader("Cargar vídeo del partido (.mp4)", type=["mp4"])
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Filtro de Acción")
            f_skill = st.selectbox("Fundamento", df['Skill'].dropna().unique(), format_func=lambda x: {"S":"Saque", "R":"Recepción", "E":"Colocación", "A":"Ataque", "B":"Bloqueo", "D":"Defensa"}.get(x, x))
            f_eval = st.selectbox("Evaluación", ["Todos"] + list(df[df['Skill'] == f_skill]['Eval'].dropna().unique()))
            f_player = st.selectbox("Jugador", ["Todos"] + list(df[df['Skill'] == f_skill]['Player'].dropna().unique()))
            
            df_vid = df.dropna(subset=['Video_Time'])
            df_vid = df_vid[df_vid['Skill'] == f_skill]
            if f_eval != "Todos": df_vid = df_vid[df_vid['Eval'] == f_eval]
            if f_player != "Todos": df_vid = df_vid[df_vid['Player'] == f_player]
            
            if not df_vid.empty:
                opciones_jugada = df_vid.apply(lambda row: f"{row['Team']}{row['Player']} | {row['Phase']} | Código: {row['Code']} | Seg: {row['Video_Time']}", axis=1)
                jugada_seleccionada = st.selectbox("Selecciona la jugada para visualizar", opciones_jugada.index, format_func=lambda x: opciones_jugada[x])
                
                tiempo_exacto = df_vid.loc[jugada_seleccionada, 'Video_Time']
                start_time = max(0, int(tiempo_exacto) - 3) 
            else:
                st.warning("No hay jugadas con vídeo sincronizado para estos filtros.")
                start_time = 0
                
        with c2:
            st.subheader("Reproductor Táctico")
            if video_file is not None and not df_vid.empty:
                st.video(video_file, start_time=start_time)
                st.info(f"Reproduciendo desde el segundo: {start_time} (Pre-roll de 3s incluido).")
            elif video_file is None:
                st.info("Sube un archivo de vídeo .mp4 para activar el reproductor.")
