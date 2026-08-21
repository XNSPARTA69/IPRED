import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:url_launcher/url_launcher.dart';
import '../theme/app_theme.dart';

class MarkdownTableBuilder extends MarkdownElementBuilder {
  final BuildContext context;
  final bool isDark;

  MarkdownTableBuilder({required this.context, required this.isDark});

  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    if (element.tag != 'table') return null;

    final headers = <String>[];
    final rows = <List<String>>[];

    for (var child in element.children ?? []) {
      if (child is md.Element) {
        if (child.tag == 'thead') {
          for (var tr in child.children ?? []) {
            if (tr is md.Element && tr.tag == 'tr') {
              for (var th in tr.children ?? []) {
                if (th is md.Element) {
                  headers.add(th.textContent.trim());
                }
              }
            }
          }
        } else if (child.tag == 'tbody') {
          for (var tr in child.children ?? []) {
            if (tr is md.Element && tr.tag == 'tr') {
              final rowCells = <String>[];
              for (var td in tr.children ?? []) {
                if (td is md.Element) {
                  rowCells.add(td.textContent.trim());
                }
              }
              if (rowCells.isNotEmpty) {
                rows.add(rowCells);
              }
            }
          }
        }
      }
    }

    if (headers.isEmpty && rows.isEmpty) return null;

    return ResponsiveMarkdownTable(
      headers: headers,
      rows: rows,
      isDark: isDark,
    );
  }
}

class ResponsiveMarkdownTable extends StatefulWidget {
  final List<String> headers;
  final List<List<String>> rows;
  final bool isDark;

  const ResponsiveMarkdownTable({
    super.key,
    required this.headers,
    required this.rows,
    required this.isDark,
  });

  @override
  State<ResponsiveMarkdownTable> createState() => _ResponsiveMarkdownTableState();
}

