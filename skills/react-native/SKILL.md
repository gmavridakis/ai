---
name: react-native
description: Write, review, or fix React Native code (0.76 to 0.87, New Architecture, Expo SDK 54 to 57, Metro, Hermes) or a React Native tell: "Unable to resolve module", "TurboModuleRegistry.getEnforcing", "requireNativeComponent", "Mismatch between JavaScript part and native part", "No bundle URL present". Use when package.json lists react-native. Do not use while the failing layer is unknown (error-triage first); web React belongs to react, npm failures to nodejs.
---

# React Native

Most React Native failures are not React failures: the JavaScript bundle and the native binary have drifted apart (a library added without a rebuild, a JS and native version of the same library that disagree, a module the New Architecture no longer loads), or the toolchain under the app (Metro, CocoaPods, Gradle, Xcode, Watchman) failed before any component ran. Each prints a verbatim *tell*; the fix depends on the pinned *row*. *Pin* first, then match the tell against every row before touching code. Hook, render and state bugs are plain React: Call the Skill tool with "react" for those once this skill has ruled out the native and toolchain rows.

Entry: the failing layer is known to be code or build. A timeout, 4xx/5xx from the API, or "works on their machine" with no layer yet: Call the Skill tool with "error-triage" first. `ERESOLVE`, `ERR_REQUIRE_ESM`, heap out of memory in Metro, or a wrong Node version: Call the Skill tool with "nodejs". A `pubspec.yaml` with a `flutter` sdk dependency (the Gradle or Xcode error belongs to a Flutter app): Call the Skill tool with "flutter-dart". The backend behind the app: a Spring API, Call the Skill tool with "java-spring-stack"; a Node API, Call the Skill tool with "nodejs"; a Django API, Call the Skill tool with "python-django".

## 1. Pin React Native, the framework, and the two sides (30 s, before any fix)

```sh
node -e "for (const p of ['react-native','react','expo','expo-router','@react-navigation/native','react-native-reanimated','react-native-worklets','react-native-gesture-handler','react-native-screens','hermes-compiler']) { try { console.log(p, require(p+'/package.json').version) } catch {} }"
grep -nE "newArchEnabled|hermesEnabled|hermesV1Enabled|android.useAndroidX" android/gradle.properties 2>/dev/null
grep -nE "RCT_NEW_ARCH_ENABLED|use_frameworks|hermes_enabled" ios/Podfile 2>/dev/null
cat .xcode.env 2>/dev/null; grep -nE "compileSdk|minSdk|targetSdk|kotlinVersion|ndkVersion" android/build.gradle 2>/dev/null
npx react-native info 2>/dev/null | sed -n '/System/,/npmGlobalPackages/p'       # bare RN: Node, Watchman, Xcode, Android SDK, CocoaPods
npx expo-doctor@latest 2>&1 | tail -20                                             # Expo: every "Expected package" line is a JS/native drift
npx react-native config 2>/dev/null | grep -c '"platforms"'                        # autolinked native libraries (0 with native deps = linking broken)
```

| React Native (Oct 2026) | Expo SDK | Defaults that decide the fix |
| --- | --- | --- |
| 0.76 to 0.79 (Oct 2024 to Apr 2025) | 52, 53 | New Architecture on by default (`newArchEnabled=true` / `RCT_NEW_ARCH_ENABLED=1` still honoured); legacy still selectable; opt-out is the fastest bisect for a library crash |
| 0.80, 0.81 (Jun, Aug 2025) | 54 | legacy architecture frozen, deep imports (`react-native/Libraries/...`) warn; 0.81: bundled JavaScriptCore removed (`@react-native-community/javascriptcore` or Hermes), Android 16 KB page size required for Play (Nov 2025), Xcode 16.1+ |
| 0.82, 0.83 (Oct, Dec 2025) | 55 | New Architecture only: `newArchEnabled=false` and `RCT_NEW_ARCH_ENABLED=0` are ignored; uncaught promise rejections now `console.error`; Hermes V1 opt-in (`hermesV1Enabled=true`, `RCT_HERMES_V1_ENABLED=1 bundle exec pod install`); Gradle 9; 0.83: React 19.2, `<Activity>`, `useEffectEvent`, DevTools Network and Performance panels, standalone DevTools app |
| 0.84 to 0.87 (Feb to Aug 2026) | 56 (0.85), 57 (0.86, React 19.2.3, Node 22.13+) | legacy classes removed in steps (RFC0929), interop layers stay; 57: `expo prebuild` clears native dirs by default, iOS 27 SDK needs the UIKit scene lifecycle or the app does not launch; Reanimated 4 (worklets split into `react-native-worklets`, New Architecture only) |

Propose fixes only from the pinned row (`newArchEnabled=false` is a real fix on 0.79 and a no-op on 0.82). Upgrade with `npx @react-native-community/upgrade-helper` diffs one minor at a time, or `npx expo install expo@^57.0.0 --fix` then `npx expo-doctor@latest` until it prints no `Expected package` line.

