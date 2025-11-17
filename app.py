import streamlit as st
import os
import re
from langchain_community.graphs import Neo4jGraph
from langchain_community.chat_models import ChatOllama
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks.base import BaseCallbackHandler
from neo4j.exceptions import AuthError, ServiceUnavailable

# --- 1. CONFIGURACIÓN (Tomada de PG6 y PG7) ---

# Configuración de conexión a Neo4j (de tu script PG6)
os.environ["NEO4J_URI"] = "neo4j://127.0.0.1:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "neo4j123"
OLLAMA_MODEL = "mistral"

# PLANTILLA DE PROMPT CYPHER (La clave de tu PG6)
CYPHER_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["schema", "question"],
    template="""You are a Neo4j Cypher expert. Generate ONLY valid Cypher syntax.

CRITICAL RULES:
- NEVER use SQL keywords: SELECT, FROM, JOIN, INSERT, UPDATE, DELETE
- ALWAYS use Cypher keywords: MATCH, WHERE, RETURN
- For exact matches use: {{property: 'value'}}
- For partial matches use: WHERE property CONTAINS 'value'
- NEVER use CONTAINS inside {{}}
- Use exact property names from schema

AVAILABLE NODES:
- Jugador (properties: nombre)
- EstadoFisico (properties: cansancio, ritmo_cardiaco)
- Recomendacion (properties: accion)
- Partido (properties: fecha, resultado)
- Rival (properties: nombre)
- JugadorRival (properties: nombre)

RELATIONSHIPS:
- (Jugador)-[:TIENE_ESTADO]->(EstadoFisico)
- (EstadoFisico)-[:GENERA_RECOMENDACION]->(Recomendacion)
- (Jugador)-[:JUEGA_EN]->(Partido)
- (Partido)-[:ENFRENTA]->(Rival)
- (Rival)-[:TIENE_JUGADOR_CLAVE]->(JugadorRival)

EXAMPLES (copy these patterns EXACTLY):

Question: ¿Qué jugadores deben ser sustituidos?
Cypher: MATCH (j:Jugador)-[:TIENE_ESTADO]->()-[:GENERA_RECOMENDACION]->(r:Recomendacion)
WHERE r.accion CONTAINS 'Sustitucion'
RETURN j.nombre

Question: ¿Cuál es el cansancio de Martinez?
Cypher: MATCH (j:Jugador)-[:TIENE_ESTADO]->(e:EstadoFisico)
WHERE j.nombre = 'Martinez'
RETURN e.cansancio

Question: ¿Qué rivales tenemos?
Cypher: MATCH (r:Rival)
RETURN r.nombre

Question: ¿Quién es el jugador clave de Boca Unidos?
Cypher: MATCH (r:Rival)-[:TIENE_JUGADOR_CLAVE]->(j:JugadorRival)
WHERE r.nombre CONTAINS 'Boca Unidos'
RETURN j.nombre

Question: ¿Quién es el jugador estrella de Atletico Parana?
Cypher: MATCH (r:Rival)-[:TIENE_JUGADOR_CLAVE]->(j:JugadorRival)
WHERE r.nombre CONTAINS 'Atletico Parana'
RETURN j.nombre

Question: ¿Quién es el jugador clave de Atletico Parana?
Cypher: MATCH (r:Rival)-[:TIENE_JUGADOR_CLAVE]->(j:JugadorRival)
WHERE r.nombre CONTAINS 'Atletico Parana'
RETURN j.nombre

Question: ¿Qué información tenemos sobre Rodriguez?
Cypher: MATCH (r:Rival)-[:TIENE_JUGADOR_CLAVE]->(j:JugadorRival)
WHERE j.nombre CONTAINS 'Rodriguez'
RETURN r.nombre AS Equipo, j.nombre AS Jugador

Question: ¿Qué información tenemos sobre Fernandez?
Cypher: MATCH (r:Rival)-[:TIENE_JUGADOR_CLAVE]->(j:JugadorRival)
WHERE j.nombre CONTAINS 'Fernandez'
RETURN r.nombre AS Equipo, j.nombre AS Jugador

Question: ¿De qué equipo es Rodriguez?
Cypher: MATCH (r:Rival)-[:TIENE_JUGADOR_CLAVE]->(j:JugadorRival)
WHERE j.nombre CONTAINS 'Rodriguez'
RETURN r.nombre

Question: ¿Contra quién jugamos?
Cypher: MATCH (p:Partido)-[:ENFRENTA]->(r:Rival)
RETURN r.nombre

Schema: {schema}
Question: {question}

Generate ONLY the Cypher query (no explanations). Use WHERE with CONTAINS for partial matches:
"""
)

