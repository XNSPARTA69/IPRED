"""
IPRED Chatbot - Servicio de información fija.
Sistema de 4 capas para consultas ultra-baratas (Zero-AI cuando sea posible).
"""

import re
import unicodedata
import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional, List

from app.db.database import get_db
from app.db.repositories.student_repository import student_repo
from app.cache.microcache import info_fija_cache
from app.config import get_colombia_now

logger = logging.getLogger(__name__)

# Micro-caché en memoria RAM L1 para respuestas frecuentes (aislada por usuario/código)
_RAM_CACHE: Dict[str, str] = {}

# Stopwords en español para normalización de preguntas
STOPWORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "en", "por", "para", "con", "sin", "sobre", "entre", "que", "cual", "cuales",
    "como", "donde", "cuando", "es", "son", "fue", "ser", "hay", "tiene",
    "tengo", "mi", "mis", "tu", "su", "sus", "nos", "les", "se", "me", "te",
    "a", "y", "o", "e", "u", "no", "si", "ya", "muy", "mas", "pero",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "yo", "he", "ha", "lo", "le", "queda", "quedan", "hacer", "puedo",
    "pasa", "quiero", "saber", "acerca", "favor", "info", "informacion",
}

# Expansiones de abreviaturas conocidas
ABREVIACIONES = {
    "bcabermeja": "barrancabermeja",
    "bca": "barrancabermeja",
    "b/bermeja": "barrancabermeja",
    "barranca": "barrancabermeja",
    "tel": "telefono",
    "fono": "telefono",
    "cel": "celular",
    "dir": "direccion",
    "prog": "programa",
    "admin": "administracion",
    "tec": "tecnica",
    "tech": "tecnologia",
    "materias": "asignaturas",
    "materia": "asignatura",
    "cancelo": "cancelacion",
    "cancelar": "cancelacion",
}


def normalize_text(text: str) -> str:
    """Normaliza texto: lowercase, sin acentos, sin signos, expandir abreviaturas."""
    # Lowercase
    text = text.lower().strip()
    # Quitar acentos
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Quitar signos de puntuación
    text = re.sub(r"[^\w\s]", " ", text)
    # Normalizar espacios
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_keywords(text: str) -> list[str]:
    """Extrae keywords relevantes de un texto normalizado."""
    normalized = normalize_text(text)
    words = normalized.split()
    # Expandir abreviaturas
    words = [ABREVIACIONES.get(w, w) for w in words]
    # Remover stopwords
    keywords = [w for w in words if w not in STOPWORDS_ES and len(w) > 1]
    return keywords


def build_normalized_key(text: str) -> str:
    """Construye la clave normalizada para la tabla de respuestas directas."""
    keywords = extract_keywords(text)
    # Ordenar para que "telefono sede barranca" == "barranca sede telefono"
    return " ".join(sorted(set(keywords)))


from app.db.repositories.student_repository import StudentRepository
from typing import Optional, Dict, Any, List

def _generar_correo_institucional(nombre_docente: str) -> str:
    """Retorna canal institucional seguro cuando el correo personal del docente no está registrado."""
    return "Coordinación IPRED"


async def _generar_respuesta_materias(codigo_est: int, student_data: Optional[Dict[str, Any]] = None) -> str | None:
    repo = StudentRepository()
    subjects = await repo.get_enrolled_subjects(codigo_est)
    if not subjects:
        return None

    nombre = (student_data.get("primer_nombre") if student_data else "") or "Estudiante"
    programa = (student_data.get("nombre_programa") if student_data else "") or "IPRED - UIS"

    lines = [
        f"Hola, **{nombre}**. Aquí tienes tus asignaturas matriculadas para este semestre en el programa **{programa}**:\n",
        "| Código | Asignatura | Grupo | Docente Asignado | Correo Institucional |",
        "| :---: | :--- | :---: | :--- | :--- |",
    ]

    for s in subjects:
        docente = s.profesor or "Por Asignar"
        correo = s.correo_profesor or "Coordinación IPRED"
        cod = s.codigo_asignatura or "-"
        lines.append(f"| `{cod}` | **{s.nombre_asignatura}** | `{s.grupo}` | {docente} | `{correo}` |")

    lines.append(f"\n📚 *Total asignaturas matriculadas:* **{len(subjects)}**.")
    return "\n".join(lines)


def _describir_modalidad_humana(mod: str) -> str:
    if not mod:
        return "Presencial (En Sede)"
    m = mod.strip().upper()
    if m in ("TP", "P", "PRESENCIAL"):
        return "Presencial (En Sede)"
    elif m in ("AH", "HIBRIDA", "AULA HIBRIDA", "AULA HÍBRIDA"):
        return "Aula Híbrida"
    elif m in ("TR", "REMOTA", "VIRTUAL", "TUTORIA REMOTA", "TUTORÍA REMOTA"):
        return "Virtual (En Vivo)"
    elif m in ("EX", "EV", "EXAMEN", "EVALUACION", "EVALUACIÓN"):
        return "Evaluación Presencial"
    elif m in ("PR", "PRACTICA", "PRÁCTICA"):
        return "Práctica Profesional"
    return mod


async def _generar_respuesta_tutorias(codigo_est: int, student_data: Optional[Dict[str, Any]] = None) -> str | None:
    repo = StudentRepository()
    schedule = await repo.get_student_schedule(codigo_est)
    if not schedule:
        return None

    nombre = (student_data.get("primer_nombre") if student_data else "") or "Estudiante"
    programa = (student_data.get("nombre_programa") if student_data else "") or "IPRED - UIS"
    today_str = get_colombia_now().date().isoformat()

    # Deduplicar por clave (fecha, hora_inicio, codigo_asignatura) conservando nombre de docente más completo
    unique_map = {}
    for s in schedule:
        key = (s.fecha_tutoria, s.hora_inicio, s.codigo_asignatura)
        if key not in unique_map or (len(s.profesor or "") > len(unique_map[key].profesor or "")):
            unique_map[key] = s

    # Filtrar estrictamente sesiones de hoy en adelante (próximas tutorías)
    upcoming = [s for s in unique_map.values() if str(s.fecha_tutoria) >= today_str]
    ordered_sessions = sorted(upcoming if upcoming else unique_map.values(), key=lambda x: (x.fecha_tutoria, x.hora_inicio))
    
    # Tomar las próximas 8 sesiones
    top_sessions = ordered_sessions[:8]

    lines = [
        f"Hola, **{nombre}**. Estas son tus próximas tutorías y actividades programadas en **{programa}**:\n",
        "| Fecha | Horario | Código | Asignatura (Grupo) | Modalidad | Docente | Correo Docente |",
        "| :--- | :---: | :---: | :--- | :---: | :--- | :--- |",
    ]

    for s in top_sessions:
        docente = s.profesor or "Docente IPRED"
        correo = s.correo_profesor or "Coordinación IPRED"
        modalidad = _describir_modalidad_humana(s.tipo_tutoria or "TP")
        cod = s.codigo_asignatura or "-"
        lines.append(f"| `{s.fecha_tutoria}` | `{s.hora_inicio[:5]} - {s.hora_fin[:5]}` | `{cod}` | **{s.nombre_asignatura}** (`{s.grupo}`) | `{modalidad}` | {docente} | `{correo}` |")

    lines.append(f"\n💡 *Mostrando las próximas {len(top_sessions)} sesiones de {len(ordered_sessions)} programadas a partir de hoy.*")
    lines.append("Puedes consultarme por fechas específicas (ej: *'¿Qué clases tengo el 22 de agosto?'*) o por una materia en particular.")
    return "\n".join(lines)


