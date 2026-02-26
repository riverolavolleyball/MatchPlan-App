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

# --- 3. MOTOR DE PARSEO DVW (VERSIÓN FILTRADA Y LIMPIA) ---
def parse_dvw(file):
    file.seek(0)
    content = file.read().decode('latin-1')
    lines = content.split('\n')
    
    data = []
    in_scout = False
    current_home_rot = None
    current_away_rot = None
    
    # Validadores para limpiar el ruido de Data Volley
    VALID_SKILLS = {'S', 'R', 'E', 'A', 'B', 'D', 'F'}
    VALID_EVALS = {'#', '+', '!', '-', '/', '='}
    
    for line in lines:
        line = line.strip()
        if '[3DATAVOLLEYSCOUT]' in line or '[3SCOUT]' in line:
            in_scout = True
            continue
        if not in_scout or not line:
            continue
            
        # Captura de cambios de rotación
        if line.startswith('*z') and len(line) >= 3 and line[2].isdigit():
            current_home_rot = f"R{line[2]}"
            continue
        if line.startswith('az') and len(line) >= 3 and line[2].isdigit():
            current_away_rot = f"R{line[2]}"
            continue
            
        parts = line.split(';')
        code = parts[0]
        
        # Filtro estricto: Solo acciones técnicas reales de jugadores
        if len(code) >= 6 and code[0] in ['*', 'a'] and code[1:3].isdigit():
            skill = code[3]
            eval_mark = code[5]
            
            # Descartar si no es una técnica o evaluación válida (limpia ruidos de sistema)
            if skill not in VALID_SKILLS or eval_mark not in VALID_EVALS:
                continue
                
            team = code[0]
            player = code[1:3]
            
            # Zonas tácticas
            start_zone = code[9] if len(code) > 9 and code[9].isdigit() else None
            end_zone = code[10] if len(code) > 10 and code[10].isdigit() else None
            
            # Coordenadas
            start_coord = parts[14] if len(parts) > 14 else ""
            end_coord = parts[15] if len(parts) > 15 else ""
            
            start_x, start_y = get_coordinates(start_coord, start_zone, is_end=False)
            end_x, end_y = get_coordinates(end_coord, end_zone, is_end=True)
            
            # Fase y Rotación
            phase = "Side-Out (K1)" if "K1" in line else "Transition (K2)"
            rotation = current_home_rot if team == '*' else current_away_rot
            
            # Tiempo de vídeo
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
    
    # Feature Engineering: Calidad de pase previo para ataques en K1
    if not df.empty:
        df['Previous_Pass'] = None
        last_rec = None
        for idx, row in df.iterrows():
            if row['Skill'] == 'R':
                last_rec = row['Eval']
            if row['Skill'] == 'A' and row['Phase'] == 'Side-Out (K1)':
                df.at[idx, 'Previous_Pass'] = last_rec
                
    return df

# --- 4. RENDERIZADO DE PISTA ---
def draw_court(fig):
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="white", width=2), fillcolor="#e08b5e", layer="below")
    fig.add_shape(type="rect", x0=0, y0=6, x1=9, y1=12, line=dict(color="white", width=2), fillcolor="#d4aa7d", layer="below")
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="white", width=4), layer="below")
    fig.update_xaxes(range=[-1, 10], showgrid=False, visible=False)
    fig.update_yaxes(range=[-1, 19], showgrid=False, visible=False)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0))
    return fig

