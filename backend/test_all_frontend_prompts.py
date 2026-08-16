import asyncio
from app.services.chat_service import chat_service

# Listado exhaustivo de TODOS los botones principales y submenús del frontend
ALL_FRONTEND_PROMPTS = [
    # --- 4 TARJETAS PRINCIPALES DEL HUB ---
    ("Hub 1: Calendario Académico", "¿Cuál es mi calendario académico, próximas tutorías y fechas clave?"),
    ("Hub 2: Mis Tutorías y Clases", "¿Cuándo son mis próximas tutorías y horarios de clase?"),
    ("Hub 3: Mis Materias y Docentes", "¿Cuáles son las materias que tengo matriculadas este semestre?"),
    ("Hub 4: Mis Profesores y Correos", "¿Quiénes son los profesores de mis asignaturas y sus correos?"),

    # --- CATEGORÍA 1: TRÁMITES Y GRADOS ---
    ("Trámites 1: Cancelación Materias/Semestre", "¿Cómo es el proceso oficial para cancelar una materia o el semestre?"),
    ("Trámites 2: Requisitos y Fechas de Grado", "¿Cuáles son los requisitos oficiales y fechas de grado en el IPRED?"),
    ("Trámites 3: Certificados de Notas y Estudio", "¿Cómo solicito un certificado de notas o constancia de estudio?"),
    ("Trámites 4: Paz y Salvo Institucional", "¿Cómo tramitar el paz y salvo institucional UIS?"),
    ("Trámites 5: Homologaciones y Reingresos", "¿Cómo es el trámite de homologación de asignaturas y reingreso?"),
    ("Trámites 6: Incapacidades y Supletorios", "¿Qué debo hacer si falto a una tutoría o evaluación por salud o fuerza mayor?"),

    # --- CATEGORÍA 2: PLATAFORMAS Y ACCESOS TIC ---
    ("TIC 1: Moodle AVA e IPRED TIC", "¿Cómo ingresar al aula virtual Moodle AVA y la plataforma IPRED TIC?"),
    ("TIC 2: Recuperar Clave o Correo UIS", "¿Cómo recuperar mi contraseña del sistema de estudiantes o el correo institucional UIS?"),
    ("TIC 3: Consulta de Calificaciones", "¿Dónde y cómo consulto mis calificaciones parciales y finales?"),
    ("TIC 4: Biblioteca Virtual UIS", "¿Cómo acceder a la Biblioteca Virtual UIS y consultar libros o bases de datos?"),

    # --- CATEGORÍA 3: MATRÍCULA Y BENEFICIOS FINANCIEROS ---
    ("Financiero 1: Descargar Liquidación y Pagos", "¿Cómo descargar mi volante de liquidación de matrícula y qué métodos de pago hay?"),
    ("Financiero 2: Política de Gratuidad", "¿Cuáles son los requisitos y cómo funciona la Política de Gratuidad en la matrícula?"),
    ("Financiero 3: Descuento 10% Votación", "¿Cómo aplicar el descuento del 10% en la matrícula con el certificado electoral?"),

    # --- CATEGORÍA 4: BIENESTAR Y SALUD UIS ---
    ("Bienestar 1: Servicio Médico y Odontológico", "¿Cómo acceder a los servicios de salud y citas médicas en Bienestar UIS?"),
    ("Bienestar 2: Apoyo Psicológico y SEA", "¿Cómo solicitar apoyo psicológico o asesoría académica en el SEA UIS?"),
    ("Bienestar 3: Deportes, Gimnasio y Cultura", "¿Qué actividades deportivas y culturales ofrece Bienestar Universitario UIS?"),
    ("Bienestar 4: Comedor y Apoyos Socioeconómicos", "¿Cuáles son los apoyos socioeconómicos y subsidios de Bienestar UIS?"),

    # --- CATEGORÍA 5: REQUISITO DE INGLÉS Y MODALIDADES GRADO ---
    ("Modalidades 1: Requisito de Inglés (ILS)", "¿Cuál es el requisito de inglés para graduarse en el IPRED y cómo se aprueba?"),
    ("Modalidades 2: Práctica Empresarial y Social", "¿Cuáles son los requisitos para hacer práctica empresarial como opción de grado?"),
    ("Modalidades 3: Proyectos de Investigación y Posgrado", "¿Cómo es la modalidad de proyecto de grado o seminario de actualizacion?"),
    ("Modalidades 4: Pruebas Saber Pro / TyT", "¿Cuándo y cómo debo presentar las pruebas Saber Pro o Saber TyT para grado?"),

    # --- CATEGORÍA 6: REGLAMENTO ESTUDIANTIL Y CALIFICACIONES ---
    ("Reglamento 1: Escala de Notas y Aprobación", "¿Cómo es la escala de calificaciones y con cuánto se aprueba una materia en la UIS?"),
    ("Reglamento 2: Promedio y Matrícula Condicional", "¿Qué pasa si mi promedio baja de 3.2 o pierdo materias en la UIS?"),
    ("Reglamento 3: Habilitaciones y Supletorios", "¿Cómo funcionan las habilitaciones, validaciones y supletorios en la UIS?"),

    # --- CATEGORÍA 7: SEDES REGIONALES ---
    ("Sedes 1: Sedes, Teléfonos y Direcciones", "¿Cuáles son las sedes del IPRED, teléfonos y canales de atención?"),

    # --- CATEGORÍA 8: OFERTA ACADÉMICA IPRED ---
    ("Oferta 1: Todas las Carreras del IPRED", "¿Cuáles son las carreras y programas académicos de pregrado que ofrece el IPRED?"),
    ("Oferta 2: Regencia de Farmacia", "¿Cuáles son los programas académicos y enfoque de Regencia de Farmacia en el IPRED?"),
    ("Oferta 3: Gestión Empresarial", "¿Cuáles son las características del programa de Gestión Empresarial en el IPRED?"),
    ("Oferta 4: Gestión Judicial y Criminalística", "¿De qué trata el programa de Gestión Judicial e Investigación Criminal del IPRED?"),
]

