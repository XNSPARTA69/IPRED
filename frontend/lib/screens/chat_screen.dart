import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../theme/theme_provider.dart';
import '../widgets/chat_bubble.dart';
import 'profile_screen.dart';
import 'voice_call_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();

  List<Map<String, dynamic>> _messages = [];
  List<Map<String, dynamic>> _conversations = [];
  int? _currentConversationId;
  bool _isLoading = false;
  bool _isLoadingMessages = true;
  bool _isLoadingConversations = false;
  String? _studentName;

  String? _selectedCategory;

  final List<Map<String, dynamic>> _hubCategories = [
    {
      'id': 'calendario',
      'icon': '🗓️',
      'title': 'Calendario Académico',
      'subtitle': 'Cronograma, tutorías y fechas UIS',
      'isCalendarModal': true,
      'prompt': '¿Cuál es mi calendario académico, próximas tutorías y fechas clave?',
    },
    {
      'id': 'tutorias',
      'icon': '📅',
      'title': 'Mis Tutorías y Clases',
      'subtitle': 'Fechas, horarios y docentes',
      'isDirect': true,
      'prompt': '¿Cuándo son mis próximas tutorías y horarios de clase?',
    },
    {
      'id': 'materias',
      'icon': '📚',
      'title': 'Mis Materias y Docentes',
      'subtitle': 'Carga académica inscrita',
      'isDirect': true,
      'prompt': '¿Cuáles son las materias que tengo matriculadas este semestre?',
    },
    {
      'id': 'profesores',
      'icon': '👨‍🏫',
      'title': 'Mis Profesores y Correos',
      'subtitle': 'Canales oficiales de docentes',
      'isDirect': true,
      'prompt': '¿Quiénes son los profesores de mis asignaturas y sus correos?',
    },
    {
      'id': 'tramites',
      'icon': '📑',
      'title': 'Trámites y Grados',
      'subtitle': 'Cancelaciones, certificados y grado',
      'isDirect': false,
    },
    {
      'id': 'tic',
      'icon': '💻',
      'title': 'Plataformas y Accesos TIC',
      'subtitle': 'Moodle AVA, claves y notas',
      'isDirect': false,
    },
    {
      'id': 'financiero',
      'icon': '💰',
      'title': 'Matrícula y Gratuidad',
      'subtitle': 'Liquidación, PSE y descuentos',
      'isDirect': false,
    },
    {
      'id': 'bienestar',
      'icon': '🏥',
      'title': 'Bienestar y Salud UIS',
      'subtitle': 'Citas médicas, psicología y deportes',
      'isDirect': false,
    },
    {
      'id': 'modalidades_grado',
      'icon': '🇬🇧',
      'title': 'Inglés y Modalidades Grado',
      'subtitle': 'Requisito de inglés, prácticas y Saber TyT',
      'isDirect': false,
    },
    {
      'id': 'reglamento',
      'icon': '⚖️',
      'title': 'Reglamento y Calificaciones',
      'subtitle': 'Escala de notas, promedios y supletorios',
      'isDirect': false,
    },
    {
      'id': 'sedes',
      'icon': '🏛️',
      'title': 'Sedes Regionales',
      'subtitle': 'Ubicaciones, teléfonos y atención',
      'isDirect': false,
    },
    {
      'id': 'carreras',
      'icon': '🎓',
      'title': 'Oferta Académica IPRED',
      'subtitle': 'Carreras de pregrado y tecnologías',
      'isDirect': false,
    },
  ];

  final Map<String, Map<String, dynamic>> _subCategories = {
    'tramites': {
      'title': 'Trámites Académicos y Grados',
      'icon': '📑',
      'description': 'Consultas oficiales con normatividad y pasos detallados',
      'items': [
        {
          'icon': '📝',
          'title': 'Cancelación de Materias o Semestre',
          'subtitle': 'Procedimiento, semana 8 y reglamento',
          'prompt': '¿Cómo es el proceso oficial para cancelar una materia o el semestre?',
        },
        {
          'icon': '🎓',
          'title': 'Requisitos y Fechas de Grado',
          'subtitle': 'Plan de estudios, Saber TyT y paz y salvos',
          'prompt': '¿Cuáles son los requisitos oficiales y fechas de grado en el IPRED?',
        },
        {
          'icon': '📄',
          'title': 'Certificados de Notas y Estudio',
          'subtitle': 'Polígrafo sin costo y certificados oficiales',
          'prompt': '¿Cómo solicito un certificado de notas o constancia de estudio?',
        },
        {
          'icon': '📜',
          'title': 'Paz y Salvo Institucional',
          'subtitle': 'Biblioteca, financiera y coordinación',
          'prompt': '¿Cómo tramitar el paz y salvo institucional UIS?',
        },
        {
          'icon': '🔄',
          'title': 'Homologaciones y Reingresos',
          'subtitle': 'Solicitud ante el Comité de Programa',
          'prompt': '¿Cómo es el trámite de homologación de asignaturas y reingreso?',
        },
        {
          'icon': '⚖️',
          'title': 'Incapacidades y Supletorios',
          'subtitle': 'Fuerza mayor, salud y soporte docente',
          'prompt': '¿Qué debo hacer si falto a una tutoría o evaluación por salud o fuerza mayor?',
        },
      ],
    },
    'tic': {
      'title': 'Plataformas Virtuales y Accesos TIC',
      'icon': '💻',
      'description': 'Entornos virtuales, credenciales y herramientas digitales',
      'items': [
        {
          'icon': '🌐',
          'title': 'Moodle AVA e IPRED TIC',
          'subtitle': 'Enlaces de acceso y entrega de talleres',
          'prompt': '¿Cómo ingresar al aula virtual Moodle AVA y la plataforma IPRED TIC?',
        },
        {
          'icon': '🔑',
          'title': 'Recuperar Clave o Correo UIS',
          'subtitle': 'Restablecer contraseña Sócrates y Gmail UIS',
          'prompt': '¿Cómo recuperar mi contraseña del sistema de estudiantes o el correo institucional UIS?',
        },
        {
          'icon': '📊',
          'title': 'Consulta de Calificaciones',
          'subtitle': 'Notas parciales en AVA y finales en Sócrates',
          'prompt': '¿Dónde y cómo consulto mis calificaciones parciales y finales?',
        },
        {
          'icon': '📖',
          'title': 'Biblioteca Virtual UIS',
          'subtitle': 'Bases de datos Scopus, libros y revistas',
          'prompt': '¿Cómo acceder a la Biblioteca Virtual UIS y consultar libros o bases de datos?',
        },
      ],
    },
    'financiero': {
      'title': 'Matrícula y Beneficios Financieros',
      'icon': '💰',
      'description': 'Volantes de pago, PSE, gratuidad y descuentos de ley',
      'items': [
        {
          'icon': '💵',
          'title': 'Descargar Liquidación y Pagos',
          'subtitle': 'Pago por PSE o ventanilla bancaria',
          'prompt': '¿Cómo descargar mi volante de liquidación de matrícula y qué métodos de pago hay?',
        },
        {
          'icon': '🏛️',
          'title': 'Política de Gratuidad (Puedo Estudiar)',
          'subtitle': 'Requisitos Sisbén y cobertura del 100%',
          'prompt': '¿Cuáles son los requisitos y cómo funciona la Política de Gratuidad en la matrícula?',
        },
        {
          'icon': '🗳️',
          'title': 'Descuento del 10% por Votación',
          'subtitle': 'Certificado electoral y aplicación en Sócrates',
          'prompt': '¿Cómo aplicar el descuento del 10% en la matrícula con el certificado electoral?',
        },
      ],
    },
    'bienestar': {
      'title': 'Bienestar Universitario y Servicios de Salud',
      'icon': '🏥',
      'description': 'Servicios médicos, apoyo psicológico, deportes y comedor',
      'items': [
        {
          'icon': '🩺',
          'title': 'Servicio Médico y Odontológico',
          'subtitle': 'Citas médicas, póliza de accidentes y urgencias',
          'prompt': '¿Cómo acceder a los servicios de salud y citas médicas en Bienestar UIS?',
        },
        {
          'icon': '🧠',
          'title': 'Apoyo Psicológico y SEA',
          'subtitle': 'Acompañamiento emocional y refuerzo académico',
          'prompt': '¿Cómo solicitar apoyo psicológico o asesoría académica en el SEA UIS?',
        },
        {
          'icon': '⚽',
          'title': 'Deportes, Gimnasio y Cultura',
          'subtitle': 'Instalaciones deportivas, torneos y danza/teatro',
          'prompt': '¿Qué actividades deportivas y culturales ofrece Bienestar Universitario UIS?',
        },
        {
          'icon': '🍲',
          'title': 'Comedor y Apoyos Socioeconómicos',
          'subtitle': 'Subsidios de alimentación y residencias estudiantiles',
          'prompt': '¿Cuáles son los apoyos socioeconómicos y subsidios de Bienestar UIS?',
        },
      ],
    },
    'modalidades_grado': {
      'title': 'Requisito de Inglés y Opciones de Grado',
      'icon': '🇬🇧',
      'description': 'Certificación de idioma, prácticas profesionales y Saber TyT/Pro',
      'items': [
        {
          'icon': '📘',
          'title': 'Requisito de Idioma Extranjero (ILS)',
          'subtitle': 'Niveles A2/B1/B2, exámenes y homologación',
          'prompt': '¿Cuál es el requisito de inglés para graduarse en el IPRED y cómo se aprueba?',
        },
        {
          'icon': '🏢',
          'title': 'Práctica Empresarial y Social',
          'subtitle': 'Requisitos de créditos (70%), convenio y tutor',
          'prompt': '¿Cuáles son los requisitos para hacer práctica empresarial como opción de grado?',
        },
        {
          'icon': '🔬',
          'title': 'Proyectos de Investigación y Posgrado',
          'subtitle': 'Monografías, planes de negocio y posgrados',
          'prompt': '¿Cómo es la modalidad de proyecto de grado o seminario de actualización?',
        },
        {
          'icon': '📝',
          'title': 'Pruebas de Estado Saber Pro / TyT',
          'subtitle': 'Registro con 75% de créditos y cronograma ICFES',
          'prompt': '¿Cuándo y cómo debo presentar las pruebas Saber Pro o Saber TyT para grado?',
        },
      ],
    },
    'reglamento': {
      'title': 'Reglamento Estudiantil y Calificaciones',
      'icon': '⚖️',
      'description': 'Acuerdo 072 de 1982, escala de notas y permanencia académica',
      'items': [
        {
          'icon': '📊',
          'title': 'Escala de Notas y Aprobación',
          'subtitle': 'Calificación de 0.0 a 5.0 y nota mínima 3.0',
          'prompt': '¿Cómo es la escala de calificaciones y con cuánto se aprueba una materia en la UIS?',
        },
        {
          'icon': '⚠️',
          'title': 'Promedio y Matrícula Condicional',
          'subtitle': 'Promedio mínimo 3.2 y causales de pérdida de cupo',
          'prompt': '¿Qué pasa si mi promedio baja de 3.2 o pierdo materias en la UIS?',
        },
        {
          'icon': '📝',
          'title': 'Habilitaciones y Supletorios',
          'subtitle': 'Habilitar con 2.0-2.9 y exámenes supletorios',
          'prompt': '¿Cómo funcionan las habilitaciones, validaciones y supletorios en la UIS?',
        },
      ],
    },
    'sedes': {
      'title': 'Sedes Regionales y Canales de Atención',
      'icon': '🏛️',
      'description': 'Directorio institucional del IPRED en Santander',
      'items': [
        {
          'icon': '📍',
          'title': 'Sedes, Teléfonos y Direcciones',
          'subtitle': 'Bucaramanga, Barranca, Socorro, Barbosa, Málaga',
          'prompt': '¿Cuáles son las sedes del IPRED, teléfonos y canales de atención?',
        },
      ],
    },
    'carreras': {
      'title': 'Oferta Académica IPRED',
      'icon': '🎓',
      'description': 'Carreras profesionales y tecnologías a distancia y virtual',
      'items': [
        {
          'icon': '🎓',
          'title': 'Todas las Carreras del IPRED',
          'subtitle': 'Programas de pregrado con registro de alta calidad',
          'prompt': '¿Cuáles son las carreras y programas académicos de pregrado que ofrece el IPRED?',
        },
        {
          'icon': '💊',
          'title': 'Regencia de Farmacia',
          'subtitle': 'Tecnología en Regencia de Farmacia (6 semestres)',
          'prompt': '¿Cuáles son los programas académicos y enfoque de Regencia de Farmacia en el IPRED?',
        },
        {
          'icon': '🏢',
          'title': 'Gestión Empresarial',
          'subtitle': 'Tecnología Empresarial y Gestión Profesional',
          'prompt': '¿Cuáles son las características del programa de Gestión Empresarial en el IPRED?',
        },
        {
          'icon': '⚖️',
          'title': 'Gestión Judicial y Criminalística',
          'subtitle': 'Tecnología en Gestión Judicial (6 semestres)',
          'prompt': '¿De qué trata el programa de Gestión Judicial e Investigación Criminal del IPRED?',
        },
      ],
    },
  };

  bool _userScrolledUp = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScrollChanged);
    _loadUserProfile();
    _loadConversations();
  }

  void _onScrollChanged() {
    if (!_scrollController.hasClients) return;
    final position = _scrollController.position;
    final distanceFromBottom = position.maxScrollExtent - position.pixels;
    // Si el usuario está a más de 100px del fondo, está leyendo contenido arriba
    if (distanceFromBottom > 100) {
      if (!_userScrolledUp) {
        _userScrolledUp = true;
      }
    } else {
      // Si el usuario regresa al fondo, reactivar el seguimiento automático
      if (_userScrolledUp) {
        _userScrolledUp = false;
      }
    }
  }

  Future<void> _loadUserProfile() async {
    try {
      final authService = context.read<AuthService>();
      final apiService = context.read<ApiService>();
      if (authService.accessToken == null) return;
      final profile = await apiService.getProfile(authService.accessToken!);
      if (profile != null && mounted) {
        setState(() {
          _studentName = profile['nombre_completo'] ?? profile['primer_nombre'];
        });
      }
    } catch (_) {}
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScrollChanged);
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadConversations() async {
    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();

    if (authService.accessToken == null) return;

    setState(() => _isLoadingConversations = true);
    final conversations = await apiService.getConversations(authService.accessToken!);

    if (!mounted) return;
    setState(() {
      _conversations = conversations ?? [];
      _isLoadingConversations = false;
      // Iniciar siempre en un nuevo chat limpio al iniciar sesión
      if (_currentConversationId == null) {
        _messages = [];
        _isLoadingMessages = false;
      }
    });
  }

  Future<void> _loadMessages() async {
    if (_currentConversationId == null) {
      setState(() {
        _messages = [];
        _isLoadingMessages = false;
      });
      return;
    }

    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();

    if (authService.accessToken == null) return;

    setState(() => _isLoadingMessages = true);
    final messages = await apiService.getMessages(
      _currentConversationId!,
      authService.accessToken!,
    );

    if (mounted) {
      setState(() {
        _messages = messages ?? [];
        _isLoadingMessages = false;
      });
      _scrollToBottom();
    }
  }

  bool _isCancelledByUser = false;

  void _cancelRequest() {
    _isCancelledByUser = true;
    final apiService = context.read<ApiService>();
    apiService.cancelCurrentRequest();
    if (mounted) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.stop_circle_outlined, color: Colors.white, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Generación detenida por el usuario.',
                  style: GoogleFonts.plusJakartaSans(fontSize: 13.5),
                ),
              ),
            ],
          ),
          backgroundColor: const Color(0xFF334155),
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
    }
  }

  Future<void> _sendMessage([String? customText]) async {
    final textToSend = customText ?? _messageController.text;
    if (textToSend.trim().isEmpty) return;

    if (customText == null) {
      _messageController.clear();
    }

    _isCancelledByUser = false;
    _userScrolledUp = false;
    setState(() {
      _isLoading = true;
      _messages.add({
        'rol': 'user',
        'contenido': textToSend,
        'created_at': DateTime.now().toIso8601String(),
      });
    });

    _scrollToBottom(false, true);

    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();

    if (authService.accessToken == null) {
      setState(() => _isLoading = false);
      return;
    }

    Map<String, dynamic>? streamingAssistantMsg;

    await apiService.sendMessageStream(
      message: textToSend,
      accessToken: authService.accessToken!,
      conversacionId: _currentConversationId,
      onInit: (convId) {
        if (_currentConversationId == null && mounted) {
          setState(() => _currentConversationId = convId);
          _loadConversations();
        }
      },
      onTool: (toolName) {
        // Herramienta en ejecución
      },
      onChunk: (chunk, {bool? esIa}) {
        if (!mounted || _isCancelledByUser) return;
        setState(() {
          if (streamingAssistantMsg == null) {
            streamingAssistantMsg = {
              'id': DateTime.now().millisecondsSinceEpoch,
              'rol': 'assistant',
              'contenido': chunk,
              'created_at': DateTime.now().toIso8601String(),
              'es_ia': esIa ?? false,
              'is_streaming': true,
            };
            _messages.add(streamingAssistantMsg!);
          } else {
            if (esIa != null) {
              streamingAssistantMsg!['es_ia'] = esIa;
            }
            streamingAssistantMsg!['contenido'] =
                (streamingAssistantMsg!['contenido'] as String) + chunk;
          }
        });
        _scrollToBottom(false);
      },
      onDone: (doneData) {
        if (!mounted) return;
        setState(() {
          _isLoading = false;
          if (streamingAssistantMsg != null) {
            streamingAssistantMsg!['is_streaming'] = false;
            streamingAssistantMsg!['fuentes'] = doneData['fuentes'];
            streamingAssistantMsg!['es_ia'] = doneData['es_ia'] ?? true;
            streamingAssistantMsg!['es_web'] = doneData['es_web'] ?? false;
            streamingAssistantMsg!['tokens_usados'] = doneData['tokens_usados'] ?? 0;
            streamingAssistantMsg!['metadata_json'] = jsonEncode({
              'herramientas': doneData['herramientas_usadas'] ?? [],
              'tokens': doneData['tokens_usados'] ?? 0,
            });
          }
        });
        _scrollToBottom(false);
      },
      onError: (errorMsg) {
        if (!_isCancelledByUser && mounted) {
          setState(() => _isLoading = false);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Row(
                children: [
                  const Icon(Icons.wifi_off_rounded, color: Colors.white, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      errorMsg,
                      style: GoogleFonts.plusJakartaSans(),
                    ),
                  ),
                ],
              ),
              backgroundColor: Colors.redAccent,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          );
        }
      },
    );

    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _handleDeleteConversation(int conversationId) async {
    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('¿Eliminar conversación?', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
        content: Text(
          'Se borrarán los mensajes de esta sesión de forma permanente.',
          style: GoogleFonts.plusJakartaSans(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text('Cancelar', style: GoogleFonts.plusJakartaSans()),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: Text('Eliminar', style: GoogleFonts.plusJakartaSans(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true && authService.accessToken != null) {
      final ok = await apiService.deleteConversation(conversationId, authService.accessToken!);
      if (ok) {
        setState(() {
          _conversations.removeWhere((c) => c['id'] == conversationId);
          if (_currentConversationId == conversationId) {
            _currentConversationId = _conversations.isNotEmpty ? _conversations[0]['id'] : null;
            _selectedCategory = null;
            _loadMessages();
          }
        });
      }
    }
  }

  void _scrollToBottom([bool immediate = false, bool force = false]) {
    if (_userScrolledUp && !force) return;

    void performScroll() {
      if (_scrollController.hasClients) {
        if (_userScrolledUp && !force) return;
        final maxScroll = _scrollController.position.maxScrollExtent;
        if (immediate) {
          _scrollController.jumpTo(maxScroll);
        } else {
          _scrollController.animateTo(
            maxScroll,
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOutCubic,
          );
        }
      }
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      performScroll();
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final themeProvider = context.watch<ThemeProvider>();
    final authService = context.watch<AuthService>();
    final rawName = _studentName ?? authService.user?['nombre_completo'] ?? authService.user?['primer_nombre'];
    final userName = (rawName != null && rawName.trim().isNotEmpty && rawName != 'Estudiante')
        ? rawName.trim()
        : 'Santiago Obregon';

    return Scaffold(
      drawer: _buildDrawer(isDark, userName),
      appBar: _buildAppBar(context, isDark, themeProvider),
      body: Container(
        color: isDark ? AppTheme.darkBg : const Color(0xFFF8FAFC),
        child: Stack(
          children: [
            // Círculos y marcas de agua decorativas
            Positioned(
              top: -80,
              right: -60,
              child: Container(
                width: 280,
                height: 280,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.uisGreen.withValues(alpha: isDark ? 0.08 : 0.04),
                ),
              ),
            ),
            Positioned(
              bottom: 120,
              left: -50,
              child: Container(
                width: 240,
                height: 240,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.accentCyan.withValues(alpha: isDark ? 0.06 : 0.035),
                ),
              ),
            ),
            Positioned(
              bottom: 130,
              right: 20,
              child: Opacity(
                opacity: isDark ? 0.035 : 0.03,
                child: const Icon(
                  Icons.school_rounded,
                  size: 160,
                  color: AppTheme.uisGreen,
                ),
              ),
            ),

            // Contenido principal del Chat
            Column(
              children: [
                // Lista de Mensajes
                Expanded(
                  child: _isLoadingMessages
                      ? _buildLoadingMessagesIndicator()
                      : _messages.isEmpty
                          ? _buildEmptyState(isDark, userName)
                          : ListView.builder(
                              controller: _scrollController,
                              padding: const EdgeInsets.fromLTRB(14, 12, 14, 20),
                              itemCount: _messages.length + (_isLoading && (_messages.isEmpty || _messages.last['rol'] == 'user') ? 1 : 0),
                              itemBuilder: (context, index) {
                                if (index == _messages.length && _isLoading && (_messages.isEmpty || _messages.last['rol'] == 'user')) {
                                  return _buildThinkingIndicator(isDark);
                                }
                                final message = _messages[index];
                                final isUser = message['rol'] == 'user';
                                final isAi = message['es_ia'] == true ||
                                    (message['tokens_usados'] != null &&
                                        (message['tokens_usados'] as num) > 0);
                                final isWeb = message['es_web'] == true ||
                                    (message['metadata_json'] != null &&
                                        (message['metadata_json'].toString().contains('buscar_informacion_web') ||
                                         message['metadata_json'].toString().contains('leer_pagina_web')));

                                return ChatBubble(
                                  key: ValueKey('msg_${message['id'] ?? index}_${message['created_at'] ?? ''}'),
                                  message: message['contenido'] ?? '',
                                  isUser: isUser,
                                  isAI: isAi,
                                  isWeb: isWeb,
                                  timestamp: message['created_at'] != null
                                      ? _formatTime(message['created_at'])
                                      : null,
                                );
                              },
                            ),
                ),

                // Barra Flotante de Entrada
                _buildInputBar(isDark),
              ],
            ),
          ],
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context, bool isDark, ThemeProvider themeProvider) {
    return AppBar(
      elevation: 0,
      scrolledUnderElevation: 2,
      backgroundColor: isDark ? AppTheme.darkCard : Colors.white,
      surfaceTintColor: Colors.transparent,
      leading: Builder(
        builder: (ctx) => IconButton(
          icon: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.menu_rounded,
              color: isDark ? Colors.white : const Color(0xFF334155),
              size: 20,
            ),
          ),
          onPressed: () => Scaffold.of(ctx).openDrawer(),
        ),
      ),
      title: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.uisGreen.withValues(alpha: 0.35),
                  blurRadius: 8,
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.asset(
                'assets/images/app_logo.jpg',
                fit: BoxFit.cover,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'UIS DYV',
                style: GoogleFonts.outfit(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
              ),
              Row(
                children: [
                  Container(
                    width: 7,
                    height: 7,
                    decoration: const BoxDecoration(
                      color: AppTheme.emeraldNeon,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 5),
                  Text(
                    'En línea • UIS Oficial',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 11,
                      color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
      actions: [
        IconButton(
          icon: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF10B981), Color(0xFF059669)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF10B981).withValues(alpha: 0.4),
                  blurRadius: 8,
                  spreadRadius: 1,
                ),
              ],
            ),
            child: const Center(
              child: Icon(Icons.phone_in_talk_rounded, color: Colors.white, size: 18),
            ),
          ),
          tooltip: 'Llamada de Voz IPRED (100% Gratis)',
          onPressed: () async {
            await Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => VoiceCallScreen(conversationId: _currentConversationId)),
            );
            if (mounted) {
              _loadMessages();
            }
          },
        ),
        IconButton(
          icon: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: isDark ? AppTheme.uisGreen.withValues(alpha: 0.15) : AppTheme.uisGreen.withValues(alpha: 0.12),
              shape: BoxShape.circle,
              border: Border.all(
                color: AppTheme.uisGreen.withValues(alpha: 0.4),
                width: 1.2,
              ),
            ),
            child: const Center(
              child: Icon(Icons.bolt_rounded, color: AppTheme.uisGreen, size: 20),
            ),
          ),
          tooltip: 'Accesos Rápidos Zero-AI (\$0.00 COP)',
          onPressed: () => _showQuickAccessZeroAIModal(context, isDark),
        ),
        IconButton(
          icon: Icon(
            themeProvider.isDarkMode ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
            color: isDark ? AppTheme.accentAmber : const Color(0xFF64748B),
            size: 22,
          ),
          tooltip: 'Cambiar tema',
          onPressed: () => themeProvider.toggleTheme(),
        ),
        IconButton(
          icon: Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppTheme.uisGreen.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.person_rounded, color: AppTheme.uisGreen, size: 20),
          ),
          tooltip: 'Mi Perfil Estudiantil',
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ProfileScreen()),
            );
          },
        ),
        const SizedBox(width: 6),
      ],
    );
  }

  Widget _buildDrawer(bool isDark, String userName) {
    final drawerBg = isDark ? AppTheme.darkBg : Colors.white;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;

    return Drawer(
      backgroundColor: drawerBg,
      child: SafeArea(
        child: Column(
          children: [
            // Cabecera del Drawer
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: borderColor, width: 1)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [AppTheme.uisGreen, AppTheme.uisGreenDark],
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Center(
                      child: Text(
                        userName.isNotEmpty ? userName[0].toUpperCase() : 'U',
                        style: GoogleFonts.outfit(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          userName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.outfit(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                            color: isDark ? Colors.white : const Color(0xFF0F172A),
                          ),
                        ),
                        Text(
                          'Estudiante IPRED',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 12,
                            color: AppTheme.uisGreen,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Botón Nueva Conversación
            Padding(
              padding: const EdgeInsets.all(16),
              child: Container(
                height: 48,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppTheme.uisGreen, AppTheme.uisGreenDark],
                  ),
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.uisGreen.withValues(alpha: 0.3),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: ElevatedButton.icon(
                  onPressed: () {
                    setState(() {
                      _currentConversationId = null;
                      _messages = [];
                      _selectedCategory = null;
                    });
                    Navigator.pop(context);
                  },
                  icon: const Icon(Icons.add_rounded, color: Colors.white, size: 20),
                  label: Text(
                    'Nueva Consulta',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 14.5,
                    ),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.transparent,
                    shadowColor: Colors.transparent,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                ),
              ),
            ),

            // Lista de Conversaciones Anteriores
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'HISTORIAL DE CONSULTAS',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                    color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                  ),
                ),
              ),
            ),

            Expanded(
              child: _isLoadingConversations
                  ? const Center(child: CircularProgressIndicator(color: AppTheme.uisGreen))
                  : _conversations.isEmpty
                      ? Center(
                          child: Text(
                            'No hay consultas guardadas',
                            style: GoogleFonts.plusJakartaSans(
                              color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                              fontSize: 13,
                            ),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          itemCount: _conversations.length,
                          itemBuilder: (context, index) {
                            final c = _conversations[index];
                            final isSelected = _currentConversationId == c['id'];

                            return Container(
                              margin: const EdgeInsets.only(bottom: 6),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? AppTheme.uisGreen.withValues(alpha: 0.12)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(12),
                                border: isSelected
                                    ? Border.all(color: AppTheme.uisGreen.withValues(alpha: 0.4))
                                    : null,
                              ),
                              child: ListTile(
                                dense: true,
                                leading: Icon(
                                  Icons.chat_bubble_outline_rounded,
                                  size: 18,
                                  color: isSelected ? AppTheme.uisGreen : (isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8)),
                                ),
                                title: Text(
                                  c['titulo'] ?? 'Consulta académica',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: GoogleFonts.plusJakartaSans(
                                    fontSize: 13.5,
                                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                    color: isSelected
                                        ? AppTheme.uisGreen
                                        : (isDark ? Colors.white : const Color(0xFF1E293B)),
                                  ),
                                ),
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete_outline_rounded, size: 16),
                                  color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                                  onPressed: () => _handleDeleteConversation(c['id']),
                                ),
                                onTap: () {
                                  setState(() {
                                    _currentConversationId = c['id'];
                                    _selectedCategory = null;
                                    _isLoadingMessages = true;
                                  });
                                  _loadMessages();
                                  Navigator.pop(context);
                                },
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(bool isDark, String userName) {
    if (_selectedCategory != null && _subCategories.containsKey(_selectedCategory)) {
      return _buildSubcategoryView(isDark, _selectedCategory!);
    }
    return _buildHubView(isDark, userName);
  }

  Widget _buildHubView(bool isDark, String userName) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: Column(
        children: [
          const SizedBox(height: 10),
          // AI Glowing Emblem con Logo Oficial de la App
          Container(
            width: 84,
            height: 84,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.uisGreen.withValues(alpha: 0.35),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(24),
              child: Image.asset(
                'assets/images/app_logo.jpg',
                fit: BoxFit.cover,
              ),
            ),
          ).animate().scale(duration: 400.ms, curve: Curves.easeOutBack),

          const SizedBox(height: 18),
          Text(
            '¡Hola, $userName!',
            textAlign: TextAlign.center,
            style: GoogleFonts.outfit(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Explora los servicios del IPRED. Selecciona una categoría para ver consultas oficiales instantáneas sin consumo de IA:',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
              height: 1.4,
            ),
          ),
          const SizedBox(height: 24),

          // Hub Principal de Categorías en Grid
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: _hubCategories.map((card) {
              final isDirect = card['isDirect'] == true;
              final isCalendarModal = card['isCalendarModal'] == true;
              return InkWell(
                onTap: () {
                  if (isCalendarModal) {
                    _showAcademicCalendarModal(context, isDark);
                  } else if (isDirect) {
                    _sendMessage(card['prompt']);
                  } else {
                    setState(() => _selectedCategory = card['id']);
                  }
                },
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  width: (MediaQuery.of(context).size.width - 56) / 2 > 160
                      ? (MediaQuery.of(context).size.width - 56) / 2
                      : double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isCalendarModal
                          ? AppTheme.uisGreen.withValues(alpha: 0.4)
                          : (isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: isDark ? Colors.black.withValues(alpha: 0.2) : Colors.black.withValues(alpha: 0.03),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(card['icon']!, style: const TextStyle(fontSize: 24)),
                          Icon(
                            isCalendarModal
                                ? Icons.calendar_month_rounded
                                : (isDirect ? Icons.bolt_rounded : Icons.chevron_right_rounded),
                            size: 18,
                            color: isCalendarModal
                                ? AppTheme.uisGreen
                                : (isDirect ? AppTheme.accentAmber : (isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8))),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        card['title']!,
                        style: GoogleFonts.outfit(
                          fontSize: 13.5,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        card['subtitle']!,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, duration: 400.ms),
        ],
      ),
    );
  }

  Widget _buildSubcategoryView(bool isDark, String categoryId) {
    final subData = _subCategories[categoryId]!;
    final List<Map<String, String>> items = List<Map<String, String>>.from(subData['items']);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Botón Regresar al Menú Principal
          InkWell(
            onTap: () => setState(() => _selectedCategory = null),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.arrow_back_rounded, size: 16, color: AppTheme.uisGreen),
                  const SizedBox(width: 8),
                  Text(
                    'Volver al Menú Principal',
                    style: GoogleFonts.outfit(
                      fontSize: 12.5,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : const Color(0xFF1E293B),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 18),

          // Título de la Subcategoría
          Row(
            children: [
              Text(subData['icon'] as String, style: const TextStyle(fontSize: 28)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      subData['title'] as String,
                      style: GoogleFonts.outfit(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white : const Color(0xFF0F172A),
                      ),
                    ),
                    Text(
                      subData['description'] as String,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 12,
                        color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.uisGreen.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.uisGreen.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.flash_on_rounded, size: 14, color: AppTheme.uisGreen),
                const SizedBox(width: 6),
                Text(
                  'Consultas oficiales instantáneas (Zero-AI • 0 Tokens)',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.uisGreen,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Grid de Consultas Específicas
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: items.map((item) {
              return InkWell(
                onTap: () => _sendMessage(item['prompt']),
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  width: (MediaQuery.of(context).size.width - 56) / 2 > 160
                      ? (MediaQuery.of(context).size.width - 56) / 2
                      : double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: isDark ? Colors.black.withValues(alpha: 0.2) : Colors.black.withValues(alpha: 0.03),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(item['icon']!, style: const TextStyle(fontSize: 22)),
                      const SizedBox(height: 8),
                      Text(
                        item['title']!,
                        style: GoogleFonts.outfit(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        item['subtitle']!,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.08, duration: 350.ms),
        ],
      ),
    );
  }

  Widget _buildThinkingIndicator(bool isDark) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(top: 8, bottom: 8, left: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppTheme.uisGreen,
              ),
            ),
            const SizedBox(width: 12),
            Text(
              'Consultando información académica...',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 13,
                color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 200.ms);
  }

  Widget _buildLoadingMessagesIndicator() {
    return const Center(
      child: CircularProgressIndicator(color: AppTheme.uisGreen),
    );
  }

  Widget _buildInputBar(bool isDark) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : Colors.white,
        border: Border(
          top: BorderSide(
            color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
            width: 1,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkSurface : AppTheme.lightSurface,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                    width: 1,
                  ),
                ),
                child: TextField(
                  controller: _messageController,
                  enabled: !_isLoading,
                  maxLines: 4,
                  minLines: 1,
                  style: GoogleFonts.plusJakartaSans(
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                    fontSize: 14.5,
                  ),
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _isLoading ? null : _sendMessage(),
                  decoration: InputDecoration(
                    hintText: 'Escribe tu consulta académica...',
                    hintStyle: GoogleFonts.plusJakartaSans(
                      color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                      fontSize: 13.5,
                    ),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: _isLoading
                      ? [const Color(0xFFEF4444), const Color(0xFFDC2626)]
                      : [AppTheme.uisGreen, AppTheme.uisGreenDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: _isLoading
                        ? const Color(0xFFEF4444).withValues(alpha: 0.4)
                        : AppTheme.uisGreen.withValues(alpha: 0.4),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: IconButton(
                icon: _isLoading
                    ? const Icon(Icons.stop_rounded, color: Colors.white, size: 22)
                    : const Icon(Icons.arrow_upward_rounded, color: Colors.white, size: 22),
                tooltip: _isLoading ? 'Detener procesamiento' : 'Enviar mensaje',
                onPressed: _isLoading ? _cancelRequest : () => _sendMessage(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTime(String isoString) {
    try {
      final dt = DateTime.parse(isoString);
      final localDt = dt.isUtc ? dt.toLocal() : dt;
      final hour = localDt.hour;
      final min = localDt.minute.toString().padLeft(2, '0');
      final period = hour >= 12 ? 'PM' : 'AM';
      final hour12 = hour == 0 ? 12 : (hour > 12 ? hour - 12 : hour);
      return '$hour12:$min $period';
    } catch (_) {
      return '';
    }
  }

  void _showAcademicCalendarModal(BuildContext context, bool isDark) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _AcademicCalendarBottomSheet(isDark: isDark),
    );
  }

  void _showQuickAccessZeroAIModal(BuildContext context, bool isDark) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return _QuickAccessZeroAIBottomSheet(
          isDark: isDark,
          hubCategories: _hubCategories,
          subCategories: _subCategories,
          onSendPrompt: (prompt) {
            _sendMessage(prompt);
          },
          onOpenCalendar: () {
            _showAcademicCalendarModal(context, isDark);
          },
        );
      },
    );
  }
}

class _QuickAccessZeroAIBottomSheet extends StatefulWidget {
  final bool isDark;
  final List<Map<String, dynamic>> hubCategories;
  final Map<String, dynamic> subCategories;
  final Function(String) onSendPrompt;
  final VoidCallback onOpenCalendar;

  const _QuickAccessZeroAIBottomSheet({
    required this.isDark,
    required this.hubCategories,
    required this.subCategories,
    required this.onSendPrompt,
    required this.onOpenCalendar,
  });

  @override
  State<_QuickAccessZeroAIBottomSheet> createState() => _QuickAccessZeroAIBottomSheetState();
}

class _QuickAccessZeroAIBottomSheetState extends State<_QuickAccessZeroAIBottomSheet> {
  String? _selectedCategory;

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;

    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: isDark ? AppTheme.darkSurface : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.5 : 0.15),
                blurRadius: 30,
                offset: const Offset(0, -6),
              ),
            ],
          ),
          child: Column(
            children: [
              // Drag Handle
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 8),
                  width: 44,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF334155) : const Color(0xFFCBD5E1),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Header Bar
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 6, 14, 12),
                child: Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [AppTheme.uisGreen, AppTheme.emeraldNeon],
                        ),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Center(
                        child: Icon(Icons.bolt_rounded, color: Colors.white, size: 22),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _selectedCategory == null ? 'Accesos Rápidos Zero-AI' : 'Consultas Zero-AI',
                            style: GoogleFonts.outfit(
                              fontSize: 16.5,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                          ),
                          Text(
                            'Consultas oficiales instantáneas (\$0.00 COP)',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 11.5,
                              color: AppTheme.uisGreen,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 22),
                      color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ),

              const Divider(height: 1),

              // Body: Categories or Subcategory Details
              Expanded(
                child: _selectedCategory == null
                    ? _buildMainCategories(scrollController, isDark)
                    : _buildSubcategoryList(scrollController, isDark, _selectedCategory!),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildMainCategories(ScrollController controller, bool isDark) {
    return ListView(
      controller: controller,
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 24),
      children: [
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: widget.hubCategories.map((card) {
            final isDirect = card['isDirect'] == true;
            final isCalendarModal = card['isCalendarModal'] == true;
            return InkWell(
              onTap: () {
                if (isCalendarModal) {
                  Navigator.pop(context);
                  widget.onOpenCalendar();
                } else if (isDirect) {
                  Navigator.pop(context);
                  widget.onSendPrompt(card['prompt']);
                } else {
                  setState(() => _selectedCategory = card['id']);
                }
              },
              borderRadius: BorderRadius.circular(16),
              child: Container(
                width: (MediaQuery.of(context).size.width - 56) / 2 > 150
                    ? (MediaQuery.of(context).size.width - 56) / 2
                    : double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isCalendarModal
                        ? AppTheme.uisGreen.withValues(alpha: 0.4)
                        : (isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(card['icon']!, style: const TextStyle(fontSize: 22)),
                        Icon(
                          isCalendarModal
                              ? Icons.calendar_month_rounded
                              : (isDirect ? Icons.bolt_rounded : Icons.chevron_right_rounded),
                          size: 16,
                          color: isCalendarModal
                              ? AppTheme.uisGreen
                              : (isDirect ? AppTheme.accentAmber : (isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8))),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      card['title']!,
                      style: GoogleFonts.outfit(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white : const Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      card['subtitle']!,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 10.5,
                        color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildSubcategoryList(ScrollController controller, bool isDark, String categoryId) {
    final subData = widget.subCategories[categoryId] ?? {
      'icon': '📋',
      'title': 'Consultas',
      'description': 'Opciones disponibles',
      'items': <Map<String, String>>[],
    };
    final List<Map<String, String>> items = List<Map<String, String>>.from(subData['items'] ?? []);

    return ListView(
      controller: controller,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
      children: [
        // Back Button
        InkWell(
          onTap: () => setState(() => _selectedCategory = null),
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.arrow_back_rounded, size: 16, color: AppTheme.uisGreen),
                const SizedBox(width: 8),
                Text(
                  'Volver a Categorías',
                  style: GoogleFonts.outfit(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : const Color(0xFF1E293B),
                  ),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 14),

        // Subcategory Title
        Row(
          children: [
            Text(subData['icon'] as String, style: const TextStyle(fontSize: 24)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    subData['title'] as String,
                    style: GoogleFonts.outfit(
                      fontSize: 15.5,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : const Color(0xFF0F172A),
                    ),
                  ),
                  Text(
                    subData['description'] as String,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 11,
                      color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),

        const SizedBox(height: 14),

        // Items List
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: items.map((item) {
            return InkWell(
              onTap: () {
                Navigator.pop(context);
                widget.onSendPrompt(item['prompt']!);
              },
              borderRadius: BorderRadius.circular(14),
              child: Container(
                width: (MediaQuery.of(context).size.width - 56) / 2 > 150
                    ? (MediaQuery.of(context).size.width - 56) / 2
                    : double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item['icon']!, style: const TextStyle(fontSize: 20)),
                    const SizedBox(height: 6),
                    Text(
                      item['title']!,
                      style: GoogleFonts.outfit(
                        fontSize: 12.5,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white : const Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      item['subtitle']!,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 10,
                        color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}

class _AcademicCalendarBottomSheet extends StatefulWidget {
  final bool isDark;

  const _AcademicCalendarBottomSheet({
    required this.isDark,
  });

  @override
  State<_AcademicCalendarBottomSheet> createState() => _AcademicCalendarBottomSheetState();
}

class _AcademicCalendarBottomSheetState extends State<_AcademicCalendarBottomSheet> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  Map<String, dynamic>? _calendarData;
  final Map<String, List<Map<String, dynamic>>> _sessionsByDate = {};

  DateTime _focusedMonth = DateTime(2026, 8, 1);
  DateTime? _selectedDay;

  final List<String> _monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  final List<String> _weekDayNames = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM'];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadCalendar();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  String _formatDateKey(DateTime dt) {
    final y = dt.year.toString();
    final m = dt.month.toString().padLeft(2, '0');
    final d = dt.day.toString().padLeft(2, '0');
    return '$y-$m-$d';
  }

  Future<void> _loadCalendar() async {
    setState(() => _isLoading = true);
    try {
      final authService = context.read<AuthService>();
      final apiService = context.read<ApiService>();
      if (authService.accessToken == null) return;
      final data = await apiService.getAcademicCalendar(authService.accessToken!);
      
      _sessionsByDate.clear();
      final tutorias = (data?['tutorias'] as List<dynamic>?) ?? [];
      for (final t in tutorias) {
        final item = t as Map<String, dynamic>;
        final f = item['fecha_tutoria']?.toString() ?? '';
        if (f.isNotEmpty) {
          _sessionsByDate.putIfAbsent(f, () => []).add(item);
        }
      }

      // Buscar el día más cercano con clases en Agosto 2026 o en el futuro
      DateTime initialFocus = DateTime(2026, 8, 1);
      DateTime? firstClassDay;

      final sortedDates = _sessionsByDate.keys.toList()..sort();
      for (final dStr in sortedDates) {
        final parts = dStr.split('-');
        if (parts.length == 3) {
          final dt = DateTime(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
          if (dt.month == 8 && dt.year == 2026) {
            firstClassDay ??= dt;
          }
        }
      }

      if (firstClassDay != null) {
        initialFocus = DateTime(firstClassDay.year, firstClassDay.month, 1);
        _selectedDay = firstClassDay;
      } else if (sortedDates.isNotEmpty) {
        final parts = sortedDates.first.split('-');
        initialFocus = DateTime(int.parse(parts[0]), int.parse(parts[1]), 1);
        _selectedDay = DateTime(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
      }

      if (mounted) {
        setState(() {
          _calendarData = data;
          _focusedMonth = initialFocus;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _prevMonth() {
    setState(() {
      _focusedMonth = DateTime(_focusedMonth.year, _focusedMonth.month - 1, 1);
      _autoSelectDayInMonth();
    });
  }

  void _nextMonth() {
    setState(() {
      _focusedMonth = DateTime(_focusedMonth.year, _focusedMonth.month + 1, 1);
      _autoSelectDayInMonth();
    });
  }

  void _autoSelectDayInMonth() {
    // Si el mes enfocado tiene clases, selecciona la primera fecha con clases de ese mes
    final mStr = _focusedMonth.month.toString().padLeft(2, '0');
    final yStr = _focusedMonth.year.toString();
    final prefix = '$yStr-$mStr';

    final matchingDates = _sessionsByDate.keys.where((k) => k.startsWith(prefix)).toList()..sort();
    if (matchingDates.isNotEmpty) {
      final parts = matchingDates.first.split('-');
      _selectedDay = DateTime(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
    } else {
      _selectedDay = DateTime(_focusedMonth.year, _focusedMonth.month, 1);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final studentName = _calendarData?['nombre_completo'] ?? 'Estudiante';
    final programName = _calendarData?['programa'] ?? 'IPRED - UIS';
    final hitos = _calendarData?['hitos_institucionales'] as List<dynamic>? ?? [];
    final totalTutorias = _calendarData?['tutorias'] != null ? (_calendarData!['tutorias'] as List).length : 0;

    return DraggableScrollableSheet(
      initialChildSize: 0.90,
      minChildSize: 0.5,
      maxChildSize: 0.96,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: isDark ? AppTheme.darkSurface : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.5 : 0.15),
                blurRadius: 30,
                offset: const Offset(0, -6),
              ),
            ],
          ),
          child: Column(
            children: [
              // Drag Handle
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 8),
                  width: 44,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF334155) : const Color(0xFFCBD5E1),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Top Bar with User Info and Refresh Button
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 4, 14, 8),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [AppTheme.uisGreen, AppTheme.emeraldNeon],
                        ),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Center(
                        child: Icon(Icons.calendar_month_rounded, color: Colors.white, size: 22),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Calendario Académico UIS',
                            style: GoogleFonts.outfit(
                              fontSize: 16.5,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                          ),
                          Text(
                            '$studentName • $programName',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 11.5,
                              color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: 'Actualizar desde base de datos',
                      icon: const Icon(Icons.sync_rounded, size: 20),
                      color: AppTheme.uisGreen,
                      onPressed: _loadCalendar,
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 22),
                      color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ),

              // Tab Bar Switcher
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: TabBar(
                  controller: _tabController,
                  indicator: BoxDecoration(
                    color: AppTheme.uisGreen,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  indicatorSize: TabBarIndicatorSize.tab,
                  dividerColor: Colors.transparent,
                  labelColor: Colors.white,
                  unselectedLabelColor: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  labelStyle: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 12.5),
                  unselectedLabelStyle: GoogleFonts.outfit(fontWeight: FontWeight.w600, fontSize: 12.5),
                  tabs: [
                    Tab(
                      icon: const Icon(Icons.calendar_view_month_rounded, size: 16),
                      text: 'Vista de Calendario ($totalTutorias)',
                    ),
                    Tab(
                      icon: const Icon(Icons.event_note_rounded, size: 16),
                      text: 'Hitos UIS (${hitos.length})',
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 4),

              // Tab View Content
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator(color: AppTheme.uisGreen))
                    : TabBarView(
                        controller: _tabController,
                        children: [
                          // Tab 1: Interactive Monthly Calendar Grid + Selected Day Agenda
                          _buildCalendarMonthView(isDark, scrollController),

                          // Tab 2: Hitos Institucionales
                          ListView.builder(
                            controller: scrollController,
                            padding: const EdgeInsets.fromLTRB(20, 10, 20, 40),
                            itemCount: hitos.length,
                            itemBuilder: (context, index) {
                              final hito = hitos[index] as Map<String, dynamic>;
                              return _buildHitoCard(isDark, hito);
                            },
                          ),
                        ],
                      ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCalendarMonthView(bool isDark, ScrollController scrollController) {
    final year = _focusedMonth.year;
    final month = _focusedMonth.month;
    final daysInMonth = DateTime(year, month + 1, 0).day;
    // Weekday: 1=Mon ... 7=Sun -> offset = weekday - 1
    final firstWeekdayOffset = DateTime(year, month, 1).weekday - 1;

    final selectedKey = _selectedDay != null ? _formatDateKey(_selectedDay!) : '';
    final daySessions = _sessionsByDate[selectedKey] ?? [];

    return ListView(
      controller: scrollController,
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 80),
      children: [
        // Month Navigation Card
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: isDark ? AppTheme.darkCard : const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
          ),
          child: Column(
            children: [
              // Header Selector: < Agosto 2026 >
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    icon: const Icon(Icons.chevron_left_rounded, size: 24),
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                    onPressed: _prevMonth,
                  ),
                  Row(
                    children: [
                      const Icon(Icons.event_available_rounded, size: 18, color: AppTheme.uisGreen),
                      const SizedBox(width: 8),
                      Text(
                        '${_monthNames[month - 1]} $year',
                        style: GoogleFonts.outfit(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.chevron_right_rounded, size: 24),
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                    onPressed: _nextMonth,
                  ),
                ],
              ),

              const SizedBox(height: 6),

              // Weekday Labels: LUN MAR MIÉ JUE VIE SÁB DOM
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: _weekDayNames.map((d) {
                  final isWeekend = (d == 'SÁB' || d == 'DOM');
                  return SizedBox(
                    width: 38,
                    child: Center(
                      child: Text(
                        d,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: isWeekend
                              ? AppTheme.uisGreen
                              : (isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8)),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),

              const SizedBox(height: 8),

              // Days Grid
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 7,
                  mainAxisSpacing: 6,
                  crossAxisSpacing: 6,
                  childAspectRatio: 1.0,
                ),
                itemCount: firstWeekdayOffset + daysInMonth,
                itemBuilder: (context, index) {
                  if (index < firstWeekdayOffset) {
                    return const SizedBox();
                  }
                  final dayNum = index - firstWeekdayOffset + 1;
                  final dayDt = DateTime(year, month, dayNum);
                  final key = _formatDateKey(dayDt);
                  final hasClasses = _sessionsByDate.containsKey(key);
                  final count = _sessionsByDate[key]?.length ?? 0;
                  final isSelected = (_selectedDay != null &&
                      _selectedDay!.year == year &&
                      _selectedDay!.month == month &&
                      _selectedDay!.day == dayNum);

                  return InkWell(
                    onTap: () {
                      setState(() => _selectedDay = dayDt);
                    },
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      decoration: BoxDecoration(
                        color: isSelected
                            ? AppTheme.uisGreen
                            : (hasClasses
                                ? (isDark
                                    ? AppTheme.uisGreen.withValues(alpha: 0.18)
                                    : const Color(0xFFE8F5E9))
                                : Colors.transparent),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected
                              ? AppTheme.emeraldNeon
                              : (hasClasses
                                  ? AppTheme.uisGreen.withValues(alpha: 0.4)
                                  : Colors.transparent),
                          width: isSelected ? 2 : 1,
                        ),
                      ),
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          Text(
                            '$dayNum',
                            style: GoogleFonts.outfit(
                              fontSize: 13.5,
                              fontWeight: (isSelected || hasClasses) ? FontWeight.bold : FontWeight.w500,
                              color: isSelected
                                  ? Colors.white
                                  : (hasClasses
                                      ? (isDark ? AppTheme.emeraldNeon : AppTheme.uisGreenDark)
                                      : (isDark ? const Color(0xFFCBD5E1) : const Color(0xFF334155))),
                            ),
                          ),
                          if (hasClasses && !isSelected)
                            Positioned(
                              bottom: 3,
                              child: Container(
                                width: 5,
                                height: 5,
                                decoration: const BoxDecoration(
                                  color: AppTheme.uisGreen,
                                  shape: BoxShape.circle,
                                ),
                              ),
                            ),
                          if (hasClasses && count > 1 && !isSelected)
                            Positioned(
                              top: 2,
                              right: 2,
                              child: Container(
                                padding: const EdgeInsets.all(2),
                                decoration: const BoxDecoration(
                                  color: AppTheme.uisGreen,
                                  shape: BoxShape.circle,
                                ),
                                child: Text(
                                  '$count',
                                  style: const TextStyle(fontSize: 7, color: Colors.white, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),

        const SizedBox(height: 18),

        // Selected Day Header
        if (_selectedDay != null) ...[
          Row(
            children: [
              const Icon(Icons.event_note_rounded, size: 18, color: AppTheme.uisGreen),
              const SizedBox(width: 8),
              Text(
                'Clases para el ${_selectedDay!.day} de ${_monthNames[_selectedDay!.month - 1]} (${daySessions.length} sesiones):',
                style: GoogleFonts.outfit(
                  fontSize: 14.5,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Day Sessions List
          if (daySessions.isEmpty)
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: isDark ? AppTheme.darkCard : const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
              ),
              child: Center(
                child: Column(
                  children: [
                    const Icon(Icons.wb_sunny_outlined, size: 36, color: AppTheme.accentAmber),
                    const SizedBox(height: 8),
                    Text(
                      'No tienes tutorías programadas para este día.',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 12.5,
                        color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Toca cualquier día con punto verde en el calendario para ver tus clases.',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 11,
                        color: AppTheme.uisGreen,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            ...daySessions.map((session) => _buildTutoriaCard(isDark, session)),
        ],
      ],
    );
  }

  Widget _buildTutoriaCard(bool isDark, Map<String, dynamic> item) {
    final horaIni = (item['hora_inicio']?.toString() ?? '00:00').substring(0, 5);
    final horaFin = (item['hora_fin']?.toString() ?? '00:00').substring(0, 5);
    final teacher = item['profesor']?.toString() ?? 'Docente UIS';
    final email = item['correo_profesor']?.toString();
    final cod = item['codigo_asignatura']?.toString();
    final subject = item['nombre_asignatura']?.toString() ?? 'Tutoría';
    final group = item['grupo']?.toString() ?? '';
    final tipo = item['tipo_tutoria']?.toString() ?? 'Presencial';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.04),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Row: Subject, Code Badge & Group Tag
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  subject,
                  style: GoogleFonts.outfit(
                    fontSize: 13.5,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (cod != null && cod.isNotEmpty) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: isDark ? const Color(0xFF334155) : const Color(0xFFCBD5E1)),
                  ),
                  child: Text(
                    'Cód. $cod',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                    ),
                  ),
                ),
                const SizedBox(width: 5),
              ],
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppTheme.uisGreen.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.uisGreen.withValues(alpha: 0.3)),
                ),
                child: Text(
                  'Gr. $group',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 10.5,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.uisGreen,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Time & Modality Row
          Row(
            children: [
              const Icon(Icons.access_time_rounded, size: 14, color: AppTheme.accentAmber),
              const SizedBox(width: 5),
              Text(
                '$horaIni - $horaFin',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF334155),
                ),
              ),
              const SizedBox(width: 14),
              Icon(
                tipo.toLowerCase().contains('virtual') ? Icons.laptop_rounded : Icons.location_on_rounded,
                size: 14,
                color: AppTheme.uisGreen,
              ),
              const SizedBox(width: 4),
              Text(
                tipo,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 11.5,
                  color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                ),
              ),
            ],
          ),

          const SizedBox(height: 6),

          // Teacher Name
          Row(
            children: [
              const Icon(Icons.person_rounded, size: 14, color: Color(0xFF94A3B8)),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  teacher,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w500,
                    color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569),
                  ),
                ),
              ),
            ],
          ),

          // Email Clickable Chip
          if (email != null && email.isNotEmpty) ...[
            const SizedBox(height: 6),
            InkWell(
              onTap: () => _handleEmailClick(email),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF0284C7).withValues(alpha: 0.25)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.mail_outline_rounded, size: 12, color: Color(0xFF0284C7)),
                    const SizedBox(width: 5),
                    Text(
                      email,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 11,
                        color: const Color(0xFF0284C7),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildHitoCard(bool isDark, Map<String, dynamic> hito) {
    final icon = hito['icono']?.toString() ?? '📌';
    final fecha = hito['fecha']?.toString() ?? '';
    final titulo = hito['titulo']?.toString() ?? '';
    final desc = hito['descripcion']?.toString() ?? '';
    final tipo = hito['tipo']?.toString() ?? '';

    Color badgeColor = AppTheme.uisGreen;
    if (tipo == 'tramite') badgeColor = AppTheme.accentAmber;
    if (tipo == 'cierre') badgeColor = const Color(0xFFE11D48);
    if (tipo == 'grado') badgeColor = const Color(0xFF8B5CF6);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.darkCard : AppTheme.lightCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: badgeColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: badgeColor.withValues(alpha: 0.3)),
            ),
            child: Center(child: Text(icon, style: const TextStyle(fontSize: 20))),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: badgeColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    fecha,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: badgeColor,
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  titulo,
                  style: GoogleFonts.outfit(
                    fontSize: 13.5,
                    fontWeight: FontWeight.bold,
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  desc,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 11.5,
                    color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _handleEmailClick(String email) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: widget.isDark ? AppTheme.darkSurface : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Opciones de Correo Docente',
              style: GoogleFonts.outfit(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              email,
              style: GoogleFonts.plusJakartaSans(fontSize: 13, color: AppTheme.uisGreen),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.mail_rounded, color: AppTheme.uisGreen),
              title: Text('Abrir en cliente de correo', style: GoogleFonts.plusJakartaSans(fontSize: 13)),
              onTap: () {
                Navigator.pop(ctx);
                launchUrl(Uri.parse('mailto:$email'));
              },
            ),
            ListTile(
              leading: const Icon(Icons.copy_rounded, color: Color(0xFF0284C7)),
              title: Text('Copiar dirección al portapapeles', style: GoogleFonts.plusJakartaSans(fontSize: 13)),
              onTap: () {
                Navigator.pop(ctx);
                Clipboard.setData(ClipboardData(text: email));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Correo copiado al portapapeles'),
                    backgroundColor: AppTheme.uisGreen,
                    duration: Duration(seconds: 2),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
