import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _isRegistering = false;
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();

  bool _isLoading = false;
  bool _showPassword = false;
  String? _errorMessage;
  String? _successMessage;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text.trim();

    if (username.isEmpty || password.isEmpty) {
      setState(() => _errorMessage = 'Por favor completa los campos requeridos');
      return;
    }

    if (_isRegistering && password.length < 6) {
      setState(() => _errorMessage = 'La contraseña debe tener al menos 6 caracteres');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    final authService = context.read<AuthService>();

    if (_isRegistering) {
      final success = await authService.register(
        username,
        password,
        _emailController.text.trim(),
        _nameController.text.trim(),
      );

      if (!mounted) return;
      setState(() => _isLoading = false);

      if (success) {
        setState(() {
          _isRegistering = false;
          _successMessage = '¡Cuenta registrada con éxito! Ingresa con tus credenciales.';
        });
      } else {
        setState(() => _errorMessage = 'No se pudo completar el registro. Verifica los datos.');
      }
    } else {
      final loginError = await authService.loginWithDetails(username, password);

      if (!mounted) return;
      setState(() => _isLoading = false);

      if (loginError != null) {
        setState(() => _errorMessage = loginError);
      }
    }
  }

  void _showServerConfigDialog(BuildContext context, bool isDark) {
    final urlController = TextEditingController(text: ApiService.currentBaseUrl);
    bool isTesting = false;
    bool? testResult;
    String? testMessage;

    showDialog(
      context: context,
      builder: (dialogCtx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.uisGreen.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.dns_rounded, color: AppTheme.uisGreen, size: 22),
              ),
              const SizedBox(width: 12),
              Text(
                'Servidor / IP',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Si accedes desde tu celular en la misma red Wi-Fi, ingresa la IP de tu PC:',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 12.5,
                    color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: urlController,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 13,
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                  ),
                  decoration: InputDecoration(
                    labelText: 'URL Base del Servidor',
                    hintText: 'http://10.13.181.2:3000',
                    prefixIcon: const Icon(Icons.link_rounded, size: 20, color: AppTheme.uisGreen),
                    filled: true,
                    fillColor: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    ActionChip(
                      label: Text('WiFi (Puerto 3000)', style: GoogleFonts.plusJakartaSans(fontSize: 11)),
                      backgroundColor: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                      onPressed: () {
                        setDialogState(() {
                          urlController.text = 'http://10.13.181.2:3000';
                          testResult = null;
                        });
                      },
                    ),
                    ActionChip(
                      label: Text('WiFi (Puerto 8000)', style: GoogleFonts.plusJakartaSans(fontSize: 11)),
                      backgroundColor: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                      onPressed: () {
                        setDialogState(() {
                          urlController.text = 'http://10.13.181.2:8000';
                          testResult = null;
                        });
                      },
                    ),
                    ActionChip(
                      label: Text('Cloudflare', style: GoogleFonts.plusJakartaSans(fontSize: 11)),
                      backgroundColor: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                      onPressed: () {
                        setDialogState(() {
                          urlController.text = 'https://ipred.pasteleriamiranda.art';
                          testResult = null;
                        });
                      },
                    ),
                  ],
                ),
                if (testMessage != null) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: (testResult ?? false)
                          ? AppTheme.uisGreen.withValues(alpha: 0.12)
                          : Colors.redAccent.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: (testResult ?? false) ? AppTheme.uisGreen : Colors.redAccent,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          (testResult ?? false) ? Icons.check_circle_rounded : Icons.error_rounded,
                          size: 18,
                          color: (testResult ?? false) ? AppTheme.uisGreen : Colors.redAccent,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            testMessage!,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
                              color: (testResult ?? false) ? AppTheme.uisGreen : Colors.redAccent,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton.icon(
              icon: isTesting
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.uisGreen),
                    )
                  : const Icon(Icons.network_check_rounded, size: 18),
              label: Text(
                'Probar Conexión',
                style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
              ),
              onPressed: isTesting
                  ? null
                  : () async {
                      setDialogState(() {
                        isTesting = true;
                        testResult = null;
                        testMessage = null;
                      });
                      final ok = await ApiService.testConnection(urlController.text);
                      setDialogState(() {
                        isTesting = false;
                        testResult = ok;
                        testMessage = ok
                            ? '✅ Servidor respondiendo correctamente'
                            : '❌ No se pudo conectar a este puerto/IP';
                      });
                    },
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.uisGreen,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () async {
                final newUrl = urlController.text.trim();
                await ApiService.saveBaseUrl(newUrl);
                if (dialogCtx.mounted) {
                  Navigator.of(dialogCtx).pop();
                }
                if (mounted) {
                  setState(() {
                    _successMessage = 'Servidor actualizado a: ${ApiService.currentBaseUrl}';
                  });
                }
              },
              child: const Text('Guardar'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: Stack(
        children: [
          // Fondo ambiental con orbes de luz
          Container(
            width: double.infinity,
            height: double.infinity,
            color: isDark ? AppTheme.darkBg : AppTheme.lightBg,
          ),
          Positioned(
            top: -100,
            left: -100,
            child: Container(
              width: 350,
              height: 350,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.uisGreen.withValues(alpha: isDark ? 0.15 : 0.12),
              ),
            ),
          ),
          Positioned(
            bottom: -50,
            right: -50,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.accentCyan.withValues(alpha: isDark ? 0.12 : 0.08),
              ),
            ),
          ),

          // Botón de configuración de servidor / IP
          Positioned(
            top: 16,
            right: 16,
            child: SafeArea(
              child: Container(
                decoration: BoxDecoration(
                  color: isDark
                      ? const Color(0xFF1E293B).withValues(alpha: 0.85)
                      : Colors.white.withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                  ),
                ),
                child: IconButton(
                  icon: const Icon(Icons.dns_rounded, size: 20),
                  tooltip: 'Configurar Servidor / IP',
                  color: AppTheme.uisGreen,
                  onPressed: () => _showServerConfigDialog(context, isDark),
                ),
              ),
            ),
          ),

          // Contenido con scroll
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 440),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Logo y Encabezado UIS
                      _buildHeader(isDark),
                      const SizedBox(height: 28),

                      // Tarjeta Glassmorphic
                      _buildFormCard(isDark),
                      const SizedBox(height: 20),

                      // Footer institucional
                      Text(
                        'Instituto de Proyección Regional y Educación a Distancia\nUniversidad Industrial de Santander',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(bool isDark) {
    return Column(
      children: [
        // Emblema con Logo Oficial de la App
        Container(
          width: 86,
          height: 86,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: AppTheme.uisGreen.withValues(alpha: 0.4),
                blurRadius: 22,
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
        ).animate().scale(begin: const Offset(0.9, 0.9), end: const Offset(1, 1), duration: 500.ms, curve: Curves.easeOutBack),
        const SizedBox(height: 16),
        Text(
          'UIS DYV',
          style: GoogleFonts.outfit(
            fontSize: 26,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
            color: isDark ? Colors.white : const Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: AppTheme.uisGreen.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            'ASISTENTE VIRTUAL UNIVERSITARIO',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 10.5,
              fontWeight: FontWeight.w700,
              color: AppTheme.uisGreen,
              letterSpacing: 1.0,
            ),
          ),
        ),
      ],
    ).animate().fadeIn(duration: 400.ms).slideY(begin: -0.1, duration: 400.ms);
  }

  Widget _buildFormCard(bool isDark) {
    final cardBg = isDark ? AppTheme.darkCard : AppTheme.lightCard;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;

    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: borderColor, width: 1.2),
        boxShadow: [
          BoxShadow(
            color: isDark ? Colors.black.withValues(alpha: 0.4) : Colors.black.withValues(alpha: 0.06),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      padding: const EdgeInsets.all(26),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Selector Deslizante de Pestañas
          _buildSegmentedTab(isDark),
          const SizedBox(height: 24),

          // Alerta de Error / Éxito
          if (_errorMessage != null) _buildAlertMessage(_errorMessage!, isError: true),
          if (_successMessage != null) _buildAlertMessage(_successMessage!, isError: false),

          // Campos del Formulario
          if (_isRegistering) ...[
            _buildInputField(
              controller: _nameController,
              label: 'Nombre Completo',
              icon: Icons.person_outline_rounded,
              isDark: isDark,
            ),
            const SizedBox(height: 16),
            _buildInputField(
              controller: _emailController,
              label: 'Correo Electrónico',
              icon: Icons.alternate_email_rounded,
              keyboardType: TextInputType.emailAddress,
              isDark: isDark,
            ),
            const SizedBox(height: 16),
          ],

          _buildInputField(
            controller: _usernameController,
            label: 'Código de Estudiante UIS',
            hint: 'Ej. 2226666',
            icon: Icons.badge_outlined,
            keyboardType: TextInputType.number,
            isDark: isDark,
          ),
          const SizedBox(height: 16),

          _buildInputField(
            controller: _passwordController,
            label: 'Contraseña',
            icon: Icons.lock_outline_rounded,
            obscureText: !_showPassword,
            isDark: isDark,
            suffixIcon: IconButton(
              icon: Icon(
                _showPassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                size: 20,
              ),
              onPressed: () => setState(() => _showPassword = !_showPassword),
            ),
          ),
          const SizedBox(height: 24),

          // Botón Principal
          _buildSubmitButton(),
          const SizedBox(height: 16),

          // Nota de ayuda para estudiante
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline_rounded, size: 18, color: AppTheme.uisGreen),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Acceso oficial para estudiantes activos del IPRED - UIS',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 11.5,
                      color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF475569),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, duration: 400.ms);
  }

  Widget _buildSegmentedTab(bool isDark) {
    return Container(
      height: 48,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF0B0F19) : const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() {
                _isRegistering = false;
                _errorMessage = null;
                _successMessage = null;
              }),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                decoration: BoxDecoration(
                  color: !_isRegistering
                      ? (isDark ? AppTheme.darkCard : Colors.white)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: !_isRegistering
                      ? [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.06),
                            blurRadius: 8,
                          ),
                        ]
                      : null,
                ),
                child: Center(
                  child: Text(
                    'Iniciar Sesión',
                    style: GoogleFonts.outfit(
                      fontSize: 13.5,
                      fontWeight: !_isRegistering ? FontWeight.bold : FontWeight.w500,
                      color: !_isRegistering
                          ? AppTheme.uisGreen
                          : (isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8)),
                    ),
                  ),
                ),
              ),
            ),
          ),
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() {
                _isRegistering = true;
                _errorMessage = null;
                _successMessage = null;
              }),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                decoration: BoxDecoration(
                  color: _isRegistering
                      ? (isDark ? AppTheme.darkCard : Colors.white)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: _isRegistering
                      ? [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.06),
                            blurRadius: 8,
                          ),
                        ]
                      : null,
                ),
                child: Center(
                  child: Text(
                    'Registrarme',
                    style: GoogleFonts.outfit(
                      fontSize: 13.5,
                      fontWeight: _isRegistering ? FontWeight.bold : FontWeight.w500,
                      color: _isRegistering
                          ? AppTheme.uisGreen
                          : (isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8)),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInputField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    String? hint,
    bool obscureText = false,
    TextInputType? keyboardType,
    Widget? suffixIcon,
    required bool isDark,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 12.5,
            fontWeight: FontWeight.w600,
            color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF334155),
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          style: GoogleFonts.plusJakartaSans(
            color: isDark ? Colors.white : const Color(0xFF0F172A),
            fontSize: 14.5,
          ),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: GoogleFonts.plusJakartaSans(
              color: isDark ? const Color(0xFF475569) : const Color(0xFF94A3B8),
              fontSize: 13.5,
            ),
            prefixIcon: Icon(icon, color: AppTheme.uisGreen, size: 20),
            suffixIcon: suffixIcon,
          ),
        ),
      ],
    );
  }

  Widget _buildAlertMessage(String text, {required bool isError}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: isError ? Colors.redAccent.withValues(alpha: 0.12) : AppTheme.uisGreen.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isError ? Colors.redAccent.withValues(alpha: 0.4) : AppTheme.uisGreen.withValues(alpha: 0.4),
        ),
      ),
      child: Row(
        children: [
          Icon(
            isError ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
            color: isError ? Colors.redAccent : AppTheme.uisGreen,
            size: 18,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 12.5,
                color: isError ? Colors.redAccent : AppTheme.uisGreen,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSubmitButton() {
    return Container(
      height: 52,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.uisGreen, AppTheme.uisGreenDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: AppTheme.uisGreen.withValues(alpha: 0.4),
            blurRadius: 14,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: ElevatedButton(
        onPressed: _isLoading ? null : _handleSubmit,
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.transparent,
          shadowColor: Colors.transparent,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: _isLoading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _isRegistering ? 'Crear Cuenta' : 'Entrar al Chatbot',
                    style: GoogleFonts.outfit(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 20),
                ],
              ),
      ),
    );
  }
}
