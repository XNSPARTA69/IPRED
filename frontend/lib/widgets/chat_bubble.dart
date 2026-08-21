import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../theme/app_theme.dart';
import 'responsive_markdown_table.dart';

class ChatBubble extends StatefulWidget {
  final String message;
  final bool isUser;
  final bool isAI;
  final bool isWeb;
  final String? timestamp;
  final String? sourceAttribution;

  const ChatBubble({
    super.key,
    required this.message,
    required this.isUser,
    this.isAI = false,
    this.isWeb = false,
    this.timestamp,
    this.sourceAttribution,
  });

  @override
  State<ChatBubble> createState() => _ChatBubbleState();
}

class _ChatBubbleState extends State<ChatBubble> {
  bool _copied = false;
  String? _lastMessage;
  bool? _lastIsDark;
  List<Widget>? _cachedContent;

  void _copyToClipboard() {
    Clipboard.setData(ClipboardData(text: widget.message));
    setState(() => _copied = true);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: AppTheme.emeraldNeon, size: 20),
            const SizedBox(width: 10),
            Text(
              'Mensaje copiado al portapapeles',
              style: GoogleFonts.plusJakartaSans(color: Colors.white, fontWeight: FontWeight.w500),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF1E293B),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        duration: const Duration(seconds: 2),
      ),
    );
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  Future<void> _handleLinkTap(String text, String? href, String title) async {
    if (href == null || href.isEmpty) return;

    final trimmed = href.trim();
    Uri? uri;
    bool isEmail = false;

    if (trimmed.contains('@') && !trimmed.startsWith('http')) {
      isEmail = true;
      final clean = trimmed.replaceAll('mailto:', '');
      uri = Uri(scheme: 'mailto', path: clean);
    } else if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      uri = Uri.parse(trimmed);
    } else {
      uri = Uri.parse('https://$trimmed');
    }

    try {
      try {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } catch (_) {
        try {
          await launchUrl(uri);
        } catch (_) {}
      }

      if (isEmail) {
        final cleanEmail = trimmed.replaceAll('mailto:', '');
        await Clipboard.setData(ClipboardData(text: cleanEmail));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Row(
                children: [
                  const Icon(Icons.mark_email_read_rounded, color: AppTheme.emeraldNeon, size: 20),
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
              duration: const Duration(seconds: 3),
            ),
          );
        }
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (widget.isUser) {
      return _buildUserBubble(context, isDark);
    } else {
      return _buildAssistantBubble(context, isDark);
    }
  }

  Widget _buildUserBubble(BuildContext context, bool isDark) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth < 600;

    return Theme(
      data: Theme.of(context).copyWith(
        textSelectionTheme: const TextSelectionThemeData(
          selectionColor: Color(0x88FFFFFF),
          selectionHandleColor: Colors.white,
        ),
      ),
      child: Align(
        alignment: Alignment.centerRight,
        child: Container(
          constraints: BoxConstraints(
            maxWidth: isMobile ? screenWidth * 0.88 : screenWidth * 0.82,
          ),
          margin: EdgeInsets.only(
            top: 6,
            bottom: 6,
            left: isMobile ? 24 : 48,
            right: isMobile ? 8 : 12,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppTheme.uisGreen, AppTheme.uisGreenDark],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(22),
              topRight: Radius.circular(22),
              bottomLeft: Radius.circular(22),
              bottomRight: Radius.circular(6),
            ),
            boxShadow: [
              BoxShadow(
                color: AppTheme.uisGreen.withValues(alpha: 0.35),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              SelectableText(
                widget.message,
                style: GoogleFonts.plusJakartaSans(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
              if (widget.timestamp != null) ...[
                const SizedBox(height: 4),
                Text(
                  widget.timestamp!,
                  style: GoogleFonts.plusJakartaSans(
                    color: Colors.white.withValues(alpha: 0.7),
                    fontSize: 11,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAssistantBubble(BuildContext context, bool isDark) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth < 600;
    final cardBg = isDark ? AppTheme.darkCard : AppTheme.lightCard;
    final borderColor = isDark ? AppTheme.darkBorder : AppTheme.lightBorder;
    final textColor = isDark ? Colors.white : const Color(0xFF0F172A);

    return Theme(
      data: Theme.of(context).copyWith(
        textSelectionTheme: TextSelectionThemeData(
          selectionColor: AppTheme.uisGreen.withValues(alpha: 0.25),
          selectionHandleColor: AppTheme.uisGreen,
        ),
      ),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Container(
          constraints: BoxConstraints(
            maxWidth: isMobile ? screenWidth * 0.96 : screenWidth * 0.90,
          ),
          margin: EdgeInsets.only(
            top: 8,
            bottom: 8,
            left: isMobile ? 6 : 12,
            right: isMobile ? 6 : 36,
          ),
          decoration: BoxDecoration(
            color: cardBg,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(6),
              topRight: Radius.circular(22),
              bottomLeft: Radius.circular(22),
              bottomRight: Radius.circular(22),
            ),
            border: Border.all(color: borderColor, width: 1),
            boxShadow: [
              BoxShadow(
                color: isDark ? Colors.black.withValues(alpha: 0.3) : Colors.black.withValues(alpha: 0.04),
                blurRadius: 14,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Encabezado del Asistente (Avatar + Badge + Copiar)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF0F1626) : const Color(0xFFF8FAFC),
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(6),
                    topRight: Radius.circular(21),
                  ),
                  border: Border(bottom: BorderSide(color: borderColor, width: 0.8)),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.asset(
                          'assets/images/app_logo.jpg',
                          fit: BoxFit.cover,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      'Asistente IPRED',
                      style: GoogleFonts.outfit(
                        fontWeight: FontWeight.bold,
                        fontSize: 13.5,
                        color: textColor,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                      decoration: BoxDecoration(
                        color: widget.isAI
                            ? const Color(0xFF8B5CF6).withValues(alpha: 0.14)
                            : AppTheme.uisGreen.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: widget.isAI
                              ? const Color(0xFF8B5CF6).withValues(alpha: 0.45)
                              : AppTheme.uisGreen.withValues(alpha: 0.45),
                          width: 0.9,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            widget.isAI ? Icons.auto_awesome_rounded : Icons.bolt_rounded,
                            size: 11,
                            color: widget.isAI ? const Color(0xFF8B5CF6) : AppTheme.uisGreen,
                          ),
                          const SizedBox(width: 3.5),
                          Text(
                            widget.isAI ? 'IA' : 'ZERO IA',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 9.5,
                              fontWeight: FontWeight.w800,
                              color: widget.isAI ? const Color(0xFF8B5CF6) : AppTheme.uisGreen,
                              letterSpacing: 0.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (widget.isWeb) ...[
                      const SizedBox(width: 5),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0EA5E9).withValues(alpha: 0.14),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: const Color(0xFF0EA5E9).withValues(alpha: 0.45),
                            width: 0.9,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.public_rounded,
                              size: 11,
                              color: Color(0xFF0EA5E9),
                            ),
                            const SizedBox(width: 3.5),
                            Text(
                              'WEB',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 9.5,
                                fontWeight: FontWeight.w800,
                                color: const Color(0xFF0EA5E9),
                                letterSpacing: 0.4,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const Spacer(),
                    InkWell(
                      onTap: _copyToClipboard,
                      borderRadius: BorderRadius.circular(8),
                      child: Padding(
                        padding: const EdgeInsets.all(4),
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 200),
                          child: _copied
                              ? const Icon(Icons.check_rounded, size: 16, color: AppTheme.emeraldNeon)
                              : Icon(Icons.copy_rounded, size: 16, color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8)),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Contenido Inteligente (Texto Markdown + Tablas Nativas con Tarjetas)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: _getOrCreateMessageContent(context, isDark, textColor),
                ),
              ),

              // Timestamp
              if (widget.timestamp != null)
                Padding(
                  padding: const EdgeInsets.only(left: 16, bottom: 10),
                  child: Text(
                    widget.timestamp!,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 10.5,
                      color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _getOrCreateMessageContent(BuildContext context, bool isDark, Color textColor) {
    if (_lastMessage == widget.message && _lastIsDark == isDark && _cachedContent != null) {
      return _cachedContent!;
    }
    _lastMessage = widget.message;
    _lastIsDark = isDark;
    _cachedContent = _buildMessageContent(widget.message, context, isDark, textColor);
    return _cachedContent!;
  }

  List<Widget> _buildMessageContent(String message, BuildContext context, bool isDark, Color textColor) {
    final lines = message.split('\n');
    final List<Widget> widgets = [];
    
    List<String> currentMarkdownLines = [];
    List<String> currentTableLines = [];
    bool inTable = false;

    void flushMarkdown() {
      if (currentMarkdownLines.isNotEmpty) {
        final text = currentMarkdownLines.join('\n').trim();
        if (text.isNotEmpty) {
          widgets.add(
            MarkdownBody(
              data: text,
              selectable: true,
              onTapLink: _handleLinkTap,
              styleSheet: _buildStyleSheet(isDark, textColor),
            ),
          );
        }
        currentMarkdownLines.clear();
      }
    }

    void flushTable() {
      if (currentTableLines.isNotEmpty) {
        final tableWidget = _parseAndBuildTable(currentTableLines, isDark);
        if (tableWidget != null) {
          widgets.add(tableWidget);
        } else {
          currentMarkdownLines.addAll(currentTableLines);
          flushMarkdown();
        }
        currentTableLines.clear();
      }
    }

    for (int i = 0; i < lines.length; i++) {
      final line = lines[i];
      final trimmed = line.trim();
      final isTableLine = trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 2;

      if (isTableLine) {
        if (!inTable) {
          flushMarkdown();
          inTable = true;
        }
        currentTableLines.add(trimmed);
      } else {
        if (inTable) {
          flushTable();
          inTable = false;
        }
        currentMarkdownLines.add(line);
      }
    }

    if (inTable) {
      flushTable();
    } else {
      flushMarkdown();
    }

    return widgets;
  }

  Widget? _parseAndBuildTable(List<String> tableLines, bool isDark) {
    if (tableLines.length < 2) return null;

    final headerLine = tableLines[0];
    final headers = headerLine
        .split('|')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();

    if (headers.isEmpty) return null;

    final rows = <List<String>>[];
    for (int i = 1; i < tableLines.length; i++) {
      final line = tableLines[i];
      if (line.contains('---') || line.contains(':-')) {
        continue;
      }
      final rawCells = line.split('|');
      final cells = <String>[];
      for (int c = 1; c < rawCells.length - 1; c++) {
        cells.add(rawCells[c].trim());
      }
      if (cells.isNotEmpty) {
        rows.add(cells);
      }
    }

    if (rows.isEmpty) return null;

    return ResponsiveMarkdownTable(
      key: ValueKey('tbl_${headers.join('_')}'),
      headers: headers,
      rows: rows,
      isDark: isDark,
    );
  }

  MarkdownStyleSheet _buildStyleSheet(bool isDark, Color textColor) {
    return MarkdownStyleSheet(
      p: GoogleFonts.plusJakartaSans(
        color: textColor,
        fontSize: 14.5,
        height: 1.5,
      ),
      strong: GoogleFonts.plusJakartaSans(
        color: isDark ? AppTheme.emeraldNeon : AppTheme.uisGreenDark,
        fontWeight: FontWeight.w700,
      ),
      h1: GoogleFonts.outfit(
        color: textColor,
        fontSize: 18,
        fontWeight: FontWeight.bold,
      ),
      h2: GoogleFonts.outfit(
        color: textColor,
        fontSize: 16,
        fontWeight: FontWeight.bold,
      ),
      h3: GoogleFonts.outfit(
        color: textColor,
        fontSize: 15,
        fontWeight: FontWeight.w600,
      ),
      a: GoogleFonts.plusJakartaSans(
        color: isDark ? AppTheme.emeraldNeon : AppTheme.uisGreenDark,
        fontWeight: FontWeight.w700,
        decoration: TextDecoration.underline,
        decorationColor: isDark ? AppTheme.emeraldNeon : AppTheme.uisGreenDark,
      ),
      listBullet: GoogleFonts.plusJakartaSans(
        color: AppTheme.uisGreen,
        fontWeight: FontWeight.bold,
      ),
      code: GoogleFonts.firaCode(
        backgroundColor: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
        color: isDark ? AppTheme.accentCyan : const Color(0xFF0284C7),
        fontSize: 12.5,
      ),
      codeblockDecoration: BoxDecoration(
        color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isDark ? AppTheme.darkBorder : AppTheme.lightBorder,
        ),
      ),
    );
  }
}
