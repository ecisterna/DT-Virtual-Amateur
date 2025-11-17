# 🤖 Asistente DT Virtual Amateur

Asistente de Director Técnico de fútbol desarrollado con Streamlit, LangChain, Neo4j y Ollama.

**Desarrollado por:** Cirrincione, Cisterna, Donnarumma

## 📋 Descripción

Esta aplicación permite consultar información sobre el estado físico de jugadores y obtener recomendaciones basadas en un grafo de conocimiento almacenado en Neo4j. Utiliza LangChain para generar consultas Cypher dinámicas y Ollama (Mistral) como modelo de lenguaje.

## 🚀 Requisitos Previos

Antes de ejecutar la aplicación, asegúrate de tener instalado:

1. **Python 3.13** o superior
2. **Neo4j** (Desktop o Server) corriendo en `localhost:7687`
3. **Ollama** con el modelo Mistral (`ollama pull mistral`)

## 📦 Instalación

1. **Clonar el repositorio:**
```bash
git clone <URL_DEL_REPOSITORIO>
cd Proyecto_DTVirtualAmateur_Grupo6
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar Neo4j:**
   - Asegúrate de que Neo4j esté corriendo en `neo4j://127.0.0.1:7687`
   - Usuario: `neo4j`
   - Contraseña: `neo4j123` (puedes cambiarla en `app.py`)

4. **Cargar datos en Neo4j:**
   
   Ejecuta el script de Python para crear la base de datos:
   ```bash
   python3 recreate_db.py
   ```
   
   O ejecuta el archivo `setup_neo4j.cypher` en Neo4j Browser.

5. **Verificar Ollama:**
```bash
ollama serve
ollama pull mistral
```

## ▶️ Ejecución

```bash
streamlit run app.py
```

La aplicación se abrirá en tu navegador en `http://localhost:8501`

## 🎯 Uso

Ejemplos de preguntas que puedes hacer:

- "¿Cuál es el cansancio de Martinez?"
- "¿Qué jugadores deben ser sustituidos?"
- "¿Cuál es el estado de Gomez?"
- "¿Quiénes están jugando contra Los Primos?"

## 🗂️ Estructura del Proyecto

```
Proyecto_DTVirtualAmateur_Grupo6/
├── app.py                    # Aplicación principal de Streamlit
├── requirements.txt          # Dependencias de Python
├── setup_neo4j.cypher       # Script para crear la base de datos Neo4j
├── recreate_db.py           # Script Python para recrear la BD
└── README.md                # Este archivo
```

## 🏗️ Estructura del Grafo Neo4j

El grafo sigue este esquema:

- **Jugador** -[`TIENE_ESTADO`]-> **EstadoFisico** -[`GENERA_RECOMENDACION`]-> **Recomendacion**
- **Jugador** -[`JUEGA_EN`]-> **Partido** -[`ENFRENTA`]-> **Rival**

### Ejemplo de nodos:

- **Jugador**: `{nombre: 'Martinez', rol: 'Comun'}`
- **EstadoFisico**: `{cansancio: 75, riesgoLesion: 60, minuto: 75}`
- **Recomendacion**: `{accion: 'Sustitucion inmediata', confianza: 0.75}`
- **Partido**: `{id: 'P01', resultado: 'Perdiendo 0-1', minuto: 75}`
- **Rival**: `{nombre: 'Los Primos', intensidad: 'Alta'}`

## ⚙️ Configuración

Puedes modificar la configuración en `app.py`:

```python
os.environ["NEO4J_URI"] = "neo4j://127.0.0.1:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "neo4j123"
OLLAMA_MODEL = "mistral"
```

## 🔧 Solución de Problemas

### Error: "No se pudo conectar a Neo4j"
- Verifica que Neo4j esté corriendo: `neo4j status`
- Asegúrate de que las credenciales sean correctas

### Error: "No se pudo conectar a Ollama"
- Inicia Ollama: `ollama serve`
- Verifica que tengas el modelo: `ollama list`

### La aplicación no encuentra datos
- Ejecuta `python3 recreate_db.py` para recrear la base de datos

## 📚 Tecnologías Utilizadas

- **Streamlit**: Framework para la interfaz web
- **LangChain**: Framework para aplicaciones con LLMs
- **Neo4j**: Base de datos de grafos
- **Ollama + Mistral**: Modelo de lenguaje local
- **Python 3.13**: Lenguaje de programación

## 📄 Licencia

Este proyecto es parte de un trabajo académico de la UTN.

## 👥 Autores

- Cirrincione
- Cisterna
- Donnarumma
