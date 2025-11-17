import streamlit as st
import os
from langchain_community.graphs import Neo4jGraph
from langchain_community.chat_models import ChatOllama
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_core.prompts import PromptTemplate
from neo4j.exceptions import AuthError, ServiceUnavailable

# --- 1. CONFIGURACIÓN (Tomada de PG6 y PG7) ---

# Configuración de conexión a Neo4j (de tu script PG6)
os.environ["NEO4J_URI"] = "neo4j://127.0.0.1:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "neo4j123"
OLLAMA_MODEL = "mistral"

# PLANTILLA DE PROMPT CYPHER (La clave de tu PG6)
CYPHER_PROMPT_TEMPLATE = """
Task: Generate Cypher query for a Neo4j graph.
**ABSOLUTE RULES BREAKING THESE WILL CAUSE QUERY FAILURE:**
1. ALL relationships MUST use forward arrows (->), NEVER backward arrows (<-)
2. The ONLY valid relationship patterns are:
(Jugador)-[:TIENE_ESTADO]->(EstadoFisico)
(EstadoFisico)-[:GENERA_RECOMENDACION]->(Recomendacion)
(Jugador)-[:JUEGA_EN]->(Partido)
(Partido)-[:ENFRENTA]->(Rival)
3. FORBIDDEN patterns that will break the query:
(EstadoFisico)<-[:GENERA_RECOMENDACION]-(Recomendacion) WRONG!
(Partido)<-[:JUEGA_EN]-(Jugador) WRONG!
4. For 'sustitucion' queries, use: 'r.accion CONTAINS 'Sustitucion''

**MANDATORY QUERY TEMPLATES COPY THESE EXACTLY:**
Template A Find players to substitute:
MATCH (j:Jugador)-[:TIENE_ESTADO]->(e:EstadoFisico)-[:GENERA_RECOMENDACION]->(r:Recomendacion)
WHERE r.accion CONTAINS 'Sustitucion'
RETURN j.nombre

Schema (for property reference only):
{schema}
Question: {question}
Generate Cypher query using ONLY forward arrows (->):
"""

# PLANTILLA DE PROMPT DE RESPUESTA (La clave de tu PG6)
QA_PROMPT_TEMPLATE = """
Eres un asistente de Director Técnico de fútbol.
Se te da una pregunta y el resultado de una consulta a la base de datos (Contexto).
Debes responder la pregunta en español usando UNICAMENTE la información del contexto.
Sé directo y conciso.
Si el contexto está vacío, di que no encontraste información.

Pregunta: {question}
Contexto (Resultado de la consulta): {context}
Respuesta:
"""


# --- 2. LÓGICA DE LA APP (Cargando la Cadena) ---

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

    # 3. Crear los Prompts Personalizados
    CYPHER_PROMPT = PromptTemplate(
        input_variables=["schema", "question"],
        template=CYPHER_PROMPT_TEMPLATE,
    )
    
    QA_PROMPT = PromptTemplate(
        input_variables=["context", "question"],
        template=QA_PROMPT_TEMPLATE,
    )

    # 4. Crear la Cadena (Chain)
    chain = GraphCypherQAChain.from_llm(
        llm,
        graph=graph,
        verbose=True, # Para ver la consulta en la terminal
        cypher_prompt=CYPHER_PROMPT, # ¡Tu prompt personalizado!
        qa_prompt=QA_PROMPT,         # ¡Tu prompt personalizado!
        return_intermediate_steps=True, # Para mostrar el Cypher en la UI
        allow_dangerous_requests=True  # Requerido por LangChain para operaciones con bases de datos
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