import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:permission_handler/permission_handler.dart';
import 'api_service.dart';
import 'local_zero_ai_service.dart';

enum VoiceCallStatus {
  idle,
  connecting,
  listening,
  thinking,
  speaking,
  muted,
  ended,
  error,
}

class VoiceCallMessage {
  final String sender; // 'user' | 'bot'
  final String text;
  final DateTime timestamp;

  VoiceCallMessage({
    required this.sender,
    required this.text,
    required this.timestamp,
  });
}

class VoiceService extends ChangeNotifier {
  static final VoiceService _instance = VoiceService._internal();
  factory VoiceService() => _instance;
  VoiceService._internal();

  final SpeechToText _speech = SpeechToText();
  final FlutterTts _tts = FlutterTts();

  VoiceCallStatus _status = VoiceCallStatus.idle;
  VoiceCallStatus get status => _status;

  bool _isSpeechInitialized = false;
  bool _isTtsInitialized = false;
  bool _isMuted = false;
  bool _isSpeakerOn = true;
  String _selectedLocaleId = 'es_CO';
  String _currentWords = '';
  String _lastRecognizedText = '';
  String _lastBotResponse = '';
  String? _errorMessage;
  double _soundLevel = 0.0;

  String? _authToken;
  int? _conversationId;
  Timer? _silenceTimer;
  Timer? _durationTimer;
  int _callDurationSeconds = 0;
  Completer<void>? _currentSpeechCompleter;

  final List<VoiceCallMessage> _messages = [];
  List<VoiceCallMessage> get messages => List.unmodifiable(_messages);

  String get currentWords => _currentWords;
  String get lastRecognizedText => _lastRecognizedText;
  String get lastBotResponse => _lastBotResponse;
  String? get errorMessage => _errorMessage;
  bool get isMuted => _isMuted;
  bool get isSpeakerOn => _isSpeakerOn;
  int get callDurationSeconds => _callDurationSeconds;
  double get soundLevel => _soundLevel;