async def _generar_respuesta_profesores(codigo_est: int, student_data: Optional[Dict[str, Any]] = None) -> str | None:
    repo = StudentRepository()
    subjects = await repo.get_enrolled_subjects(codigo_est)
    if not subjects:
        return None

    nombre = (student_data.get("primer_nombre") if student_data else "") or "Estudiante"

    lines = [
        f"Hola, **{nombre}**. Aquí tienes el listado oficial de tus docentes y canales de contacto institucional:\n",
        "| Código | Asignatura | Grupo | Docente Titular | Correo Institucional |",
        "| :---: | :--- | :---: | :--- | :--- |",
    ]

    for s in subjects:
        docente = s.profesor or "Por Asignar"
        correo = s.correo_profesor or "Coordinación IPRED"
        cod = s.codigo_asignatura or "-"
        lines.append(f"| `{cod}` | **{s.nombre_asignatura}** | `{s.grupo}` | {docente} | `{correo}` |")

    lines.append("\n✉️ *Los correos terminados en `@correo.uis.edu.co` corresponden al canal institucional de mensajería docente.*")
    return "\n".join(lines)


async def _generar_respuesta_calendario_academico(codigo_est: int, student_data: Optional[Dict[str, Any]] = None) -> str:
    repo = StudentRepository()
    profile = await repo.get_profile_by_code(codigo_est)
    nombre = profile.nombre_completo if profile else "Estudiante"
    schedules = await repo.get_student_schedule(codigo_est)
    today_str = get_colombia_now().date().isoformat()

    lines = [
        f"### 🗓️ Calendario Académico y Fechas Clave UIS 2026-2",
        f"Estudiante: **{nombre}** | Programa: **{profile.nombre_programa if profile else 'IPRED'}**\n",
        "💡 *Consejo: Puedes consultar horarios por fecha o materia cuando desees.*\n",
        "#### ⏰ Próximas Tutorías más Cercanas:",
        "| Fecha | Horario | Código | Asignatura | Grupo | Docente Titular |",
        "| :--- | :---: | :---: | :--- | :---: | :--- |",
    ]

    if schedules:
        # Filtrar sesiones a partir de hoy
        upcoming_schedules = [s for s in schedules if str(s.fecha_tutoria) >= today_str]
        target_schedules = upcoming_schedules if upcoming_schedules else schedules
        # Mostrar las próximas 5 sesiones más cercanas
        for s in target_schedules[:5]:
            hora = f"{s.hora_inicio[:5]} - {s.hora_fin[:5]}" if s.hora_inicio and s.hora_fin else "Por definir"
            prof = s.profesor or "Docente UIS"
            cod = s.codigo_asignatura or "-"
            lines.append(f"| `{s.fecha_tutoria}` | `{hora}` | `{cod}` | **{s.nombre_asignatura}** | `{s.grupo}` | {prof} |")
    else:
        lines.append("| - | - | - | *No hay sesiones pendientes registradas* | - | - |")

    lines.extend([
        "\n#### 🏛️ Hitos Institucionales del Semestre 2026-2:",
        "* 🚀 **04/Ago/2026:** Inicio oficial de Clases y Tutorías.",
        "* ⚠️ **26/Sep/2026:** Límite para Cancelación de Asignaturas (**Semana 8**).",
        "* 📝 **10/Oct/2026:** Cierre de Evaluaciones de Medio Término (50%).",
        "* 🏁 **21/Nov/2026:** Fin de Periodo Lectivo y Evaluaciones Finales.",
        "* 📊 **28/Nov/2026:** Cierre de Registro de Calificaciones en UISARD (Sistema de Estudiantes).",
        "* 🎓 **11/Dic/2026:** Ceremonia Solemne de Grados Colectivos IPRED.",
    ])

    return "\n".join(lines)


def _generar_respuesta_sedes() -> str:
    return (
        "📍 **Sedes Regionales del IPRED - Universidad Industrial de Santander**\n\n"
        "* 🏢 **Sede Principal Bucaramanga (Campus Central):**\n"
        "  * 📍 **Ubicación:** Cra. 27 Calle 9, Edificio Camilo Torres, Bucaramanga.\n"
        "  * 📞 **Teléfono:** (607) 6344000 / Ext. 1450, 1451, 1452\n"
        "  * ✉️ **Correo:** `ipred@uis.edu.co`\n\n"
        "* 🏢 **Sede Barrancabermeja:**\n"
        "  * 📍 **Ubicación:** Diagonal 56 No. 28-39, Barrio Galán.\n"
        "  * 📞 **Teléfono:** (607) 6222880 / Ext. 101, 102\n"
        "  * ✉️ **Correo:** `sedebarranca@uis.edu.co`\n\n"
        "* 🏢 **Sede Socorro:**\n"
        "  * 📍 **Ubicación:** Calle 4 No. 12-40, Convento San Juan Bautista.\n"
        "  * 📞 **Teléfono:** (607) 7272200 / Ext. 101\n"
        "  * ✉️ **Correo:** `sedesocorro@uis.edu.co`\n\n"
        "* 🏢 **Sede Barbosa:**\n"
        "  * 📍 **Ubicación:** Calle 8 No. 8-40.\n"
        "  * 📞 **Teléfono:** (607) 7485000 / Ext. 102\n"
        "  * ✉️ **Correo:** `sedebarbosa@uis.edu.co`\n\n"
        "* 🏢 **Sede Málaga:**\n"
        "  * 📍 **Ubicación:** Calle 14 No. 5-30.\n"
        "  * 📞 **Teléfono:** (607) 6607212 / Ext. 103\n"
        "  * ✉️ **Correo:** `sedemalaga@uis.edu.co`\n\n"
        "⏰ **Horario de Atención:** Lunes a Viernes de 7:30 a.m. a 12:00 m. y de 2:00 p.m. a 5:30 p.m. Sábados de 8:00 a.m. a 12:00 m."
    )


def _generar_respuesta_cancelacion_materias() -> str:
    return (
        "### 📝 Proceso Oficial de Cancelación de Asignaturas y Semestre\n\n"
        "El trámite se rige por el **Acuerdo No. 072 de 1982** (Reglamento Académico Estudiantil UIS) y se realiza de manera 100% autónoma:\n\n"
        "1. **Acceso al Portal:** Ingresa al [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/) con tu código y contraseña.\n"
        "2. **Módulo de Cancelaciones:** En el menú lateral, dirígete a *Matrícula y Solicitudes Académicas* → *Cancelación de Asignaturas*.\n"
        "3. **Selección y Justificación:** Marca la asignatura que deseas cancelar, ingresa la justificación y haz clic en *Confirmar Cancelación*.\n"
        "4. **Comprobante:** Guarda el número de radicado generado por el sistema como soporte oficial.\n\n"
        "⚠️ **Reglas y Plazos Clave:**\n"
        "* ⏰ **Plazo Límite:** Hasta la **semana 8** del calendario académico ordinario.\n"
        "* 📊 **Créditos Mínimos:** La cancelación no puede dejar tu matrícula por debajo del mínimo de créditos exigidos por el programa.\n"
        "* 🚫 **Cancelación de Matrícula (Semestre Completo):** Se solicita ante el Consejo de Escuela / Dirección del IPRED antes de la semana 10."
    )


def _generar_respuesta_requisitos_grado() -> str:
    return (
        "### 🎓 Requisitos Oficiales de Grado IPRED - UIS\n\n"
        "Para optar al título académico de Tecnólogo o Profesional en el IPRED, debes cumplir con los siguientes requisitos reglamentarios:\n\n"
        "1. ✅ **Aprobación del 100% del Plan de Estudios:** Haber cursado y aprobado todas las asignaturas obligatorias, electivas y prácticas.\n"
        "2. ✅ **Trabajo de Grado / Proyecto Aplicado:** Sustentación y aprobación oficial de la modalidad de grado elegida.\n"
        "3. ✅ **Pruebas de Estado (Saber TyT o Saber Pro):** Haber presentado el examen del ICFES correspondiente y adjuntado el certificado de asistencia.\n"
        "4. ✅ **Paz y Salvo Institucional:** Estar a paz y salvo con Biblioteca, Cartera Financiera, Almacén y Coordinación del IPRED.\n"
        "5. ✅ **Requisito de Idioma Extranjero:** Acreditación del nivel de suficiencia en inglés según la reglamentación del programa.\n"
        "6. 💳 **Derechos de Grado:** Realizar el pago de los derechos de grado dentro de las fechas fijadas en el calendario de grados UIS."
    )


