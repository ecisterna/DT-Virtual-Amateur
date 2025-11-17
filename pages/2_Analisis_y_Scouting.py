import streamlit as st
import pandas as pd
import spacy
from spacy import displacy
import altair as alt
import os
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable  # <-- ¡AGREGADO!

# --- CONFIGURACIÓN DE CONEXIÓN A NEO4J (¡NUEVO!) ---
# Copiamos las mismas credenciales que usa app.py
URI = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
USER = os.environ.get("NEO4J_USERNAME", "neo4j")
PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j123")

# --- FUNCIONES DE LÓGICA (¡NUEVO!) ---

@st.cache_resource
def get_neo4j_driver():
    """
    Crea y cachea una instancia del driver de Neo4j.
    """
    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        driver.verify_connectivity()
        return driver
    except AuthError:
        st.error("Error de autenticación con Neo4j. Revisa las credenciales.")
        return None
    except ServiceUnavailable:
        st.error("Error: No se pudo conectar a Neo4j. ¿Está la base de datos corriendo?")
        return None

def update_graph_with_entities(driver, entities, text):
    """
    Toma las entidades de spaCy y el texto original para extraer información del rival.
    Estrategia mejorada:
    1. Buscar nombres de equipos entre comillas
    2. Buscar nombres de jugadores entre comillas
    3. Usar entidades de spaCy como respaldo
    """
    import re
    
    # 1. ESTRATEGIA PRIMARIA: Buscar texto entre comillas
    quoted_pattern = r"['\"]([^'\"]+)['\"]"
    quoted_matches = re.findall(quoted_pattern, text)
    
    rival_org = None
    rival_players = []
    
    # Palabras comunes que NO son nombres de jugadores
    palabras_comunes = {
        'recomendamos', 'debemos', 'tenemos', 'es', 'son', 'tiene', 'tienen',
        'juega', 'juegan', 'marca', 'marcan', 'cansa', 'cansan', 'evitar',
        'presionar', 'defender', 'atacar', 'y', 'o', 'pero', 'si', 'no',
        'muy', 'poco', 'mucho', 'más', 'menos', 'el', 'la', 'los', 'las',
        'un', 'una', 'unos', 'unas', 'desde', 'hasta', 'para', 'por', 'con'
    }
    
    # El primer texto entre comillas después de "Análisis de" o "rival" suele ser el equipo
    if "Análisis de" in text or "análisis de" in text.lower():
        team_pattern = r"[Aa]nálisis de ['\"]?([^'\":\n]+)['\"]?"
        team_match = re.search(team_pattern, text)
        if team_match:
            rival_org = team_match.group(1).strip()
    elif "rival" in text.lower():
        # Buscar patrón "rival 'Nombre'"
        rival_pattern = r"rival ['\"]([^'\"]+)['\"]"
        rival_match = re.search(rival_pattern, text, re.IGNORECASE)
        if rival_match:
            rival_org = rival_match.group(1).strip()
    
    # Si no encontramos el equipo con patrones, usar la primera entidad ORG
    if not rival_org:
        for ent in entities:
            if ent.label_ == "ORG":
                rival_org = ent.text
                break
    
    # 2. BUSCAR JUGADORES: Texto entre comillas que parezca nombre de persona
    for match in quoted_matches:
        match_clean = match.strip()
        match_lower = match_clean.lower()
        
        # Filtrar:
        # - No es el nombre del equipo
        # - Longitud razonable (3-30 caracteres)
        # - No contiene números
        # - Primera letra mayúscula
        # - No es una palabra común
        # - Máximo 3 palabras (para evitar frases completas)
        if (match_clean != rival_org and 
            2 <= len(match_clean) <= 30 and 
            not any(char.isdigit() for char in match_clean) and
            match_clean[0].isupper() and
            match_lower not in palabras_comunes and
            len(match_clean.split()) <= 3):
            
            # Verificar que no sea una palabra común al inicio
            primera_palabra = match_clean.split()[0].lower()
            if primera_palabra not in palabras_comunes:
                rival_players.append(match_clean)
    
    # Agregar también las entidades PER de spaCy (son más confiables)
    for ent in entities:
        ent_clean = ent.text.strip()
        ent_lower = ent_clean.lower()
        
        # Filtrar palabras comunes incluso si vienen de spaCy
        if ent_lower in palabras_comunes:
            continue
            
        if ent.label_ == "PER" and ent_clean not in rival_players:
            rival_players.append(ent_clean)
        # IMPORTANTE: A veces spaCy marca jugadores como ORG incorrectamente
        # Si ya tenemos un equipo, otras ORG cortas podrían ser jugadores
        elif ent.label_ == "ORG" and ent_clean != rival_org and rival_org:
            # Solo agregar si es un nombre corto (max 3 palabras) y no es palabra común
            if (len(ent_clean.split()) <= 3 and 
                ent_clean not in rival_players and
                ent_lower not in palabras_comunes):
                rival_players.append(ent_clean)
    
    # 3. Si encontramos equipo y al menos un jugador, escribir en Neo4j
    if rival_org and rival_players:
        results = []
        try:
            with driver.session() as session:
                # Crear el nodo Rival
                session.run(
                    "MERGE (r:Rival {nombre: $nombre})",
                    nombre=rival_org
                )
                
                # Crear cada jugador clave y su relación
                for player in rival_players:
                    query = (
                        "MERGE (r:Rival {nombre: $rival_nombre}) "
                        "MERGE (j:JugadorRival {nombre: $jugador_nombre}) "
                        "MERGE (r)-[:TIENE_JUGADOR_CLAVE]->(j)"
                    )
                    session.run(query, rival_nombre=rival_org, jugador_nombre=player)
                    results.append(f"  • {player}")
                
            result_text = f"✅ **Grafo actualizado exitosamente:**\n"
            result_text += f"**Equipo:** {rival_org}\n"
            result_text += f"**Jugadores clave:** ({len(rival_players)})\n"
            result_text += "\n".join(results)
            return result_text
            
        except Exception as e:
            return f"❌ Error al escribir en Neo4j: {e}"
    
    # 4. Mensajes de ayuda si no se encontró información
    if not rival_org:
        return "⚠️ No se detectó el nombre del equipo rival. Intenta incluirlo entre comillas, ej: Análisis de 'Los Primos' o rival 'Boca Unidos'"
    elif not rival_players:
        return f"⚠️ Se detectó el equipo '{rival_org}' pero no se encontraron jugadores. Incluye nombres entre comillas, ej: 'Martinez'"
    
    return "❌ No se encontraron entidades válidas para actualizar el grafo."


