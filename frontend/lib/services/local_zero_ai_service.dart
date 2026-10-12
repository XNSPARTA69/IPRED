import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Motor local determinista Zero-AI para funcionamiento offline (sin conexión a internet).
/// Empaqueta las reglas institucionales del IPRED, trámites fijos y la caché de asignaturas y horarios.
class LocalZeroAiService {
  static final LocalZeroAiService _instance = LocalZeroAiService._internal();
  factory LocalZeroAiService() => _instance;
  LocalZeroAiService._internal();

  static const String _kOfflineProfileKey = 'offline_student_profile';
  static const String _kOfflineSubjectsKey = 'offline_student_subjects';
  static const String _kOfflineScheduleKey = 'offline_student_schedule';

  /// Guarda en almacenamiento local los datos del estudiante autenticado para uso offline.
  Future<void> cacheStudentData({
    required Map<String, dynamic> profile,
    List<dynamic>? subjects,
    List<dynamic>? schedule,
  }) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kOfflineProfileKey, jsonEncode(profile));
      if (subjects != null) {
        await prefs.setString(_kOfflineSubjectsKey, jsonEncode(subjects));
      }
      if (schedule != null) {
        await prefs.setString(_kOfflineScheduleKey, jsonEncode(schedule));
      }
      debugPrint('⚡ [Zero-AI Offline] Datos del estudiante cacheados exitosamente.');
    } catch (e) {
      debugPrint('⚠️ [Zero-AI Offline] Error guardando caché local: $e');
    }
  }

  /// Recupera los datos locales guardados.
  Future<Map<String, dynamic>?> getCachedProfile() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString(_kOfflineProfileKey);
      if (str != null && str.isNotEmpty) {
        return jsonDecode(str) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  Future<List<dynamic>> getCachedSubjects() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString(_kOfflineSubjectsKey);
      if (str != null && str.isNotEmpty) {
        return jsonDecode(str) as List<dynamic>;
      }
    } catch (_) {}
    return [];
  }

  Future<List<dynamic>> getCachedSchedule() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString(_kOfflineScheduleKey);
      if (str != null && str.isNotEmpty) {
        return jsonDecode(str) as List<dynamic>;
      }
    } catch (_) {}
    return [];
  }

  /// Normaliza el texto de entrada (minúsculas, sin tildes, sin signos especiales).
  static String normalize(String text) {
    var s = text.toLowerCase().trim();
    s = s.replaceAll(RegExp(r'[áàäâ]'), 'a');
    s = s.replaceAll(RegExp(r'[éèëê]'), 'e');
    s = s.replaceAll(RegExp(r'[íìïî]'), 'i');
    s = s.replaceAll(RegExp(r'[óòöô]'), 'o');
    s = s.replaceAll(RegExp(r'[úùüû]'), 'u');
    s = s.replaceAll(RegExp(r'[^\w\s]'), ' ');
    s = s.replaceAll(RegExp(r'\s+'), ' ').trim();
    return s;
  }

  /// Procesa la consulta localmente cuando no hay conexión.
  /// Retorna un mapa con { 'respuesta': String, 'es_ia': false, 'herramientas': [] } o null si requiere conexión.
  Future<Map<String, dynamic>?> processOfflineQuery(String message) async {
    final clean = normalize(message);
    if (clean.isEmpty) return null;

    final profile = await getCachedProfile();
    final subjects = await getCachedSubjects();
    final schedule = await getCachedSchedule();

    final nombre = profile?['primer_nombre'] ?? profile?['nombre'] ?? 'Estudiante';
    final programa = profile?['nombre_programa'] ?? profile?['programa'] ?? 'IPRED - UIS';

    // 0. Guardrails estrictos contra tareas y código (Zero-AI Offline)
    final regexTareas = RegExp(r'\b(codigo python|algoritmo|java|matriz|integral|derivada|ecuacion|ensayo de|resumen de la obra|resuelveme)\b');
    if (regexTareas.hasMatch(clean) && !clean.contains('codigo de')) {
      return {
        'respuesta': 'Mi función es exclusivamente de orientación administrativa e institucional en el IPRED - UIS (horarios, docentes, trámites, reglamentos y redacción de correos). No estoy habilitado para resolver tareas, operaciones matemáticas ni trabajos académicos.',
        'es_ia': false,
        'herramientas': ['guardrail_offline_zero_ai'],
        'tokens': 0,
      };
    }

    // 1. Saludos
    if (RegExp(r'^(hola|buenos dias|buenas tardes|buenas noches|saludos|que tal)$').hasMatch(clean) ||
        (clean.startsWith('hola') && clean.split(' ').length <= 4)) {
      return {
        'respuesta': '¡Hola! 👋 Soy tu Asistente Virtual IPRED - UIS *(Modo Sin Conexión)*.\n\n'
            'Estando offline puedo ayudarte con:\n'
            '* 📚 **Tus materias matriculadas y profesores guardados**\n'
            '* ⏰ **Tus horarios de clases y tutorías guardados**\n'
            '* 📑 **Información de trámites, cancelaciones y requisitos de grado**\n'
            '* 🏛️ **Teléfonos y correos de sedes y coordinaciones**',
        'es_ia': false,
        'herramientas': ['saludo_offline'],
        'tokens': 0,
      };
    }

    // 2. Agradecimientos y despedidas
    if (RegExp(r'\b(gracias|muchas gracias|mil gracias|chao|hasta luego|adios)\b').hasMatch(clean)) {
      return {
        'respuesta': '¡Con el mayor gusto! 🎓 Siempre a tu disposición en el IPRED - Universidad Industrial de Santander. ¡Muchos éxitos!',
        'es_ia': false,
        'herramientas': ['despedida_offline'],
        'tokens': 0,
      };
    }

    // 3. Materias / Asignaturas matriculadas
    if (RegExp(r'\b(materias?|asignaturas?|mis clases|que veo|carga academica)\b').hasMatch(clean) &&
        !clean.contains('cancel') && !clean.contains('inscrib')) {
      if (subjects.isNotEmpty) {
        final buffer = StringBuffer();
        buffer.writeln('Hola, **$nombre**. Aquí tienes tus asignaturas matriculadas para este semestre en **$programa**:\n');
        buffer.writeln('| Código | Asignatura | Grupo | Docente Asignado | Correo Institucional |');
        buffer.writeln('| :---: | :--- | :---: | :--- | :--- |');
        for (final s in subjects) {
          final cod = s['codigo_asignatura'] ?? '-';
          final asig = s['nombre_asignatura'] ?? 'Asignatura';
          final grp = s['grupo'] ?? 'A1';
          final prof = s['profesor'] ?? 'Docente Titular UIS';
          final correo = s['correo_profesor'] ?? 'Coordinación IPRED';
          buffer.writeln('| `$cod` | **$asig** | `$grp` | $prof | `$correo` |');
        }
        buffer.writeln('\n📚 *Total asignaturas matriculadas:* **${subjects.length}**.');
        return {
          'respuesta': buffer.toString(),
          'es_ia': false,
          'herramientas': ['materias_offline'],
          'tokens': 0,
        };
      }
    }

    // 4. Profesores y Docentes
    if (RegExp(r'\b(profesores?|docentes?|tutores?|contactos? docentes?)\b').hasMatch(clean)) {
      if (subjects.isNotEmpty) {
        final buffer = StringBuffer();
        buffer.writeln('Hola, **$nombre**. Aquí tienes el listado oficial de tus docentes y canales de contacto:\n');
        buffer.writeln('| Código | Asignatura | Grupo | Docente Titular | Correo Institucional |');
        buffer.writeln('| :---: | :--- | :---: | :--- | :--- |');
        for (final s in subjects) {
          final cod = s['codigo_asignatura'] ?? '-';
          final asig = s['nombre_asignatura'] ?? 'Asignatura';
          final grp = s['grupo'] ?? 'A1';
          final prof = s['profesor'] ?? 'Docente Titular UIS';
          final correo = s['correo_profesor'] ?? 'Coordinación IPRED';
          buffer.writeln('| `$cod` | **$asig** | `$grp` | $prof | `$correo` |');
        }
        buffer.writeln('\n✉️ *Los correos institucionales terminados en `@correo.uis.edu.co` corresponden al canal oficial.*');
        return {
          'respuesta': buffer.toString(),
          'es_ia': false,
          'herramientas': ['profesores_offline'],
          'tokens': 0,
        };
      }
    }

    // 5. Horarios y Tutorías
    if (RegExp(r'\b(horarios?|tutorias?|cuando tengo clase|clases programadas)\b').hasMatch(clean)) {
      if (schedule.isNotEmpty) {
        final buffer = StringBuffer();
        buffer.writeln('Hola, **$nombre**. Estas son tus próximas tutorías y actividades programadas en **$programa**:\n');
        buffer.writeln('| Fecha | Horario | Código | Asignatura (Grupo) | Modalidad | Docente |');
        buffer.writeln('| :--- | :---: | :---: | :--- | :---: | :--- |');
        for (final h in schedule.take(8)) {
          final cod = h['codigo_asignatura'] ?? '-';
          final asig = h['nombre_asignatura'] ?? 'Tutoría';
          final grp = h['grupo'] ?? 'A1';
          final fecha = h['fecha_tutoria'] ?? '-';
          final ini = (h['hora_inicio'] ?? '').toString().length >= 5 ? h['hora_inicio'].toString().substring(0, 5) : h['hora_inicio'];
          final fin = (h['hora_fin'] ?? '').toString().length >= 5 ? h['hora_fin'].toString().substring(0, 5) : h['hora_fin'];
          final mod = h['tipo_tutoria'] ?? 'Presencial';
          final prof = h['profesor'] ?? 'Docente IPRED';
          buffer.writeln('| `$fecha` | `$ini - $fin` | `$cod` | **$asig** (`$grp`) | `$mod` | $prof |');
        }
        buffer.writeln('\n💡 *Mostrando sesiones disponibles en la memoria de tu dispositivo.*');
        return {
          'respuesta': buffer.toString(),
          'es_ia': false,
          'herramientas': ['horarios_offline'],
          'tokens': 0,
        };
      }
    }

    // 6. Trámites Fijos Institucionales (Markdown precargado)
    if (clean.contains('cancel') && (clean.contains('materia') || clean.contains('semestre') || clean.contains('asignatura'))) {
      return {
        'respuesta': '### 📝 Cancelación de Asignaturas - IPRED UIS\n\n'
            '* ⏱️ **Plazo Reglamentario:** La cancelación se realiza a través del Sistema de Estudiantes dentro de las semanas estipuladas en el Calendario Académico oficial.\n'
            '* 📄 **Requisitos:**\n'
            '  1. No quedar con menos del mínimo de créditos permitidos.\n'
            '  2. Estar al día académica y financieramente.\n'
            '* 🌐 **Procedimiento:** Ingresa a [Sistema de Estudiantes](https://estudiantes.uis.edu.co/), módulo *Trámites Académicos -> Cancelación de Asignaturas*.',
        'es_ia': false,
        'herramientas': ['tramites_offline'],
        'tokens': 0,
      };
    }

    if (clean.contains('grado') && (clean.contains('requisito') || clean.contains('opcion') || clean.contains('modalidad'))) {
      return {
        'respuesta': '### 🎓 Requisitos y Modalidades de Grado - IPRED UIS\n\n'
            '* 📋 **Requisitos Generales:**\n'
            '  1. Haber cursado y aprobado el 100% de créditos del plan de estudios.\n'
            '  2. Cumplir con el requisito de lengua extranjera (Inglés reglamentado).\n'
            '  3. Presentar prueba Saber Pro / Saber TyT.\n'
            '  4. Aprobar la modalidad de grado establecida (Monografía, Proyecto de Emprendimiento, Práctica o Asignaturas de Posgrado).\n'
            '  5. Estar a Paz y Salvo académico, financiero y de biblioteca.',
        'es_ia': false,
        'herramientas': ['grados_offline'],
        'tokens': 0,
      };
    }

    if (clean.contains('gratuidad') || clean.contains('matricula cero')) {
      return {
        'respuesta': '### 🏛️ Política de Gratuidad en la Matrícula ("Puedo Estudiar")\n\n'
            '* Cubre el **100% del valor de la matrícula neta ordinaria** para estudiantes de pregrado en estratos socioeconómicos 1, 2 o 3 o Sisbén IV (grupos A, B o C).\n'
            '* Se renueva automáticamente cada semestre si el estudiante conserva su condición académica activa.',
        'es_ia': false,
        'herramientas': ['gratuidad_offline'],
        'tokens': 0,
      };
    }

    if (clean.contains('moodle') || clean.contains('ava') || clean.contains('plataforma')) {
      return {
        'respuesta': '### 💻 Plataforma Moodle AVA IPRED\n\n'
            '* 🔗 **Enlace Oficial:** [Moodle AVA UIS](https://lms.uis.edu.co/ava/)\n'
            '* 🔑 **Usuario:** Tu código de estudiante o correo institucional (`@correo.uis.edu.co`).\n'
            '* 🛡️ **Soporte Técnico:** `admincorreo@correo.uis.edu.co` o coordinación de tu programa.',
        'es_ia': false,
        'herramientas': ['moodle_offline'],
        'tokens': 0,
      };
    }

    if (clean.contains('sede') || clean.contains('telefono') || clean.contains('contacto') || clean.contains('correo ipred')) {
      return {
        'respuesta': '### 🏛️ Sedes y Canales de Atención IPRED UIS\n\n'
            '* 📍 **Dirección General IPRED:** Edificio Administrativo II, Campus Central Bucaramanga. Tel: (607) 6344000 Ext. 1397, 2612. Correo: `ipred@uis.edu.co`\n'
            '* 📍 **Sede Barrancabermeja:** Correo: `regenciadefarmacia@uis.edu.co` / `estudiantesipred@uis.edu.co`\n'
            '* 📍 **Sede El Carmen de Chucurí / San Vicente / Socorro / Málaga / Barbosa / Puerto Wilches.**',
        'es_ia': false,
        'herramientas': ['sedes_offline'],
        'tokens': 0,
      };
    }

    // Si es una consulta compleja fuera de las plantillas Zero-AI, retornar mensaje claro
    return {
      'respuesta': '⚠️ **Estás en modo sin conexión a internet.**\n\n'
          'Puedo mostrarte tus materias, profesores, horarios y reglamentos guardados en tu dispositivo. Para consultas personalizadas avanzadas o búsqueda con Inteligencia Artificial, conéctate a una red Wi-Fi o datos móviles.',
      'es_ia': false,
      'herramientas': ['offline_unsupported'],
      'tokens': 0,
    };
  }
}