**Done when** the react-native, react and expo versions, Expo or bare, New Architecture state, Hermes version, the native toolchain (Xcode, Android SDK, CocoaPods, Node) and the autolinked library count are written down and one row of the table is chosen.

## 2. Match the tell: symptom → cause → fix

| Symptom (verbatim tell) | Cause | Fix (in this order) |
| --- | --- | --- |
| `Unable to resolve module <x> from <file>: <x> could not be found within the project or in these directories: node_modules` | package not installed, a stale Metro cache after an install or rename, or a monorepo path outside `watchFolders` | `ls node_modules/<x>`; `npx react-native start --reset-cache` (Expo: `npx expo start -c`); monorepo: add the root to `watchFolders` and `nodeModulesPaths` in `metro.config.js` |
| `Invariant Violation: TurboModuleRegistry.getEnforcing(...): '<Name>' could not be found. Verify that a module by this name is registered in the native binary.` / `requireNativeComponent: "<RNSScreen>" was not found in the UIManager.` | native code not in the running binary: library added without `pod install` and a rebuild, Expo Go without that module, or a library with no New Architecture support | `cd ios && bundle exec pod install && cd ..` then rebuild (`npx react-native run-ios` / `run-android`); Expo Go: `npx expo run:ios` or a dev client (`npx expo install expo-dev-client`); check the library on reactnative.directory for New Architecture support, replace it if unsupported |
| `Error: Cannot find native module 'Expo<Name>'` | an Expo module not bundled in Expo Go, or `expo-dev-client` build older than the dependency list | `npx expo prebuild --clean` and `npx expo run:<platform>`; the dev client must be rebuilt after every native dependency change |
| `[Reanimated] Mismatch between JavaScript part and native part of Reanimated (<a> vs <b>)` / `[Worklets] Mismatch between JavaScript part and native part` | JS updated, native not rebuilt; or Reanimated 4 with `react-native-worklets` missing or mismatched | `npx expo install react-native-reanimated react-native-worklets` (bare: pin both to the same minor); `pod install`; rebuild; `react-native-reanimated/plugin` is replaced by `react-native-worklets/plugin` in `babel.config.js` and must be the last plugin |
| `TypeError: null is not an object (evaluating '_RNGestureHandlerModule.default.flushOperations')` / gestures do nothing on Android | `GestureHandlerRootView` missing at the root, or gesture-handler native side absent | wrap the app root in `<GestureHandlerRootView style={{ flex: 1 }}>`; rebuild if the error names `null` |
| `Text strings must be rendered within a <Text> component.` | a string, number or `{cond && 'x'}` directly inside `<View>`; the Android build crashes where iOS only warns | wrap in `<Text>`; `{cond ? <Text>x</Text> : null}`; search with `grep -rnE "&& ['\"]" src` |
| `VirtualizedLists should never be nested inside plain ScrollViews with the same orientation` / list does not scroll or renders every row | `FlatList` inside `ScrollView` | one `FlatList` with `ListHeaderComponent` / `ListFooterComponent`; horizontal lists inside a vertical one are fine |
| `No bundle URL present.` / `Could not connect to development server.` | Metro not running, device and host on different networks, port 8081 taken, or a release build with no embedded bundle | `npx react-native start`; `adb reverse tcp:8081 tcp:8081`; `sudo lsof -i :8081` and kill, or `npm start -- --port=8088`; release: check the `Bundle React Native code and images` phase ran |
| `Invariant Violation: "main" has not been registered.` | a bundling error above it in Metro, or `AppRegistry.registerComponent` with a name that differs from `app.json` `name` / `MainApplication` | fix the first red Metro error; make `appKey` match; Expo: `registerRootComponent(App)` |
| `env: node: No such file or directory` in the Xcode build log | Xcode does not inherit the nvm/fnm shell PATH | `echo 'export NODE_BINARY=$(command -v node)' > ios/.xcode.env.local` |
| `CocoaPods could not find compatible versions for pod "<Name>"` / `[!] Unable to find a specification for <Name>` | stale spec repo, `Podfile.lock` from another RN version, or Ruby/CocoaPods too old | `bundle exec pod install --repo-update`; move `ios/Podfile.lock` and `ios/Pods` aside and reinstall; `bundle install` first |
| `SDK location not found. Define a valid SDK location with an ANDROID_HOME environment variable or by setting the sdk.dir path in your project's local properties file` / `Error: spawnSync adb ENOENT` | Android SDK not on the shell environment | `export ANDROID_HOME=$HOME/Library/Android/sdk` (Windows: `%LOCALAPPDATA%\Android\Sdk`), `PATH=$PATH:$ANDROID_HOME/platform-tools`; or `sdk.dir=<path>` in `android/local.properties` |
| `Execution failed for task ':app:mergeDebugResources'` / `Duplicate class <X> found in modules` / `Unsupported class file major version` | Gradle, AGP, Kotlin or JDK triad off the row, or two libraries shipping one class | `cd android && ./gradlew clean`; JDK 17 for 0.76 to 0.87 (`java -version`); `./gradlew app:dependencies --configuration debugRuntimeClasspath \| grep <X>` then `exclude group:` on the duplicate |
| `Unsupported top level event type "<topX>" dispatched` / library view renders blank only on the New Architecture | a legacy-architecture library on 0.82+ (interop layer cannot map the event) | update to the library version marked New Architecture on reactnative.directory; 0.76 to 0.81 only: `newArchEnabled=false` as a bisect, not a fix |
| `ReferenceError: Property 'Intl' doesn't exist` / `Property 'structuredClone' doesn't exist` | Hermes before the API landed, or an `Intl` build flag off | upgrade RN (Hermes ships with it); polyfill with `@formatjs/intl-*` or `core-js/actual/structured-clone` only on the pinned row that lacks it |
| `Error: EMFILE: too many open files, watch` / `Error "code":"ENOSPC","errno":"ENOSPC"` | Watchman missing or inotify limit | `brew install watchman` and `watchman watch-del-all`; Linux: `echo fs.inotify.max_user_watches=582222 \| sudo tee -a /etc/sysctl.conf && sudo sysctl -p` |
| Scrolling at 30 fps, JS thread pinned, `Perf Monitor` shows JS frame drops | work on the JS thread per frame: `Animated` without `useNativeDriver`, `onScroll` handlers, large `FlatList` without `getItemLayout` | `useNativeDriver: true` or Reanimated worklets; `FlatList` `getItemLayout`, `windowSize`, `removeClippedSubviews`, or `@shopify/flash-list`; confirm in the DevTools Performance panel (0.83+) |
| Release build crashes on launch, debug works | `console.log` of a huge object, a missing env var, ProGuard/R8 stripping a native class, or an unhandled rejection surfaced by 0.82+ | `npx react-native log-ios` / `adb logcat -s ReactNativeJS AndroidRuntime`; `-keep` rules for the library in `proguard-rules.pro`; a global `ErrorUtils.setGlobalHandler` only after the cause is read |

