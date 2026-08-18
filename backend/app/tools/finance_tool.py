import os
import csv
import logging
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger("finance_tool")

FINANZAS_DIR = "/app/data/finanzas" if os.path.exists("/app/data/finanzas") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "finanzas"))
FINANZAS_CSV = os.path.join(FINANZAS_DIR, "finanzas_db.csv")

VALID_CUENTAS = ["BLB", "BDV"]
VALID_TIPOS = ["ingreso", "egreso"]
VALID_CATEGORIAS = ["comida", "ocio", "casa", "trabajo", "transporte", "otros"]

INITIAL_SEED_RECORDS = [
    {
        "fecha": "14/08/2026",
        "concepto": "Pago de quincena",
        "monto": "2070000.00",
        "cuenta": "BDV",
        "tipo": "ingreso",
        "categoria": "trabajo"
    },
    {
        "fecha": "14/08/2026",
        "concepto": "Pago por insumos de la granja",
        "monto": "300000.00",
        "cuenta": "BDV",
        "tipo": "egreso",
        "categoria": "trabajo"
    }
]

class StructuredFinanceManager:
    def __init__(self, dir_path: str = FINANZAS_DIR):
        self.dir_path = dir_path
        os.makedirs(self.dir_path, exist_ok=True)
        self.db_path = os.path.join(self.dir_path, "finanzas_db.csv")
        self._ensure_seed_data()

    def _ensure_seed_data(self):
        """Inicializa la base de datos CSV con los registros iniciales obligatorios si no existe"""
        if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0:
            try:
                with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                    fieldnames = ["fecha", "concepto", "monto", "cuenta", "tipo", "categoria"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for rec in INITIAL_SEED_RECORDS:
                        writer.writerow(rec)
                logger.info("Base de datos financiera inicializada con registros iniciales por defecto.")
            except Exception as e:
                logger.error(f"Error al inicializar semillas en finanzas_db.csv: {e}")

    def add_transaction(
        self,
        cuenta: str,
        monto: float,
        fecha: str,
        tipo: str,
        categoria: str,
        concepto: str
    ) -> Dict[str, Any]:
        """Agrega una transacción a la base de datos cumpliendo el esquema estricto"""
        cuenta_upper = cuenta.upper().strip()
        if cuenta_upper not in VALID_CUENTAS:
            cuenta_upper = "BDV" if "BDV" in cuenta_upper or "DAVIVIENDA" in cuenta_upper else "BLB"

        tipo_clean = tipo.lower().strip()
        if tipo_clean not in VALID_TIPOS:
            tipo_clean = "ingreso" if "ingreso" in tipo_clean else "egreso"

        cat_clean = categoria.lower().strip()
        if cat_clean not in VALID_CATEGORIAS:
            cat_clean = "otros"

        clean_monto = abs(float(monto))

        record = {
            "fecha": fecha.strip(),
            "concepto": concepto.strip(),
            "monto": f"{clean_monto:.2f}",
            "cuenta": cuenta_upper,
            "tipo": tipo_clean,
            "categoria": cat_clean
        }

        try:
            file_exists = os.path.exists(self.db_path)
            with open(self.db_path, "a", newline="", encoding="utf-8") as f:
                fieldnames = ["fecha", "concepto", "monto", "cuenta", "tipo", "categoria"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(record)
            logger.info(f"Transacción registrada exitosamente: {record}")
            return {"status": "success", "record": record}
        except Exception as e:
            logger.error(f"Error registrando transacción financiera: {e}")
            return {"status": "error", "message": str(e)}

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Calcula el estado de fondos de cada cuenta (BDV, BLB), últimos movimientos y Top 3 movimientos más comunes"""
        self._ensure_seed_data()
        
        records = []
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    records.append(r)
        except Exception as e:
            logger.error(f"Error al leer finanzas_db.csv: {e}")

        saldos = {"BDV": 0.0, "BLB": 0.0}
        total_ingresos = 0.0
        total_egresos = 0.0

        concepto_counter = Counter()
        concepto_amounts = {}
        categoria_counter = Counter()

        parsed_records = []
        for idx, r in enumerate(records):
            cuenta = r.get("cuenta", "BDV").upper()
            tipo = r.get("tipo", "ingreso").lower()
            concepto = r.get("concepto", "Transacción").strip()
            categoria = r.get("categoria", "otros").lower()
            try:
                monto = float(r.get("monto", "0").replace("$", "").replace(",", "").strip())
            except ValueError:
                monto = 0.0

            if tipo == "ingreso":
                saldos[cuenta] = saldos.get(cuenta, 0.0) + monto
                total_ingresos += monto
            else:
                saldos[cuenta] = saldos.get(cuenta, 0.0) - monto
                total_egresos += monto

            # Conteo para Top Movimientos
            concepto_counter[concepto] += 1
            concepto_amounts[concepto] = concepto_amounts.get(concepto, 0.0) + monto
            categoria_counter[categoria] += 1

            parsed_records.append({
                "id": idx,
                "fecha": r.get("fecha", "14/08/2026"),
                "concepto": concepto,
                "monto": round(monto, 2),
                "cuenta": cuenta,
                "cuenta_nombre": "Banco Davivienda" if cuenta == "BDV" else "Bancolombia",
                "tipo": tipo,
                "categoria": categoria
            })

        # Top 3 Movimientos Más Comunes (por frecuencia de concepto / categoría)
        top_conceptos = []
        for conc, freq in concepto_counter.most_common(3):
            top_conceptos.append({
                "concepto": conc,
                "frecuencia": freq,
                "monto_total": round(concepto_amounts.get(conc, 0.0), 2)
            })

        saldo_consolidado = saldos.get("BDV", 0.0) + saldos.get("BLB", 0.0)

        return {
            "saldos_cuentas": {
                "BDV": round(saldos.get("BDV", 0.0), 2),
                "BLB": round(saldos.get("BLB", 0.0), 2),
                "total_consolidado": round(saldo_consolidado, 2)
            },
            "total_ingresos": round(total_ingresos, 2),
            "total_egresos": round(total_egresos, 2),
            "top_3_movimientos": top_conceptos,
            "total_transacciones": len(parsed_records),
            "ultimos_movimientos": list(reversed(parsed_records))
        }

    def update_transaction(
        self,
        record_id: int,
        cuenta: str,
        monto: float,
        fecha: str,
        tipo: str,
        categoria: str,
        concepto: str
    ) -> Dict[str, Any]:
        """Actualiza una transacción existente por su ID (índice)"""
        self._ensure_seed_data()
        records = []
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                records = list(reader)
        except Exception as e:
            return {"status": "error", "message": f"Error leyendo CSV: {e}"}

        if record_id < 0 or record_id >= len(records):
            return {"status": "error", "message": f"Registro con ID {record_id} no encontrado."}

        cuenta_upper = cuenta.upper().strip()
        if cuenta_upper not in VALID_CUENTAS:
            cuenta_upper = "BDV" if "BDV" in cuenta_upper or "DAVIVIENDA" in cuenta_upper else "BLB"

        tipo_clean = tipo.lower().strip()
        if tipo_clean not in VALID_TIPOS:
            tipo_clean = "ingreso" if "ingreso" in tipo_clean else "egreso"

        cat_clean = categoria.lower().strip()
        if cat_clean not in VALID_CATEGORIAS:
            cat_clean = "otros"

        clean_monto = abs(float(monto))

        records[record_id] = {
            "fecha": fecha.strip(),
            "concepto": concepto.strip(),
            "monto": f"{clean_monto:.2f}",
            "cuenta": cuenta_upper,
            "tipo": tipo_clean,
            "categoria": cat_clean
        }

        try:
            fieldnames = ["fecha", "concepto", "monto", "cuenta", "tipo", "categoria"]
            with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)
            logger.info(f"Transacción {record_id} actualizada exitosamente.")
            return {"status": "success", "record": records[record_id]}
        except Exception as e:
            logger.error(f"Error actualizando transacción {record_id}: {e}")
            return {"status": "error", "message": str(e)}

    def delete_transaction(self, record_id: int) -> Dict[str, Any]:
        """Elimina una transacción por su ID (índice)"""
        self._ensure_seed_data()
        records = []
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                records = list(reader)
        except Exception as e:
            return {"status": "error", "message": f"Error leyendo CSV: {e}"}

        if record_id < 0 or record_id >= len(records):
            return {"status": "error", "message": f"Registro con ID {record_id} no encontrado."}

        removed = records.pop(record_id)

        try:
            fieldnames = ["fecha", "concepto", "monto", "cuenta", "tipo", "categoria"]
            with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)
            logger.info(f"Transacción {record_id} eliminada exitosamente.")
            return {"status": "success", "removed_record": removed}
        except Exception as e:
            logger.error(f"Error eliminando transacción {record_id}: {e}")
            return {"status": "error", "message": str(e)}

    # Compatibilidad con métodos anteriores
    def list_financial_files() -> List[str]:
        return ["finanzas_db.csv"]

    def add_financial_record_extended(self, filename="finanzas_db.csv", fecha="14/08/2026", concepto="Pago", monto=0.0, tipo="ingreso", entidad="BDV", categoria="trabajo") -> bool:
        res = self.add_transaction(cuenta=entidad, monto=monto, fecha=fecha, tipo=tipo, categoria=categoria, concepto=concepto)
        return res.get("status") == "success"

    def get_all_balances(self) -> Dict[str, Any]:
        dash = self.get_dashboard_summary()
        return {
            "total_ingresos": dash["total_ingresos"],
            "total_gastos": dash["total_egresos"],
            "saldo_neto": dash["saldos_cuentas"]["total_consolidado"],
            "desglose_cuentas": dash["saldos_cuentas"],
            "total_transacciones": dash["total_transacciones"],
            "ultimas_transacciones": dash["ultimos_movimientos"][:5]
        }

finance_manager = StructuredFinanceManager()

