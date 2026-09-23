import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../services/local_zero_ai_service.dart';
import '../services/voice_service.dart';
import '../theme/app_theme.dart';

class VoiceCallScreen extends StatefulWidget {
  final int? conversationId;
  const VoiceCallScreen({super.key, this.conversationId});

  @override
  State<VoiceCallScreen> createState() => _VoiceCallScreenState();
}

class _VoiceCallScreenState extends State<VoiceCallScreen> with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _waveController;
  late AnimationController _barsController;
  late Animation<double> _pulseAnimation;

  final VoiceService _voiceService = VoiceService();

  final List<Map<String, dynamic>> _suggestedTopics = [
    {'icon': '⏰', 'label': 'Próximas tutorías', 'query': '¿Cuándo y a qué hora son mis próximas tutorías?'},
    {'icon': '📚', 'label': 'Mis asignaturas', 'query': '¿Cuáles son mis materias matriculadas y profesores?'},
    {'icon': '📝', 'label': 'Cancelar materia', 'query': '¿Cuál es el plazo y cómo cancelo una materia en la UIS?'},
    {'icon': '📜', 'label': 'Paz y Salvo / Grado', 'query': '¿Qué paz y salvos y requisitos necesito para grado?'},
  ];

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);

    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();

    _barsController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.94, end: 1.14).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startVoiceCall();
    });
  }

  void _startVoiceCall() {
    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();
    final zeroAiService = LocalZeroAiService();

    final user = authService.user;
    final studentName = user?['nombre_completo'] ?? user?['primer_nombre'] ?? 'Estudiante';

    _voiceService.startCall(
      apiService: apiService,
      zeroAiService: zeroAiService,
      token: authService.accessToken,
      conversationId: widget.conversationId,
      studentName: studentName,
      studentData: user,
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _waveController.dispose();
    _barsController.dispose();
    _voiceService.endCall();
    super.dispose();
  }

  Color _getStatusColor(VoiceCallStatus status) {
    switch (status) {
      case VoiceCallStatus.listening:
        return const Color(0xFF10B981); // Esmeralda UIS
      case VoiceCallStatus.speaking:
        return const Color(0xFF06B6D4); // Cyan vibrante
      case VoiceCallStatus.thinking:
        return const Color(0xFFF59E0B); // Ámbar
      case VoiceCallStatus.muted:
        return const Color(0xFFEF4444); // Rojo
      case VoiceCallStatus.connecting:
        return const Color(0xFF8B5CF6); // Púrpura
      case VoiceCallStatus.error:
        return Colors.redAccent;
      case VoiceCallStatus.ended:
      case VoiceCallStatus.idle:
        return Colors.grey;
    }
  }

  String _getStatusText(VoiceCallStatus status) {
    switch (status) {
      case VoiceCallStatus.connecting:
        return 'Conectando llamada con IPRED...';
      case VoiceCallStatus.listening:
        return 'Te escucho, habla libremente...';
      case VoiceCallStatus.thinking:
        return 'Consultando sistema académico...';
      case VoiceCallStatus.speaking:
        return 'IPRED está respondiendo...';
      case VoiceCallStatus.muted:
        return 'Micrófono silenciado';
      case VoiceCallStatus.error:
        return 'Error en la llamada';
      case VoiceCallStatus.ended:
        return 'Llamada finalizada';
      case VoiceCallStatus.idle:
        return 'En espera';
    }
  }

  IconData _getStatusIcon(VoiceCallStatus status) {
    switch (status) {
      case VoiceCallStatus.connecting:
        return Icons.phone_in_talk_rounded;
      case VoiceCallStatus.listening:
        return Icons.mic_rounded;
      case VoiceCallStatus.thinking:
        return Icons.psychology_rounded;
      case VoiceCallStatus.speaking:
        return Icons.volume_up_rounded;
      case VoiceCallStatus.muted:
        return Icons.mic_off_rounded;
      case VoiceCallStatus.error:
        return Icons.error_outline_rounded;
      case VoiceCallStatus.ended:
      case VoiceCallStatus.idle:
        return Icons.call_end_rounded;
    }
  }

  void _showTranscriptHistorySheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0F1A15),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        final messages = _voiceService.messages;
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Transcripción de la Llamada',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(ctx),
                    icon: const Icon(Icons.close_rounded, color: Colors.white70),
                  ),
                ],
              ),
              const Divider(color: Colors.white12),
              Expanded(
                child: messages.isEmpty
                  ? Center(
                      child: Text(
                        'Aún no hay transcripciones.',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.4)),
                      ),
                    )
                  : ListView.builder(
                      itemCount: messages.length,
                      itemBuilder: (context, index) {
                        final msg = messages[index];
                        final isBot = msg.sender == 'bot';
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 6),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: const EdgeInsets.all(6),
                                decoration: BoxDecoration(
                                  color: isBot ? const Color(0xFF06B6D4).withValues(alpha: 0.2) : const Color(0xFF10B981).withValues(alpha: 0.2),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  isBot ? Icons.smart_toy_rounded : Icons.person_rounded,
                                  color: isBot ? const Color(0xFF06B6D4) : const Color(0xFF10B981),
                                  size: 16,
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      isBot ? 'IPRED UIS' : 'Tú',
                                      style: TextStyle(
                                        color: isBot ? const Color(0xFF06B6D4) : const Color(0xFF10B981),
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      msg.text,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 13.5,
                                        height: 1.35,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _voiceService,
      builder: (context, _) {
        final status = _voiceService.status;
        final statusColor = _getStatusColor(status);
        final statusText = _getStatusText(status);
        final statusIcon = _getStatusIcon(status);

        return Scaffold(
          backgroundColor: const Color(0xFF080E0C), // Ultra deep dark UIS canvas
          body: SafeArea(
            child: Stack(
              children: [
                // Fondo decorativo con gradientes radiales
                Positioned.fill(
                  child: CustomPaint(
                    painter: _CallBackgroundGlowPainter(color: statusColor),
                  ),
                ),

                // Contenido principal
                Column(
                  children: [
                    // 1. Barra Superior con Título, Duración y Botón de Transcripción
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          IconButton(
                            onPressed: () {
                              _voiceService.endCall();
                              Navigator.of(context).pop();
                            },
                            icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white70, size: 20),
                          ),
                          Column(
                            children: [
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 8,
                                    height: 8,
                                    decoration: BoxDecoration(
                                      color: statusColor,
                                      shape: BoxShape.circle,
                                      boxShadow: [
                                        BoxShadow(color: statusColor.withValues(alpha: 0.7), blurRadius: 8, spreadRadius: 2),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Llamada de Voz IPRED',
                                    style: GoogleFonts.outfit(
                                      color: Colors.white,
                                      fontSize: 16,
                                      fontWeight: FontWeight.w600,
                                      letterSpacing: 0.3,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 3),
                              Text(
                                _voiceService.formattedDuration,
                                style: GoogleFonts.plusJakartaSans(
                                  color: Colors.white.withValues(alpha: 0.65),
                                  fontSize: 13,
                                  fontFeatures: const [FontFeature.tabularFigures()],
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                          IconButton(
                            onPressed: () => _showTranscriptHistorySheet(context),
                            icon: Container(
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.08),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(Icons.subtitles_rounded, color: Colors.white70, size: 18),
                            ),
                            tooltip: 'Ver Transcripción',
                          ),
                        ],
                      ),
                    ),

                    const Spacer(flex: 1),

                    // 2. Orbe Central de Audio y Ondas Animadas
                    Center(
                      child: SizedBox(
                        width: 250,
                        height: 250,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            // Ondas expansivas concéntricas
                            if (status == VoiceCallStatus.listening || status == VoiceCallStatus.speaking)
                              AnimatedBuilder(
                                animation: _waveController,
                                builder: (context, child) {
                                  return CustomPaint(
                                    size: const Size(250, 250),
                                    painter: _SoundWaveRipplesPainter(
                                      animationValue: _waveController.value,
                                      color: statusColor,
                                    ),
                                  );
                                },
                              ),

                            // Orbe central con respiración
                            ScaleTransition(
                              scale: (status == VoiceCallStatus.listening || status == VoiceCallStatus.speaking)
                                  ? _pulseAnimation
                                  : const AlwaysStoppedAnimation(1.0),
                              child: Container(
                                width: 135,
                                height: 135,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: RadialGradient(
                                    colors: [
                                      statusColor.withValues(alpha: 0.95),
                                      statusColor.withValues(alpha: 0.35),
                                      const Color(0xFF0F1A15),
                                    ],
                                    stops: const [0.3, 0.7, 1.0],
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: statusColor.withValues(alpha: 0.5),
                                      blurRadius: 40,
                                      spreadRadius: 8,
                                    ),
                                  ],
                                  border: Border.all(
                                    color: statusColor.withValues(alpha: 0.6),
                                    width: 2.5,
                                  ),
                                ),
                                child: Center(
                                  child: Icon(
                                    statusIcon,
                                    size: 50,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: 16),

                    // Ecualizador de Barras de Frecuencia
                    if (status == VoiceCallStatus.listening || status == VoiceCallStatus.speaking)
                      AnimatedBuilder(
                        animation: _barsController,
                        builder: (context, _) {
                          return Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: List.generate(12, (index) {
                              final waveOffset = math.sin((_barsController.value * math.pi * 2) + (index * 0.5));
                              final height = 8.0 + (waveOffset.abs() * 22.0);
                              return Container(
                                margin: const EdgeInsets.symmetric(horizontal: 2.5),
                                width: 3.5,
                                height: height,
                                decoration: BoxDecoration(
                                  color: statusColor.withValues(alpha: 0.7 + (waveOffset.abs() * 0.3)),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                              );
                            }),
                          );
                        },
                      )
                    else
                      const SizedBox(height: 30),

                    const SizedBox(height: 16),

                    // Badge de Estado Actual
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 7),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: statusColor.withValues(alpha: 0.3), width: 1),
                      ),
                      child: Text(
                        statusText,
                        textAlign: TextAlign.center,
                        style: GoogleFonts.plusJakartaSans(
                          color: statusColor,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),

                    const Spacer(flex: 1),

                    // 3. Tarjeta de Transcripción / Subtítulos en Vivo
                    Container(
                      margin: const EdgeInsets.symmetric(horizontal: 20),
                      padding: const EdgeInsets.all(14),
                      constraints: const BoxConstraints(minHeight: 80, maxHeight: 120),
                      decoration: BoxDecoration(
                        color: const Color(0xFF122019).withValues(alpha: 0.75),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.4),
                            blurRadius: 16,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: SingleChildScrollView(
                        reverse: true,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (_voiceService.currentWords.isNotEmpty) ...[
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    children: [
                                      const Icon(Icons.mic, size: 14, color: Color(0xFF10B981)),
                                      const SizedBox(width: 6),
                                      Text(
                                        'Tú (hablando...):',
                                        style: TextStyle(
                                          color: const Color(0xFF10B981).withValues(alpha: 0.9),
                                          fontSize: 11.5,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ],
                                  ),
                                  InkWell(
                                    onTap: () => _voiceService.submitCurrentSpeech(),
                                    borderRadius: BorderRadius.circular(12),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF10B981).withValues(alpha: 0.25),
                                        borderRadius: BorderRadius.circular(12),
                                        border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.5), width: 1),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          const Text(
                                            'Enviar ya',
                                            style: TextStyle(
                                              color: Color(0xFF10B981),
                                              fontSize: 11,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                          const SizedBox(width: 4),
                                          const Icon(Icons.send_rounded, size: 11, color: Color(0xFF10B981)),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 3),
                              Text(
                                _voiceService.currentWords,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 13.5,
                                  height: 1.35,
                                ),
                              ),
                            ] else if (_voiceService.lastBotResponse.isNotEmpty) ...[
                              Row(
                                children: [
                                  const Icon(Icons.smart_toy_rounded, size: 14, color: Color(0xFF06B6D4)),
                                  const SizedBox(width: 6),
                                  Text(
                                    'IPRED UIS:',
                                    style: TextStyle(
                                      color: const Color(0xFF06B6D4).withValues(alpha: 0.9),
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 3),
                              Text(
                                _voiceService.lastBotResponse,
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.9),
                                  fontSize: 13,
                                  height: 1.35,
                                ),
                              ),
                            ] else ...[
                              Center(
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 6),
                                  child: Text(
                                    'Habla con naturalidad o toca una sugerencia rápida...',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      color: Colors.white.withValues(alpha: 0.45),
                                      fontSize: 12.5,
                                      fontStyle: FontStyle.italic,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: 12),

                    // 4. Chips de Preguntas Frecuentes Rápidas (Interactivas)
                    SizedBox(
                      height: 38,
                      child: ListView.builder(
                        scrollDirection: Axis.horizontal,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: _suggestedTopics.length,
                        itemBuilder: (context, index) {
                          final topic = _suggestedTopics[index];
                          return Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ActionChip(
                              backgroundColor: Colors.white.withValues(alpha: 0.07),
                              side: BorderSide(color: Colors.white.withValues(alpha: 0.12)),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                              label: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(topic['icon'] as String, style: const TextStyle(fontSize: 13)),
                                  const SizedBox(width: 6),
                                  Text(
                                    topic['label'] as String,
                                    style: GoogleFonts.plusJakartaSans(
                                      color: Colors.white.withValues(alpha: 0.85),
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                              onPressed: () {
                                _voiceService.sendSuggestedQuery(topic['query'] as String);
                              },
                            ),
                          );
                        },
                      ),
                    ),

                    const Spacer(flex: 1),

                    // 5. Barra de Controles de Llamada (Mute, Colgar, Altavoz)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 28, left: 24, right: 24),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          // Botón Silenciar Micrófono
                          _CallControlButton(
                            icon: _voiceService.isMuted ? Icons.mic_off_rounded : Icons.mic_rounded,
                            label: _voiceService.isMuted ? 'Silenciado' : 'Silenciar',
                            isActive: _voiceService.isMuted,
                            activeColor: Colors.redAccent,
                            onTap: () => _voiceService.toggleMute(),
                          ),

                          // Botón Colgar (Rojo Circular Prominente)
                          GestureDetector(
                            onTap: () {
                              _voiceService.endCall();
                              Navigator.of(context).pop();
                            },
                            child: Container(
                              width: 72,
                              height: 72,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFF3B30), Color(0xFFD32F2F)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFFFF3B30).withValues(alpha: 0.5),
                                    blurRadius: 20,
                                    spreadRadius: 2,
                                    offset: const Offset(0, 4),
                                  ),
                                ],
                              ),
                              child: const Center(
                                child: Icon(
                                  Icons.call_end_rounded,
                                  color: Colors.white,
                                  size: 34,
                                ),
                              ),
                            ),
                          ),

                          // Botón Altavoz
                          _CallControlButton(
                            icon: _voiceService.isSpeakerOn ? Icons.volume_up_rounded : Icons.volume_mute_rounded,
                            label: _voiceService.isSpeakerOn ? 'Altavoz' : 'Auricular',
                            isActive: _voiceService.isSpeakerOn,
                            activeColor: AppTheme.uisGreen,
                            onTap: () => _voiceService.toggleSpeaker(),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _CallControlButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final Color activeColor;
  final VoidCallback onTap;

  const _CallControlButton({
    required this.icon,
    required this.label,
    required this.isActive,
    required this.activeColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(30),
          child: Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isActive ? activeColor.withValues(alpha: 0.2) : Colors.white.withValues(alpha: 0.08),
              border: Border.all(
                color: isActive ? activeColor : Colors.white.withValues(alpha: 0.15),
                width: 1.5,
              ),
            ),
            child: Icon(
              icon,
              color: isActive ? activeColor : Colors.white70,
              size: 25,
            ),
          ),
        ),
        const SizedBox(height: 7),
        Text(
          label,
          style: GoogleFonts.plusJakartaSans(
            color: Colors.white.withValues(alpha: 0.7),
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

class _SoundWaveRipplesPainter extends CustomPainter {
  final double animationValue;
  final Color color;

  _SoundWaveRipplesPainter({
    required this.animationValue,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2;

    for (int i = 0; i < 3; i++) {
      final waveProgress = (animationValue + (i / 3)) % 1.0;
      final radius = 68 + (maxRadius - 68) * waveProgress;
      final opacity = (1.0 - waveProgress).clamp(0.0, 1.0) * 0.45;

      final paint = Paint()
        ..color = color.withValues(alpha: opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0;

      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _SoundWaveRipplesPainter oldDelegate) {
    return oldDelegate.animationValue != animationValue || oldDelegate.color != color;
  }
}

class _CallBackgroundGlowPainter extends CustomPainter {
  final Color color;

  _CallBackgroundGlowPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height * 0.40);

    final glowPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          color.withValues(alpha: 0.20),
          color.withValues(alpha: 0.06),
          Colors.transparent,
        ],
        stops: const [0.0, 0.5, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: size.width * 0.65));

    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), glowPaint);
  }

  @override
  bool shouldRepaint(covariant _CallBackgroundGlowPainter oldDelegate) {
    return oldDelegate.color != color;
  }
}
