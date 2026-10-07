---
name: flutter-dart
description: Write, review, or fix Flutter or Dart code, or interpret a Flutter tell: "A RenderFlex overflowed", "Vertical viewport was given unbounded height", "setState() called after dispose()", "Null check operator used on a null value", "version solving failed", MissingPluginException, Gradle/AGP mismatch, jank. Use when pubspec.yaml lists a flutter sdk dependency. Do not use while the layer is unknown (error-triage first); the API belongs to java-spring-stack, nodejs, python-django; React Native to react-native.
---

# Flutter and Dart

Most Flutter failures are one of three things: a *constraint* (the min/max width and height a parent passes down) that is missing or unbounded, a `BuildContext` or `State` used after it left the tree, or a toolchain triad (Flutter SDK, Android Gradle Plugin, JDK) out of step. The framework prints a verbatim *tell* for each; the fix depends on the pinned SDK row. *Pin* first, then match the tell against every *row* before touching code. Writing or reviewing code: pin, then use the Fix column as the review checklist.

Entry: the failing layer is known to be code. A timeout, 4xx/5xx from the API, or "works on their phone" with no layer yet: Call the Skill tool with "error-triage" first. The same Gradle, AGP or Xcode tell in a project with `package.json` listing `react-native` and no `pubspec.yaml`: Call the Skill tool with "react-native". The backend behind the app: a Spring API, Call the Skill tool with "java-spring-stack"; a Node API, Call the Skill tool with "nodejs"; a Django API, Call the Skill tool with "python-django".

## 1. Pin the SDK, the stack, and the renderer (30 s, before any fix)

```sh
flutter --version --machine | grep -E '"(frameworkVersion|dartSdkVersion|channel)"'
cat .fvmrc .fvm/fvm_config.json 2>/dev/null; grep -n -A3 '^environment:' pubspec.yaml   # FVM pin and the sdk: ^3.x constraint
flutter pub deps --style=compact | grep -E "^(flutter_riverpod|riverpod|flutter_bloc|provider|get|get_it|go_router|auto_route|freezed|json_serializable|build_runner) "
grep -n "FLTEnableImpeller\|EnableImpeller" ios/Runner/Info.plist android/app/src/main/AndroidManifest.xml   # explicit renderer opt-out
grep -n "id(\"com.android.application\")\|org.jetbrains.kotlin.android" android/settings.gradle.kts; grep distributionUrl android/gradle/wrapper/gradle-wrapper.properties
flutter analyze --no-pub 2>&1 | tail -3                                   # the analyzer finds most tells before the device does
```

| Flutter / Dart (Oct 2026) | Defaults that decide the fix |
| --- | --- |
| 3.38 / 3.10 (Nov 2025) | Impeller default on Android (Vulkan, API 29+) and iOS; dot shorthands (`.center` for `Alignment.center`); HTML web renderer already removed (3.29): web is CanvasKit or `--wasm` |
| 3.41 / 3.11 (Feb 2026) | `dart:html` unsupported under `--wasm`, migrate to `package:web`; Widget Previews experimental |
| 3.44 / 3.12 (May 2026) | Google I/O release; `flutter build web --wasm` is the performance path; Dart 3.12 analyzer stricter on unused results |
| 3.47 / 3.13 (Aug 2026, stable 3.47.5) | Impeller default on macOS, Windows, Linux; iOS 15 and macOS 12 minimum; Android triad **AGP 9.1.0, Gradle 9.3.1, Kotlin 2.4.0, JDK 17**, compile/target SDK 36, minSdk 24; `material.dart`/`cupertino.dart` deprecated in Nov 2026 for `material_ui`/`cupertino_ui` (`dart fix --apply --code=migrate_design_widgets`); Widget Previews stable |

Propose fixes only from the pinned row (an Impeller opt-out flag does nothing on a Skia build; `material_ui` imports need 3.47+). Upgrade one stable at a time: `flutter upgrade` on the `stable` channel, then `dart fix --dry-run` before `dart fix --apply`.

**Done when** the Flutter and Dart versions, the state-management and routing packages, the renderer, and the Android triad are written down and one row of the table is chosen.

## 2. Match the tell: symptom → cause → fix

