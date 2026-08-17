#!/bin/bash
# =========================================================================
# Script de Inicialización de Directorios Físicos en Raspberry Pi 5
# =========================================================================

echo "⚡ Creando estructura de directorios en /AssAntigravity..."

mkdir -p /AssAntigravity/data/pdfs
mkdir -p /AssAntigravity/data/obsidian
mkdir -p /AssAntigravity/data/finanzas
mkdir -p /AssAntigravity/dbs/qdrant_storage

# Asignar permisos amplios para evitar conflictos de usuario entre host y contenedor Docker
chmod -R 777 /AssAntigravity/data
chmod -R 777 /AssAntigravity/dbs

echo "✅ Directorios creados exitosamente en /AssAntigravity:"
ls -la /AssAntigravity/data
