---
name: angular
description: Write, review, or fix Angular code (17+, standalone, signals, zoneless, SSR, Material, NgRx), or interpret an Angular tell: NG0100, NG0203, NG0201, NG0302, NG8001/NG8002, NG05xx hydration, NG0600, NG0950, NG0955/NG0956, NG01203, NG05104, a zoneless view that stops updating, CommonJS bailout, budget exceeded. Use when angular.json or @angular/core is present. Do not use while the failing layer is unknown (error-triage first); npm/Node-runtime failures (ERESOLVE, heap OOM, Node version) belong to nodejs.
---

# Angular

Angular errors carry an `NG` code and a template or DI location; the code names the mechanism, not the fix, and the fix depends on the major (standalone vs NgModule, signals vs decorators, zoneless vs zone.js). *Pin* the major and the change-detection mode first, then match the *tell* against every row of the table before touching code. Writing or reviewing code: pin, then use the table's Fix column as the review checklist.

Entry: the failing layer is known to be code. A timeout, 4xx/5xx from the API, or "works on their machine" with no layer yet: Call the Skill tool with "error-triage" first. `ERESOLVE`, lockfile drift, heap out of memory during `ng build`, or a wrong Node version: Call the Skill tool with "nodejs". The backend behind the app: a Spring API (`pom.xml` names `org.springframework.boot`), Call the Skill tool with "java-spring-stack"; a Node API, Call the Skill tool with "nodejs"; a Django API (`manage.py`), Call the Skill tool with "python-django". A React app in the same monorepo: Call the Skill tool with "react". Adding or reviewing the app's own log lines (a `log.ts` wrapper, levels, the request ID of a failed call) rather than an Angular tell: Call the Skill tool with "log-instrumentation".

## 1. Pin the major and the mode (30 s, before any fix)

```sh
npx ng version | sed -n '/Angular CLI/,/^$/p;/@angular\/core/p'    # CLI, core, Node, TypeScript, RxJS
node -p "require('./package.json').dependencies['zone.js'] || 'NO zone.js (zoneless)'"
grep -rn "provideZonelessChangeDetection\|provideExperimentalZonelessChangeDetection\|bootstrapModule" src/ | head -5
grep -n '"polyfills"' -A3 angular.json | grep -c zone.js            # 0 ⇒ zoneless build
grep -n "strictTemplates\|strict\"" tsconfig.json                  # false ⇒ template errors become runtime errors
npx ng config projects.*.architect.build.builder                    # @angular/build:application is the non-webpack builder
```

| Major (Sep 2026) | Support (6 mo active + 12 mo LTS) | Defaults that decide the fix |
| --- | --- | --- |
| 19 | LTS ended 2026‑05 | standalone is the default (`standalone: true` implied); signal `input()`/`output()`/`viewChild()` stable; `@let` in templates |
| 20 | LTS until 2026‑11 | `effect`, `linkedSignal`, `toSignal` stable; `resource`/`httpResource` experimental; new file naming drops the `.component` suffix (`user.ts`, not `user.component.ts`) |
| 21 | LTS until 2027‑05 | **zoneless is the default** for new projects (`provideZonelessChangeDetection()`); Vitest is the default unit‑test runner; signal forms experimental |
| 22 | Active (released 2026‑06‑03); LTS until 2027‑12 | **OnPush is the default**; signal forms, `resource`, `httpResource`, Angular Aria stable; `@Service` replaces `@Injectable({providedIn:'root'})` for singletons; webpack builders (`@angular-devkit/build-angular`) deprecated; TypeScript 6 |

Propose fixes only from the pinned row (`@Service` needs 22; `NgZone.onStable` logic has no effect on a zoneless app; `provideExperimentalZonelessChangeDetection` is renamed `provideZonelessChangeDetection` on 20+). Upgrade one major at a time: `npx ng update @angular/core@21 @angular/cli@21` then `@22`.

**Done when** the Angular major, the change-detection mode (zone.js or zoneless), `strictTemplates`, and the builder are written down and one row of the table is chosen.

## 2. Match the tell: symptom → cause → fix

