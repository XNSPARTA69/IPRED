import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_service.dart';
import 'local_zero_ai_service.dart';

class AuthService extends ChangeNotifier {
  static final AuthService _instance = AuthService._internal();
  
  factory AuthService() {
    return _instance;
  }
  
  static AuthService get instance => _instance;
  
  AuthService._internal();

  final _secureStorage = const FlutterSecureStorage();
  
  String? _accessToken;
  String? _refreshToken;
  Map<String, dynamic>? _user;
  bool _isInitialized = false;

  bool get isAuthenticated => _accessToken != null && _accessToken!.isNotEmpty;
  bool get isInitialized => _isInitialized;
  String? get accessToken => _accessToken;
  Map<String, dynamic>? get user => _user;

  Future<void> _writeStorage(String key, String value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(key, value);
    } catch (_) {}
    if (!kIsWeb) {
      try {
        await _secureStorage.write(key: key, value: value);
      } catch (_) {}
    }
  }

  Future<String?> _readStorage(String key) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final val = prefs.getString(key);
      if (val != null && val.isNotEmpty) return val;
    } catch (_) {}
    if (!kIsWeb) {
      try {
        return await _secureStorage.read(key: key);
      } catch (_) {}
    }
    return null;
  }

  Future<void> _deleteStorageAll() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('access_token');
      await prefs.remove('refresh_token');
      await prefs.remove('username');
      await prefs.remove('user_profile_json');
    } catch (_) {}
    if (!kIsWeb) {
      try {
        await _secureStorage.deleteAll();
      } catch (_) {}
    }
  }

  /// Carga instantánea de sesión (< 2ms) desde almacenamiento local
  Future<void> loadStoredToken() async {
    try {
      _accessToken = await _readStorage('access_token');
      _refreshToken = await _readStorage('refresh_token');
      
      final storedUserData = await _readStorage('user_profile_json');
      if (storedUserData != null && storedUserData.isNotEmpty) {
        try {
          _user = jsonDecode(storedUserData) as Map<String, dynamic>;
        } catch (_) {}
      }

      final storedUsername = await _readStorage('username');
      if (_user == null && storedUsername != null) {
        _user = {
          'username': storedUsername,
          'codigo_est': int.tryParse(storedUsername) ?? 0,
        };
      }

      _isInitialized = true;
      notifyListeners();

      // Validación asíncrona en segundo plano sin bloquear el renderizado inicial
      if (_accessToken != null && _accessToken!.isNotEmpty) {
        _verifyTokenInBackground(_accessToken!);
      }
    } catch (e) {
      debugPrint('Error cargando token: $e');
      _isInitialized = true;
      _accessToken = null;
      _user = null;
      notifyListeners();
    }
  }

  void _verifyTokenInBackground(String token) {
    ApiService().getProfile(token).then((profile) {
      if (profile != null && profile['codigo_est'] != null && profile['codigo_est'] != 0) {
        _user = profile;
        _writeStorage('user_profile_json', jsonEncode(profile));
        notifyListeners();
      } else {
        // Token inválido o expirado -> Cerrar sesión limpiamente
        debugPrint('Token inválido en verificación de fondo. Redirigiendo a login...');
        logout();
      }
    }).catchError((err) {
      debugPrint('Error verificando token en segundo plano: $err');
    });

    // Sincronizar datos académicos en caché para disponibilidad offline
    ApiService().getAcademicSummary(token).then((summary) {
      if (summary != null) {
        LocalZeroAiService().cacheStudentData(
          profile: summary['profile'] as Map<String, dynamic>? ?? {},
          subjects: summary['subjects'] as List<dynamic>? ?? [],
          schedule: summary['schedule'] as List<dynamic>? ?? [],
        );
      }
    }).catchError((err) {
      debugPrint('No se pudo sincronizar resumen académico offline: $err');
    });
  }

  Future<bool> login(String username, String password) async {
    final err = await loginWithDetails(username, password);
    return err == null;
  }

  Future<String?> loginWithDetails(String username, String password) async {
    try {
      final response = await ApiService().login(username, password);
      
      if (response != null) {
        _accessToken = response['access_token'];
        _refreshToken = response['refresh_token'];
        
        await _writeStorage('access_token', _accessToken!);
        await _writeStorage('refresh_token', _refreshToken!);
        await _writeStorage('username', username.trim());

        final profile = await ApiService().getProfile(_accessToken!);
        if (profile != null) {
          _user = profile;
          await _writeStorage('user_profile_json', jsonEncode(profile));
        } else {
          _user = {
            'username': username.trim(),
            'codigo_est': int.tryParse(username.trim()) ?? 0,
          };
        }
        
        notifyListeners();

        // Precargar caché offline de forma inmediata en segundo plano
        ApiService().getAcademicSummary(_accessToken!).then((summary) {
          if (summary != null) {
            LocalZeroAiService().cacheStudentData(
              profile: summary['profile'] as Map<String, dynamic>? ?? {},
              subjects: summary['subjects'] as List<dynamic>? ?? [],
              schedule: summary['schedule'] as List<dynamic>? ?? [],
            );
          }
        }).catchError((_) {});

        return null; // Éxito, sin error
      }
      return 'Código de estudiante o contraseña incorrectos.';
    } catch (e) {
      debugPrint('Error en login: $e');
      return 'Error de conexión con el servidor. Intenta de nuevo.';
    }
  }

  Future<bool> register(String username, String password, String email, String nombre) async {
    try {
      final success = await ApiService().register(username, password, email, nombre);
      return success;
    } catch (e) {
      debugPrint('Error en registro: $e');
      return false;
    }
  }

  Future<void> logout() async {
    try {
      _accessToken = null;
      _refreshToken = null;
      _user = null;
      
      await _deleteStorageAll();
      
      notifyListeners();
    } catch (e) {
      debugPrint('Error en logout: $e');
    }
  }

  Future<bool> refreshToken() async {
    try {
      if (_refreshToken == null) return false;
      
      final response = await ApiService().refreshToken(_refreshToken!);
      
      if (response != null) {
        _accessToken = response['access_token'];
        _refreshToken = response['refresh_token'];
        
        await _writeStorage('access_token', _accessToken!);
        await _writeStorage('refresh_token', _refreshToken!);
        
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Error en refresh token: $e');
      return false;
    }
  }
}
