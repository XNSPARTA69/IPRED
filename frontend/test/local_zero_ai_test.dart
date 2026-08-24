import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/services/local_zero_ai_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('🧪 Suite de Pruebas Unitarias Motor Local Zero-AI Offline', () {
    final service = LocalZeroAiService();

    test('1. Almacenamiento y Recuperación de Caché del Estudiante', () async {
      final mockProfile = {
        'codigo_est': 2226666,
        'primer_nombre': 'SANTIAGO',
        'primer_apellido': 'OBREGON',
        'nombre_programa': 'TECNOLOGIA EN REGENCIA DE FARMACIA',
        'nombre_sede': 'BARRANCABERMEJA',
        'grupo': 'NF1',
      };

      final mockSubjects = [
        {
          'codigo_asignatura': '27338',
          'nombre_asignatura': 'FARMACOGNOSIA',
          'grupo': 'NF1',
          'profesor': 'Sidnia Cecilia Rebolledo Sanchez',
          'correo_profesor': 'sidniare@correo.uis.edu.co',
        },
        {
          'codigo_asignatura': '27335',
          'nombre_asignatura': 'SALUD PUBLICA',
          'grupo': 'NE1',
          'profesor': 'Alba Lucia Arciniegas Vargas',
          'correo_profesor': 'malualon@correo.uis.edu.co',
        }
      ];

      final mockSchedule = [
        {
          'codigo_asignatura': '27338',
          'nombre_asignatura': 'FARMACOGNOSIA',
          'grupo': 'NF1',
          'profesor': 'Sidnia Cecilia Rebolledo Sanchez',
          'fecha_tutoria': '2026-08-29',
          'hora_inicio': '10:00:00',
          'hora_fin': '12:00:00',
          'tipo_tutoria': 'Presencial (En Sede)',
        }
      ];

      await service.cacheStudentData(
        profile: mockProfile,
        subjects: mockSubjects,
        schedule: mockSchedule,
      );

      final p = await service.getCachedProfile();
      final s = await service.getCachedSubjects();
      final sch = await service.getCachedSchedule();

      expect(p?['codigo_est'], equals(2226666));
      expect(s.length, equals(2));
      expect(sch.length, equals(1));
    });

    test('2. Consulta de Materias Offline con Códigos y Docentes', () async {
      await service.cacheStudentData(
        profile: {'primer_nombre': 'SANTIAGO', 'nombre_programa': 'TECNOLOGIA EN REGENCIA DE FARMACIA'},
        subjects: [
          {
            'codigo_asignatura': '27338',
            'nombre_asignatura': 'FARMACOGNOSIA',
            'grupo': 'NF1',
            'profesor': 'Sidnia Cecilia Rebolledo Sanchez',
            'correo_profesor': 'sidniare@correo.uis.edu.co',
          }
        ],
      );

      final res = await service.processOfflineQuery('cuales son mis materias');
      expect(res, isNotNull);
      expect(res!['es_ia'], isFalse);
      expect(res['tokens'], equals(0));
      expect(res['respuesta'], contains('FARMACOGNOSIA'));
      expect(res['respuesta'], contains('27338'));
      expect(res['respuesta'], contains('Sidnia Cecilia Rebolledo Sanchez'));
      expect(res['respuesta'], contains('sidniare@correo.uis.edu.co'));
    });

    test('3. Consulta de Horarios y Tutorías Offline', () async {
      await service.cacheStudentData(
        profile: {'primer_nombre': 'SANTIAGO', 'nombre_programa': 'TECNOLOGIA EN REGENCIA DE FARMACIA'},
        schedule: [
          {
            'codigo_asignatura': '27338',
            'nombre_asignatura': 'FARMACOGNOSIA',
            'grupo': 'NF1',
            'profesor': 'Sidnia Cecilia Rebolledo Sanchez',
            'fecha_tutoria': '2026-08-29',
            'hora_inicio': '10:00',
            'hora_fin': '12:00',
            'tipo_tutoria': 'Presencial',
          }
        ],
      );

      final res = await service.processOfflineQuery('mi horario de tutorias');
      expect(res, isNotNull);
      expect(res!['es_ia'], isFalse);
      expect(res['respuesta'], contains('2026-08-29'));
      expect(res['respuesta'], contains('10:00 - 12:00'));
      expect(res['respuesta'], contains('27338'));
    });

    test('4. Trámites Fijos Institucionales Offline', () async {
      // Cancelación
      final resCanc = await service.processOfflineQuery('como cancelar una materia');
      expect(resCanc!['respuesta'], contains('Cancelación de Asignaturas'));
      expect(resCanc['es_ia'], isFalse);

      // Requisitos de Grado
      final resGrad = await service.processOfflineQuery('cuales son los requisitos para grado');
      expect(resGrad!['respuesta'], contains('Requisitos y Modalidades de Grado'));

      // Gratuidad
      final resGrat = await service.processOfflineQuery('tengo politica de gratuidad');
      expect(resGrat!['respuesta'], contains('Política de Gratuidad en la Matrícula'));

      // Moodle AVA
      final resMood = await service.processOfflineQuery('donde ingreso a moodle ava');
      expect(resMood!['respuesta'], contains('Plataforma Moodle AVA IPRED'));

      // Sedes
      final resSede = await service.processOfflineQuery('telefono o correo de la sede barrancabermeja');
      expect(resSede!['respuesta'], contains('Sedes y Canales de Atención'));
    });

    test('5. Guardrails Offline contra Tareas, Matemáticas y Código', () async {
      final resMath = await service.processOfflineQuery('resuelveme esta integral de x al cuadrado');
      expect(resMath!['respuesta'], contains('Mi función es exclusivamente de orientación administrativa'));

      final resCode = await service.processOfflineQuery('hazme un codigo python con algoritmo de ordenamiento');
      expect(resCode!['respuesta'], contains('Mi función es exclusivamente de orientación administrativa'));
    });

    test('6. Saludos y Agradecimientos Offline', () async {
      final resSal = await service.processOfflineQuery('hola buenas tardes');
      expect(resSal!['respuesta'], contains('Modo Sin Conexión'));

      final resThx = await service.processOfflineQuery('muchas gracias por todo');
      expect(resThx!['respuesta'], contains('Con el mayor gusto'));
    });
  });
}