# --- 5. UI Y NAVEGACIÓN ---
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
    st.info("A la espera de carga de archivos .dvw para procesar.")
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtros Globales")
    lista_partidos = ["Todos"] + list(df_master['Match'].unique())
    partido_seleccionado = st.sidebar.selectbox("Seleccionar Partido", lista_partidos)
    
    df = df_master if partido_seleccionado == "Todos" else df_master[df_master['Match'] == partido_seleccionado].copy()

    # --- LÓGICA DE MÓDULOS ---
    if menu == "1. Validador de Datos":
        st.header("1. Consolidación de Datos")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Acciones", len(df))
        c2.metric("Ataques", len(df[df['Skill'] == 'A']))
        c3.metric("Saques", len(df[df['Skill'] == 'S']))
        c4.metric("Partidos", df['Match'].nunique())
        st.dataframe(df.head(100), use_container_width=True)
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", data=csv_data, file_name="match_data_clean.csv", mime="text/csv")

    elif menu == "2. Distribución K1 (Colocador)":
        st.header("2. Distribución en Side-Out")
        rot = st.sidebar.selectbox("Rotación", ["Todas", "R1", "R2", "R3", "R4", "R5", "R6"])
        df_k1 = df[(df['Skill'] == 'A') & (df['Phase'] == 'Side-Out (K1)') & (df['Previous_Pass'].notna())]
        if rot != "Todas": df_k1 = df_k1[df_k1['Rotation'] == rot]
        
        if not df_k1.empty:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("Crosstab %")
                ct = pd.crosstab(df_k1['Previous_Pass'], df_k1['Start_Zone'], normalize='index') * 100
                st.dataframe(ct.style.format("{:.1f}%"))
            with c2:
                fig = px.bar(df_k1, x="Previous_Pass", color="Start_Zone", barmode="group", title="Ataques por Pase")
                st.plotly_chart(fig, use_container_width=True)
            
            # Predictor
            st.markdown("---")
            st.subheader("Motor Predictivo")
            cp1, cp2 = st.columns(2)
            p_rot = cp1.selectbox("Simular Rotación", ["R1", "R2", "R3", "R4", "R5", "R6"])
            p_pass = cp2.selectbox("Simular Pase", ["#", "+", "!", "-", "/", "="])
            df_p = df[(df['Skill'] == 'A') & (df['Rotation'] == p_rot) & (df['Previous_Pass'] == p_pass)]
            if not df_p.empty:
                probs = df_p['Start_Zone'].value_counts(normalize=True) * 100
                cols = st.columns(len(probs))
                for i, (z, p) in enumerate(probs.items()):
                    cols[i].metric(f"Zona {z}", f"{p:.1f}%")
                    cols[i].progress(int(p)/100)
            else: st.info("Sin datos para esta combinación.")

    elif menu == "3. Mapas de Ataque":
        st.header("3. Shot Charts")
        players = sorted(df[df['Skill'] == 'A']['Player'].unique())
        sel_p = st.sidebar.selectbox("Jugador", ["Todos"] + list(players))
        df_a = df[df['Skill'] == 'A'].copy()
        if sel_p != "Todos": df_a = df_a[df_a['Player'] == sel_p]
        
        pts = len(df_a[df_a['Eval'] == '#'])
        err = len(df_a[df_a['Eval'] == '='])
        eff = ((pts - err) / len(df_a) * 100) if len(df_a) > 0 else 0
        st.metric(f"EFF% {sel_p}", f"{eff:.1f}%", f"{pts} Pts | {err} Err")

        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure()
            draw_court(fig)
            for _, r in df_a.dropna(subset=['Start_X', 'End_Y']).iterrows():
                color = "green" if r['Eval'] == '#' else "red" if r['Eval'] == '=' else "gray"
                fig.add_trace(go.Scatter(x=[r['Start_X'], r['End_X']], y=[r['Start_Y'], r['End_Y']], mode='lines+markers', line=dict(color=color, width=1), showlegend=False))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig_h = go.Figure()
            draw_court(fig_h)
            fig_h.add_trace(go.Histogram2dContour(x=df_a['End_X'], y=df_a['End_Y'], colorscale="YlOrRd", opacity=0.7))
            st.plotly_chart(fig_h, use_container_width=True)

    elif menu == "4. Presión de Saque y Recepción":
        st.header("4. Saque / Recepción")
        c1, c2 = st.columns(2)
        with c1:
            df_s = df[df['Skill'] == 'S']
            st.metric("Aces", len(df_s[df_s['Eval'] == '#']))
            st.plotly_chart(px.histogram(df_s, x="End_Zone", title="Destino Saque"), use_container_width=True)
        with c2:
            df_r = df[df['Skill'] == 'R']
            pos = len(df_r[df_r['Eval'].isin(['#', '+'])]) / len(df_r) * 100 if len(df_r) > 0 else 0
            st.metric("Positiva %", f"{pos:.1f}%")
            st.plotly_chart(px.pie(df_r, names='Eval', title="Calidad Recepción"), use_container_width=True)

    elif menu == "5. Cara a Cara (H2H)":
        st.header("5. Team Comparison")
        def get_team_kpis(t):
            d = df[df['Team'] == t]
            a = d[d['Skill'] == 'A']
            r = d[d['Skill'] == 'R']
            eff = (len(a[a['Eval'] == '#']) - len(a[a['Eval'] == '='])) / len(a) * 100 if len(a) > 0 else 0
            pos = len(r[r['Eval'].isin(['#', '+'])]) / len(r) * 100 if len(r) > 0 else 0
            return [eff, pos, len(d[d['Skill'] == 'S' and d['Eval'] == '#'])]
        
        k_h = get_team_kpis('*')
        k_a = get_team_kpis('a')
        cat = ['EFF Ataque', 'REC Positiva', 'Aces']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=k_h, theta=cat, fill='toself', name='Local'))
        fig.add_trace(go.Scatterpolar(r=k_a, theta=cat, fill='toself', name='Away'))
        st.plotly_chart(fig, use_container_width=True)

    elif menu == "6. Dossier PDF (Cuerpo Técnico)":
        st.header("6. Reporte Ejecutivo")
        if st.button("Generar PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Reporte: {partido_seleccionado}", ln=True)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Acciones: {len(df)}", ln=True)
            pdf.cell(0, 10, f"Ataques: {len(df[df['Skill']=='A'])}", ln=True)
            st.download_button("Descargar PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="reporte.pdf")

    elif menu == "7. Sincronización de Vídeo":
        st.header("7. Video Sync")
        v_file = st.file_uploader("Video .mp4", type=["mp4"])
        c1, c2 = st.columns(2)
        with c1:
            df_v = df.dropna(subset=['Video_Time'])
            if not df_v.empty:
                idx = st.selectbox("Acción", df_v.index, format_func=lambda x: f"{df_v.loc[x, 'Code']} (Seg: {df_v.loc[x, 'Video_Time']})")
                t = max(0, int(df_v.loc[idx, 'Video_Time']) - 3)
                if v_file: st.video(v_file, start_time=t)
            else: st.warning("Sin marcas de tiempo en el archivo.")