| Symptom (verbatim tell) | Cause | Fix (in this order) |
| --- | --- | --- |
| `NG0100: ExpressionChangedAfterItHasBeenCheckedError` (dev only) | a binding's value is changed during the same check: parent reads state a child set in `ngAfterViewInit`/`ngOnInit`, or a getter returns a new object each call | 1. move the write into a `signal` and read the signal in the template; 2. derive with `computed()` instead of a getter. `setTimeout` or `detectChanges()` in a lifecycle hook hides the ordering bug |
| `NG0203: inject() must be called from an injection context` | `inject()` inside a callback (`subscribe`, `setTimeout`, a plain function) or inside a `static` method | call `inject()` in the field initializer or constructor; for later use capture `const injector = inject(Injector)` then `runInInjectionContext(injector, () => …)` |
| `NG0201: No provider for X` | standalone component imports the component but not its provider; `providedIn: 'root'` missing; service only provided in a lazy route | `@Injectable({providedIn: 'root'})` (`@Service` on 22) for singletons; route‑scoped ⇒ `providers: [X]` on that `Route`. It is a runtime error, so `ng build` is clean: open the stack, the first `NodeInjector` frame names the consumer |
| `NG8001: 'mat-form-field' is not a known element` / `NG8002: Can't bind to 'ngModel' since it isn't a known property of 'input'` | standalone component missing the `imports: [MatFormFieldModule]` / `FormsModule` entry (`CUSTOM_ELEMENTS_SCHEMA` only masks it) | add the module/component to `imports`; for a custom element use `schemas: [CUSTOM_ELEMENTS_SCHEMA]` only in that one component |
| `NG0302: The pipe 'date' could not be found in the 'UserCard' component` / `NG0302: … could not be found. Verify that it is included in the '@Component.imports' of this component` | standalone component uses a pipe without importing it (`DatePipe`, `AsyncPipe`, a custom pipe); `CommonModule` removed during a migration | add the pipe class to `imports` (`DatePipe`, not `CommonModule`); the message names the component, `ng build` with `strictTemplates: true` catches it before runtime |
| `NG0200: Circular dependency in DI detected for X` | two services inject each other, or a service injects the component that provides it | break the cycle: move the shared state into a third service, or inject lazily with `inject(Injector)` and resolve in the method that needs it; the stack lists the cycle `X -> Y -> X` |
| `NG0500: Hydration Node Mismatch` / `NG0502` / `NG0507: HTML content was altered after SSR` | DOM manipulated outside Angular (jQuery, `innerHTML`, a third‑party widget), invalid HTML nesting (`<p><div>`), or server/client rendering different content (dates, `Math.random`, `window` checks) | fix the nesting (`npx html-validate`), move the widget into `afterNextRender()`, or mark the subtree `ngSkipHydration`; reproduce with `ng build && node dist/<app>/server/server.mjs`, not `ng serve` |
| `NG0600: Writing to signals is not allowed in a computed or an effect` | `set()`/`update()` inside `computed()` or a template expression | derive with `computed()`; in `effect()` on 19+ writes are allowed (the old `allowSignalWrites` is removed), so a 0600 inside an effect means the project is on ≤18 |
| `NG0950: Input is required but no value is available yet` | `input.required<T>()` read in the constructor or a field initializer | read it in `ngOnInit`, a `computed()`, or the template; a required input takes no default |
| `NG0955: Track expression resulted in duplicated keys` / `NG0956: tracking expression caused re-creation of the DOM structure` | `@for (x of xs; track $index)` with reorders, or `track x` on objects recreated per fetch | `track x.id` (a stable key); for primitives `track x`; `$index` only for truly static lists |
| `NG01203: No value accessor for form control name: 'x'` | `formControlName` on a custom component with no `ControlValueAccessor`, or `FormsModule`/`ReactiveFormsModule` not imported | import the forms module; implement `ControlValueAccessor` + `NG_VALUE_ACCESSOR` provider, or on 22 use signal forms (`form()` + `[field]`) |
| `NG05104: The selector "app-root" did not match any elements` | `index.html` tag ≠ bootstrapped component's selector, or SSR `index.server.html` out of date | compare `bootstrapApplication(App)` selector with `src/index.html`; `ng build` regenerates `index.server.html` |
| View stops updating after a `setTimeout`, WebSocket, `addEventListener`, or third‑party callback (no error) | zoneless app mutating plain fields: nothing marks the view dirty | store the state in a `signal()`; for RxJS use `toSignal()` or `AsyncPipe`; last resort `inject(ChangeDetectorRef).markForCheck()`. Find all offenders: `provideCheckNoChangesConfig({exhaustive: true, interval: 1000})` in dev config throws NG0100 at each un‑notified binding |
| `NG0506: Angular detected that this application remains unstable` (SSR hangs ~10 s) | long‑polling, `setInterval`, or an unresolved `PendingTasks` on the server | wrap the work in `afterNextRender()` or `isPlatformBrowser`; for real async use `inject(PendingTasks).run(() => …)` |
| `Warning: … depends on 'moment'. CommonJS or AMD dependencies can cause optimization bailouts` | CJS package defeats tree‑shaking | replace (`date-fns`/`luxon` for moment); if impossible, `"allowedCommonJsDependencies": ["pkg"]` in `angular.json` build options and accept the size |
| `Error: bundle initial exceeded maximum budget. Budget 500.00 kB was not met by 120.00 kB` | eager import of a heavy module/route | `npx ng build --stats-json && npx esbuild-visualizer --metadata dist/<app>/stats.json`; lazy‑load with `loadComponent: () => import('./x')` or `@defer (on viewport)`; raise `budgets` only after the lazy split |
| Tests pass on 20, fail on 21 with stale DOM assertions or `tick()` doing nothing | zoneless `TestBed` (no `zone.js` in test polyfills) with leftover `fakeAsync`/`tick` and `detectChanges()`‑after‑mutation habits | on 21+: `await fixture.whenStable()` after inputs change, `fixture.autoDetectChanges()` once, drop `fakeAsync`; with Vitest use `vi.useFakeTimers()` instead of `tick()` |

