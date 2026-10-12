import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/voice_service.dart';

void main() {
  group('🧪 Pruebas Unitarias de Sanitizador de Voz (VoiceService)', () {
    test('1. Limpieza de tablas markdown y formato', () {
      const input = '''
### Horario de Clases
| Asignatura | Horario | Aula |
| --- | --- | --- |
| Cálculo | 07:00 AM | 201 |
''';
      final clean = VoiceService.sanitizeTextForSpeech(input);
      expect(clean.contains('|'), isFalse);
      expect(clean.contains('###'), isFalse);
      expect(clean.contains('Horario de Clases'), isTrue);
    });

    test('2. Limpieza de enlaces Markdown y Emojis', () {
      const input = '📌 Puedes revisar la [Plataforma TIC](https://ipredtic.uis.edu.co) para tu matrícula 🚀';
      final clean = VoiceService.sanitizeTextForSpeech(input);
      expect(clean.contains('https://'), isFalse);
      expect(clean.contains('Plataforma Tic'), isTrue);
      expect(clean.contains('📌'), isFalse);
      expect(clean.contains('🚀'), isFalse);
    });

    test('3. Limpieza de asteriscos y negritas', () {
      const input = 'Tu clase de **Programación Orientada a Objetos** es el *Sábado* a las 8:00 AM.';
      final clean = VoiceService.sanitizeTextForSpeech(input);
      expect(clean.contains('**'), isFalse);
      expect(clean.contains('*'), isFalse);
      expect(clean.contains('Programación Orientada a Objetos'), isTrue);
    });

    test('4. Ajuste de acrónimos institucionales UIS e IPRED', () {
      const input = 'Bienvenido a IPRED UIS TIC';
      final clean = VoiceService.sanitizeTextForSpeech(input);
      expect(clean, equals('Bienvenido a Ipred Uis Tic'));
    });
  });
}