# --- CONFIGURACIÓN DE LA PÁGINA (Sin cambios) ---
st.set_page_config(page_title="Análisis y Scouting", page_icon="📊")
st.title("📊 Análisis Histórico y Scouting NLP")

# --- Carga de Modelos y Datos (Sin cambios) ---
@st.cache_resource
def load_spacy_model():
    try:
        nlp = spacy.load("es_core_news_md")
    except OSError:
        st.error(
            "Modelo de spaCy 'es_core_news_md' no encontrado. "
            "Ejecuta `python -m spacy download es_core_news_md` en tu terminal."
        )
        st.stop()
    return nlp

nlp_model = load_spacy_model()

@st.cache_data
def load_data(csv_path="dataset.csv"):
    try:
        df = pd.read_csv(csv_path)
        return df
    except FileNotFoundError:
        st.error(
            f"Error: No se encontró el archivo '{csv_path}'. "
            "Asegúrate de que 'dataset.csv' esté en la carpeta raíz del proyecto."
        )
        return pd.DataFrame()
    
df = load_data()

# Obtener el driver de Neo4j al cargar la página
neo4j_driver = get_neo4j_driver()

# --- Pestaña 1: Análisis del Dataset (EDA) ---
tab1, tab2 = st.tabs(["📈 Análisis del Dataset", "📝 Procesador de Scouting (NLP)"])

