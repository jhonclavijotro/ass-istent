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

    def add_financial_record_extended(
        self,
        filename: str = "Registro_Financiero.csv",
        fecha: str = "2026-08-14",
        concepto: str = "Ingreso",
        monto: float = 0.0,
        tipo: str = "Ingreso",
        entidad: str = "Davivienda",
        categoria: str = "Salario"
    ) -> bool:
        """Agrega un registro financiero completo a un archivo CSV"""
        if not filename.endswith(".csv"):
            filename += ".csv"
        file_path = os.path.join(self.dir_path, filename)
        file_exists = os.path.exists(file_path)
        
        try:
            with open(file_path, "a", newline="", encoding="utf-8") as f:
                fieldnames = ["fecha", "concepto", "monto", "tipo", "entidad", "categoria"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    "fecha": fecha,
                    "concepto": concepto,
                    "monto": f"{monto:.2f}",
                    "tipo": tipo,
                    "entidad": entidad,
                    "categoria": categoria
                })
            logger.info(f"Registro financiero agregado a '{filename}': {concepto} - ${monto} ({entidad})")
            return True
        except Exception as e:
            logger.error(f"Error al escribir en archivo financiero '{filename}': {e}")
            return False

    def add_financial_record(self, filename: str, concepto: str, monto: float, categoria: str = "General") -> bool:
        return self.add_financial_record_extended(filename=filename, fecha="2026-08-17", concepto=concepto, monto=monto, tipo="Ingreso" if monto>=0 else "Gasto", entidad="General", categoria=categoria)

    def get_all_balances(self) -> Dict[str, Any]:
        """Calcula el saldo consolidado leyendo todos los archivos CSV de finanzas"""
        files = self.list_financial_files()
        total_ingresos = 0.0
        total_gastos = 0.0
        registros = []
        cuentas = {}

        for f in files:
            if not f.endswith(".csv"): continue
            path = os.path.join(self.dir_path, f)
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    reader = csv.DictReader(fp)
                    for r in reader:
                        m_str = r.get("monto", "0").replace("$", "").replace(",", "").strip()
                        try:
                            val = float(m_str)
                        except ValueError:
                            val = 0.0

                        tipo = r.get("tipo", "").capitalize()
                        entidad = r.get("entidad", "Davivienda").capitalize()
                        if not tipo:
                            tipo = "Ingreso" if val >= 0 else "Gasto"
                            val = abs(val)

                        if tipo == "Ingreso":
                            total_ingresos += val
                            cuentas[entidad] = cuentas.get(entidad, 0.0) + val
                        else:
                            total_gastos += val
                            cuentas[entidad] = cuentas.get(entidad, 0.0) - val

                        registros.append(r)
            except Exception as e:
                logger.error(f"Error procesando '{f}': {e}")

        saldo_neto = total_ingresos - total_gastos
        return {
            "total_ingresos": round(total_ingresos, 2),
            "total_gastos": round(total_gastos, 2),
            "saldo_neto": round(saldo_neto, 2),
            "desglose_cuentas": cuentas,
            "total_transacciones": len(registros),
            "ultimas_transacciones": registros[-5:]
        }

finance_manager = FinanceManager()
