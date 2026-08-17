import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.gemini_service import gemini_service

async def test_gemini_service():
    print("=== PRUEBA DE SERVICIO GEMINI: ALMACENAMIENTO SEGURO Y MODELOS ===")
    print(f"[+] Modelo activo por defecto: {gemini_service.active_model}")
    print(f"[+] API Key cargada: {'[CONFIGURADA]' if gemini_service.api_key else '[VACÍA]'}")
    
    # Probar cambio de modelo
    gemini_service.set_active_model("gemini-1.5-pro")
    print(f"[+] Modelo actualizado a: {gemini_service.active_model}")
    assert gemini_service.active_model == "gemini-1.5-pro"
    
    # Restaurar modelo preferido
    gemini_service.set_active_model("gemini-2.0-flash")
    print("[+] Servicio Gemini verificado correctamente.")

if __name__ == "__main__":
    asyncio.run(test_gemini_service())
