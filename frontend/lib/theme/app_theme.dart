import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Paleta de colores UIS & Neón Moderno
  static const Color uisGreen = Color(0xFF67B93E);
  static const Color uisGreenDark = Color(0xFF438A23);
  static const Color uisGreenLight = Color(0xFF86D958);
  static const Color emeraldNeon = Color(0xFF4ADE80);
  
  static const Color darkBg = Color(0xFF0B0F19);
  static const Color darkCard = Color(0xFF131C2E);
  static const Color darkSurface = Color(0xFF1A263D);
  static const Color darkBorder = Color(0xFF263750);

  static const Color lightBg = Color(0xFFF8FAFC);
  static const Color lightCard = Color(0xFFFFFFFF);
  static const Color lightSurface = Color(0xFFF1F5F9);
  static const Color lightBorder = Color(0xFFE2E8F0);

  static const Color accentCyan = Color(0xFF38BDF8);
  static const Color accentAmber = Color(0xFFF59E0B);
  static const Color accentPurple = Color(0xFF818CF8);

  static ThemeData get lightTheme {
    final baseTextTheme = GoogleFonts.plusJakartaSansTextTheme(ThemeData.light().textTheme);
    
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: lightBg,
      primaryColor: uisGreen,
      colorScheme: ColorScheme.light(
        primary: uisGreen,
        secondary: emeraldNeon,
        surface: lightCard,
        onPrimary: Colors.white,
        onSurface: const Color(0xFF0F172A),
        outline: lightBorder,
      ),
      textTheme: baseTextTheme.copyWith(
        headlineLarge: GoogleFonts.outfit(
          fontSize: 32,
          fontWeight: FontWeight.bold,
          color: const Color(0xFF0F172A),
          letterSpacing: -0.5,
        ),
        headlineMedium: GoogleFonts.outfit(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: const Color(0xFF0F172A),
          letterSpacing: -0.3,
        ),
        titleLarge: GoogleFonts.outfit(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: const Color(0xFF0F172A),
        ),
        bodyLarge: baseTextTheme.bodyLarge?.copyWith(
          color: const Color(0xFF334155),
          fontSize: 15,
          height: 1.5,
        ),
        bodyMedium: baseTextTheme.bodyMedium?.copyWith(
          color: const Color(0xFF475569),
          fontSize: 14,
          height: 1.4,
        ),
      ),
      cardTheme: CardThemeData(
        color: lightCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: lightBorder, width: 1),
        ),
      ),
      textSelectionTheme: TextSelectionThemeData(
        selectionColor: uisGreen.withValues(alpha: 0.30),
        selectionHandleColor: uisGreen,
        cursorColor: uisGreen,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: lightSurface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: lightBorder, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: lightBorder, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: uisGreen, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Colors.redAccent, width: 1),
        ),
      ),
    );
  }

  static ThemeData get darkTheme {
    final baseTextTheme = GoogleFonts.plusJakartaSansTextTheme(ThemeData.dark().textTheme);

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBg,
      primaryColor: uisGreen,
      colorScheme: ColorScheme.dark(
        primary: uisGreen,
        secondary: emeraldNeon,
        surface: darkCard,
        onPrimary: Colors.white,
        onSurface: const Color(0xFFF8FAFC),
        outline: darkBorder,
      ),
      textTheme: baseTextTheme.copyWith(
        headlineLarge: GoogleFonts.outfit(
          fontSize: 32,
          fontWeight: FontWeight.bold,
          color: Colors.white,
          letterSpacing: -0.5,
        ),
        headlineMedium: GoogleFonts.outfit(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: Colors.white,
          letterSpacing: -0.3,
        ),
        titleLarge: GoogleFonts.outfit(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
        bodyLarge: baseTextTheme.bodyLarge?.copyWith(
          color: const Color(0xFFE2E8F0),
          fontSize: 15,
          height: 1.5,
        ),
        bodyMedium: baseTextTheme.bodyMedium?.copyWith(
          color: const Color(0xFF94A3B8),
          fontSize: 14,
          height: 1.4,
        ),
      ),
      cardTheme: CardThemeData(
        color: darkCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: darkBorder, width: 1),
        ),
      ),
      textSelectionTheme: TextSelectionThemeData(
        selectionColor: emeraldNeon.withValues(alpha: 0.30),
        selectionHandleColor: emeraldNeon,
        cursorColor: emeraldNeon,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: darkSurface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: darkBorder, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: darkBorder, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: emeraldNeon, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Colors.redAccent, width: 1),
        ),
      ),
    );
  }
}