No row matches the tell: Call the Skill tool with "debug-from-raw-logs" and bring the pinned row with you. The tell is a React one (`Rendered more hooks`, `Maximum update depth exceeded`, `Invalid hook call`): Call the Skill tool with "react".

**Done when** the tell matched one row, the row's fix was applied in its listed order, and the verbatim tell no longer appears in Metro, the red box, `npx expo-doctor`, the Xcode or Gradle build log, or `adb logcat` on re-run; or no row matched and debug-from-raw-logs was called.

## See what React Native actually does

```sh
npx react-native start --reset-cache 2>&1 | head -40     # the first red line is the bundling error every "main has not been registered" hides
npx expo-doctor@latest; npx expo install --check          # JS/native drift per package
adb logcat -s ReactNativeJS:V AndroidRuntime:E; npx react-native log-ios
xcodebuild -workspace ios/App.xcworkspace -scheme App -configuration Debug -sdk iphonesimulator build 2>&1 | grep -E "error:|warning: .*deprecated" | head
cd android && ./gradlew app:assembleDebug --warning-mode all 2>&1 | grep -E "error|FAILURE|What went wrong" -A3
```

- Which side is stale: a tell naming `TurboModuleRegistry`, `UIManager`, `native part` or `Cannot find native module` is the binary; `Unable to resolve`, `has not been registered` or a red box with a JS stack is the bundle. Rebuild the stale side, never both at once.
- Which thread is slow: Dev Menu → Perf Monitor; a UI frame rate under 60 with JS at 60 is layout or images, the reverse is JS work (row 17). 0.83+: DevTools Performance panel records both.
- Whether a library supports the New Architecture: `reactnative.directory` filter *New Architecture*; a library that patches `UIManager` or `NativeModules` directly will fail on 0.82+ whatever its README says.

## Example

User: "After adding `react-native-screens` the Android app red-boxes with `Invariant Violation: requireNativeComponent: "RNSScreen" was not found in the UIManager` but iOS is fine. Expo project."

1. Pin: `react-native 0.86.3`, `expo 57.0.17`, `react-native-screens 4.19.0`, New Architecture only (row 0.84 to 0.87), `expo-doctor` prints `Expected package react-native-screens@~4.20.0`; the Android build is an `expo-dev-client` from last week.
2. Match: tell is verbatim row 2; the binary is stale (the client predates the dependency). iOS passes because it was rebuilt this morning.
3. Fix: `npx expo install react-native-screens` (aligns to 4.20.0), `npx expo prebuild --clean`, `npx expo run:android`. No `newArchEnabled` change: ignored on 0.86.
4. Verify: red box gone on launch, `npx expo-doctor@latest` prints no `Expected package` line, navigating three screens shows no `UIManager` line in `adb logcat -s ReactNativeJS`. Tell gone.
