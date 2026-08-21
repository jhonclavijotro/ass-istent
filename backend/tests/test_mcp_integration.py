import asyncio
import sys
import os
import fitz

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools.notebooklm_mcp import notebooklm_mcp

async def test_notebooklm_mcp_creation():
    print("=== PRUEBA DE CREACIÓN DE CUADERNO ===")
    nb = notebooklm_mcp.create_notebook("Test Notebook MCP")
    print(f"[+] Cuaderno Creado: {nb}")
    assert nb["title"] == "Test Notebook MCP"
    assert nb["notebook_id"].startswith("nb-")

async def test_pdf_extraction_and_cache():
    print("\n=== PRUEBA DE EXTRACCIÓN Y CACHÉ DE PDF ===")
    # Crear un PDF de prueba simple
    test_pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_doc.pdf"))
    
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Este es un parrafo de prueba para validar la extraccion y cache del motor MCP.")
    doc.save(test_pdf_path)
    doc.close()
    
    print(f"[+] PDF de prueba creado en: {test_pdf_path}")
    
    # Extraer y cachear
    extracted_text = notebooklm_mcp.extract_and_cache_text(test_pdf_path)
    print(f"[+] Texto extraído: '{extracted_text.strip()}'")
    assert "extraccion y cache" in extracted_text
    
    # Verificar que se creó el archivo de caché
    filename = os.path.basename(test_pdf_path)
    cache_file = os.path.join(notebooklm_mcp.registry_file.replace("notebooks_registry.json", "extracted_text"), f"{filename}.txt")
    
    # Si estamos corriendo localmente, la ruta podría diferir de la dockerizada, pero la clase la maneja con EXTRACTED_TEXT_DIR
    import app.tools.notebooklm_mcp as mcp_mod
    cache_file_local = os.path.join(mcp_mod.EXTRACTED_TEXT_DIR, f"{filename}.txt")
    
    print(f"[+] Buscando archivo caché en: {cache_file_local}")
    assert os.path.exists(cache_file_local)
    
    with open(cache_file_local, "r", encoding="utf-8") as f:
        cached_content = f.read()
    assert "extraccion y cache" in cached_content
    print("[+] Archivo de caché de texto validado con éxito.")
    
    # Limpieza
    try:
        os.remove(test_pdf_path)
        os.remove(cache_file_local)
    except Exception:
        pass

async def test_query_notebook_fallback():
    print("\n=== PRUEBA DE CONSULTA CON FALLBACK ===")
    nb = notebooklm_mcp.create_notebook("Test Notebook MCP Fallback")
    
    # Agregar una fuente ficticia que existe (usando un archivo temporal txt para simular PDF)
    dummy_pdf = os.path.abspath(os.path.join(os.path.dirname(__file__), "dummy.pdf"))
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "El protocolo MCP define SSE y stdio.")
    doc.save(dummy_pdf)
    doc.close()
    
    notebooklm_mcp.add_source_to_notebook(nb["notebook_id"], dummy_pdf, "dummy.pdf")
    
    # Realizar query. Dado que no hay un servidor MCP corriendo localmente en el puerto 8080 durante este test unitario,
    # debería conmutar a fallback local y ejecutar con éxito.
    print("[+] Realizando consulta al cuaderno (esperando conmutación a fallback)...")
    res = await notebooklm_mcp.query_notebook(nb["notebook_id"], "Explica qué es el protocolo MCP")
    print(f"[+] Proveedor activo: {res.get('provider')}")
    print(f"[+] Respuesta: {res.get('answer')[:120]}...")
    
    assert "provider" in res
    assert "answer" in res
    assert "Fallback" in res["provider"] or "SSE Real" in res["provider"]
    
    try:
        os.remove(dummy_pdf)
        cache_file_local = os.path.join(notebooklm_mcp.registry_file.replace("notebooks_registry.json", "extracted_text"), "dummy.pdf.txt")
        if os.path.exists(cache_file_local):
            os.remove(cache_file_local)
    except Exception:
        pass

async def main():
    await test_notebooklm_mcp_creation()
    await test_pdf_extraction_and_cache()
    await test_query_notebook_fallback()
    print("\n[+] Pruebas de integración de MCP completadas con éxito.")

if __name__ == "__main__":
    asyncio.run(main())
