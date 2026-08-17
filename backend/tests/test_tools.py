import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools.obsidian_tool import obsidian_manager
from app.tools.finance_tool import finance_manager
from app.tools.pdf_watchdog import pdf_watchdog_service
from app.tools.google_workspace import google_workspace_manager

def test_obsidian_tool():
    print("=== PRUEBA DE HERRAMIENTA OBSIDIAN ===")
    test_note = "Prueba_Sistema.md"
    content = "# Nota de Prueba\nCreada durante la validación de la Fase 4."
    
    ok = obsidian_manager.create_or_update_note(test_note, content)
    print(f"[+] Creación de Nota '{test_note}': {ok}")
    assert ok
    
    notes = obsidian_manager.list_notes()
    print(f"[+] Notas en la Bóveda: {notes}")
    assert test_note in notes
    
    read_text = obsidian_manager.get_note_content(test_note)
    print(f"[+] Contenido Leído: {read_text[:50]}...")
    assert "Nota de Prueba" in read_text

def test_finance_tool():
    print("\n=== PRUEBA DE HERRAMIENTA FINANZAS ===")
    test_file = "presupuesto_test.csv"
    ok = finance_manager.add_financial_record(test_file, "Servicios Cloud", 45.50, "Infraestructura")
    print(f"[+] Registro Financiero Creado: {ok}")
    assert ok
    
    summary = finance_manager.read_csv_summary(test_file)
    print(f"[+] Resumen CSV: {summary}")
    assert summary["total_registros"] >= 1

def test_google_workspace_tool():
    print("\n=== PRUEBA DE HERRAMIENTA GOOGLE WORKSPACE ===")
    status = google_workspace_manager.is_authenticated
    print(f"[+] Estado de Autenticación OAuth Google: {'[AUTENTICADO]' if status else '[PENDIENTE AUTH]'}")
    events = google_workspace_manager.list_calendar_events()
    print(f"[+] Eventos de Calendario: {events if status else 'Requiere Auth'}")

if __name__ == "__main__":
    test_obsidian_tool()
    test_finance_tool()
    test_google_workspace_tool()
    print("\n[+] Todas las herramientas de la Fase 4 probadas con éxito.")
