import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../theme/theme_provider.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _profile;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    final authService = context.read<AuthService>();
    final apiService = context.read<ApiService>();

    if (authService.accessToken == null) return;

    final profile = await apiService.getProfile(authService.accessToken!);

    if (profile != null && mounted) {
      setState(() {
        _profile = profile;
        _isLoading = false;
      });
    } else if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _handleLogout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('¿Cerrar sesión?', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
        content: Text(
          'Tendrás que ingresar tu código de estudiante y contraseña de nuevo.',
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
            child: Text('Cerrar Sesión', style: GoogleFonts.plusJakartaSans(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final authService = context.read<AuthService>();
      Navigator.of(context).pop();
      await authService.logout();
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final themeProvider = context.watch<ThemeProvider>();
    final authService = context.watch<AuthService>();

    final studentCode = _profile?['codigo_est']?.toString() ??
        _profile?['usuario_id']?.toString() ??
        authService.user?['username'] ??
        'UIS';

    final studentName = _profile?['nombre_completo'] ??
        authService.user?['nombre_completo'] ??
        'Estudiante UIS';

    final programName = _profile?['programa_nombre'] ?? 'Tecnología en Regencia de Farmacia';
    final sedeName = _profile?['sede_nombre'] ?? 'Bucaramanga';
    final group = _profile?['grupo'] ?? 'NW7';

    return Scaffold(
      backgroundColor: isDark ? AppTheme.darkBg : AppTheme.lightBg,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: isDark ? AppTheme.darkCard : Colors.white,
        title: Text(
          'Perfil Estudiantil',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: isDark ? Colors.white : const Color(0xFF0F172A),
          ),
        ),
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: isDark ? Colors.white : const Color(0xFF0F172A),
            size: 20,
          ),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.uisGreen))
          : SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
              child: Column(
                children: [
                  // Carné Digital Virtual
                  _buildDigitalCard(isDark, studentName, studentCode, programName, sedeName),
                  const SizedBox(height: 24),

                  // Módulos Informativos
                  _buildAcademicGrid(isDark, studentCode, programName, sedeName, group),
                  const SizedBox(height: 24),

                  // Selector de Tema
                  _buildThemeSelector(isDark, themeProvider),
                  const SizedBox(height: 24),

                  // Botón Cerrar Sesión
                  _buildLogoutButton(),
                  const SizedBox(height: 20),
                ],
              ),
            ),
    );
  }

  Widget _buildDigitalCard(bool isDark, String name, String code, String program, String sede) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFF1E3A1A),
            Color(0xFF0D2310),
            Color(0xFF0B1710),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.emeraldNeon.withValues(alpha: 0.4), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: AppTheme.uisGreen.withValues(alpha: 0.25),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.uisGreen.withValues(alpha: 0.2),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.school_rounded, color: AppTheme.emeraldNeon, size: 22),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'UNIVERSIDAD INDUSTRIAL DE SANTANDER',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: GoogleFonts.plusJakartaSans(
                              color: Colors.white70,
                              fontSize: 8.5,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.5,
                            ),
                          ),
                          Text(
                            'IPRED • Carné Digital',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: GoogleFonts.outfit(
                              color: AppTheme.emeraldNeon,
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.emeraldNeon.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  'ACTIVO',
                  style: GoogleFonts.plusJakartaSans(
                    color: AppTheme.emeraldNeon,
                    fontSize: 9.5,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Nombre del Estudiante
          Text(
            name.toUpperCase(),
            style: GoogleFonts.outfit(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.3,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            program,
            style: GoogleFonts.plusJakartaSans(
              color: const Color(0xFFCBD5E1),
              fontSize: 12.5,
            ),
          ),
          const SizedBox(height: 18),

          // Pie del Carné (Código y Sede)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'CÓDIGO UIS',
                    style: GoogleFonts.plusJakartaSans(
                      color: Colors.white54,
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    code,
                    style: GoogleFonts.firaCode(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.0,
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    'SEDE',
                    style: GoogleFonts.plusJakartaSans(
                      color: Colors.white54,
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    sede,
                    style: GoogleFonts.outfit(
                      color: AppTheme.emeraldNeon,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, duration: 400.ms);
  }

  Widget _buildAcademicGrid(bool isDark, String code, String program, String sede, String group) {
    final cardBg = isDark ? AppTheme.darkCard : AppTheme.lightCard;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 12),
          child: Text(
            'INFORMACIÓN ACADÉMICA OFICIAL',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
            ),
          ),
        ),
        GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.35,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          children: [
            _buildInfoCard(
              title: 'Código Estudiantil',
              value: code,
              icon: Icons.tag_rounded,
              color: AppTheme.uisGreen,
              cardBg: cardBg,
              borderColor: borderColor,
              isDark: isDark,
            ),
            _buildInfoCard(
              title: 'Grupo Asignado',
              value: group,
              icon: Icons.groups_rounded,
              color: AppTheme.accentCyan,
              cardBg: cardBg,
              borderColor: borderColor,
              isDark: isDark,
            ),
            _buildInfoCard(
              title: 'Sede Universitaria',
              value: sede,
              icon: Icons.location_city_rounded,
              color: AppTheme.accentAmber,
              cardBg: cardBg,
              borderColor: borderColor,
              isDark: isDark,
            ),
            _buildInfoCard(
              title: 'Modalidad',
              value: 'A Distancia / Virtual',
              icon: Icons.laptop_chromebook_rounded,
              color: AppTheme.accentPurple,
              cardBg: cardBg,
              borderColor: borderColor,
              isDark: isDark,
            ),
          ],
        ),
      ],
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, duration: 400.ms);
  }

  Widget _buildInfoCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    required Color cardBg,
    required Color borderColor,
    required bool isDark,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: borderColor, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 18),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 11,
                  color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.outfit(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildThemeSelector(bool isDark, ThemeProvider themeProvider) {
    final cardBg = isDark ? AppTheme.darkCard : AppTheme.lightCard;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'APARIENCIA DE LA APLICACIÓN',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _buildThemeOption(
                label: 'Claro',
                icon: Icons.light_mode_rounded,
                selected: themeProvider.themeMode == ThemeMode.light,
                onTap: () => themeProvider.setThemeMode(ThemeMode.light),
                isDark: isDark,
              ),
              const SizedBox(width: 8),
              _buildThemeOption(
                label: 'Oscuro',
                icon: Icons.dark_mode_rounded,
                selected: themeProvider.themeMode == ThemeMode.dark,
                onTap: () => themeProvider.setThemeMode(ThemeMode.dark),
                isDark: isDark,
              ),
              const SizedBox(width: 8),
              _buildThemeOption(
                label: 'Sistema',
                icon: Icons.settings_brightness_rounded,
                selected: themeProvider.themeMode == ThemeMode.system,
                onTap: () => themeProvider.setThemeMode(ThemeMode.system),
                isDark: isDark,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildThemeOption({
    required String label,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
    required bool isDark,
  }) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected
                ? AppTheme.uisGreen.withValues(alpha: 0.15)
                : (isDark ? AppTheme.darkSurface : AppTheme.lightSurface),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected ? AppTheme.uisGreen : Colors.transparent,
              width: 1.5,
            ),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                size: 20,
                color: selected ? AppTheme.uisGreen : (isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B)),
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  fontWeight: selected ? FontWeight.bold : FontWeight.w500,
                  color: selected ? AppTheme.uisGreen : (isDark ? Colors.white70 : Colors.black87),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLogoutButton() {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: OutlinedButton.icon(
        onPressed: _handleLogout,
        icon: const Icon(Icons.logout_rounded, color: Colors.redAccent, size: 20),
        label: Text(
          'Cerrar Sesión',
          style: GoogleFonts.outfit(
            color: Colors.redAccent,
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
        ),
        style: OutlinedButton.styleFrom(
          side: const BorderSide(color: Colors.redAccent, width: 1.2),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
    );
  }
}