async def audit_all_frontend_prompts():
    print(f"================ AUDITORÍA TOTAL DE PROMPTS FRONTEND ({len(ALL_FRONTEND_PROMPTS)} ÍTEMS) ================")
    user_dict = {"user_id": 2, "username": "2226666"}
    
    zero_ai_count = 0
    gemini_ai_count = 0
    failures = []

    for idx, (title, prompt) in enumerate(ALL_FRONTEND_PROMPTS, 1):
        resp = await chat_service.process_user_message(prompt, user_dict=user_dict)
        tools = resp.herramientas_usadas or []
        tokens = resp.tokens_usados or 0
        is_zero_ai = ("zero_ai_directa" in tools or tokens == 0)
        
        if is_zero_ai:
            zero_ai_count += 1
            status = "✅ ZERO-AI ($0.00 / 0 Tok)"
        else:
            gemini_ai_count += 1
            status = f"❌ GEMINI AI ({tokens} Tok)"
            failures.append((title, prompt, tokens))
            
        print(f"[{idx:02d}/{len(ALL_FRONTEND_PROMPTS):02d}] {title} -> {status}")

    print("\n================ RESUMEN DE LA AUDITORÍA ================")
    print(f"Total Evaluados: {len(ALL_FRONTEND_PROMPTS)}")
    print(f"✅ Zero-AI (0 Tokens): {zero_ai_count} ({zero_ai_count/len(ALL_FRONTEND_PROMPTS)*100:.1f}%)")
    print(f"❌ Gemini AI: {gemini_ai_count} ({gemini_ai_count/len(ALL_FRONTEND_PROMPTS)*100:.1f}%)")

    if failures:
        print("\n⚠️ PROMPTS QUE SE FUERON A GEMINI AI:")
        for t, p, tok in failures:
            print(f"- {t}: '{p}' ({tok} tokens)")

if __name__ == "__main__":
    asyncio.run(audit_all_frontend_prompts())