class _ResponsiveMarkdownTableState extends State<ResponsiveMarkdownTable> {
  Future<void> _launchEmail(String email) async {
    final cleanEmail = email.replaceAll('`', '').replaceAll(' ', '').trim();
    if (cleanEmail.isEmpty) return;

    if (cleanEmail.toLowerCase().contains('coordinacion')) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Por favor contacta a la Coordinación IPRED a través de ipred@uis.edu.co',
              style: GoogleFonts.plusJakartaSans(color: Colors.white),
            ),
            backgroundColor: const Color(0xFF1E293B),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
      return;
    }

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 30),
        decoration: BoxDecoration(
          color: widget.isDark ? const Color(0xFF1E293B) : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.3),
              blurRadius: 20,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.uisGreen.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.email_rounded, color: AppTheme.uisGreen, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Escribir a Docente UIS',
                        style: GoogleFonts.outfit(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: widget.isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                      SelectableText(
                        cleanEmail,
                        style: GoogleFonts.firaCode(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.uisGreen,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.uisGreen.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.mail_outline_rounded, color: AppTheme.uisGreen, size: 20),
              ),
              title: Text('Abrir aplicación de correo', style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600)),
              subtitle: Text('Cliente predeterminado del sistema (mailto:)', style: GoogleFonts.plusJakartaSans(fontSize: 11.5)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              onTap: () async {
                Navigator.pop(ctx);
                final uri = Uri(scheme: 'mailto', path: cleanEmail);
                try {
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                } catch (_) {
                  await launchUrl(uri);
                }
              },
            ),
            ListTile(
              leading: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.open_in_browser_rounded, color: Color(0xFF0284C7), size: 20),
              ),
              title: Text('Redactar en Gmail Web', style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600)),
              subtitle: Text('Abre directamente en una pestaña del navegador', style: GoogleFonts.plusJakartaSans(fontSize: 11.5)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              onTap: () async {
                Navigator.pop(ctx);
                final gmailUri = Uri.parse('https://mail.google.com/mail/?view=cm&fs=1&to=$cleanEmail');
                await launchUrl(gmailUri, mode: LaunchMode.platformDefault);
              },
            ),
            ListTile(
              leading: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.emeraldNeon.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.copy_rounded, color: AppTheme.emeraldNeon, size: 20),
              ),
              title: Text('Copiar dirección al portapapeles', style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600)),
              subtitle: Text('Guardar texto para pegarlo en cualquier app', style: GoogleFonts.plusJakartaSans(fontSize: 11.5)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              onTap: () async {
                Navigator.pop(ctx);
                await Clipboard.setData(ClipboardData(text: cleanEmail));
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Row(
                        children: [
                          const Icon(Icons.check_circle_rounded, color: AppTheme.emeraldNeon, size: 20),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              'Correo copiado al portapapeles: $cleanEmail',
                              style: GoogleFonts.plusJakartaSans(color: Colors.white, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                      backgroundColor: const Color(0xFF1E293B),
                      behavior: SnackBarBehavior.floating,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  );
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final borderColor = widget.isDark ? const Color(0xFF243049) : const Color(0xFFE2E8F0);
    final cardHeaderBg = widget.isDark ? const Color(0xFF0F1626) : const Color(0xFFF8FAFC);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: widget.isDark ? const Color(0xFF131B2E) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: widget.isDark ? 0.25 : 0.04),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Cabecera compacta
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: cardHeaderBg,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(15),
                topRight: Radius.circular(15),
              ),
              border: Border(bottom: BorderSide(color: borderColor, width: 0.8)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                    color: AppTheme.uisGreen.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.view_agenda_rounded,
                    size: 15,
                    color: AppTheme.uisGreen,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'Detalle de Asignaturas y Horarios',
                  style: GoogleFonts.outfit(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: widget.isDark ? Colors.white : const Color(0xFF1E293B),
                  ),
                ),
              ],
            ),
          ),

          // Lista de Tarjetas Exclusiva con Texto Seleccionable
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            padding: const EdgeInsets.all(12),
            itemCount: widget.rows.length,
            separatorBuilder: (context, index) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final row = widget.rows[index];
              return _buildItemCard(row, index);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildItemCard(List<String> row, int index) {
    final cardBorder = widget.isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0);
    final cardBg = widget.isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC);

    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: cardBorder, width: 1),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(13),
        child: Container(
          decoration: const BoxDecoration(
            border: Border(
              left: BorderSide(color: AppTheme.uisGreen, width: 4),
            ),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: List.generate(widget.headers.length, (colIndex) {
              final header = widget.headers[colIndex];
              final value = colIndex < row.length ? row[colIndex] : '';
              final h = header.toLowerCase();

              IconData icon = Icons.info_outline_rounded;
              if (h.contains('fecha')) icon = Icons.calendar_today_rounded;
              if (h.contains('hora')) icon = Icons.access_time_rounded;
              if (h.contains('asignatura') || h.contains('materia')) icon = Icons.menu_book_rounded;
              if (h.contains('docente') || h.contains('profesor')) icon = Icons.person_rounded;
              if (h.contains('correo') || h.contains('email')) icon = Icons.alternate_email_rounded;
              if (h.contains('grupo')) icon = Icons.groups_rounded;
              if (h.contains('modalidad') || h.contains('tipo')) icon = Icons.location_on_rounded;

              // 1. FECHA CON FORMATO AA/MM/DD MEJOR ACOMODADO Y SELECCIONABLE
              if (h.contains('fecha')) {
                final cleanDate = value.replaceAll('`', '').trim();
                return Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Icon(icon, size: 14, color: AppTheme.uisGreen),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 88,
                        child: Text(
                          header,
                          style: GoogleFonts.outfit(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            color: widget.isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                          ),
                        ),
                      ),
                      Expanded(
                        child: Row(
                          children: [
                            SelectableText(
                              cleanDate,
                              style: GoogleFonts.firaCode(
                                fontSize: 12.5,
                                fontWeight: FontWeight.bold,
                                color: widget.isDark ? Colors.white : const Color(0xFF0F172A),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                              decoration: BoxDecoration(
                                color: widget.isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                                borderRadius: BorderRadius.circular(5),
                              ),
                              child: Text(
                                'AAAA/MM/DD',
                                style: GoogleFonts.plusJakartaSans(
                                  fontSize: 9,
                                  fontWeight: FontWeight.w700,
                                  color: widget.isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569),
                                  letterSpacing: 0.3,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }

              // 2. HORARIO ACOMODADO Y SELECCIONABLE
              if (h.contains('hora')) {
                final cleanHour = value.replaceAll('`', '').trim();
                return Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Icon(icon, size: 14, color: AppTheme.uisGreen),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 88,
                        child: Text(
                          header,
                          style: GoogleFonts.outfit(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            color: widget.isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                          ),
                        ),
                      ),
                      Expanded(
                        child: SelectableText(
                          cleanHour,
                          style: GoogleFonts.firaCode(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: widget.isDark ? const Color(0xFF38BDF8) : const Color(0xFF0284C7),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }

              // 3. CORREO INTERACTIVO CLICKEABLE Y SELECCIONABLE
              if (h.contains('correo') || h.contains('email') || value.contains('@')) {
                final cleanEmail = value.replaceAll('`', '').trim();
                return Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Icon(icon, size: 14, color: AppTheme.uisGreen),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 88,
                        child: Text(
                          header,
                          style: GoogleFonts.outfit(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            color: widget.isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                          ),
                        ),
                      ),
                      Expanded(
                        child: Row(
                          children: [
                            InkWell(
                              onTap: () => _launchEmail(cleanEmail),
                              borderRadius: BorderRadius.circular(6),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(vertical: 2),
                                child: Text(
                                  cleanEmail,
                                  style: GoogleFonts.firaCode(
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w600,
                                    color: widget.isDark ? const Color(0xFF86D958) : const Color(0xFF2C6B14),
                                    decoration: TextDecoration.underline,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }

              // 4. MODALIDAD CON TEXTO HUMANO Y COMPRENSIBLE PARA ESTUDIANTES
              if (h.contains('modalidad') || h.contains('tipo')) {
                String humanModalidad = value.replaceAll('`', '').trim();
                final upper = humanModalidad.toUpperCase();
                Color badgeColor = AppTheme.uisGreen;
                IconData modIcon = Icons.location_city_rounded;

                if (upper == 'TP' || upper.contains('PRESENCIAL')) {
                  humanModalidad = 'Presencial (En Sede)';
                  badgeColor = const Color(0xFF10B981);
                  modIcon = Icons.location_city_rounded;
                } else if (upper == 'AH' || upper.contains('HÍBRIDA') || upper.contains('HIBRIDA')) {
                  humanModalidad = 'Aula Híbrida (Presencial / Remota)';
                  badgeColor = const Color(0xFF06B6D4);
                  modIcon = Icons.sensors_rounded;
                } else if (upper == 'TR' || upper.contains('REMOTA') || upper.contains('VIRTUAL')) {
                  humanModalidad = 'Virtual (En Vivo)';
                  badgeColor = const Color(0xFFA855F7);
                  modIcon = Icons.laptop_chromebook_rounded;
                } else if (upper.contains('EXAMEN') || upper.contains('EVALUACIÓN') || upper.contains('EVALUACION')) {
                  humanModalidad = 'Evaluación Presencial';
                  badgeColor = const Color(0xFFF59E0B);
                  modIcon = Icons.assignment_turned_in_rounded;
                } else if (upper.contains('PRÁCTICA') || upper.contains('PRACTICA') || upper == 'PR') {
                  humanModalidad = 'Práctica Profesional';
                  badgeColor = const Color(0xFF3B82F6);
                  modIcon = Icons.work_outline_rounded;
                }

                return Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(
                    children: [
                      Icon(modIcon, size: 14, color: badgeColor),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 88,
                        child: Text(
                          header,
                          style: GoogleFonts.outfit(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            color: widget.isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                          ),
                        ),
                      ),
                      Expanded(
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: badgeColor.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: badgeColor.withValues(alpha: 0.4)),
                            ),
                            child: SelectableText(
                              humanModalidad,
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: badgeColor,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }

              // 5. ASIGNATURA O CAMPOS GENERALES SELECCIONABLES
              final isAsignatura = h.contains('asignatura') || h.contains('materia');

              return Padding(
                padding: const EdgeInsets.only(bottom: 7),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(icon, size: 14, color: AppTheme.uisGreen),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 88,
                      child: Text(
                        header,
                        style: GoogleFonts.outfit(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          color: widget.isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                        ),
                      ),
                    ),
                    Expanded(
                      child: SelectableText(
                        value.replaceAll('**', '').replaceAll('`', ''),
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: isAsignatura ? 13 : 12,
                          fontWeight: isAsignatura ? FontWeight.bold : FontWeight.normal,
                          color: widget.isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}