# PLANTILLA DE PROMPT DE RESPUESTA (La clave de tu PG6)
QA_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["question", "context"],
    template="""
Eres un asistente de Director Técnico de fútbol.
Se te da una pregunta y el resultado de una consulta a la base de datos (Contexto).
Debes responder la pregunta en español usando UNICAMENTE la información del contexto.
Sé directo y conciso.
Si el contexto está vacío, di que no encontraste información.

Pregunta: {question}
Contexto (Resultado de la consulta): {context}
Respuesta:
"""
)


# --- 2. LÓGICA DE LA APP (Cargando la Cadena) ---

class CypherValidationCallback(BaseCallbackHandler):
    """Callback para validar queries Cypher antes de ejecutarlas"""
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Se llama antes de ejecutar cada herramienta (incluido el query Cypher)"""
        # Verificar si el input contiene un query Cypher
        if isinstance(input_str, str):
            query_upper = input_str.upper()
            
            # Palabras SQL prohibidas
            sql_keywords = ['SELECT', 'FROM', 'JOIN', 'INSERT', 'UPDATE', 'DELETE', 'TABLE']
            
            for keyword in sql_keywords:
                if keyword in query_upper:
                    raise ValueError(
                        f"❌ Error: Query inválido contiene sintaxis SQL '{keyword}'. "
                        f"Solo se permite sintaxis Cypher (MATCH, WHERE, RETURN).\n\n"
                        f"💡 Intenta reformular tu pregunta de forma más simple."
                    )
            
            # Detectar CONTAINS dentro de llaves (sintaxis incorrecta)
            if re.search(r'\{[^}]*CONTAINS[^}]*\}', input_str, re.IGNORECASE):
                raise ValueError(
                    "❌ Error: CONTAINS no puede usarse dentro de {{}}. "
                    "Usa: MATCH (n:Node) WHERE n.property CONTAINS 'value'\n\n"
                    "💡 Intenta reformular tu pregunta."
                )

def validate_cypher_query(query):
    """
    Valida que la consulta sea Cypher válido y no SQL.
    Retorna (es_valido, mensaje_error)
    """
    query_upper = query.upper()
    
    # Palabras prohibidas de SQL
    sql_keywords = ['SELECT', 'FROM', 'JOIN', 'INSERT', 'UPDATE', 'DELETE', 'TABLE']
    
    for keyword in sql_keywords:
        if keyword in query_upper:
            return False, f"❌ Error: La consulta contiene sintaxis SQL '{keyword}'. Solo se permite sintaxis Cypher (MATCH, WHERE, RETURN)."
    
    # Validar que tenga al menos MATCH o CREATE/MERGE
    if 'MATCH' not in query_upper and 'CREATE' not in query_upper and 'MERGE' not in query_upper:
        return False, "❌ Error: La consulta debe contener al menos MATCH, CREATE o MERGE."
    
    return True, ""

# Usamos cache_resource para no reconectar/recargar todo cada vez
@st.cache_resource
def load_chain():
    """
    Carga la GraphCypherQAChain con las plantillas personalizadas.
    """
    try:
        # 1. Conectar al Grafo
        graph = Neo4jGraph()
        graph.refresh_schema()
        
    except AuthError:
        st.error("ERROR: Autenticación de Neo4j fallida. Revisa tu contraseña en el script.")
        st.stop()
    except ServiceUnavailable:
        st.error("ERROR: No se pudo conectar a Neo4j. Asegúrate de que la base de datos esté corriendo en 'neo4j://127.0.0.1:7687'.")
        st.stop()
    except Exception as e:
        st.error(f"Error inesperado al conectar con Neo4j: {e}")
        st.stop()

    try:
        # 2. Conectar al LLM (Ollama)
        llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)
        llm.invoke("Hola") # Prueba de conexión
        
    except Exception as e:
        st.error(f"ERROR: No se pudo conectar a Ollama. Asegúrate de que esté corriendo (ej. 'ollama serve' o 'ollama run mistral').")
        st.stop()

    # 3. Crear la Cadena (Chain) con los PromptTemplates y callback de validación
    chain = GraphCypherQAChain.from_llm(
        llm,
        graph=graph,
        verbose=True, # Para ver la consulta en la terminal
        cypher_prompt=CYPHER_PROMPT_TEMPLATE, # ¡Tu prompt personalizado!
        qa_prompt=QA_PROMPT_TEMPLATE,         # ¡Tu prompt personalizado!
        return_intermediate_steps=True, # Para mostrar el Cypher en la UI
        allow_dangerous_requests=True,  # Requerido por LangChain para operaciones con bases de datos
        callbacks=[CypherValidationCallback()]  # Validar antes de ejecutar
    )
    
    return chain, graph.schema

# --- 3. INTERFAZ DE STREAMLIT (UI) ---

st.set_page_config(page_title="DT Virtual Amateur", page_icon="🤖")
st.title("🤖 Asistente DT Virtual Amateur")
st.caption("Desarrollado por: Cirrincione, Cisterna, Donnarumma")

try:
    # Cargar la cadena y el schema
    chain, schema = load_chain()

    # Mostrar el schema en un expander (útil para debug)
    with st.expander("Ver Schema del Grafo (detectado por LangChain)"):
        st.code(schema, language="text")

    # Inicializar el historial del chat en st.session_state
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "¡Hola, DT! Estoy conectado a la base de conocimiento. Haz tus preguntas sobre el grafo."
        }]

    # Mostrar mensajes del historial
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Si el mensaje tiene pasos intermedios (Cypher), muéstralos
            if "intermediate_steps" in msg:
                 with st.expander("Ver consulta Cypher generada"):
                    st.code(msg["intermediate_steps"]["query"], language="cypher")

    # Obtener nueva entrada del usuario
    if prompt := st.chat_input("¿Qué jugadores deben ser sustituidos?"):
        # Agregar mensaje del usuario al historial y mostrarlo
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generar respuesta del asistente
        with st.chat_message("assistant"):
            with st.spinner("Consultando el grafo..."):
                try:
                    # Invocar la cadena
                    response = chain.invoke({"query": prompt})
                    
                    # Extraer resultados
                    result_text = response["result"]
                    intermediate_steps = response.get("intermediate_steps", {})
                    
                    # VALIDACIÓN: Verificar que el Cypher generado NO sea SQL
                    if "query" in intermediate_steps:
                        generated_cypher = intermediate_steps["query"]
                        is_valid, error_msg = validate_cypher_query(generated_cypher)
                        
                        if not is_valid:
                            # Mostrar error específico
                            st.error("❌ " + error_msg)
                            st.warning("⚠️ El modelo generó SQL en lugar de Cypher.")
                            st.info("💡 **Sugerencia**: Intenta reformular tu pregunta de forma más simple, por ejemplo:\n- '¿Quiénes son los jugadores clave de Boca Unidos?'\n- '¿Qué rivales tenemos?'")
                            
                            # Guardar error en historial
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"Error: {error_msg}",
                                "intermediate_steps": intermediate_steps
                            })
                            st.stop()  # Detener ejecución aquí

                    # Mostrar respuesta
                    st.markdown(result_text)
                    
                    # Mostrar Cypher generado (si existe)
                    if "query" in intermediate_steps:
                        with st.expander("Ver consulta Cypher generada"):
                            st.code(intermediate_steps["query"], language="cypher")
                    
                    # Guardar respuesta completa en el historial
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result_text,
                        "intermediate_steps": intermediate_steps
                    })

                except Exception as e:
                    st.error(f"Ha ocurrido un error inesperado: {e}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Error al procesar la consulta: {e}"
                    })

except Exception as e:
    st.error(f"Error fatal al inicializar la aplicación: {e}")