No row matches the tell: Call the Skill tool with "debug-from-raw-logs" and bring the pinned major and mode with you. The complaint is "slow" with no tell and no number yet (no p95, no profile, no query count): Call the Skill tool with "performance-profiling" and return with its top frame or statement count.

**Done when** the tell matched one row, the row's fix was applied in its listed order, and the verbatim tell no longer appears in the dev console, the build output, or the failing test on re-run; or no row matched and debug-from-raw-logs was called.

## See what Angular actually does

```sh
npx ng build --configuration development 2>&1 | grep -E "NG[0-9]{4}|error TS"   # template type errors with file:line
npx ng serve --open=false --hmr=false            # rule out HMR when state looks stale (NG0751)
npx ng generate @angular/core:control-flow       # *ngIf/*ngFor → @if/@for (then re-run tests)
npx ng generate @angular/core:signal-input-migration --path src/app   # @Input() → input(); also :output-migration, :signal-queries-migration, :inject
npx ng generate @angular/core:cleanup-unused-imports
npx ng test --watch=false --code-coverage        # Vitest on 21+ new projects; Karma on older (`ng test --browsers=ChromeHeadless`)
```

- Which provider wins: in DevTools → Angular tab → Injector Tree; or `inject(Injector).get(X, null, {self: true})` in a component to see if it resolves locally.
- Which component owns a DOM node: `ng.getComponent($0)` in the browser console (dev builds only); `ng.applyChanges($0)` forces a check to confirm a missing‑notification bug.
- Hydration: the server HTML must carry an `ngh` attribute on the root; the dev console prints `Angular hydrated N component(s) and M node(s)`, and 0 components means hydration never ran (missing `provideClientHydration()`).

## Example

User: "Since upgrading to 21 our dashboard table stops refreshing after a minute. No errors in the console."

1. Pin: `node -p "…zone.js"` → `NO zone.js`; `main.ts` has `provideZonelessChangeDetection()` ⇒ row "View stops updating … zoneless".
2. Add `provideCheckNoChangesConfig({exhaustive: true, interval: 1000})` to `appConfig.providers` in dev → NG0100 thrown at `dashboard.ts:48` where `this.rows = data` runs inside `socket.onmessage`.
3. Fix: `rows = signal<Row[]>([])` and `this.rows.set(data)`; template `@for (r of rows(); track r.id)`. Remove the interval probe.
4. Verify: `await fixture.whenStable()` in the spec after emitting a fake socket message → the row count changes; in the browser the table updates with no `markForCheck()`. Tell gone.
