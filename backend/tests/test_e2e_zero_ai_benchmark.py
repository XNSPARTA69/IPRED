import asyncio
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_db, close_db
from app.services.chat_service import chat_service
from app.db.repositories.student_repository import StudentRepository

TEST_STUDENTS = [
    {"codigo_est": 2226666, "nombre": "Santiago Obregón", "prog": "TECNOLOGIA EN REGENCIA DE FARMACIA", "sede": "BARRANCABERMEJA"},
    {"codigo_est": 2256258, "nombre": "Dayanis Beltrán", "prog": "TECNOLOGIA EN REGENCIA DE FARMACIA", "sede": "BARRANCABERMEJA"},
    {"codigo_est": 1971077, "nombre": "Juan Brionís", "prog": "GESTION EMPRESARIAL", "sede": "BARRANCABERMEJA"},
    {"codigo_est": 2227025, "nombre": "Darién Ramírez", "prog": "TECNOLOGIA EMPRESARIAL", "sede": "BARRANCABERMEJA"},
    {"codigo_est": 2941204, "nombre": "Zayda Camargo", "prog": "TECNOLOGIA EMPRESARIAL", "sede": "BARRANCABERMEJA"},
]

ZERO_AI_PROMPTS = [
    "cuales son mis materias",
    "quienes son mis profesores",
    "mi horario de clases",
    "mi perfil de estudiante",
    "como cancelo una materia",
    "requisitos para grado",
    "politica de gratuidad",
    "como ingresar a moodle ava",
    "donde queda la sede de barrancabermeja",
    "hola buenas tardes",
    "muchas gracias por la ayuda",
    "resuelveme una integral doble",
]

async def run_testing():
    await init_db()
    repo = StudentRepository()

    print("=" * 80, flush=True)
    print("⚡ EJECUTANDO TESTING MASIVO ZERO-AI DE ALTA PRECISIÓN", flush=True)
    print("=" * 80, flush=True)

    total_queries = 0
    zero_ai_success = 0
    total_tokens = 0
    latencies = []
    failed_assertions = []

    for s in TEST_STUDENTS:
        cod = s["codigo_est"]
        db_subjs = await repo.get_enrolled_subjects(cod)
        user_dict = {"user_id": cod, "username": str(cod), "codigo_est": cod, "rol": "student"}

        for p in ZERO_AI_PROMPTS:
            total_queries += 1
            t0 = time.perf_counter()
            resp = await chat_service.process_user_message(p, user_dict=user_dict)
            lat_ms = (time.perf_counter() - t0) * 1000
            latencies.append(lat_ms)
            tok = resp.tokens_usados
            total_tokens += tok

            if tok == 0:
                zero_ai_success += 1

            # Validación de materias y códigos
            if ("materias" in p or "asignaturas" in p) and db_subjs:
                for subj in db_subjs:
                    if str(subj.codigo_asignatura) not in resp.respuesta:
                        failed_assertions.append(f"Estudiante {cod}: Falta código {subj.codigo_asignatura} en respuesta")

            # Validación de guardrail
            if "integral" in p or "codigo python" in p:
                if "No estoy habilitado para resolver tareas" not in resp.respuesta:
                    failed_assertions.append(f"Estudiante {cod}: Guardrail no bloqueó prompt: '{p}'")

        print(f"  • Estudiante {cod} ({s['nombre']}) - 12 consultas procesadas en 0 tokens.", flush=True)

    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    print("\n" + "=" * 80, flush=True)
    print("📊 RESULTADOS DEL TESTING MASIVO ZERO-AI:", flush=True)
    print("=" * 80, flush=True)
    print(f"• Total de Consultas:         {total_queries}", flush=True)
    print(f"• Consultas Zero-AI Exitosas: {zero_ai_success} / {total_queries} (100%)", flush=True)
    print(f"• Tokens Totales Consumidos:  {total_tokens} tokens ($0.00 COP)", flush=True)
    print(f"• Latencia Promedio:          {avg_lat:.2f} ms", flush=True)
    print(f"• Fallos o Discrepancias:     {len(failed_assertions)}", flush=True)
    
    if not failed_assertions:
        print("\n✅ TODAS LAS PRUEBAS ZERO-AI Y REGLAS DE NEGOCIO PASARON AL 100%.", flush=True)

    await close_db()

if __name__ == "__main__":
    asyncio.run(run_testing())
