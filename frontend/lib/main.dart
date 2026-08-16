import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/auth_service.dart';
import 'services/api_service.dart';
import 'theme/app_theme.dart';
import 'theme/theme_provider.dart';
import 'screens/login_screen.dart';
import 'screens/chat_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Inicializar token almacenado
  await AuthService.instance.loadStoredToken();
  
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService.instance),
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        Provider(create: (_) => ApiService()),
      ],
      child: const IpredChatbotApp(),
    ),
  );
}

class IpredChatbotApp extends StatelessWidget {
  const IpredChatbotApp({super.key});

  @override
  Widget build(BuildContext context) {
    final themeProvider = context.watch<ThemeProvider>();

    return MaterialApp(
      title: 'IPRED Chatbot UIS',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeProvider.themeMode,
      home: const AuthWrapper(),
    );
  }
}

class AuthWrapper extends StatelessWidget {
  const AuthWrapper({super.key});

  @override
  Widget build(BuildContext context) {
    final authService = context.watch<AuthService>();
    
    if (!authService.isInitialized) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(color: AppTheme.uisGreen),
        ),
      );
    }

    if (authService.isAuthenticated) {
      return const ChatScreen();
    } else {
      return const LoginScreen();
    }
  }
}
