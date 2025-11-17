# 📤 Guía para Subir a GitHub

## ✅ Archivos que SE SUBIRÁN a GitHub (ya incluidos):

1. **app.py** - Aplicación principal de Streamlit
2. **requirements.txt** - Dependencias de Python
3. **setup_neo4j.cypher** - Script para crear la base de datos Neo4j
4. **README.md** - Documentación del proyecto
5. **.gitignore** - Archivos a ignorar

## ❌ Archivos que NO se subirán (automáticamente ignorados):

- `check_db.py`, `fix_relations.py`, etc. - Scripts temporales de verificación
- `.vscode/` - Configuración local de VS Code
- `__pycache__/`, `*.pyc` - Archivos compilados de Python
- `.venv/`, `venv/` - Entornos virtuales (cada uno debe crear el suyo)
- `.DS_Store` - Archivos del sistema macOS

## 🚀 Pasos para subir a GitHub:

### 1. Crear repositorio en GitHub
- Ve a https://github.com/new
- Nombre sugerido: `DT-Virtual-Amateur`
- Descripción: "Asistente de Director Técnico de fútbol con IA"
- **NO** inicialices con README (ya lo tienes)

### 2. Conectar y subir el repositorio

```bash
# En tu terminal, ejecuta estos comandos:

# Conectar con tu repositorio de GitHub (reemplaza <USERNAME> y <REPO>)
git remote add origin https://github.com/<USERNAME>/<REPO>.git

# Subir los archivos
git branch -M main
git push -u origin main
```

### 3. Tus compañeros pueden clonar el proyecto:

```bash
git clone https://github.com/<USERNAME>/<REPO>.git
cd <REPO>
pip install -r requirements.txt
python3 recreate_db.py  # Para crear la base de datos
streamlit run app.py
```

## 📋 Checklist antes de compartir:

✅ Verificar que Neo4j esté instalado (lo necesitarán)
✅ Verificar que Ollama esté instalado (lo necesitarán)
✅ Asegurarte de que no hay contraseñas sensibles en el código
✅ Documentar bien el README con instrucciones

## 🔐 Nota de Seguridad:

Si quieres usar variables de entorno para las credenciales de Neo4j, puedes crear un archivo `.env` (que está en .gitignore) y modificar app.py para usar `python-dotenv`.

## 💡 Extras opcionales:

Puedes agregar a `recreate_db.py` al repositorio para que tus compañeros puedan recrear fácilmente la base de datos. Para eso:

```bash
git add recreate_db.py
git commit -m "Add: script para recrear base de datos Neo4j"
git push
```