def _generar_respuesta_certificados_notas() -> str:
    return (
        "### 📑 Solicitud de Certificados de Estudio y Calificaciones\n\n"
        "1. 📄 **Polígrafo de Notas (Sin Costo):**\n"
        "   * Ingresa a [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/) → *Consulta de Calificaciones* → *Imprimir Polígrafo*.\n"
        "   * Es gratuito y tiene validez informativa para trámites semestrales.\n\n"
        "2. 📜 **Certificado Oficial de Calificaciones con Firma y Estampilla:**\n"
        "   * **Costo Reglamentado:** **$16.500 COP**.\n"
        "   * **Trámite:** Ingresa a *Servicios Financieros* → *Generar Recibo de Certificado*, cancela en línea por PSE o banco, y descárgalo firmado digitalmente.\n\n"
        "3. 🏛️ **Certificados Especiales ($14.800 / $23.900 COP):**\n"
        "   * Buena conducta, terminación de materias o intensidad horaria se gestionan directamente a través de la Coordinación de tu programa."
    )


def _generar_respuesta_paz_y_salvo() -> str:
    return (
        "### 📜 Paz y Salvo Institucional UIS\n\n"
        "El Paz y Salvo se expide de forma automática y digital a través del sistema institucional:\n\n"
        "1. **Dependencias Involucradas:**\n"
        "   * 📚 **Biblioteca UIS:** No tener libros ni material pendiente de devolución ni multas activas.\n"
        "   * 💰 **División Financiera / Cartera:** No presentar saldos pendientes por matrícula o derechos pecuniarios.\n"
        "   * 🏢 **Coordinación del Programa IPRED:** Entrega de documentos de admisión y soporte de práctica.\n"
        "2. **Consulta en Línea:** Ingresa al [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/) → *Trámites* → *Estado de Paz y Salvo*.\n"
        "3. ✉️ **Dudas o Bloqueos:** Si presentas bloqueo por biblioteca, escribe a `prestamos.biblioteca@uis.edu.co`."
    )


def _generar_respuesta_homologaciones_reingreso() -> str:
    return (
        "### 🔄 Homologaciones, Validaciones y Reingresos\n\n"
        "* 📑 **Homologación de Asignaturas:**\n"
        "  * Aplica para estudiantes que provienen de otros programas UIS o de instituciones de educación superior acreditadas.\n"
        "  * Se debe radicar la solicitud formal adjuntando contenidos programáticos y certificado de notas oficial ante el Comité Asesor del Programa.\n\n"
        "* 🚪 **Reingreso al Programa:**\n"
        "  * Si suspendiste tus estudios y deseas retomarlos, debes solicitar el reingreso en las fechas fijadas en el calendario académico UIS.\n"
        "  * Canal de radicación: `ipred@uis.edu.co` o directamente con la secretaría de tu coordinación."
    )


def _generar_respuesta_fuerza_mayor_salud() -> str:
    return (
        "### ⚖️ Dificultades Académicas, Inasistencias y Evaluaciones Supletorias\n\n"
        "Si presentas dificultades médicas, laborales o de fuerza mayor que te impidan asistir a una tutoría o evaluación presencial:\n\n"
        "1. 📩 **Notificación Inmediata:** Informa al docente titular de la materia antes o dentro de los **5 días hábiles** siguientes al hecho.\n"
        "2. 📑 **Radicación de Soportes:** Envía certificado médico emitido por tu EPS o constancia laboral formal a la coordinación del programa.\n"
        "3. 📝 **Evaluación Supletoria (Art. 56 Reglamento):** Una vez justificada la inasistencia, el docente programará la evaluación supletoria correspondiente sin costo adicional cuando se trate de fuerza mayor comprobada."
    )


def _generar_respuesta_moodle_ava() -> str:
    return (
        "### 🌐 Plataformas Virtuales IPRED TIC y Moodle AVA\n\n"
        "El IPRED cuenta con entornos virtuales oficiales para tus actividades académicas:\n\n"
        "* 💻 **Moodle AVA (Ambiente Virtual de Aprendizaje):**\n"
        "  * 🔗 **Enlace Oficial:** [Plataforma Moodle AVA UIS](https://lms.uis.edu.co/ava/)\n"
        "  * 🔑 **Acceso:** Usuario (tu código de estudiante) y tu contraseña del Sistema de Estudiantes.\n"
        "  * 📚 **Uso:** Entrega de talleres, foros de debate, material de estudio y calificaciones parciales.\n\n"
        "* 🖥️ **Plataforma IPRED TIC v2:**\n"
        "  * 🔗 **Enlace Oficial:** [Plataforma IPRED TIC v2](https://ipredtic.uis.edu.co/plataformaticv2/)\n"
        "  * 📅 **Uso:** Consulta pública de cronogramas, horarios de tutorías, aulas híbridas y guías del programa.\n\n"
        "💡 *Si una materia matriculada no te aparece en Moodle, verifica que tu matrícula financiera esté legalizada en el [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/).*\n"
    )


def _generar_respuesta_recuperar_clave_correo() -> str:
    return (
        "### 🔑 Recuperación de Clave y Correo Institucional UIS\n\n"
        "1. 🔓 **Contraseña del Sistema de Estudiantes (UISARD):**\n"
        "   * Ingresa a: [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/)\n"
        "   * Haz clic en **'Solicitar contraseña'** e ingresa tu código y fecha de nacimiento registrada.\n"
        "   * El sistema enviará un enlace de restablecimiento a tu correo personal registrado.\n\n"
        "2. ✉️ **Acceso al Correo Institucional (`@correo.uis.edu.co`):**\n"
        "   * Si no puedes ingresar a tu cuenta de Google Workspace UIS, escribe a: `admincorreo@correo.uis.edu.co`\n"
        "   * **Datos obligatorios a incluir:** Nombre completo, código de estudiante, documento de identidad escaneado y descripción del inconveniente."
    )


def _generar_respuesta_calificaciones_notas() -> str:
    return (
        "### 📊 Consulta de Calificaciones y Notas en la UIS\n\n"
        "Las calificaciones en el IPRED se gestionan en dos niveles:\n\n"
        "1. 📝 **Calificaciones Parciales (Durante el Semestre):**\n"
        "   * Se consultan en tiempo real dentro de cada materia en [Moodle AVA](https://lms.uis.edu.co/ava/) en la pestaña *Calificaciones*.\n\n"
        "2. 🎓 **Calificaciones Finales y Promedio Acumulado:**\n"
        "   * Se registran en el [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/).\n"
        "   * Puedes generar tu **Polígrafo de Notas** oficial en PDF con promedio ponderado e historial académico completo sin costo."
    )


def _generar_respuesta_biblioteca_virtual() -> str:
    return (
        "### 📖 Biblioteca Virtual UIS y Recursos Digitales\n\n"
        "Como estudiante activo del IPRED tienes acceso 24/7 a la colección científica y bibliográfica de la UIS:\n\n"
        "* 🔗 **Portal Oficial:** [Biblioteca Virtual UIS](https://biblioteca.uis.edu.co/)\n"
        "* 🔑 **Acceso Remoto:** Ingresa con tu usuario y contraseña institucional UIS.\n"
        "* 📚 **Recursos Disponibles:**\n"
        "  * Bases de datos científicas: *Scopus, ScienceDirect, ProQuest, IEEE, SpringerLink*.\n"
        "  * Libros electrónicos completos: *eLibro, Pearson, McGraw-Hill, Digitalia*.\n"
        "  * Repositorio Institucional UIS con trabajos de grado y tesis descargables."
    )


def _generar_respuesta_liquidacion_matricula() -> str:
    return (
        "### 💵 Descarga de Liquidación de Matrícula y Canales de Pago\n\n"
        "1. 📥 **Descargar Recibo de Matrícula:**\n"
        "   * Ingresa a: [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/)\n"
        "   * Dirígete a: *Servicios Financieros* → *Liquidación de Matrícula*.\n"
        "   * Selecciona el periodo académico y genera el volante de pago en formato PDF.\n\n"
        "2. 💳 **Métodos de Pago Autorizados:**\n"
        "   * **Pago Electrónico:** Vía **PSE** directamente desde el portal de estudiantes con tarjeta débito o crédito.\n"
        "   * **Pago en Ventanilla:** En bancos autorizados (*Banco de Bogotá, Davivienda*) presentando el recibo impreso en impresora láser."
    )