  String get formattedDuration {
    final minutes = (_callDurationSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (_callDurationSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  /// Inicializa los motores de STT y TTS con configuraciones de alta fidelidad
  Future<bool> initialize() async {
    try {
      if (!_isSpeechInitialized) {
        final hasSpeech = await _speech.initialize(
          onError: _onSpeechError,
          onStatus: _onSpeechStatus,
          debugLogging: false,
        );
        _isSpeechInitialized = hasSpeech;

        if (hasSpeech) {
          final locales = await _speech.locales();
          for (final l in locales) {
            final locLower = l.localeId.toLowerCase();
            if (locLower.startsWith('es_co') || locLower.startsWith('es-co')) {
              _selectedLocaleId = l.localeId;
              break;
            } else if (locLower.startsWith('es')) {
              _selectedLocaleId = l.localeId;
            }
          }
        }
      }

      if (!_isTtsInitialized) {
        await _tts.setLanguage('es-CO');

        // En Web la escala estándar es 1.0; en móvil es ~0.50
        if (kIsWeb) {
          await _tts.setSpeechRate(1.0);
        } else {
          await _tts.setSpeechRate(0.50);
        }
        await _tts.setVolume(1.0);
        await _tts.setPitch(1.0);

        // Habilitar espera de finalización nativa para reproducción continua
        try {
          await _tts.awaitSpeakCompletion(true);
        } catch (_) {}

        if (!kIsWeb && (Platform.isAndroid || Platform.isIOS)) {
          try {
            await _tts.awaitSynthCompletion(true);
          } catch (_) {}
        }

        // Seleccionar la mejor voz neuronal en español
        try {
          final voices = await _tts.getVoices;
          if (voices is List && voices.isNotEmpty) {
            Map<String, String>? bestVoice;
            for (final v in voices) {
              if (v is Map) {
                final name = (v['name'] ?? '').toString().toLowerCase();
                final locale = (v['locale'] ?? '').toString().toLowerCase();
                if (locale.contains('es') || name.contains('spanish') || name.contains('español')) {
                  if (name.contains('natural') || name.contains('neural') || name.contains('sabina') || name.contains('jorge') || name.contains('paulina') || name.contains('google')) {
                    bestVoice = {'name': v['name'].toString(), 'locale': v['locale']?.toString() ?? 'es-CO'};
                    break;
                  } else {
                    bestVoice ??= {'name': v['name'].toString(), 'locale': v['locale']?.toString() ?? 'es-CO'};
                  }
                }
              }
            }
            if (bestVoice != null) {
              await _tts.setVoice(bestVoice);
            }
          }
        } catch (e) {
          debugPrint('[VoiceService] Voice selection note: $e');
        }

        _tts.setStartHandler(() {});

        _tts.setCompletionHandler(() {
          if (_currentSpeechCompleter != null && !_currentSpeechCompleter!.isCompleted) {
            _currentSpeechCompleter!.complete();
          }
        });

        _tts.setCancelHandler(() {
          if (_currentSpeechCompleter != null && !_currentSpeechCompleter!.isCompleted) {
            _currentSpeechCompleter!.complete();
          }
        });

        _tts.setErrorHandler((msg) {
          debugPrint('[VoiceService] TTS Error: $msg');
          if (_currentSpeechCompleter != null && !_currentSpeechCompleter!.isCompleted) {
            _currentSpeechCompleter!.complete();
          }
        });

        _isTtsInitialized = true;
      }

      return _isSpeechInitialized && _isTtsInitialized;
    } catch (e) {
      debugPrint('[VoiceService] Init Error: $e');
      _errorMessage = 'Error al inicializar audio: $e';
      notifyListeners();
      return false;
    }
  }

  /// Inicia una llamada de voz interactiva
  Future<void> startCall({
    required ApiService apiService,
    required LocalZeroAiService zeroAiService,
    String? token,
    int? conversationId,
    String? studentName,
    Map<String, dynamic>? studentData,
  }) async {
    _authToken = token;
    _conversationId = conversationId;
    _status = VoiceCallStatus.connecting;
    _callDurationSeconds = 0;
    _messages.clear();
    _currentWords = '';
    _lastRecognizedText = '';
    _lastBotResponse = '';
    _errorMessage = null;
    _soundLevel = 0.0;
    notifyListeners();

    // Permisos en móvil
    if (!kIsWeb) {
      final micStatus = await Permission.microphone.request();
      if (!micStatus.isGranted) {
        _status = VoiceCallStatus.error;
        _errorMessage = 'Se requiere permiso de micrófono para la llamada.';
        notifyListeners();
        return;
      }
    }

    final ready = await initialize();
    if (!ready && !_isSpeechInitialized) {
      _status = VoiceCallStatus.error;
      _errorMessage = 'El reconocimiento de voz no está disponible en este dispositivo.';
      notifyListeners();
      return;
    }

    // Temporizador de duración de la llamada
    _durationTimer?.cancel();
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      _callDurationSeconds++;
      notifyListeners();
    });

    // Saludo inicial cálido y personalizado
    final name = (studentName != null && studentName.trim().isNotEmpty && studentName != 'Estudiante')
        ? studentName.trim().split(' ').first
        : 'Estudiante';
    final greeting = 'Hola $name, te habla tu asistente virtual IPRED UIS. ¿En qué te puedo colaborar hoy?';

    _messages.add(VoiceCallMessage(
      sender: 'bot',
      text: greeting,
      timestamp: DateTime.now(),
    ));
    _lastBotResponse = greeting;
    notifyListeners();

    await speak(greeting);
  }

  /// Reproduce un texto con el sintetizador nativo frase por frase sin cortes
  Future<void> speak(String text) async {
    final cleanText = sanitizeTextForSpeech(text);
    if (cleanText.isEmpty) {
      _startListeningLoop();
      return;
    }

    // 1. Apagar micrófono para evitar eco y auto-interrupción por altavoz
    _silenceTimer?.cancel();
    try {
      await _speech.stop();
    } catch (_) {}

    _status = VoiceCallStatus.speaking;
    _lastBotResponse = cleanText;
    _soundLevel = 0.0;
    notifyListeners();

    // 2. Dividir en frases cohesivas para que la síntesis sea continua y natural
    final rawSentences = cleanText.split(RegExp(r'(?<=[.?!;])\s+|\n+'));
    final sentences = rawSentences.map((s) => s.trim()).where((s) => s.isNotEmpty).toList();
    if (sentences.isEmpty) sentences.add(cleanText);

    try {
      for (final sentence in sentences) {
        if (_status == VoiceCallStatus.ended || _status == VoiceCallStatus.muted) break;

        _currentSpeechCompleter = Completer<void>();
        await _tts.speak(sentence);

        // Guardián watchdog: asegura que no se quede bloqueado si el navegador no emite el evento de finalización
        final timeoutMs = math.max(3500, (sentence.length * 140));
        await _currentSpeechCompleter!.future.timeout(
          Duration(milliseconds: timeoutMs),
          onTimeout: () {
            debugPrint('[VoiceService] Watchdog timeout on sentence: ${sentence.substring(0, math.min(30, sentence.length))}...');
          },
        );

        // Breve respiro natural entre frases (90ms)
        await Future.delayed(const Duration(milliseconds: 90));
      }
    } catch (e) {
      debugPrint('[VoiceService] Error speaking: $e');
    } finally {
      // 3. Margen de 450ms para decaimiento completo del eco antes de abrir el micrófono
      if (_status != VoiceCallStatus.ended && !_isMuted) {
        await Future.delayed(const Duration(milliseconds: 450));
        _startListeningLoop();
      }
    }
  }

  /// Inicia el bucle de escucha activa con dictado continuo y nivel sonoro
  void _startListeningLoop() async {
    if (_status == VoiceCallStatus.ended || _isMuted || _status == VoiceCallStatus.speaking || _status == VoiceCallStatus.thinking) {
      return;
    }

    _status = VoiceCallStatus.listening;
    _currentWords = '';
    _soundLevel = 0.0;
    notifyListeners();

    try {
      await _speech.listen(
        onResult: (result) => _onSpeechResult(result),
        onSoundLevelChange: (level) {
          if (_status == VoiceCallStatus.listening) {
            _soundLevel = level;
            notifyListeners();
          }
        },
        listenOptions: SpeechListenOptions(
          partialResults: true,
          cancelOnError: false,
          listenMode: ListenMode.dictation, // Dictado continuo para oraciones completas y fluidas
          listenFor: const Duration(seconds: 60),
          pauseFor: const Duration(seconds: 4), // Pausa amplia para que no corte mientras el usuario respira o piensa
          localeId: _selectedLocaleId,
        ),
      );
    } catch (e) {
      debugPrint('[VoiceService] Error listen: $e');
    }
  }

  /// Manejo de resultados de reconocimiento de voz
  void _onSpeechResult(SpeechRecognitionResult result) {
    // Si no estamos en modo escucha (e.g. el bot está hablando), ignorar para evitar eco
    if (_status != VoiceCallStatus.listening) {
      return;
    }

    final words = result.recognizedWords.trim();
    if (words.isNotEmpty) {
      _currentWords = words;
      notifyListeners();

      _silenceTimer?.cancel();
      // Pausa conversacional de 2.5 segundos de silencio antes de procesar
      _silenceTimer = Timer(const Duration(milliseconds: 2500), () {
        if (_currentWords.trim().isNotEmpty && _status == VoiceCallStatus.listening) {
          _processUserInput(_currentWords.trim());
        }
      });
    }
  }

  /// Enviar inmediatamente lo que se ha hablado sin esperar el temporizador de silencio
  void submitCurrentSpeech() {
    if (_currentWords.trim().isNotEmpty && _status == VoiceCallStatus.listening) {
      _silenceTimer?.cancel();
      _processUserInput(_currentWords.trim());
    }
  }

  /// Ejecuta una pregunta explícita (e.g. desde chips de sugerencias rápidas)
  Future<void> sendSuggestedQuery(String text) async {
    await _tts.stop();
    await _speech.stop();
    await _processUserInput(text);
  }

  /// Procesa la pregunta del estudiante con la IA o Zero-AI
  Future<void> _processUserInput(String text) async {
    if (text.isEmpty) return;

    _silenceTimer?.cancel();
    try {
      await _speech.stop();
    } catch (_) {}

    _lastRecognizedText = text;
    _currentWords = '';
    _status = VoiceCallStatus.thinking;
    _soundLevel = 0.0;

    _messages.add(VoiceCallMessage(
      sender: 'user',
      text: text,
      timestamp: DateTime.now(),
    ));
    notifyListeners();

    try {
      final zeroAiService = LocalZeroAiService();
      String botReply = '';

      // 1. Consulta con el backend en línea enviando el texto limpio
      if (_authToken != null && _authToken!.isNotEmpty) {
        try {
          final api = ApiService();
          final res = await api.sendMessage(
            text,
            _authToken!,
            _conversationId,
          );
          if (res != null) {
            botReply = (res['respuesta'] as String?) ?? (res['mensaje'] as String?) ?? '';
          }
        } catch (e) {
          debugPrint('[VoiceService] Backend fetch failed, falling back to Zero-AI: $e');
        }
      }

      // 2. Si no hubo respuesta en línea, utilizar el motor local Zero-AI
      if (botReply.isEmpty) {
        final offlineRes = await zeroAiService.processOfflineQuery(text);
        if (offlineRes != null) {
          botReply = (offlineRes['respuesta'] as String?) ??
              'Disculpa, no pude obtener esa información en este momento. ¿Deseas consultar tu horario o asignaturas?';
        } else {
          botReply = 'Disculpa, no pude obtener esa información en este momento. ¿Deseas consultar tu horario o asignaturas?';
        }
      }

      _messages.add(VoiceCallMessage(
        sender: 'bot',
        text: botReply,
        timestamp: DateTime.now(),
      ));
      _lastBotResponse = botReply;
      notifyListeners();

      await speak(botReply);
    } catch (e) {
      debugPrint('[VoiceService] Process Error: $e');
      const errReply = 'Tuve un inconveniente al consultar la información. Por favor repíteme tu pregunta.';
      _messages.add(VoiceCallMessage(
        sender: 'bot',
        text: errReply,
        timestamp: DateTime.now(),
      ));
      await speak(errReply);
    }
  }

  /// Alterna silenciar micrófono
  void toggleMute() {
    _isMuted = !_isMuted;
    if (_isMuted) {
      _speech.stop();
      _silenceTimer?.cancel();
      _status = VoiceCallStatus.muted;
      _soundLevel = 0.0;
    } else {
      _status = VoiceCallStatus.listening;
      _startListeningLoop();
    }
    notifyListeners();
  }

  /// Alterna altavoz
  void toggleSpeaker() {
    _isSpeakerOn = !_isSpeakerOn;
    notifyListeners();
  }

  /// Finaliza la llamada
  Future<void> endCall() async {
    _status = VoiceCallStatus.ended;
    _silenceTimer?.cancel();
    _durationTimer?.cancel();
    _soundLevel = 0.0;
    if (_currentSpeechCompleter != null && !_currentSpeechCompleter!.isCompleted) {
      _currentSpeechCompleter!.complete();
    }
    try {
      await _speech.stop();
    } catch (_) {}
    try {
      await _tts.stop();
    } catch (_) {}
    notifyListeners();
  }

  void _onSpeechError(SpeechRecognitionError error) {
    debugPrint('[VoiceService] Speech Error: ${error.errorMsg}');
    if (_status == VoiceCallStatus.listening && !_isMuted) {
      Future.delayed(const Duration(milliseconds: 500), () {
        if (_status == VoiceCallStatus.listening && !_isMuted) {
          _startListeningLoop();
        }
      });
    }
  }

  void _onSpeechStatus(String status) {
    if (status == 'done' || status == 'notListening') {
      if (_status == VoiceCallStatus.listening && !_isMuted) {
        // Si el motor se detuvo por pausa natural pero hay palabras pendientes, no reiniciar abruptamente
        if (_currentWords.isEmpty) {
          Future.delayed(const Duration(milliseconds: 300), () {
            if (_status == VoiceCallStatus.listening && !_isMuted && _currentWords.isEmpty) {
              _startListeningLoop();
            }
          });
        }
      }
    }
  }

  /// Limpia y humaniza el texto para que la voz sintética suene fluida, cálida y natural
  static String sanitizeTextForSpeech(String text) {
    String clean = text;

    // Eliminar bloques de código
    clean = clean.replaceAll(RegExp(r'```[\s\S]*?```'), '');
    clean = clean.replaceAll(RegExp(r'`[^`]*`'), '');

    // Convertir enlaces markdown [texto](url) en solo texto
    clean = clean.replaceAllMapped(RegExp(r'\[([^\]]+)\]\([^\)]+\)'), (m) => m[1] ?? '');

    // Convertir fechas ISO YYYY-MM-DD a formato hablado en español
    clean = clean.replaceAllMapped(RegExp(r'\b(202\d)-(\d{2})-(\d{2})\b'), (m) {
      const meses = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
      final mIdx = int.tryParse(m[2] ?? '') ?? 0;
      final dia = int.tryParse(m[3] ?? '') ?? 0;
      if (mIdx >= 1 && mIdx <= 12 && dia > 0) {
        return '$dia de ${meses[mIdx]}';
      }
      return m[0] ?? '';
    });

    // Convertir rangos de horas HH:MM - HH:MM a lenguaje hablado
    clean = clean.replaceAllMapped(RegExp(r'\b(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\b'), (m) {
      return 'de ${m[1]}:${m[2]} a ${m[3]}:${m[4]}';
    });

    // Humanizar tablas markdown (| Col1 | Col2 | ...) en frases comprensibles
    if (clean.contains('|')) {
      final lines = clean.split('\n');
      final processedLines = <String>[];
      for (final l in lines) {
        if (l.contains('---') || l.contains(':-')) continue;
        if (l.trim().startsWith('|') && l.trim().endsWith('|')) {
          final cells = l.split('|').map((c) => c.trim()).where((c) => c.isNotEmpty).toList();
          if (cells.isNotEmpty) {
            final firstLower = cells.first.toLowerCase();
            if (!firstLower.contains('código') && !firstLower.contains('asignatura') && !firstLower.contains('fecha')) {
              processedLines.add(cells.join(', '));
            }
          }
        } else {
          processedLines.add(l);
        }
      }
      clean = processedLines.join('\n');
    }

    // Convertir viñetas y listas en pausas naturales
    clean = clean.replaceAll(RegExp(r'^\s*[-•*+]\s+', multiLine: true), '. ');
    clean = clean.replaceAll(RegExp(r'^\s*\d+\.\s+', multiLine: true), '. ');

    // Eliminar encabezados #, **, *, _, ~
    clean = clean.replaceAll(RegExp(r'#+\s*'), '');
    clean = clean.replaceAll(RegExp(r'\*\*|__'), '');
    clean = clean.replaceAll(RegExp(r'[\*_~]'), '');

    // Eliminar emojis
    clean = clean.replaceAll(RegExp(r'[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]', unicode: true), '');

    // Pronunciaciones institucionales fluidas
    clean = clean.replaceAll('IPRED', 'Ipred');
    clean = clean.replaceAll('UIS', 'Uis');
    clean = clean.replaceAll('TIC', 'Tic');
    clean = clean.replaceAll('AVA', 'Ava');
    clean = clean.replaceAll('Créd.', 'créditos');
    clean = clean.replaceAll('Asig.', 'asignatura');
    clean = clean.replaceAll('Prof.', 'profesor');
    clean = clean.replaceAll('Doc.', 'docente');

    // Normalizar espacios y signos repetidos
    clean = clean.replaceAll(RegExp(r'\s+'), ' ');
    clean = clean.replaceAll(RegExp(r'\.{2,}'), '.').trim();

    return clean;
  }
}
