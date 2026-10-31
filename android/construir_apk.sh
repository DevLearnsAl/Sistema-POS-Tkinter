#!/usr/bin/env bash
# Arma el APK del sistema. Se corre dentro de WSL (Ubuntu), no en Windows:
#
#     wsl -d Ubuntu -- bash "/mnt/c/Users/TU_USUARIO/Documents/Minimarket referencia/android/construir_apk.sh"
#
# Copia el proyecto a la carpeta de Linux (construir sobre /mnt/c es mucho más
# lento) y deja el APK en ~/minimarket-android/bin/.
#
# La primera vez descarga el SDK y el NDK de Android: unos 2 GB y entre 30 y 90
# minutos. Las siguientes son cuestión de minutos.
set -e

ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="$HOME/minimarket-android"

# Las herramientas de Android todavía no funcionan con Python 3.14, que es el que
# trae Ubuntu 26.04. Se usa un Python 3.11 independiente instalado con uv.
VERSION_PYTHON="3.11"
export PATH="$HOME/.local/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
# Buildozer instala sus dependencias con «pip --user», y Ubuntu lo bloquea si no
# se le indica lo contrario.
export PIP_BREAK_SYSTEM_PACKAGES=1

echo "==> Comprobando herramientas"
if ! command -v uv > /dev/null; then
    echo "    instalando uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
    export PATH="$HOME/.local/bin:$PATH"
fi

uv python install "$VERSION_PYTHON" > /dev/null 2>&1 || true
PYTHON=$(find "$HOME/.local/share/uv/python" -maxdepth 2 -type d -name bin 2>/dev/null \
         | grep "cpython-$VERSION_PYTHON" | head -1)/python"$VERSION_PYTHON"
if [ ! -x "$PYTHON" ]; then
    echo "    no se encontró Python $VERSION_PYTHON"
    exit 1
fi
echo "    Python: $("$PYTHON" --version)"
echo "    Java:   $(java -version 2>&1 | head -1)"

# Buildozer 1.5.0 es el que acompaña a la versión de python-for-android que se
# fija en buildozer.spec. Con la 1.6.0 no combinan.
VERSION_BUILDOZER="1.5.0"
if ! "$PYTHON" -m buildozer --version 2>/dev/null | grep -q "$VERSION_BUILDOZER"; then
    echo "    instalando buildozer $VERSION_BUILDOZER y cython..."
    "$PYTHON" -m pip install -q --user "buildozer==$VERSION_BUILDOZER" cython
fi
echo "    Buildozer: $("$PYTHON" -m buildozer --version 2>&1 | tail -1)"

# En la última etapa, python-for-android llama a «python» a secas para armar un
# entorno virtual y resolver paquetes. Sin esto tomaría el 3.14 del sistema y
# buscaría paquetes para esa versión, que no existen para Android. El atajo hace
# que «python» sea el 3.11 durante toda la construcción.
ATAJOS="$HOME/.local/atajos-buildozer"
mkdir -p "$ATAJOS"
ln -sf "$PYTHON" "$ATAJOS/python"
ln -sf "$PYTHON" "$ATAJOS/python3"
# La receta de libjpeg (que necesita pillow) trae un CMakeLists antiguo, y el
# CMake 4 de Ubuntu 26.04 dejó de aceptar «cmake_minimum_required» por debajo de
# 3.5. No alcanza con exportar la variable: python-for-android le arma a cada
# receta un entorno propio y lo reemplaza entero. Sí alcanza con este envoltorio,
# porque la receta llama a «cmake» a secas y lo busca en el PATH.
cat > "$ATAJOS/cmake" <<'FIN'
#!/bin/sh
# «cmake --build» y «cmake --version» no aceptan -D, así que la opción se agrega
# solo cuando se está configurando un proyecto.
case "$1" in
    --*) exec /usr/bin/cmake "$@" ;;
esac
exec /usr/bin/cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 "$@"
FIN
chmod +x "$ATAJOS/cmake"
export PATH="$ATAJOS:$PATH"
echo "    «python» apunta a: $(python --version 2>&1)"

echo "==> Copiando el proyecto a $DESTINO"
mkdir -p "$DESTINO"
# Se conservan .buildozer y bin para no volver a descargar el SDK en cada corrida.
find "$DESTINO" -maxdepth 1 -mindepth 1 ! -name .buildozer ! -name bin -exec rm -rf {} +
for archivo in "$ORIGEN"/*; do
    nombre=$(basename "$archivo")
    case "$nombre" in
        .buildozer|bin|__pycache__) continue ;;
    esac
    cp -r "$archivo" "$DESTINO/"
done
rm -rf "$DESTINO/__pycache__" "$DESTINO/pantallas/__pycache__"

# El entorno virtual que arma python-for-android para instalar los paquetes
# puros se corrompe si una construcción se interrumpe a medias, y queda roto
# para siempre. Se borra en cada corrida: recrearlo cuesta segundos.
rm -rf "$DESTINO/.buildozer/android/platform/build-"*/build/venv

# La receta de libjpeg empieza borrando los restos de CMake con «rm -f», que no
# sirve para carpetas. Si una construcción se cortó a la mitad queda una carpeta
# CMakeFiles y la receta falla antes de compilar nada.
rm -rf "$DESTINO/.buildozer/android/platform/build-"*/build/other_builds/jpeg/*/jpeg/CMakeFiles
rm -f  "$DESTINO/.buildozer/android/platform/build-"*/build/other_builds/jpeg/*/jpeg/CMakeCache.txt

REGISTRO="$DESTINO/construccion.log"
echo "==> Construyendo el APK (esto tarda)"
echo "    El registro completo queda en $REGISTRO"
cd "$DESTINO"
# Se guarda todo el registro: cuando algo falla, el motivo suele estar a cientos
# de líneas del final.
if "$PYTHON" -m buildozer android debug > "$REGISTRO" 2>&1; then
    echo
    echo "==> Listo"
    ls -la "$DESTINO/bin/"
else
    echo
    echo "==> Falló. Últimas líneas del registro:"
    sed 's/\x1b\[[0-9;]*m//g' "$REGISTRO" | grep -nE "ERROR|error:|Exception|not a supported|Command failed" | tail -10
    exit 1
fi
