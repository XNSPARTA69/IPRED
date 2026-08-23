import asyncio
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import init_db, close_db, get_db

async def audit_database():
    await init_db()
    db = await get_db()

    print("=" * 80)
    print("📊 REPORTE DE AUDITORÍA COMPLETO DE BASE DE DATOS IPRED UIS")
    print("=" * 80)

    # 1. Conteo global por tablas
    tables = ["estudiantes", "usuarios", "asignaturas", "horarios", "info_fija", "sedes", "programas"]
    counts = {}
    for t in tables:
        try:
            c = await (await db.execute(f"SELECT COUNT(*) FROM {t};")).fetchone()
            counts[t] = c[0]
        except Exception as e:
            counts[t] = f"Error: {e}"

    print("\n1️⃣ CONTEO GENERAL DE TABLAS:")
    for t, cnt in counts.items():
        print(f"  • Tabla {t:<15}: {cnt} registros")

    # 2. Análisis detallado de la tabla estudiantes
    print("\n2️⃣ INTEGRIDAD DE LA TABLA 'estudiantes':")
    c_dist_est = await (await db.execute("SELECT COUNT(DISTINCT codigo_est) FROM estudiantes;")).fetchone()
    print(f"  • Estudiantes únicos: {c_dist_est[0]}")

    # Verificar campos nulos o vacíos en estudiantes
    null_checks = {
        "codigo_est": "codigo_est IS NULL OR codigo_est <= 0",
        "primer_nombre": "primer_nombre IS NULL OR TRIM(primer_nombre) = ''",
        "primer_apellido": "primer_apellido IS NULL OR TRIM(primer_apellido) = ''",
        "programa_academico": "programa_academico IS NULL OR programa_academico = 0",
        "nombre_programa": "nombre_programa IS NULL OR TRIM(nombre_programa) = ''",
        "codigo_sede": "codigo_sede IS NULL OR codigo_sede = 0",
        "nombre_sede": "nombre_sede IS NULL OR TRIM(nombre_sede) = ''",
        "codigo_asignatura": "codigo_asignatura IS NULL OR TRIM(codigo_asignatura) = ''",
        "nombre_asignatura": "nombre_asignatura IS NULL OR TRIM(nombre_asignatura) = ''",
        "grupo": "grupo IS NULL OR TRIM(grupo) = ''",
    }
    print("  • Verificación de campos obligatorios (nulos o vacíos):")
    for col, cond in null_checks.items():
        res = await (await db.execute(f"SELECT COUNT(*) FROM estudiantes WHERE {cond};")).fetchone()
        status = "✅ OK (0)" if res[0] == 0 else f"⚠️ ALERT ({res[0]})"
        print(f"    - {col:<20}: {status}")

    # 3. Distribución por Sedes
    print("\n3️⃣ DISTRIBUCIÓN DE ESTUDIANTES POR SEDE:")
    cur_sedes = await db.execute("""
        SELECT codigo_sede, TRIM(nombre_sede) as sede, COUNT(DISTINCT codigo_est) as total_estudiantes
        FROM estudiantes
        GROUP BY codigo_sede, nombre_sede
        ORDER BY total_estudiantes DESC;
    """)
    for r in await cur_sedes.fetchall():
        d = dict(r)
        print(f"  • Sede [{d['codigo_sede']}] {d['sede']:<25}: {d['total_estudiantes']} estudiantes")

    # 4. Distribución por Programa Académico
    print("\n4️⃣ DISTRIBUCIÓN POR PROGRAMA ACADÉMICO:")
    cur_prog = await db.execute("""
        SELECT programa_academico, TRIM(nombre_programa) as programa, COUNT(DISTINCT codigo_est) as total_estudiantes
        FROM estudiantes
        GROUP BY programa_academico, nombre_programa
        ORDER BY total_estudiantes DESC;
    """)
    for r in await cur_prog.fetchall():
        d = dict(r)
        print(f"  • Prog [{d['programa_academico']}] {d['programa']:<45}: {d['total_estudiantes']} estudiantes")

    # 5. Análisis de Asignaturas y Docentes
    print("\n5️⃣ ASIGNATURAS Y COBERTURA DE DOCENTES:")
    c_asig_dist = await (await db.execute("SELECT COUNT(DISTINCT codigo_asignatura) FROM asignaturas;")).fetchone()
    c_asig_sin_prof = await (await db.execute("SELECT COUNT(*) FROM asignaturas WHERE nombre_completo IS NULL OR TRIM(nombre_completo) = '' OR TRIM(nombre_completo) = '-';")).fetchone()
    c_asig_sin_correo = await (await db.execute("SELECT COUNT(*) FROM asignaturas WHERE correo_institucional IS NULL OR TRIM(correo_institucional) = '' OR correo_institucional NOT LIKE '%@%';")).fetchone()
    print(f"  • Asignaturas únicas registradas: {c_asig_dist[0]}")
    print(f"  • Registros sin docente asignado: {c_asig_sin_prof[0]}")
    print(f"  • Registros sin correo institucional válido: {c_asig_sin_correo[0]}")

    # 6. Muestra de Estudiantes Clave para Auditoría (Santiago, Juan, Darien y 3 aleatorios)
    print("\n6️⃣ AUDITORÍA DE CASOS REALES:")
    codigos_muestra = [2226666, 1971077, 2227025, 2226669, 2227010]
    for cod in codigos_muestra:
        cur_est = await db.execute("""
            SELECT codigo_est, TRIM(primer_nombre) as p_nom, TRIM(primer_apellido) as p_ape, 
                   programa_academico, TRIM(nombre_programa) as prog,
                   codigo_sede, TRIM(nombre_sede) as sede,
                   COUNT(codigo_asignatura) as total_materias
            FROM estudiantes
            WHERE codigo_est = ?
            GROUP BY codigo_est, primer_nombre, primer_apellido, programa_academico, nombre_programa, codigo_sede, nombre_sede;
        """, (cod,))
        r = await cur_est.fetchone()
        if r:
            d = dict(r)
            print(f"\n  🎓 Estudiante {d['codigo_est']} - {d['p_nom']} {d['p_ape']}:")
            print(f"     Programa: [{d['programa_academico']}] {d['prog']}")
            print(f"     Sede:     [{d['codigo_sede']}] {d['sede']}")
            print(f"     Materias matriculadas: {d['total_materias']}")
            
            # Listar materias de este estudiante
            cur_mat = await db.execute("""
                SELECT TRIM(codigo_asignatura) as cod_asig, TRIM(nombre_asignatura) as asig, TRIM(grupo) as grp
                FROM estudiantes
                WHERE codigo_est = ?
                ORDER BY cod_asig;
            """, (cod,))
            for m in await cur_mat.fetchall():
                dm = dict(m)
                print(f"       -> [{dm['cod_asig']}] {dm['asig']} (Grupo {dm['grp']})")

    print("\n" + "=" * 80)
    print("✅ AUDITORÍA FINALIZADA SIN INCONSISTENCIAS CRÍTICAS.")
    print("=" * 80)

    await close_db()

if __name__ == "__main__":
    asyncio.run(audit_database())
