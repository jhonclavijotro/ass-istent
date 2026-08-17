#!/bin/bash
# =========================================================================
# Script de Inicialización de Directorios con Permisos Elevados (RPi 5)
# =========================================================================

# Obtener ruta actual de ejecución o usar /AssAntigravity por defecto
BASE_DIR="$(pwd)"
if [ -d "/AssAntigravity" ]; then
    BASE_DIR="/AssAntigravity"
fi

echo "⚡ Creando estructura de directorios en: $BASE_DIR"

# Intentar creación de directorios (con sudo si se requieren permisos elevados)
sudo mkdir -p "$BASE_DIR/data/pdfs"
sudo mkdir -p "$BASE_DIR/data/obsidian"
sudo mkdir -p "$BASE_DIR/data/finanzas"
sudo mkdir -p "$BASE_DIR/dbs"

# Asignar propiedad al usuario actual y permisos totales de lectura/escritura
CURRENT_USER="$(whoami)"
sudo chown -R $CURRENT_USER:$CURRENT_USER "$BASE_DIR/data" "$BASE_DIR/dbs" 2>/dev/null || true
sudo chmod -R 777 "$BASE_DIR/data" "$BASE_DIR/dbs"

echo "✅ Directorios creados e inspeccionados:"
ls -la "$BASE_DIR/data"
