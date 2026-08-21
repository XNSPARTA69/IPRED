import 'dart:convert';
import 'dart:io' show Platform;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'auth_service.dart';

class ApiService {
  CancelToken? _currentChatCancelToken;

  /// Cancels the current in-flight chat request, if any.
  void cancelCurrentRequest() {
    _currentChatCancelToken?.cancel('User cancelled');
    _currentChatCancelToken = null;
  }

  static String get defaultBaseUrl {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) {
      return fromEnv;
    }
    if (kIsWeb) {
      // En Web (móvil y escritorio), conectarse al mismo origen (puerto 3000 con Nginx proxy inverso)
      if (Uri.base.origin.isNotEmpty && !Uri.base.origin.contains('null')) {
        return Uri.base.origin;
      }
      final host = Uri.base.host.isNotEmpty ? Uri.base.host : 'localhost';
      return 'http://$host:8000';
    }
    // En APK Android / App iOS nativo, conectar vía dominio HTTPS permanente
    return 'https://ipred.pasteleriamiranda.art';
  }

  late final Dio _dio;

  ApiService({String? baseUrl}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl ?? defaultBaseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
        onError: (error, handler) async {
          debugPrint('DIO Error [${error.response?.statusCode}]: ${error.message}');
          // Si el servidor responde 401 (token expirado o sesión perdida), expulsar inmediatamente al Login
          if (error.response?.statusCode == 401) {
            debugPrint('⚠️ Sesión expirada (401). Redirigiendo automáticamente a Login...');
            try {
              await AuthService.instance.logout();
            } catch (e) {
              debugPrint('Error en auto-logout: $e');
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  // ============================================================
  // AUTENTICACIÓN
  // ============================================================

  Future<Map<String, dynamic>?> login(String username, String password) async {
    try {
      final response = await _dio.post(
        '/auth/login',
        data: {
          'username': username.trim(),
          'password': password,
        },
        options: Options(
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } on DioException catch (de) {
      debugPrint('Error en login DioException: ${de.response?.data ?? de.message}');
      return null;
    } catch (e) {
      debugPrint('Error general en login: $e');
      return null;
    }
  }

  Future<bool> register(
    String username,
    String password,
    String? email,
    String? nombre,
  ) async {
    try {
      final response = await _dio.post(
        '/auth/register',
        data: {
          'username': username.trim(),
          'password': password,
          if (email != null && email.isNotEmpty) 'email': email.trim(),
          if (nombre != null && nombre.isNotEmpty) 'nombre_completo': nombre.trim(),
        },
        options: Options(
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      return response.statusCode == 201;
    } catch (e) {
      debugPrint('Error en registro: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> refreshToken(String refreshToken) async {
    try {
      final response = await _dio.post(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('Error renovando token: $e');
      return null;
    }
  }

  // ============================================================
  // CHAT STREAMING (Server-Sent Events con Fallback Universal)
  // ============================================================

  Future<void> sendMessageStream({
    required String message,
    required String accessToken,
    required int? conversacionId,
    required Function(int convId) onInit,
    required Function(String chunk) onChunk,
    required Function(String toolName) onTool,
    required Function(Map<String, dynamic> doneData) onDone,
    required Function(String error) onError,
  }) async {
    _currentChatCancelToken = CancelToken();

    // 1. Intentar streaming SSE en Mobile / Plataformas nativas
    if (!kIsWeb) {
      try {
        final response = await _dio.post<ResponseBody>(
          '/chat/stream',
          data: {
            'message': message,
            'conversacion_id': conversacionId,
          },
          cancelToken: _currentChatCancelToken,
          options: Options(
            headers: {
              'Authorization': 'Bearer $accessToken',
              'Accept': 'text/event-stream',
            },
            responseType: ResponseType.stream,
            sendTimeout: const Duration(seconds: 30),
            receiveTimeout: const Duration(seconds: 120),
          ),
        );

        final stream = response.data?.stream;
        if (stream != null) {
          String buffer = '';
          await for (final unit in stream) {
            buffer += utf8.decode(unit, allowMalformed: true);
            final lines = buffer.split('\n');
            buffer = lines.removeLast();

            for (final line in lines) {
              final trimmed = line.trim();
              if (trimmed.startsWith('data:')) {
                final jsonStr = trimmed.substring(5).trim();
                if (jsonStr.isNotEmpty) {
                  try {
                    final data = jsonDecode(jsonStr) as Map<String, dynamic>;
                    final type = data['type'];
                    if (type == 'init') {
                      onInit(data['conversacion_id']);
                    } else if (type == 'chunk') {
                      onChunk(data['text'] ?? '');
                    } else if (type == 'tool') {
                      onTool(data['name'] ?? '');
                    } else if (type == 'done') {
                      onDone(data);
                    } else if (type == 'error') {
                      onError(data['detail'] ?? 'Error desconocido');
                    }
                  } catch (_) {}
                }
              }
            }
          }
          _currentChatCancelToken = null;
          return;
        }
      } on DioException catch (de) {
        if (de.type == DioExceptionType.cancel) {
          debugPrint('Stream cancelado por el usuario.');
          return;
        }
        debugPrint('Fallo SSE nativo ($de). Pasando a fallback síncrono...');
      } catch (e) {
        debugPrint('Error en stream nativo ($e). Pasando a fallback síncrono...');
      }
    }

    // 2. Fallback Universal (Web y plataformas con restricciones SSE)
    try {
      final syncResp = await sendMessage(message, accessToken, conversacionId);
      if (syncResp != null) {
        if (syncResp['conversacion_id'] != null) {
          onInit(syncResp['conversacion_id']);
        }
        final respuesta = (syncResp['respuesta'] as String?) ?? '';
        final words = respuesta.split(' ');
        for (int i = 0; i < words.length; i++) {
          if (_currentChatCancelToken != null && _currentChatCancelToken!.isCancelled) {
            break;
          }
          onChunk(words[i] + (i < words.length - 1 ? ' ' : ''));
          await Future.delayed(const Duration(milliseconds: 10));
        }
        onDone(syncResp);
      } else {
        onError('No se pudo conectar con el servidor. Intenta de nuevo.');
      }
    } catch (e) {
      onError('Error de comunicación con el servidor.');
    } finally {
      _currentChatCancelToken = null;
    }
  }

  // ============================================================
  // CHAT (Timeout ampliado a 60s para razonamiento multi-hop)
  // ============================================================

  Future<Map<String, dynamic>?> sendMessage(
    String message,
    String accessToken,
    int? conversacionId,
  ) async {
    _currentChatCancelToken = CancelToken();
    try {
      final response = await _dio.post(
        '/chat/message',
        data: {
          'message': message,
          'conversacion_id': conversacionId,
        },
        cancelToken: _currentChatCancelToken,
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
          sendTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 60), // 60 segundos para tool-calling
        ),
      );
      _currentChatCancelToken = null;

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } on DioException catch (de) {
      if (de.type == DioExceptionType.cancel) {
        debugPrint('Solicitud de chat cancelada por el usuario.');
        return null;
      }
      debugPrint('DioException en sendMessage: ${de.type} - ${de.message}');
      return null;
    } catch (e) {
      debugPrint('Error enviando mensaje: $e');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> getConversations(String accessToken) async {
    try {
      final response = await _dio.get(
        '/chat/conversations',
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(response.data);
      }
      return null;
    } catch (e) {
      debugPrint('Error obteniendo conversaciones: $e');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> getMessages(
    int conversacionId,
    String accessToken,
  ) async {
    try {
      final response = await _dio.get(
        '/chat/conversations/$conversacionId/messages',
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(response.data);
      }
      return null;
    } catch (e) {
      debugPrint('Error obteniendo mensajes: $e');
      return null;
    }
  }

  Future<bool> deleteConversation(
    int conversacionId,
    String accessToken,
  ) async {
    try {
      final response = await _dio.delete(
        '/chat/conversations/$conversacionId',
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );
      return response.statusCode == 200 || response.statusCode == 204;
    } catch (e) {
      debugPrint('Error eliminando conversación: $e');
      return true; // Permitir eliminación local en UI
    }
  }

  // ============================================================
  // PERFIL
  // ============================================================

  Future<Map<String, dynamic>?> getProfile(String accessToken) async {
    try {
      final response = await _dio.get(
        '/profile',
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('Error obteniendo perfil: $e');
      return null;
    }
  }

  Future<bool> updateProfile(
    Map<String, dynamic> data,
    String accessToken,
  ) async {
    try {
      final response = await _dio.put(
        '/profile',
        data: data,
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error actualizando perfil: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> getAcademicCalendar(String accessToken) async {
    try {
      final response = await _dio.get(
        '/profile/calendar',
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('Error obteniendo calendario académico: $e');
      return null;
    }
  }
}
