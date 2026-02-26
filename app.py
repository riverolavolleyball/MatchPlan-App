import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import random

# ==========================================
# 1. CONFIGURACIÓN CORPORATIVA (RIVEROLA VOLLEYBALL)
# ==========================================
st.set_page_config(page_title="MatchPlan Pro | Riverola Volleyball", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
    /* Tema oscuro ejecutivo estilo untan.gl */
    .main { background-color: #0d1117; color: #c9d1d9; font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    [data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    h1, h2, h3 { color: #ffffff; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏐 MatchPlan Pro")
st.markdown("**Powered by Riverola Volleyball | Tactical Intelligence System**")

# ==========================================
# 2. DICCIONARIOS DE EXTRACCIÓN DATA VOLLEY 4
# ==========================================
# Fundamentos según sintaxis oficial
SKILLS = {'S': 'Saque', 'R': 'Recepción', 'E': 'Colocación', 'A': 'Ataque', 'B': 'Bloqueo', 'D': 'Defensa', 'F': 'Finta'}
# Evaluaciones según estándar FIVB/DV4
RATINGS = {'#': 'Punto / Perfecto (#)', '+': 'Positivo (+)', '!': 'En Juego (!)', '-': 'Negativo (-)', '/': 'Pobre (/)', '=': 'Error (=)'}

# ==========================================
# 3. MOTOR ESPACIAL (ALGORITMO GEOESPACIAL)
# ==========================================
def get_coordenadas(exact_val, zone_char, is_start):
    """
    Motor híbrido: Lee clics exactos de DV4 (Matriz 100x100).
    Si no existen, traduce la zona tecleada a metros (Fórmula untan.gl).
    """
    # 1. Coordenadas Exactas (Clic del Scouter)
    if exact_val and str(exact_val).isdigit() and int(exact_val) > 0:
        val = int(exact_val)
        x = (val % 100) * 0.09  # Escala X a 9m
        y = (val // 100) * 0.18 # Escala Y a 18m
        return x, y
        
    # 2. Mapeo por Zonas (Fallback)
    if not zone_char or not zone_char.isdigit() or zone_char == '0':
        return None, None
        
    z = int(zone_char)
    # Coordenadas centrales de cada zona (1-9)
    if is_start: # Campo Inferior (Origen)
        x_map = {1: 7.5, 2: 7.5, 3: 4.5, 4: 1.5, 5: 1.5, 6: 4.5, 7: 1.5, 8: 4.5, 9: 7.5}
        y_map = {1: 1.5, 2: 7.5, 3: 7.5, 4: 7.5, 5: 1.5, 6: 1.5, 7: -0.5, 8: -0.5, 9: -0.5}
    else: # Campo Superior (Destino)
        x_map = {1: 1.5, 2: 1.5, 3: 4.5, 4: 7.5, 5: 7.5, 6: 4.5, 7: 7.5, 8: 4.5, 9: 1.5}
        y_map = {1: 16.5, 2: 10.5, 3: 10.5, 4: 10.5, 5: 16.5, 6: 16.5, 7: 18.5, 8: 18.5, 9: 18.5}
        
    if z in x_map:
        # Añade dispersión (Jitter) de +-0.6m para formar nubes de calor orgánicas
        return x_map[z] + random.uniform(-0.6, 0.6), y_map[z] + random.uniform(-0.6, 0.6)
        
    return None, None

# ==========================================
# 4. PARSER DE DATOS DE ALTA PRECISIÓN
# ==========================================
@st.cache_data # Optimiza la carga para que la app sea ultrarrápida
def procesar_archivo_dvw(lineas):
    try:
        scout_idx = next(i for i, l in enumerate(lineas) if "[3SCOUT]" in l) + 1
    except StopIteration:
        return pd.DataFrame()

    datos = []
    for line in lineas[scout_idx:]:
        p = line.split(';')
        if len(p) < 11: continue
        
        c = p[0] # Cadena de la acción (ej. *09ST-~~~95A)
        
        # Filtro: Ignorar líneas cortas, rotaciones y comandos de sistema
        if len(c) < 6 or c[0] not in ['*', 'a'] or not c[1:3].isdigit() or c[3] not in SKILLS:
            continue
            
        # Extracción de Zonas (Posiciones 9 y 10 en la cadena)
        z_in = c[9] if len(c) > 9 and c[9] != '~' else None
        z_out = c[10] if len(c) > 10 and c[10] != '~' else None
        
        # Extracción de Coordenadas (Columnas 14 y 15 en el split por ';')
        x_in, y_in = get_coordenadas(p[14] if len(p) > 14 else None, z_in, True)
        x_out, y_out = get_coordenadas(p[15] if len(p) > 15 else None, z_out, False)

        datos.append({
            "Equipo": "Local" if c[0] == "*" else "Visitante",
            "Dorsal": c[1:3],
            "Acción": SKILLS[c[3]],
            "Resultado": RATINGS.get(c[5], "Continuidad"),
            "Z_Origen": z_in if z_in else "-",
            "Z_Destino": z_out if z_out else "-",
            "Marcador": f"{p[9]}-{p[10]}",
            "X_In": x_in, "Y_In": y_in, "X_Out": x_out, "Y_Out": y_out,
            "Fase": "K1 (Side-Out)" if "K1" in line else "K2 (Transición)"
        })
        
    return pd.DataFrame(datos)

def dibujar_pista_fivb(fig):
    """Renderiza las líneas oficiales de la pista FIVB (9x18m)"""
    # Perímetro
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=18, line=dict(color="#ffffff", width=2))
    # Red Central
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#00ffcc", width=5))
    # Líneas de 3 metros (Ataque)
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="#8b949e", width=1.5, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=12, x1=9, y1=12, line=dict(color="#8b949e", width=1.5, dash="dash"))
    
    fig.update_layout(
        xaxis=dict(range=[-0.5, 9.5], visible=False),
        yaxis=dict(range=[-0.5, 18.5], visible=False),
        template="plotly_dark",
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ==========================================
# 5. INTERFAZ Y DASHBOARD EJECUTIVO
# ==========================================
archivo = st.file_uploader("📥 Cargar archivo de Data Volley 4 (.dvw)", type=["dvw"])

if archivo:
    # Decodificación segura para archivos de Windows/DataVolley
    df = procesar_archivo_dvw(archivo.read().decode('latin-1').splitlines())
    
    if not df.empty:
        # --- PANEL LATERAL DE CONTROL ---
        st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Volleyball_icon.svg/200px-Volleyball_icon.svg.png", width=50) # Logo genérico
        st.sidebar.header("🎯 Parámetros Tácticos")
        
        equipo_sel = st.sidebar.selectbox("Seleccionar Equipo", df['Equipo'].unique())
        accion_sel = st.sidebar.selectbox("Fundamento", df['Acción'].unique(), index=list(df['Acción'].unique()).index('Ataque') if 'Ataque' in df['Acción'].unique() else 0)
        
        jugadores_disp = df[df['Equipo'] == equipo_sel]['Dorsal'].unique()
        jugadores_sel = st.sidebar.multiselect("Filtrar Dorsales", jugadores_disp, default=jugadores_disp)
        
        # Filtro de Fase de Juego (K1/K2)
        fase_sel = st.sidebar.multiselect("Fase de Juego", df['Fase'].unique(), default=df['Fase'].unique())
        
        # Aplicación de filtros
        df_f = df[(df['Equipo'] == equipo_sel) & 
                  (df['Acción'] == accion_sel) & 
                  (df['Dorsal'].isin(jugadores_sel)) & 
                  (df['Fase'].isin(fase_sel))]

        # --- KPIs SUPERIORES (MÉTRICAS CLAVE) ---
        st.markdown(f"### 📈 Reporte de Análisis: {equipo_sel} | {accion_sel}")
        c1, c2, c3, c4 = st.columns(4)
        
        volumen = len(df_f)
        aciertos = len(df_f[df_f['Resultado'] == 'Punto / Perfecto (#)'])
        errores = len(df_f[df_f['Resultado'] == 'Error (=)'])
        eficiencia = ((aciertos - errores) / volumen * 100) if volumen > 0 else 0

        c1.metric("Volumen (Acciones)", volumen)
        c2.metric("Puntos / Éxito (#)", aciertos)
        c3.metric("Errores No Forzados (=)", errores)
        c4.metric("Eficiencia Neta (EFF %)", f"{eficiencia:.1f}%")

        st.divider()

        # --- VISUALIZACIÓN GRÁFICA TIPO UNTAN.GL ---
        tab1, tab2, tab3 = st.tabs(["🔥 Mapa de Calor (Zonas de Impacto)", "🏹 Shot Chart (Direcciones)", "📋 Panel de Datos Limpios"])

        with tab1:
            st.markdown("##### Densidad espacial de los impactos en pista")
            if not df_f['X_Out'].dropna().empty:
                fig_calor = px.density_heatmap(df_f, x="X_Out", y="Y_Out", nbinsx=25, nbinsy=50,
                                             range_x=[0, 9], range_y=[0, 18], color_continuous_scale="Inferno")
                fig_calor = dibujar_pista_fivb(fig_calor)
                fig_calor.update_layout(width=450, height=750)
                st.plotly_chart(fig_calor, use_container_width=False)
            else:
                st.info("No hay destinos registrados para generar el Mapa de Calor con los filtros actuales.")

        with tab2:
            st.markdown("##### Vectores de trayectoria táctica")
            st.markdown("<small>🟢 Punto | 🔴 Error | ⚪ Continuidad</small>", unsafe_allow_html=True)
            
            fig_direcciones = go.Figure()
            fig_direcciones = dibujar_pista_fivb(fig_direcciones)
            
            for _, fila in df_f.dropna(subset=['X_In', 'X_Out']).iterrows():
                # Colores Ejecutivos
                if "Punto" in fila['Resultado']: color_vector = "#00ffcc" # Verde Neón
                elif "Error" in fila['Resultado']: color_vector = "#ff4b4b" # Rojo Alerta
                else: color_vector = "#8b949e" # Gris Neutro
                
                fig_direcciones.add_trace(go.Scatter(x=[fila['X_In'], fila['X_Out']], y=[fila['Y_In'], fila['Y_Out']],
                                                   mode='lines+markers', line=dict(color=color_vector, width=1.8),
                                                   marker=dict(size=5, symbol='circle'), hoverinfo='text', 
                                                   text=f"Dorsal: {fila['Dorsal']} | Res: {fila['Resultado']}"))
            
            fig_direcciones.update_layout(width=450, height=750, showlegend=False)
            st.plotly_chart(fig_direcciones, use_container_width=False)

        with tab3:
            st.markdown("##### 📊 Rendimiento Agrupado por Jugador")
            if not df_f.empty:
                resumen = df_f.groupby('Dorsal').agg(
                    Intentos=('Acción', 'count'),
                    Puntos=('Resultado', lambda x: (x == 'Punto / Perfecto (#)').sum()),
                    Errores=('Resultado', lambda x: (x == 'Error (=)').sum())
                ).reset_index()
                resumen['EFF %'] = ((resumen['Puntos'] - resumen['Errores']) / resumen['Intentos'] * 100).round(1)
                
                # Resaltar la tabla con el estilo nativo de Streamlit
                st.dataframe(resumen.sort_values(by='Intentos', ascending=False), use_container_width=True, hide_index=True)
                
            st.markdown("##### 📝 Registro de Acciones (Log Táctico)")
            st.dataframe(df_f[['Marcador', 'Fase', 'Dorsal', 'Acción', 'Resultado', 'Z_Origen', 'Z_Destino']].reset_index(drop=True), use_container_width=True)

    else:
        st.error("No se han encontrado datos tácticos procesables en este archivo. Verifica que contenga acciones bajo la etiqueta [3SCOUT].")