def _generar_respuesta_politica_gratuidad() -> str:
    return (
        "### 🏛️ Política de Gratuidad en la Matrícula ('Puedo Estudiar')\n\n"
        "La Política de Gratuidad del Gobierno Nacional y la UIS cubre el **100% del valor de la matrícula neta ordinaria** para estudiantes de pregrado del IPRED.\n\n"
        "📋 **Requisitos para ser Beneficiario:**\n"
        "1. Estar matriculado en un programa académico de pregrado (técnico, tecnológico o universitario) en el IPRED.\n"
        "2. No tener título profesional universitario.\n"
        "3. Pertenecer a los estratos socioeconómicos 1, 2, 3 o estar clasificado en los grupos **A, B o C del Sisbén IV**.\n"
        "4. Cumplir con la nacionalidad colombiana.\n\n"
        "💡 *El beneficio se renueva automáticamente cada semestre siempre que mantengas tu condición académica activa.*"
    )


def _generar_respuesta_oferta_programas() -> str:
    return (
        "### 🎓 Oferta Académica de Pregrado - IPRED UIS\n\n"
        "El Instituto de Proyección Regional y Educación a Distancia (IPRED) ofrece carreras de alta calidad con registro calificado:\n\n"
        "* 💊 **Tecnología en Regencia de Farmacia** (6 semestres - A distancia / Virtual)\n"
        "* 🏢 **Tecnología Empresarial** (6 semestres - A distancia / Virtual)\n"
        "* 💼 **Profesional en Gestión Empresarial** (4 semestres - Ciclo propedéutico profesional)\n"
        "* ⚖️ **Tecnología en Gestión Judicial y Criminalística** (6 semestres)\n"
        "* 🌾 **Técnica Profesional en Producción Agropecuaria** (4 semestres)\n"
        "* ⚙️ **Tecnología Agroindustrial** (6 semestres) / **Administración Agroindustrial** (10 semestres)\n\n"
        "📌 *Inscripciones abiertas semestralmente a través de `https://www.uis.edu.co` sección Admisiones.*"
    )


def _generar_respuesta_farmacia() -> str:
    return (
        "### 💊 Tecnología en Regencia de Farmacia - IPRED UIS\n\n"
        "* 🎓 **Título Otorgado:** Tecnólogo(a) en Regencia de Farmacia.\n"
        "* ⏱️ **Duración:** 6 semestres académicos (Modalidad a Distancia y Virtual).\n"
        "* 🏥 **Campos de Acción:** Dirección técnica de establecimientos farmacéuticos minoristas y mayoristas, dispensación de medicamentos y apoyo en servicios farmacéuticos hospitalarios de baja y mediana complejidad.\n"
        "* 📋 **Registro Calificado:** Programa acreditado de alta calidad por el Ministerio de Educación Nacional."
    )


def _generar_respuesta_gestion_empresarial() -> str:
    return (
        "### 🏢 Gestión Empresarial (Tecnología y Profesional) - IPRED UIS\n\n"
        "* 🎓 **Ciclo 1: Tecnología Empresarial:** 6 semestres (Modalidad a Distancia / Virtual).\n"
        "* 🎓 **Ciclo 2: Profesional en Gestión Empresarial:** 4 semestres adicionales (Ciclo Propedéutico).\n"
        "* 💼 **Enfoque:** Creación de planes de empresa (Plan Emprendedor), administración estratégica, finanzas y gerencia de pymes.\n"
        "* 🌐 **Modalidad:** Tutorías presenciales y virtuales en Bucaramanga y sedes regionales."
    )


def _generar_respuesta_gestion_judicial() -> str:
    return (
        "### ⚖️ Tecnología en Gestión Judicial y Criminalística - IPRED UIS\n\n"
        "* 🎓 **Título Otorgado:** Tecnólogo(a) en Gestión Judicial y Criminalística.\n"
        "* ⏱️ **Duración:** 6 semestres académicos.\n"
        "* 🔍 **Campos de Acción:** Asistencia judicial en juzgados, fiscalías, notarías y defensoría; investigación pericial, cadena de custodia y criminalística de campo."
    )


def _generar_respuesta_salud_bienestar() -> str:
    return (
        "### 🏥 Servicios de Salud y Atención Médica - Bienestar UIS\n\n"
        "Como estudiante activo del IPRED tienes acceso a los servicios de salud universitarios:\n\n"
        "* 🩺 **Medicina General y Odontología:** Consulta externa, prevención y atención primaria en Bucaramanga y sedes regionales.\n"
        "* 🚑 **Póliza Estudiantil de Accidentes (24/7):** Cobertura médica y de urgencias activa durante todo el semestre ante accidentes dentro o fuera de la universidad.\n"
        "* 📅 **Agendamiento de Citas:** A través del portal de Bienestar Universitario (`https://bienestar.uis.edu.co/`) o directamente en la oficina de Bienestar de tu sede.\n"
        "* ✉️ **Contacto:** `bienestar.salud@uis.edu.co`"
    )


def _generar_respuesta_psicologia_sea() -> str:
    return (
        "### 🧠 Apoyo Psicológico y Sistema de Excelencia Académica (SEA)\n\n"
        "La UIS te brinda acompañamiento emocional y académico integral y gratuito:\n\n"
        "* 🛋️ **Acompañamiento Psicológico:** Citas de asesoría psicológica individual y confidencial para manejo de estrés, ansiedad y bienestar emocional.\n"
        "* 📚 **Sistema de Excelencia Académica (SEA):** Tutorías académicas entre pares, talleres de técnicas de estudio y refuerzo en materias críticas.\n"
        "* 🔗 **Solicitud en Línea:** Ingresa a `https://bienestar.uis.edu.co/` sección *Acompañamiento Estudiantil*.\n"
        "* ✉️ **Correos de Atención:** `bienestar.psicologia@uis.edu.co` y `sea@uis.edu.co`"
    )


def _generar_respuesta_deportes_cultura() -> str:
    return (
        "### ⚽ Deportes, Gimnasio y Actividades Culturales UIS\n\n"
        "Bienestar Universitario ofrece formación deportiva y artística gratuita para estudiantes del IPRED:\n\n"
        "* 🏋️ **Infraestructura Deportiva:** Gimnasio, piscina olímpica, canchas de fútbol, tenis y polideportivos en Campus Central y sedes.\n"
        "* 🏆 **Torneos Interfacultades e Intersedes:** Fútbol sala, baloncesto, voleibol, tenis de mesa y atletismo.\n"
        "* 🎭 **Grupos Artísticos:** Danza folclórica y moderna, coro universitario, teatro, música y artes plásticas.\n"
        "* 📌 **Inscripciones:** Abiertas cada inicio de semestre en `https://bienestar.uis.edu.co/`."
    )


def _generar_respuesta_apoyos_alimentacion() -> str:
    return (
        "### 🍲 Subsidios Socioeconómicos y Comedor Estudiantil\n\n"
        "La Dirección de Bienestar Universitario gestiona programas de apoyo económico para estudiantes:\n\n"
        "* 🍛 **Subsidio de Alimentación / Comedor:** Descuento y gratuidad en almuerzos estudiantiles en Bucaramanga y sedes.\n"
        "* 🏠 **Residencias y Auxilios de Alojamiento:** Para estudiantes foráneos de estratos 1 y 2.\n"
        "* 📋 **Requisitos de Postulación:** Pertenecer a estratos 1 o 2, clasificación en Sisbén IV (Grupos A o B) y mantener rendimiento académico.\n"
        "* 📑 **Convocatorias:** Se publican al inicio de cada semestre en los canales oficiales de Trabajo Social UIS."
    )