| Symptom (verbatim tell) | Cause | Fix (in this order) |
| --- | --- | --- |
| `A RenderFlex overflowed by 42 pixels on the right.` (yellow-black stripes) | a `Row`/`Column` child has no constraint along the main axis: long `Text`, nested `Row`, image at intrinsic size | 1. `Expanded`/`Flexible` around the child; 2. `Text(…, overflow: TextOverflow.ellipsis, maxLines: 1)`; 3. `SingleChildScrollView` only when the content legitimately scrolls. Keyboard pushing the bottom: `resizeToAvoidBottomInset: false` is a mask, scroll the form instead |
| `Vertical viewport was given unbounded height.` | `ListView`/`GridView`/`CustomScrollView` inside a `Column` or another scrollable | `Expanded(child: ListView(…))` or `SizedBox(height: …)`; `shrinkWrap: true` plus `NeverScrollableScrollPhysics()` only for lists under ~50 items (it lays out every child) |
| `RenderBox was not laid out: RenderViewport#a1b2c NEEDS-LAYOUT NEEDS-PAINT` | side effect of the first constraint error above it | fix the first `══╡ EXCEPTION CAUGHT BY RENDERING LIBRARY ╞══` block in the log, never this one |
| `An InputDecorator, which is typically created by a TextField, cannot have an unbounded width.` | `TextField` inside a `Row` | `Expanded(child: TextField())` or `SizedBox(width: 240, child: …)` |
| `Incorrect use of ParentDataWidget.` | `Expanded`/`Flexible` not a direct child of `Row`/`Column`/`Flex`; `Positioned` outside `Stack`; `TableCell` outside `Table` | move the widget to be the direct child of the matching parent (a `Padding` or `Container` in between breaks it) |
| `setState() or markNeedsBuild() called during build.` | `setState`, `showDialog`, `Navigator.push`, or a provider notify inside `build` or `initState` | run it after the frame: `WidgetsBinding.instance.addPostFrameCallback((_) { … })`, or from the event handler that owns the change |
| `setState() called after dispose(): _FooState#b3c4d(lifecycle state: defunct)` | a `Future`, `Stream`, or `Timer` completes after the widget left the tree | `if (!mounted) return;` before `setState`; cancel the `StreamSubscription`, `Timer`, `AnimationController` in `dispose()` |
| `Looking up a deactivated widget's ancestor is unsafe.` / lint `use_build_context_synchronously` | `context` used after an `await` | capture before the gap (`final nav = Navigator.of(context);`) or guard `if (!context.mounted) return;` after it |
| `Null check operator used on a null value` / `LateInitializationError: Field '_x' has not been initialized.` | `!` on a null, or a `late` field read before assignment; the first frame of the stack names the line | replace `!` with `?.`, `??`, or `if (x case final v?)`; initialise `late` fields in `initState` or make them nullable |
| `Navigator operation requested with a context that does not include a Navigator.` / `Could not find the correct Provider<Cart> above this Widget` | the `context` is above `MaterialApp` or above the provider (typically the widget that builds `MaterialApp` itself) | wrap the consumer in a `Builder`, move it below the provider, or use a `navigatorKey` on `MaterialApp` |
| `MissingPluginException(No implementation found for method getAll on channel plugins.flutter.io/shared_preferences)` | plugin added while the app was running (hot reload and hot restart do not register plugins), or iOS pods stale | stop the app, `flutter run` again; then `flutter clean && flutter pub get`; iOS: `cd ios && pod install --repo-update` |
| `Because myapp depends on dio ^5.9.0 and retrofit >=4.4.0 depends on dio ^4.0.0, version solving failed.` | two constraints with no common version | `flutter pub outdated`, then `dart pub upgrade --major-versions <pkg>`; `dependency_overrides:` is the last resort and carries a comment naming the blocking package |
| `Your project's Gradle version is incompatible with the Java version that Flutter is using for Gradle.` / `Namespace not specified.` / `Dependency ':foo' requires compileSdk 36` | AGP, Gradle, Kotlin, JDK triad out of step with the pinned row | set the triad from the table: `android/settings.gradle.kts` plugins block (AGP, Kotlin), `gradle-wrapper.properties` (Gradle), `flutter config --jdk-dir <jdk17>`; add `namespace` in each plugin module's `build.gradle`; `flutter.compileSdkVersion` in `android/app/build.gradle.kts` |
| `Skipped 47 frames! The application may be doing too much work on its main thread.` (logcat) / red bars in the performance overlay | JSON or image decoding on the UI isolate, `ListView(children: [...])` with hundreds of items, a whole-screen rebuild per tick, missing `const` | measure in `--profile` first; `Isolate.run(() => jsonDecode(body))` for payloads over 100 KB; `ListView.builder`; `const` constructors (`prefer_const_constructors` lint); `RepaintBoundary` around the animating subtree. Stutter only on first run of an animation is a shader warm-up on Skia: switch to Impeller |
| Hot reload prints `Reloaded 0 libraries` or the change is invisible | change in `main()`, `initState`, a `const`, an `enum`, or in generated code | hot restart (`R`); generated code: `dart run build_runner build --delete-conflicting-outputs` |
| `Error: Member not found: 'headline1'` / `The method 'X' isn't defined for the type 'Y'` right after `flutter upgrade` | API removed or renamed in the new row | `dart fix --dry-run`, then `dart fix --apply`; what it cannot fix is in the breaking-changes page of the pinned release |
| `Bad state: Stream has already been listened to.` | second `listen()` on a single-subscription stream | `.asBroadcastStream()` once at the source, or share one subscription through the state object |
| Red screen (debug) or grey screen (release) with no tell | uncaught exception thrown during `build` | read the first `══╡ EXCEPTION CAUGHT BY WIDGETS LIBRARY ╞══` block (it names `The relevant error-causing widget was: Row Row:file:///lib/x.dart:42:11`); install `FlutterError.onError` and `PlatformDispatcher.instance.onError` so release builds report instead of greying |

