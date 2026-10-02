import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final queryProvider = StateProvider<String>((ref) => '');

final hostsProvider = Provider<List<String>>((ref) {
  final q = ref.watch(queryProvider).toLowerCase();
  return List.generate(2000, (i) => 'host-${i.toString().padLeft(4, '0')}.corp.example')
      .where((h) => h.contains(q))
      .toList();
});

class SearchPage extends ConsumerWidget {
  const SearchPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hosts = ref.watch(hostsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Hosts')),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Filter hosts',
              ),
              onChanged: (v) => ref.read(queryProvider.notifier).state = v,
            ),
            const SizedBox(height: 8),
            ListView.builder(
              itemCount: hosts.length,
              itemBuilder: (context, i) => ListTile(
                leading: const Icon(Icons.dns),
                title: Text(hosts[i]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