def _generar_respuesta_requisito_ingles() -> str:
    return (
        "### 🇬🇧 Requisito de Idioma Extranjero (Inglés) para Grado IPRED\n\n"
        "Para optar al título en el IPRED, debes certificar la suficiencia en inglés según tu nivel de formación:\n\n"
        "* 📘 **Nivel Exigido:**\n"
        "  * **Tecnologías:** Nivel **A2 o B1** (según el plan de estudios del programa).\n"
        "  * **Carreras Profesionales:** Nivel **B1 o B2** (Marco Común Europeo).\n\n"
        "* 🎓 **Formas de Cumplimiento:**\n"
        "  1. **Cursos en el Instituto de Lenguas UIS (ILS):** Aprobación de los niveles curriculares.\n"
        "  2. **Examen de Suficiencia ILS:** Presentación del examen oficial interno en la UIS.\n"
        "  3. **Convalidación de Certificados Internacionales:** Presentar examen vigente (*IELTS, TOEFL, Duolingo English Test, Cambridge, MET*).\n\n"
        "* ✉️ **Contacto:** `lenguas@uis.edu.co`"
    )


def _generar_respuesta_practica_empresarial() -> str:
    return (
        "### 🏢 Modalidad de Grado: Práctica Empresarial y Social\n\n"
        "La Práctica Empresarial permite aplicar tus conocimientos en empresas u organizaciones aliadas:\n\n"
        "* 📊 **Requisito Académico:** Haber aprobado como mínimo el **70% u 80% de los créditos** del plan de estudios (según el programa).\n"
        "* 📝 **Convenio Previo:** La empresa debe contar con convenio interinstitucional vigente con la UIS.\n"
        "* 👨‍🏫 **Tutoría:** Se te asigna un docente director de práctica por parte del IPRED y un supervisor en la empresa.\n"
        "* 📄 **Entregables:** Plan de trabajo inicial, informes bimensuales de avance y sustentación final del informe de práctica."
    )


def _generar_respuesta_modalidades_grado() -> str:
    return (
        "### 🔬 Modalidades de Trabajo de Grado en el IPRED\n\n"
        "Los estudiantes de último ciclo pueden optar por cualquiera de las siguientes modalidades reglamentarias:\n\n"
        "1. 📑 **Proyecto de Investigación Aplicada / Monografía:** Desarrollo de un trabajo investigativo con director de tesis.\n"
        "2. 🏢 **Práctica de Extensión o Empresarial:** Desempeño profesional en una organización legalmente constituida.\n"
        "3. 🎓 **Cursos de Posgrado:** Cursar y aprobar asignaturas del primer semestre de una Especialización o Maestría UIS.\n"
        "4. 💡 **Creación de Empresa (Plan Emprendedor):** Estructuración y validación de un plan de negocio innovador.\n"
        "5. 📚 **Seminario de Actualización:** En programas tecnológicos autorizados por el Consejo de Escuela."
    )


def _generar_respuesta_saber_pro_tyt() -> str:
    return (
        "### 📝 Exámenes de Estado Saber Pro y Saber TyT\n\n"
        "La presentación de las pruebas del ICFES es un **requisito de grado de ley obligatorio**:\n\n"
        "* 📋 **¿Cuál te corresponde presentar?**\n"
        "  * **Tecnologías IPRED:** Presentan el examen **Saber TyT** (Técnicos y Tecnólogos).\n"
        "  * **Profesionales IPRED:** Presentan el examen **Saber Pro** (Profesionales Universitarios).\n\n"
        "* 📊 **Requisito UIS:** Haber cursado y aprobado al menos el **75% de los créditos** del plan de estudios.\n"
        "* 📅 **Fechas y Prerregistro:** La UIS publica semestralmente el listado de preregistro institucional en `https://www.uis.edu.co`. Debes cancelar los derechos ante el ICFES en las fechas fijadas."
    )


def _generar_respuesta_escala_notas() -> str:
    return (
        "### 📊 Sistema de Calificación y Escala de Notas UIS\n\n"
        "El sistema de evaluación académica en la UIS se rige por el **Acuerdo No. 072 de 1982**:\n\n"
        "* 📈 **Escala Numérica:** Las calificaciones se asignan de **0.0 a 5.0** (con una cifra decimal).\n"
        "* ✅ **Nota Mínima Aprobatoria:** **3.0** (tres punto cero).\n"
        "* 🧮 **Nota Final:** Es el promedio ponderado de los porcentajes asignados a las evaluaciones parciales, talleres y proyectos acordados en el plan de evaluación de cada asignatura."
    )


def _generar_respuesta_promedio_condicional() -> str:
    return (
        "### ⚠️ Promedio Ponderado, Matrícula Condicional y Pérdida de Cupo\n\n"
        "El reglamento estudiantil UIS establece las siguientes condiciones de permanencia:\n\n"
        "* 📊 **Promedio Mínimo Exigido:** El Promedio Acumulado (P.A.) mínimo para estar en condición regular es **3.2**.\n"
        "* ⚠️ **Matrícula Condicional (P.F.A. < 3.2):** Si en un semestre tu promedio es inferior a 3.2, quedas en condición académica condicional.\n"
        "* 🚫 **Pérdida de Calidad de Estudiante (Pérdida de Cupo):**\n"
        "  * Obtener promedio ponderado semestral inferior a 3.2 en dos semestres consecutivos.\n"
        "  * Promedio acumulado inferior a 3.0 al completar el 50% de la carrera.\n"
        "  * Reprobar una misma asignatura por tercera vez."
    )


def _generar_respuesta_habilitaciones_supletorios() -> str:
    return (
        "### 📝 Exámenes de Habilitación, Validación y Supletorios\n\n"
        "* 🔄 **Examen de Habilitación:**\n"
        "  * Aplica para asignaturas teóricas reprobadas con nota definitiva entre **2.0 y 2.9**.\n"
        "  * No son habilitables las materias prácticas, laboratorios, seminarios ni talleres de grado.\n\n"
        "* 📑 **Validación por Suficiencia:**\n"
        "  * Examen para acreditar conocimientos de una materia sin necesidad de cursarla. Se solicita ante el Comité de Programa.\n\n"
        "* 🩺 **Evaluaciones Supletorias:**\n"
        "  * Se programan cuando el estudiante no pudo asistir a una evaluación por causa médica o de fuerza mayor debidamente soportada antes de 5 días hábiles."
    )


def _generar_respuesta_descuento_electoral() -> str:
    return (
        "### 🗳️ Descuento del 10% por Certificado Electoral\n\n"
        "Por ley de la República (Ley 403 de 1997 y Ley 815 de 2003), los estudiantes tienen derecho a un descuento del **10% sobre el valor de la matrícula neta**:\n\n"
        "1. 📥 **Requisito:** Haber ejercido el voto en las **últimas elecciones ordinarias nacionales** (presidenciales o de congreso).\n"
        "2. 💻 **Procedimiento:** Carga el certificado electoral escaneado en formato PDF en **UISARD (Sistema de Estudiantes)** en las fechas de preregistro de matrícula.\n"
        "3. 💳 **Aplicación:** El descuento se descuenta automáticamente en el volante de liquidación del semestre."
    )


def _generar_respuesta_matricula_materias() -> str:
    return (
        "### 📚 Proceso Oficial de Matrícula e Inscripción de Asignaturas UIS\n\n"
        "El proceso de matrícula en el IPRED se realiza a través de las siguientes etapas:\n\n"
        "1. 📑 **1. Matrícula Financiera (Pago o Gratuidad):**\n"
        "   * Ingresa a: [Sistema de Estudiantes UIS](https://estudiantes.uis.edu.co/)\n"
        "   * Descarga tu volante en *'Servicios Financieros'* → *'Liquidación de Matrícula'*.\n"
        "   * Realiza el pago en línea por **PSE** o en bancos autorizados. Si eres beneficiario de la **Política de Gratuidad ('Puedo Estudiar')**, la liquidación se legaliza automáticamente con valor $0.\n\n"
        "2. 🖥️ **2. Matrícula Académica (Inscripción y Ajuste de Materias):**\n"
        "   * **Estudiantes Antiguos:** En las fechas fijadas en el calendario académico, ingresa a *'Matrícula y Solicitudes Académicas'* → *'Inscripción de Asignaturas'* para seleccionar tus asignaturas y grupos disponibles.\n"
        "   * **Estudiantes Nuevos:** La coordinación del programa matricula automáticamente las asignaturas del primer nivel.\n\n"
        "3. 🔄 **3. Adición y Cambio de Grupos (Semana de Ajustes):**\n"
        "   * Durante la primera semana de clases puedes solicitar adiciones o cambios de grupo en el módulo de ajustes de matrícula en UISARD.\n\n"
        "💡 *Si tienes dudas con cupos o cruces de horario, comunícate con la coordinación de tu programa académico o al correo `ipred@uis.edu.co`.*"
    )