with tab1:
    st.header("Análisis del Dataset de Scouting")
    
    if not df.empty:
        # Mostrar información general del dataset
        st.subheader("Resumen del Dataset")
        
        col1, col2 = st.columns(2)
        col1.metric("Total de Reportes", len(df))
        col2.metric("Categorías", df["categoria"].nunique())
        
        # Distribución de categorías
        st.subheader("Distribución de Categorías")
        
        categoria_counts = df["categoria"].value_counts().reset_index()
        categoria_counts.columns = ["Categoría", "Cantidad"]
        
        chart = alt.Chart(categoria_counts).mark_bar().encode(
            x=alt.X('Cantidad:Q', title='Cantidad de Reportes'),
            y=alt.Y('Categoría:N', title='Categoría', sort='-x'),
            color=alt.Color('Categoría:N', legend=None),
            tooltip=['Categoría', 'Cantidad']
        ).properties(height=300)
        
        st.altair_chart(chart, use_container_width=True)
        
        # Filtro por categoría
        st.subheader("Explorar Reportes por Categoría")
        categorias = ["Todas"] + df["categoria"].unique().tolist()
        categoria_seleccionada = st.selectbox(
            "Selecciona una categoría:",
            options=categorias
        )
        
        if categoria_seleccionada == "Todas":
            df_filtrado = df
        else:
            df_filtrado = df[df["categoria"] == categoria_seleccionada]
        
        st.write(f"Mostrando {len(df_filtrado)} reportes")
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Mostrar ejemplos aleatorios
        st.subheader("Ejemplos Aleatorios")
        if st.button("🎲 Generar nuevos ejemplos"):
            st.rerun()
        
        ejemplos = df_filtrado.sample(min(3, len(df_filtrado)))
        for idx, row in ejemplos.iterrows():
            with st.expander(f"📝 {row['categoria']}"):
                st.write(row['explicacion'])
    else:
        st.warning("No se pudieron cargar los datos para el análisis.")