No row matches the tell: Call the Skill tool with "debug-from-raw-logs" and bring the pinned row with you.

**Done when** the tell matched one row, the row's fix was applied in its listed order, and the verbatim tell no longer appears in `flutter analyze`, the run console, or the failing test on re-run; or no row matched and debug-from-raw-logs was called.

## See what Flutter actually does

```sh
flutter run -d <device-id> --profile          # performance is only real in profile; debug jank is not a bug. `P` toggles the overlay
flutter devices; flutter doctor -v            # the triad (Android SDK, JDK, Xcode, CocoaPods) with the versions Flutter actually picked
flutter test --coverage --reporter expanded   # widget tests: `await tester.pumpAndSettle()` after every tap
flutter pub outdated; flutter pub deps --style=compact | grep <pkg>
dart run build_runner watch --delete-conflicting-outputs   # freezed, json_serializable, riverpod_generator
flutter build apk --analyze-size --target-platform android-arm64   # size breakdown; `flutter build web --wasm` for the web
```

- Which widget overflows: the rendering-library block names the widget and `file:///lib/<path>:<line>:<col>`; `debugPaintSizeEnabled = true` in `main()` draws every constraint.
- Which widget rebuilds: DevTools → Flutter Inspector → *Track widget rebuilds*; or `debugPrintRebuildDirtyWidgets = true`. More than one rebuild of the screen root per frame is the bug.
- Which isolate blocks: DevTools → Performance → *Enhance tracing*; a `build` frame over 16 ms (60 Hz) or 8 ms (120 Hz) is jank.

## Example

User: "I put a search field above the results list and now the screen is yellow-and-black stripes; the console says `Vertical viewport was given unbounded height.`"

1. Pin: `flutter --version --machine` → `3.47.5` / Dart `3.13.4`; `pubspec.yaml` has `flutter_riverpod`, `go_router`; no Impeller opt-out; AGP 9.1.0 ⇒ row 3.47.
2. Match: tell is verbatim row 2; `lib/search_page.dart:31` has `Column(children: [TextField(...), ListView.builder(...)])`.
3. Fix: `Expanded(child: ListView.builder(...))` as the direct child of the `Column`; no `shrinkWrap` (the list has 2,000 rows).
4. Verify: `flutter analyze --no-pub` clean; `flutter run` shows no stripes and no rendering-library block; the widget test `await tester.pumpWidget(...); expect(tester.takeException(), isNull);` passes. Tell gone.