def _generar_respuesta_tramites() -> str:
    return (
        "### 📋 Trámites Académicos y Administrativos IPRED\n\n"
        "Selecciona el trámite de tu interés para obtener la guía detallada:\n\n"
        "* 📚 **Matrícula e Inscripción de Asignaturas:** Proceso financiero, inscripción en línea y ajustes.\n"
        "* 📝 **Cancelación de Asignaturas / Semestre:** Procedimiento, plazos y reglamento.\n"
        "* 🎓 **Requisitos de Grado:** Pruebas Saber Pro, paz y salvos y trabajo de grado.\n"
        "* 📑 **Certificados de Estudio:** Polígrafo sin costo y certificados oficiales con estampilla.\n"
        "* 📜 **Paz y Salvo:** Validación en línea con Biblioteca y Cartera.\n"
        "* 🔄 **Homologaciones y Reingresos:** Trámite ante el Comité de Programa.\n"
        "* ⚖️ **Excusas Médicas / Fuerza Mayor:** Plazos para evaluaciones supletorias."
    )


async def _generar_respuesta_perfil_estudiante(codigo_est: int, student_data: Optional[Dict[str, Any]] = None) -> str:
    repo = StudentRepository()
    profile = await repo.get_profile_by_code(codigo_est)
    if not profile:
        return f"Tu código de estudiante es **{codigo_est}**. Estás autenticado en el sistema institucional del IPRED."

    nom = profile.nombre_completo or "Estudiante"
    prog = profile.nombre_programa or "Programa IPRED"
    sede = profile.nombre_sede or "Bucaramanga (Sede Principal)"
    grp = profile.grupo or "Principal"

    return (
        f"### 👤 Ficha del Estudiante UIS\n\n"
        f"* 🎓 **Nombre:** {nom}\n"
        f"* 🆔 **Código Estudiantil:** `{codigo_est}`\n"
        f"* 📚 **Programa Académico:** **{prog}**\n"
        f"* 📍 **Sede Regional:** {sede}\n"
        f"* 👥 **Grupo Principal:** `{grp}`\n\n"
        f"💡 *Tus datos están sincronizados directamente con el sistema de admisiones y registro UIS.*"
    )


