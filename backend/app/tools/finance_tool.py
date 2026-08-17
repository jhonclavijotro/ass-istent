import os
import csv
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("finance_tool")

FINANZAS_DIR = "/app/data/finanzas" if os.path.exists("/app/data/finanzas") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "finanzas"))

class FinanceManager:
    def __init__(self, dir_path: str = FINANZAS_DIR):
        self.dir_path = dir_path
        os.makedirs(self.dir_path, exist_ok=True)

    def list_financial_files(self) -> List[str]:
        """Lista todos los archivos de finanzas (.csv, .xlsx) en el directorio"""
        files = []
        if os.path.exists(self.dir_path):
            files = [f for f in os.listdir(self.dir_path) if f.endswith(".csv") or f.endswith(".xlsx")]
        return files

    def read_csv_summary(self, filename: str) -> Dict[str, Any]:
        """Lee y genera un resumen cuantitativo de un archivo CSV financiero"""
        if not filename.endswith(".csv"):
            filename += ".csv"
        file_path = os.path.join(self.dir_path, filename)
        if not os.path.exists(file_path):
            return {"error": f"Archivo '{filename}' no encontrado."}

        rows = []
        total_monto = 0.0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for row in reader:
                    rows.append(row)
                    # Intentar sumar valores numéricos si existe columna 'monto' o 'valor'
                    for col in ["monto", "valor", "precio", "amount"]:
                        if col in row and row[col]:
                            try:
                                total_monto += float(row[col].replace("$", "").replace(",", "").strip())
                            except ValueError:
                                pass
            return {
                "file": filename,
                "headers": headers,
                "total_registros": len(rows),
                "suma_detectada": round(total_monto, 2),
                "primeros_registros": rows[:5]
            }
        except Exception as e:
            logger.error(f"Error al leer archivo CSV '{filename}': {e}")
            return {"error": str(e)}

    def add_financial_record(self, filename: str, concepto: str, monto: float, categoria: str = "General") -> bool:
        """Agrega un nuevo registro financiero a un archivo CSV"""
        if not filename.endswith(".csv"):
            filename += ".csv"
        file_path = os.path.join(self.dir_path, filename)
        file_exists = os.path.exists(file_path)
        
        try:
            with open(file_path, "a", newline="", encoding="utf-8") as f:
                fieldnames = ["fecha", "concepto", "monto", "categoria"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    "fecha": os.getenv("CURRENT_DATE", "2026-08-17"),
                    "concepto": concepto,
                    "monto": str(monto),
                    "categoria": categoria
                })
            logger.info(f"Registro financiero agregado a '{filename}': {concepto} - ${monto}")
            return True
        except Exception as e:
            logger.error(f"Error al escribir en archivo financiero '{filename}': {e}")
            return False

finance_manager = FinanceManager()
