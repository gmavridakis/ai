import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'search_page.dart';

void main() {
  runApp(const ProviderScope(child: HostSearchApp()));
}

class HostSearchApp extends StatelessWidget {
  const HostSearchApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Host search',
      theme: ThemeData(colorSchemeSeed: Colors.indigo),
      home: const SearchPage(),
    );
  }
}