async def buscar_respuesta_directa(
    pregunta: str,
    codigo_est: Optional[int] = None,
    student_data: Optional[Dict[str, Any]] = None,
) -> str | None:
    """
    CAPA 0: Búsqueda por coincidencia exacta y despachador determinista Zero-AI.
    Costo de IA: $0.00 (Zero-AI instantáneo, 0 tokens)
    """
    clean_p = normalize_text(pregunta)
    
    # 0. Interceptor Zero-AI para tareas académicas, programación, matemáticas y temas fuera de contexto (0 tokens)
    es_codigo_institucional = any(
        kw in clean_p for kw in [
            "codigo de la materia", "codigo de materia", "codigo de asignatura",
            "codigo de estudiante", "mi codigo", "codigo est", "codigo uis",
            "codigo de profesor", "codigo de la sede", "codigo postal"
        ]
    )
    
    es_programacion = any(
        re.search(p, clean_p) for p in [
            r"\bpython\b", r"\bjavascript\b", r"\bjava\b", r"\bc\+\+\b", r"\bc#\b", r"\bphp\b", r"\bruby\b",
            r"\bscript\b", r"\bprogramar\b", r"\bprogramacion\b", r"\bhtml\b", r"\bcss\b", r"\bsql\b",
            r"\balgoritmo\b", r"\bhazme un codigo\b", r"\bescribe un codigo\b", r"\bcomo hacer un codigo\b",
            r"\bcodigo de python\b", r"\bcodigo para\b", r"\bfuncion en\b", r"\bhacer un codigo\b"
        ]
    )
    
    es_matematica_ciencias = any(
        re.search(p, clean_p) for p in [
            r"\bmatriz\b", r"\bmatrices\b", r"\bdeterminante\b", r"\bvector\b", r"\bvectores\b",
            r"\bcalcula\b", r"\bcalcular\b", r"\bderivada\b", r"\bintegral\b", r"\becuacion\b",
            r"\btrigonometria\b", r"\bgeometria\b", r"\balgebra\b", r"\barea del\b", r"\bperimetro\b",
            r"\bquimica\b", r"\bfisica\b", r"\bbalanceo\b", r"\btermodinamica\b", r"\bmolecula\b",
            r"\bcuanto es \d+", r"\d+\s*[\+\-\*\/x]\s*\d+"
        ]
    )

    es_tarea_humanidades = any(
        re.search(p, clean_p) for p in [
            r"\bejercicio de\b", r"\btarea de\b", r"\btaller de\b", r"\bparcial resuelto\b",
            r"\bresuelve este\b", r"\bresolver este\b", r"\bresuelve el\b", r"\bresolver el\b",
            r"\bensayo sobre\b", r"\bensayo de\b", r"\bresumen del libro\b", r"\bresumen de la obra\b",
            r"\btraduccion de texto\b", r"\btraduce este texto\b", r"\bque es la celula\b",
            r"\bfotosintesis\b", r"\brevolucion industrial\b", r"\bsegunda guerra mundial\b"
        ]
    )

    es_fuera_de_lugar = any(
        re.search(p, clean_p) for p in [
            r"\breceta\b", r"\bcocinar\b", r"\bcomo hacer arroz\b", r"\bcomo hacer pasta\b", r"\bchiste\b",
            r"\bpartido de futbol\b", r"\bmusica\b", r"\bcancion\b", r"\bletra de\b", r"\bpelicula\b",
            r"\bpoema\b", r"\bcuento\b", r"\bhistoria de terror\b", r"\badivinanza\b",
            r"\bhoroscopo\b", r"\bsigno zodiacal\b", r"\bbitcoin\b", r"\bcriptomoneda\b", r"\bdolar hoy\b", r"\bclima hoy\b"
        ]
    )

    if (es_programacion and not es_codigo_institucional) or es_matematica_ciencias or es_tarea_humanidades or es_fuera_de_lugar:
        logger.info("Capa 0 ZERO-AI HIT: Tarea/Ejercicio/Código/Fuera de contexto declinado en 1 línea.")
        return "Mi función es exclusivamente de orientación administrativa e institucional en el IPRED - UIS (horarios, docentes, trámites, reglamentos y redacción de correos). No estoy habilitado para resolver tareas, operaciones matemáticas ni trabajos académicos."

    # 0.1 Protección contra negaciones o consultas complejas
    if any(neg in clean_p for neg in ["no quiero", "no me muestres", "no ver", "sin mis", "otra cosa", "en vez de", "diferente a"]):
        return None

    # 1. Saludos comunes (Zero-AI)
    greetings = {"hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "que tal", "hola buenas", "hola buenas tardes", "hola buenos dias"}
    is_greeting = (
        clean_p in greetings
        or any(clean_p.startswith(g) for g in ["hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "buen dia"])
        or (len(clean_p.split()) <= 4 and any(g in clean_p for g in ["hola", "buenos dias", "buenas tardes", "buenas noches"]))
    )
    # Si contiene una pregunta específica además del saludo, continuar con los interceptores
    if is_greeting and not any(kw in clean_p for kw in ["materia", "tutor", "profesor", "horario", "cancelar", "grado", "sede", "moodle", "clave", "nota", "portal", "uisard", "biblioteca", "gratuidad"]):
        return (
            "¡Hola! 👋 Soy tu Asistente Virtual IPRED - UIS. ¿En qué te puedo colaborar hoy?\n\n"
            "Puedes consultarme sobre:\n"
            "* 📚 **Tus materias matriculadas y profesores**\n"
            "* ⏰ **Tus próximas tutorías y horarios de clase**\n"
            "* 📑 **Trámites académicos, grados y cancelaciones**\n"
            "* 💻 **Moodle AVA, claves y plataformas TIC**\n"
            "* 🏛️ **Sedes del IPRED, teléfonos y canales de atención**"
        )

    # 2. Despedidas y agradecimientos (Zero-AI)
    thanks_words = ["gracias", "muchas gracias", "mil gracias", "vale gracias", "ok gracias", "chao", "hasta luego", "adios", "buen dia"]
    if any(t in clean_p for t in thanks_words):
        return "¡Con el mayor gusto! 🎓 Siempre a tu disposición en el IPRED - Universidad Industrial de Santander. ¡Muchos éxitos en tu semestre!"

    # 3. Interceptores deterministas Zero-AI

    # A0. Extractor de Entidad: Código de Asignatura específico (ej. "27338" o "materia 27338")
    if codigo_est:
        cod_match = re.search(r"\b(2\d{4}|1\d{4})\b", clean_p)
        if cod_match:
            cod_target = cod_match.group(1)
            sched = await student_repo.get_student_schedule(codigo_est)
            target_sched = [s for s in sched if str(s.codigo_asignatura) == cod_target]
            if target_sched:
                nom = target_sched[0].nombre_asignatura
                today_str = get_colombia_now().date().isoformat()
                future_ts = [s for s in target_sched if str(s.fecha_tutoria) >= today_str]
                disp_sched = future_ts if future_ts else target_sched
                lines = [f"### ⏰ Horario y Tutorías de {nom} (Código: {cod_target})\n"]
                for s in disp_sched:
                    lines.append(f"* **{s.fecha_tutoria}** ({s.hora_inicio[:5]} - {s.hora_fin[:5]}) | Prof: {s.profesor or 'Por asignar'} | *{s.tipo_tutoria or 'Tutoría'}*")
                logger.info("Capa 0 ZERO-AI HIT: Horario de asignatura específica %s", cod_target)
                return "\n".join(lines)
            else:
                # Si el código no está matriculado por este estudiante, responder en Capa 0 de forma limpia
                logger.info("Capa 0 ZERO-AI HIT: Código %s no matriculado por estudiante %d", cod_target, codigo_est)
                return f"La asignatura con código `{cod_target}` no figura matriculada en tu plan de estudios actual del semestre."

    # A1. Botón / Consulta Explícita de Calendario Académico
    if codigo_est and (clean_p in ["calendario academico", "ver calendario", "cronograma institucional", "fechas clave", "calendario", "cual es mi calendario academico proximas tutorias y fechas clave", "calendario academico proximas tutorias y fechas clave"] or clean_p.startswith("cual es mi calendario academico") or clean_p.startswith("cual es el calendario")):
        resp = await _generar_respuesta_calendario_academico(codigo_est, student_data)
        if resp:
            logger.info("Capa 0 ZERO-AI HIT: Calendario Académico para estudiante %d", codigo_est)
            return resp

    # A2. Botón / Consulta Explícita de Mis Materias
    if codigo_est and clean_p in [
        "mis materias", "mis asignaturas", "materias matriculadas", "cuales son mis materias", "que materias tengo", "ver mis materias",
        "cuales son las materias que tengo matriculadas este semestre", "mis materias y docentes", "materias que tengo matriculadas este semestre",
        "materias matriculadas este semestre", "mis materias matriculadas"
    ]:
        resp = await _generar_respuesta_materias(codigo_est, student_data)
        if resp:
            logger.info("Capa 0 ZERO-AI HIT: Mis Materias para estudiante %d", codigo_est)
            return resp

    # A3. Botón / Consulta Explícita de Mis Tutorías / Próximas Clases
    if codigo_est and clean_p in [
        "mis tutorias", "mis horarios", "proximas tutorias", "cuales son mis tutorias", "horario de clases", "cuando son mis tutorias", "ver tutorias", "mi horario",
        "cuando son mis proximas tutorias y horarios de clase", "mis tutorias y clases", "proximas tutorias y horarios de clase",
        "horarios de clase y proximas tutorias", "cuando tengo clases"
    ]:
        resp = await _generar_respuesta_tutorias(codigo_est, student_data)
        if resp:
            logger.info("Capa 0 ZERO-AI HIT: Mis Tutorías para estudiante %d", codigo_est)
            return resp

    # A4. Botón / Consulta Explícita de Mis Profesores
    if codigo_est and clean_p in [
        "mis profesores", "mis docentes", "quienes son mis profesores", "profesores", "docentes", "correos docentes",
        "quienes son los profesores de mis asignaturas y sus correos", "mis profesores y correos", "profesores de mis asignaturas y sus correos",
        "quienes son mis docentes", "docentes y sus correos"
    ]:
        resp = await _generar_respuesta_profesores(codigo_est, student_data)
        if resp:
            logger.info("Capa 0 ZERO-AI HIT: Mis Profesores para estudiante %d", codigo_est)
            return resp

    # A5. Botón / Consulta Explícita de Ficha de Perfil
    if codigo_est and clean_p in ["mi perfil", "quien soy", "mis datos", "ver mi perfil", "ficha estudiantil", "quien soy yo", "mis datos de estudiante"]:
        logger.info("Capa 0 ZERO-AI HIT: Perfil de estudiante %d", codigo_est)
        return await _generar_respuesta_perfil_estudiante(codigo_est, student_data)

    # A6. Botones de Subpreguntas y Preguntas Rápidas del Modal Flutter (Zero-AI instantáneo)
    if clean_p in ["cancelacion de materias o semestre", "como es el proceso oficial para cancelar una materia o el semestre", "cancelar materia", "cancelar semestre", "como cancelo una materia", "cancelar materias"]:
        return _generar_respuesta_cancelacion_materias()

    if clean_p in ["requisitos de grado", "requisitos grado", "como me graduo", "grados ipred", "cuales son los requisitos oficiales y fechas de grado en el ipred", "requisitos y fechas de grado"]:
        return _generar_respuesta_requisitos_grado()

    if clean_p in ["certificados de notas y estudio", "como solicito un certificado de notas o constancia de estudio", "certificados de estudio", "solicitar certificado", "certificado de notas"]:
        return _generar_respuesta_certificados_notas()

    if clean_p in ["paz y salvo institucional", "como tramitar el paz y salvo institucional uis", "paz y salvo uis", "paz y salvo"]:
        return _generar_respuesta_paz_y_salvo()

    if clean_p in ["homologaciones y reingresos", "como es el tramite de homologacion de asignaturas y reingreso", "homologacion", "reingreso"]:
        return _generar_respuesta_homologaciones_reingreso()

    if clean_p in ["incapacidades y supletorios", "que debo hacer si falto a una tutoria o evaluacion por salud o fuerza mayor", "incapacidad", "supletorios"]:
        return _generar_respuesta_fuerza_mayor_salud()

    if clean_p in ["moodle", "moodle ava", "plataforma moodle", "ingreso moodle", "ipred tic", "moodle ava e ipred tic", "como ingresar al aula virtual moodle ava y la plataforma ipred tic"]:
        return _generar_respuesta_moodle_ava()

    if clean_p in ["recuperar clave o correo uis", "como recuperar mi contrasena del sistema de estudiantes o el correo institucional uis", "recuperar clave", "recuperar contrasena", "olvide mi clave"]:
        return _generar_respuesta_recuperar_clave_correo()

    if clean_p in ["consulta de calificaciones", "donde y como consulto mis calificaciones parciales y finales", "donde veo mis notas"]:
        return _generar_respuesta_calificaciones_notas()

    if clean_p in ["biblioteca virtual uis", "como acceder a la biblioteca virtual uis y consultar libros o bases de datos", "biblioteca virtual", "biblioteca uis"]:
        return _generar_respuesta_biblioteca_virtual()

    if clean_p in ["descargar liquidacion y pagos", "como descargar mi volante de liquidacion de matricula y que metodos de pago hay", "liquidacion de matricula", "recibo de matricula", "como pagar la matricula"]:
        return _generar_respuesta_liquidacion_matricula()

    if clean_p in ["politica de gratuidad puedo estudiar", "politica de gratuidad", "puedo estudiar", "cuales son los requisitos y como funciona la politica de gratuidad en la matricula", "matricula cero"]:
        return _generar_respuesta_politica_gratuidad()

    if clean_p in ["descuento del 10 por votacion", "descuento electoral", "descuento por votar", "descuento del 10", "como aplicar el descuento del 10 en la matricula con el certificado electoral"]:
        return _generar_respuesta_descuento_electoral()

    if clean_p in ["servicio medico y odontologico", "como acceder a los servicios de salud y citas medicas en bienestar uis", "citas medicas", "salud bienestar"]:
        return _generar_respuesta_salud_bienestar()

    if clean_p in ["apoyo psicologico y sea", "como solicitar apoyo psicologico o asesoria academica en el sea uis", "apoyo psicologico", "psicologia uis", "sea uis"]:
        return _generar_respuesta_psicologia_sea()

    if clean_p in ["deportes gimnasio y cultura", "que actividades deportivas y culturales ofrece bienestar universitario uis", "gimnasio uis", "deportes uis"]:
        return _generar_respuesta_deportes_cultura()

    if clean_p in ["comedor y apoyos socioeconomicos", "cuales son los apoyos socioeconomicos y subsidios de bienestar uis", "comedor uis", "subsidio de alimentacion"]:
        return _generar_respuesta_apoyos_alimentacion()

    if clean_p in ["requisito de idioma extranjero ils", "cual es el requisito de ingles para graduarse en el ipred y como se aprueba", "requisito de ingles", "nivel de ingles"]:
        return _generar_respuesta_requisito_ingles()

    if clean_p in ["practica empresarial y social", "cuales son los requisitos para hacer practica empresarial como opcion de grado", "practica empresarial"]:
        return _generar_respuesta_practica_empresarial()

    if clean_p in ["proyectos de investigacion y posgrado", "como es la modalidad de proyecto de grado o seminario de actualizacion", "modalidades de grado"]:
        return _generar_respuesta_modalidades_grado()

    if clean_p in ["pruebas de estado saber pro tyt", "pruebas saber pro", "saber tyt", "cuando y como debo presentar las pruebas saber pro o saber tyt para grado"]:
        return _generar_respuesta_saber_pro_tyt()

    if clean_p in ["escala de notas y aprobacion", "como es la escala de calificaciones y con cuanto se aprueba una materia en la uis", "escala de notas", "escala calificaciones", "con cuanto se aprueba", "sistema de calificaciones"]:
        return _generar_respuesta_escala_notas()

    if clean_p in ["promedio y matricula condicional", "que pasa si mi promedio baja de 3 2 o pierdo materias en la uis", "promedio condicional", "perdida de cupo"]:
        return _generar_respuesta_promedio_condicional()

    if clean_p in ["habilitaciones y supletorios", "como funcionan las habilitaciones validaciones y supletorios en la uis", "habilitaciones"]:
        return _generar_respuesta_habilitaciones_supletorios()

    if clean_p in ["sedes regionales", "sedes", "sedes ipred", "sedes uis", "donde estan las sedes", "telefonos sedes", "cuales son las sedes del ipred telefonos y canales de atencion", "sedes telefonos y direcciones"]:
        return _generar_respuesta_sedes()

    if clean_p in ["todas las carreras del ipred", "oferta academica ipred", "oferta academica", "carreras ipred", "cuales son las carreras y programas academicos de pregrado que ofrece el ipred"]:
        return _generar_respuesta_oferta_programas()

    if clean_p in ["regencia de farmacia", "cuales son los programas academicos y enfoque de regencia de farmacia en el ipred"]:
        return _generar_respuesta_farmacia()

    if clean_p in ["gestion empresarial", "cuales son las caracteristicas del programa de gestion empresarial en el ipred"]:
        return _generar_respuesta_gestion_empresarial()

    if clean_p in ["gestion judicial y criminalistica", "de que trata el programa de gestion judicial e investigacion criminal del ipred"]:
        return _generar_respuesta_gestion_judicial()

    if clean_p in ["proceso de matricula", "como matricular materias", "inscripcion de asignaturas"]:
        return _generar_respuesta_matricula_materias()

    # Si la pregunta no coincide exactamente con un botón o prompt oficial, se entrega limpiamente a Gemini AI
    return None


async def buscar_fts5(pregunta: str, limite: int = 3) -> list[dict]:
    """
    CAPA 1: Búsqueda Full-Text en Español sobre PostgreSQL con índices GIN.
    Costo de IA: $0.00 (Zero-AI)
    """
    keywords = extract_keywords(pregunta)
    if not keywords:
        return []

    safe_keywords = [re.sub(r"[^\w]", "", k) for k in keywords if len(re.sub(r"[^\w]", "", k)) > 1]
    if not safe_keywords:
        return []

    db = await get_db()
    ts_query_str = " | ".join(safe_keywords)

    # 1. PostgreSQL Full-Text Search nativo con ranking
    try:
        cursor = await db.execute(
            """SELECT
                id,
                titulo,
                contenido,
                categoria,
                ts_rank(tsv_search, to_tsquery('spanish', ?)) as relevancia
            FROM info_fija
            WHERE tsv_search @@ to_tsquery('spanish', ?) AND activo = true
            ORDER BY relevancia DESC
            LIMIT ?""",
            (ts_query_str, ts_query_str, limite),
        )
        rows = await cursor.fetchall()
        if rows:
            logger.info("Capa 1 PG-FTS: %d resultados para '%s'", len(rows), ts_query_str)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.debug("PG FTS bypass: %s", e)

    # 2. Fallback con Trigramas / LIKE case-insensitive universal
    try:
        cursor = await db.execute(
            """SELECT id, titulo, contenido, categoria, 0.5 as relevancia
               FROM info_fija
               WHERE activo = true AND (LOWER(titulo) LIKE LOWER(?) OR LOWER(contenido) LIKE LOWER(?))
               LIMIT ?""",
            (f"%{safe_keywords[0]}%", f"%{safe_keywords[0]}%", limite),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("FTS fallback error: %s", e)
        return []


async def buscar_por_categoria(
    categoria: str | None = None,
    sede_codigo: str | None = None,
    subcategoria: str | None = None,
) -> list[dict]:
    """Búsqueda directa por categoría y filtros."""
    db = await get_db()
    conditions = ["1=1"]
    params = []

    if categoria:
        conditions.append("categoria = ?")
        params.append(categoria)
    if sede_codigo:
        # sede_codigo doesn't exist in info_fija in new schema, ignore for now
        pass
    if subcategoria:
        conditions.append("subcategoria = ?")
        params.append(subcategoria)

    where_clause = " AND ".join(conditions)
    cursor = await db.execute(
        f"SELECT * FROM info_fija WHERE {where_clause} ORDER BY titulo",
        params,
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def obtener_sedes() -> list[dict]:
    """Devuelve el catálogo de sedes."""
    cache_key = "catalogo_sedes"
    cached = await info_fija_cache.get(cache_key)
    if cached:
        return cached

    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM sedes ORDER BY nombre"
    )
    rows = await cursor.fetchall()
    result = [dict(row) for row in rows]
    await info_fija_cache.set(cache_key, result, ttl=3600)
    return result


async def obtener_programas() -> list[dict]:
    """Devuelve el catálogo de programas."""
    cache_key = "catalogo_programas"
    cached = await info_fija_cache.get(cache_key)
    if cached:
        return cached

    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM programas ORDER BY nombre"
    )
    rows = await cursor.fetchall()
    result = [dict(row) for row in rows]
    await info_fija_cache.set(cache_key, result, ttl=3600)
    return result


async def guardar_respuesta_aprendida(pregunta: str, respuesta: str, categoria: str = "auto") -> None:
    """Guarda una respuesta generada por la IA como atajo para futuras consultas (aprendizaje pasivo)."""
    key = build_normalized_key(pregunta)
    if not key or len(key) < 5:
        return

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO respuestas_directas (pregunta, pregunta_norm, respuesta, categoria, origen)
               VALUES (?, ?, ?, ?, 'auto')
               ON CONFLICT (pregunta_norm) DO NOTHING""",
            (pregunta[:250], key, respuesta, categoria),
        )
        await db.commit()
        logger.info("Respuesta aprendida guardada: '%s'", key)
    except Exception as e:
        logger.warning("Error guardando respuesta aprendida: %s", e)