# --- Pestaña 2: Procesador de Scouting (NLP) (¡MODIFICADO!) ---
with tab2:
    st.header("Procesador de Reportes de Scouting (NER con spaCy)")
    st.markdown(
        "Pega un reporte de scouting. El sistema extraerá las entidades clave "
        "y **actualizará el grafo de Neo4j automáticamente**."
    )
    
    # Mostrar ejemplos predefinidos en un expander
    with st.expander("📖 Ver ejemplos de reportes"):
        st.markdown("""
        ### Ejemplo 1: Reporte Completo
        ```
        Reporte del próximo rival 'Boca Unidos': Su defensa es muy sólida y tienen 
        un juego aéreo dominante. El jugador clave es 'Fernandez', quien organiza 
        el mediocampo con pases largos precisos. Debemos presionarlo desde el inicio.
        ```
        
        ### Ejemplo 2: Análisis Táctico
        ```
        Análisis de 'Los Primos': Utilizan un 4-3-3 muy ofensivo. Su delantero 
        'Martinez' es rápido y aprovecha los espacios. El mediocampista 'Silva' 
        tiene excelente visión de juego pero es lento en la recuperación.
        ```
        
        ### Ejemplo 3: Análisis Individual
        ```
        El jugador estrella del rival 'Atletico Parana' es 'Diaz'. Juega como 
        enganche y tiene gran técnica individual. Marca poco en defensa y se 
        cansa después del minuto 70. Recomendamos presión constante para agotarlo.
        ```
        
        **💡 Tip:** Para mejores resultados, incluye nombres de equipos y jugadores entre comillas.
        """)

    # Selector de ejemplos rápidos
    col1, col2 = st.columns([3, 1])
    with col2:
        ejemplo_seleccionado = st.selectbox(
            "Ejemplos rápidos:",
            ["Personalizado", "Boca Unidos", "Los Primos", "Atletico Parana"]
        )
    
    # Definir ejemplos
    ejemplos = {
        "Boca Unidos": (
            "Reporte del próximo rival 'Boca Unidos': Su defensa es muy sólida y tienen "
            "un juego aéreo dominante. El jugador clave es 'Fernandez', quien organiza "
            "el mediocampo con pases largos precisos. Debemos presionarlo desde el inicio."
        ),
        "Los Primos": (
            "Análisis de 'Los Primos': Utilizan un 4-3-3 muy ofensivo. Su delantero "
            "'Martinez' es rápido y aprovecha los espacios. El mediocampista 'Silva' "
            "tiene excelente visión de juego pero es lento en la recuperación."
        ),
        "Atletico Parana": (
            "El jugador estrella del rival 'Atletico Parana' es 'Diaz'. Juega como "
            "enganche y tiene gran técnica individual. Marca poco en defensa y se "
            "cansa después del minuto 70. Recomendamos presión constante para agotarlo."
        ),
        "Personalizado": (
            "Reporte de 'Los Primos': Tienen un juego aéreo fuerte y su "
            "defensa es sólida. El jugador clave es 'Martinez', que maneja "
            "la presión alta. Debemos evitar las faltas cerca del área."
        )
    }
    
    with col1:
        texto_reporte = st.text_area(
            "Ingresa el reporte de scouting aquí:",
            value=ejemplos[ejemplo_seleccionado],
            height=200
        )
    
    if st.button("Analizar y Actualizar Grafo"):
        if not neo4j_driver:
            st.error("No se puede actualizar: falta la conexión con Neo4j.")
        elif not texto_reporte:
            st.warning("Por favor, ingresa un texto para analizar.")
        else:
            with st.spinner("Procesando texto y actualizando grafo..."):
                # 1. Procesar el texto con spaCy
                doc = nlp_model(texto_reporte)
                
                # 2. ¡NUEVO! Escribir las entidades en Neo4j (pasar texto también)
                status_message = update_graph_with_entities(neo4j_driver, doc.ents, texto_reporte)
                
                # 3. Mostrar el mensaje de estado (éxito o advertencia)
                if "✅" in status_message or "Éxito" in status_message:
                    st.success(status_message)
                    
                    # Mostrar consultas de ejemplo
                    st.info("💡 **Ahora puedes hacer estas consultas en la pestaña principal:**")
                    
                    # Extraer nombres para personalizar las sugerencias
                    rival_nombre = None
                    jugador_nombre = None
                    for ent in doc.ents:
                        if ent.label_ == "ORG" and not rival_nombre:
                            rival_nombre = ent.text
                        elif ent.label_ == "PER" and not jugador_nombre:
                            jugador_nombre = ent.text
                    
                    if rival_nombre and jugador_nombre:
                        st.code(f"¿Quién es el jugador clave de {rival_nombre}?", language="text")
                        st.code(f"¿Qué información tenemos sobre {jugador_nombre}?", language="text")
                    
                    st.code("¿Qué rivales tenemos en la base de datos?", language="text")
                else:
                    st.warning(status_message)

                # 4. Mostrar la visualización de entidades (como antes)
                html = displacy.render(doc, style="ent", jupyter=False)
                st.subheader("Entidades Tácticas Identificadas")
                st.write(html, unsafe_allow_html=True)
                
                entidades_encontradas = [(ent.text, ent.label_) for ent in doc.ents]
                if entidades_encontradas:
                    st.subheader("Resumen de Entidades")
                    df_entidades = pd.DataFrame(entidades_encontradas, columns=["Texto", "Tipo"])
                    # Traducir tipos de entidades
                    tipo_traduccion = {
                        "ORG": "Organización (Equipo)",
                        "PER": "Persona (Jugador)",
                        "LOC": "Lugar",
                        "MISC": "Otro"
                    }
                    df_entidades["Tipo"] = df_entidades["Tipo"].map(lambda x: tipo_traduccion.get(x, x))
                    st.table(df_entidades)