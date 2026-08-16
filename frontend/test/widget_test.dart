import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:frontend/services/auth_service.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/theme/theme_provider.dart';
import 'package:frontend/screens/login_screen.dart';

void main() {
  testWidgets('Smoke test: LoginScreen renders form with UIS branding', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthService.instance),
          ChangeNotifierProvider(create: (_) => ThemeProvider()),
          Provider(create: (_) => ApiService()),
        ],
        child: const MaterialApp(
          home: LoginScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verificar presencia de elementos institucionales
    expect(find.text('IPRED CHATBOT'), findsOneWidget);
    expect(find.text('Iniciar Sesión'), findsOneWidget);
    expect(find.text('Registrarme'), findsOneWidget);
    expect(find.text('Entrar al Chatbot'), findsOneWidget);
  });
}
