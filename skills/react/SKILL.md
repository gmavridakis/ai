---
name: react
description: Write, review, or fix React code (19.x hooks, Server Components, React Compiler, Next.js, Vite) or a tell: "Rendered more hooks than during the previous render", "Maximum update depth exceeded", "Hydration failed because the server rendered HTML", "Invalid hook call", "not wrapped in act(...)". Use when package.json lists react-dom. Do not use while the failing layer is unknown (error-triage first); npm failures belong to nodejs, Angular to angular, mobile to react-native.
---

# React

Most React failures are one of three things: a *render* that is not pure (state set, a ref read, or a side effect during render), a hook whose identity or dependency list drifts between renders (stale closure, missing dependency, conditional call), or a *boundary* crossed in the wrong direction (server code in a client component, browser API on the server, a second copy of `react` in the bundle). React prints a verbatim *tell* for each; the fix depends on the pinned row. *Pin* first, then match the tell against every *row* before touching code. Writing or reviewing code: pin, then use the Fix column as the review checklist.

Entry: the failing layer is known to be code. A timeout, 4xx/5xx from the API, or "works on their machine" with no layer yet: Call the Skill tool with "error-triage" first. `ERESOLVE`, `ERR_REQUIRE_ESM`, heap out of memory during `next build` or `vite build`, or a wrong Node version: Call the Skill tool with "nodejs". `NG`-coded errors or an `angular.json` in the workspace: Call the Skill tool with "angular". `react-native` instead of `react-dom` in package.json, Metro, a red box, or a native module tell: Call the Skill tool with "react-native". The backend behind the app: a Spring API, Call the Skill tool with "java-spring-stack"; a Node API, Call the Skill tool with "nodejs"; a Django API, Call the Skill tool with "python-django". Adding or reviewing the app's own log lines (a `log.ts` wrapper, levels, the request ID of a failed call) rather than a React tell: Call the Skill tool with "log-instrumentation".

## 1. Pin React, the toolchain, and the boundaries (30 s, before any fix)

```sh
node -e "for (const p of ['react','react-dom','next','vite','@vitejs/plugin-react','babel-plugin-react-compiler','eslint-plugin-react-hooks']) { try { console.log(p, require(p+'/package.json').version) } catch {} }"
npm ls react react-dom 2>/dev/null | grep -vE "deduped|^$"            # more than one react version printed = duplicate copy
grep -nE '"(react-router|react-router-dom|@tanstack/react-query|@reduxjs/toolkit|zustand|jotai|swr|react-hook-form)"' package.json
grep -nE "reactCompiler|reactCompilerPreset|babel-plugin-react-compiler|reactStrictMode" next.config.* vite.config.* babel.config.* 2>/dev/null
grep -rlE --include='*.tsx' --include='*.jsx' "^['\"]use client['\"]" app src 2>/dev/null | wc -l   # client boundary count; 0 with an app/ dir = everything is a Server Component
npx eslint --max-warnings=0 'src/**/*.{ts,tsx}' 'app/**/*.{ts,tsx}' 2>&1 | grep -E "react-hooks/|react-compiler" | head   # rules-of-hooks, exhaustive-deps, compiler bailouts
```

| React (Oct 2026) | Defaults that decide the fix |
| --- | --- |
| 18.3 (Apr 2024) | last 18: prints every 19 removal as a warning (`ReactDOM.render`, string refs, `defaultProps` on functions, `element.ref`); run `npx types-react-codemod@latest preset-19 ./src` and `npx codemod@latest react/19/migration-recipe` before 19 |
| 19.0 (Dec 2024) | `ref` is a prop (`forwardRef` deprecated), `use()`, Actions (`useActionState`, `useFormStatus`, `useOptimistic`), `<Context>` as provider, `propTypes` ignored, errors no longer re-thrown (`onCaughtError`/`onUncaughtError` on `createRoot`); hydration mismatch is one diff instead of many warnings |
| 19.1 / 19.2 (Mar / Oct 2025) | owner stacks in dev; `<Activity mode="hidden">`, `useEffectEvent`, `cacheSignal`; React Compiler 1.0 (`babel-plugin-react-compiler@1`, `eslint-plugin-react-hooks@6` `recommended-latest` carries the compiler rules); Next.js 16 pairs with 19.2 (Turbopack default, `reactCompiler: true`, async `params`/`cookies()`, `proxy.ts`) |
| 19.3 (Sep 2026) | `<ViewTransition>` and `<Fragment ref>` stable, `use(browser())` from `react-dom` to skip SSR for one subtree, Trusted Types passed through, Strict Mode double-invokes effects during hydration too; Vite 8 + `@vitejs/plugin-react@6` (rolldown, no Babel: compiler via `@rolldown/plugin-babel` + `reactCompilerPreset()`) |

Propose fixes only from the pinned row (`useEffectEvent` needs 19.2+; `forwardRef` is still required on 18). Upgrade one major at a time, codemods first, then `npm ls react` until one version remains.

**Done when** the react and react-dom versions, the framework or bundler (Next.js, Vite, other), whether the React Compiler is on, the client-boundary count, and the eslint hook findings are written down and one row of the table is chosen.

## 2. Match the tell: symptom → cause → fix

| Symptom (verbatim tell) | Cause | Fix (in this order) |
| --- | --- | --- |
| `Rendered more hooks than during the previous render.` / `React has detected a change in the order of Hooks called by <Comp>.` / eslint `react-hooks/rules-of-hooks` | a hook after an early `return`, inside `if`, a loop, or a callback | move every hook above the first `return`; branch inside the hook's callback, or split the branch into a child component |
| `Invalid hook call. Hooks can only be called inside of the body of a function component.` with correct code | two copies of `react` (`npm ls react` shows 2 versions: a linked package, a monorepo, or a library with `react` in `dependencies` instead of `peerDependencies`) | `npm dedupe`; library: move `react` to `peerDependencies`; linked package: `resolve.dedupe: ['react','react-dom']` in `vite.config` or `npm link ../app/node_modules/react` |
| `Maximum update depth exceeded.` / `Too many re-renders. React limits the number of renders to prevent an infinite loop.` | `setState` during render (`onClick={setOpen(true)}` instead of `() => setOpen(true)`), or an effect that sets state it depends on with a new object or array each render | call the setter from the handler; derive the value during render instead of mirroring it in state; a dependency that is an object literal or `[]` moves into `useMemo` or becomes a primitive |
| `Cannot update a component (\`Parent\`) while rendering a different component (\`Child\`).` | `Child` calls a parent setter in its render body (often through a store subscribe or a `useEffect`-less "sync") | move the call into `useEffect` of `Child`, or lift the derivation into `Parent` and pass the value down |
| `Hydration failed because the server rendered HTML didn't match the client. As a result this tree will be regenerated on the client.` (19: one diff with `+`/`-` lines) / `In HTML, <div> cannot be a child of <p>.` | `Date.now()`, `Math.random()`, `window`, `localStorage`, locale or timezone read during render; a browser extension injecting markup; invalid nesting | read browser-only values in `useEffect` or `useSyncExternalStore` with a server snapshot; 19.3: `use(browser())` on that subtree; fix the nesting the diff names; `suppressHydrationWarning` only on a timestamp text node |
| `You're importing a component that needs useState. It only works in a Client Component but none of its parents are marked with "use client"` / `Error: useContext only works in Client Components` | hook, event handler, or context consumer inside a Server Component (Next.js `app/` is server by default) | `'use client'` at the top of the leaf that needs state, not the page; keep data fetching in the server parent and pass serialisable props (no functions, no class instances) |
| `Route "/items/[id]" used \`params.id\`. \`params\` should be awaited before using its properties.` / `cookies() should be awaited` | Next.js 15+/16 made `params`, `searchParams`, `cookies()`, `headers()` async | `const { id } = await params;` (`npx @next/codemod@canary next-async-request-api .` rewrites all) |
| `Each child in a list should have a unique "key" prop.` / items keep the wrong text or focus after sorting | missing key, or `key={index}` on a list that reorders, inserts, or deletes | key on the item's stable id; `index` only for a static list |
| `A component is changing an uncontrolled input to be controlled.` | `value` starts as `undefined` (async default) and becomes a string | initialise to `''`, or render the field only once the default is loaded |
| `Objects are not valid as a React child (found: object with keys {id, name})` / `Functions are not valid as a React child.` | rendering a record or a `Date`, or `{Component}` instead of `<Component />` | render a field or `String(x)`; call the component |
| `useEffect must not return anything besides a function, which is used for clean-up.` | `useEffect(async () => …)` | declare the async function inside the effect and call it; cancel with an `AbortController` or an `ignore` flag in the clean-up |
| `React Hook useEffect has a missing dependency: 'x'` (`react-hooks/exhaustive-deps`) / counter or interval stuck on the first value | stale closure | add the dependency; a callback the effect must see fresh without re-running: `useEffectEvent` (19.2+) or a functional `setX(x => …)`; never silence the lint with `// eslint-disable` |
| An effect or fetch runs twice in dev, `console.log` doubles | `<StrictMode>` double-invokes mount, effects and (19.3) hydration effects to expose missing clean-ups | a correct clean-up makes the double invisible; `reactStrictMode: false` is a mask |
| `An update to <Comp> inside a test was not wrapped in act(...)` | state settles after the assertion, or `IS_REACT_ACT_ENVIRONMENT` unset | `await screen.findBy…` / `await waitFor(…)` instead of `getBy` after an async update; `globalThis.IS_REACT_ACT_ENVIRONMENT = true` in the test setup; 19 exports `act` from `react`, not `react-dom/test-utils` |
| `TypeError: react_dom.render is not a function` / `ReactDOM.render is no longer supported` / `element.ref was removed in React 19` | 18-era API on 19 | `createRoot(el).render(<App />)`; read `props.ref`; the codemods in row 18.3 |
| React Compiler on, no `Memo ✨` badge on a component in DevTools, or wrong stale values after enabling it | the compiler skipped the component because it mutates props or state, reads `ref.current` in render, or breaks a hook rule (eslint `react-compiler/*` names it) | fix the rule it names; `"use no memo"` as the first line of that one component only while the fix is pending |
| `fetch` waterfall: 3 sequential spinners, `useEffect` fetches per component | each component awaits its own data after mount | fetch in the Server Component or route loader and pass down, or `useQuery` with a shared key; `<Suspense>` with `use(promise)` on 19 |
| Typing lags, every keystroke re-renders a 1,000-row list | the list and the input share one state and no memo boundary | `useDeferredValue(query)` for the list, `startTransition` for the filter; lists over 100 rows: `@tanstack/react-virtual`; confirm with the Profiler, not by adding `memo` everywhere |

No row matches the tell: Call the Skill tool with "debug-from-raw-logs" and bring the pinned row with you. The complaint is "slow" with no tell and no number yet (no p95, no profile, no query count): Call the Skill tool with "performance-profiling" and return with its top frame or statement count.

**Done when** the tell matched one row, the row's fix was applied in its listed order, and the verbatim tell no longer appears in the dev console, `npx eslint`, `next build` or `vite build`, or the failing test on re-run; or no row matched and debug-from-raw-logs was called.

## See what React actually does

```sh
npx eslint --max-warnings=0 'src/**/*.{ts,tsx}'      # rules-of-hooks and exhaustive-deps catch rows 1, 3 and 12 before the browser does
npm ls react react-dom                                # duplicate react (row 2) is in the tree, not the code
npx next build 2>&1 | grep -E "Error|Warning|⨯" ; npx vite build 2>&1 | tail -5
npx vitest run --reporter=verbose; npx jest --verbose 2>&1 | grep -B2 "act(...)"
npx react-scan@latest http://localhost:3000           # paints every re-render; a component painting on each keystroke is row 18
```

- Which component re-renders: React DevTools → Profiler → record one interaction → *Ranked*; enable *Highlight updates when components render*. A commit over 16 ms (60 Hz) is jank; a component rendered more than once per user action with the same props is the bug.
- Which component set state: the Profiler's *Why did this render?* names the hook index; owner stacks (19.1+) in the console name the component that created the element.
- Which boundary a module crosses: Next.js prints `⨯ You're importing a component that needs …` with the import chain; the first file in the chain without `'use client'` is the one to fix.

## Example

User: "After upgrading to Next 16 the product page logs `Hydration failed because the server rendered HTML didn't match the client` and the price flickers from $0 to the real value."

1. Pin: `react 19.2.0`, `next 16.1.4`, `reactCompiler: true`, 14 `'use client'` files, eslint clean ⇒ row 19.1 / 19.2.
2. Match: tell is verbatim row 5; the 19 diff shows `- $0.00` / `+ $12.50`; `app/products/[id]/price.tsx` formats with `new Intl.NumberFormat(navigator.language)` during render, and `navigator` does not exist on the server.
3. Fix: the locale comes from the request (`headers()` → `accept-language`) in the Server Component and is passed as a prop; the client component formats with that prop. `suppressHydrationWarning` rejected: the value differed, not a timestamp.
4. Verify: dev console shows no hydration diff on reload; `npx next build` prints no `⨯`; the Playwright test `await expect(page.getByTestId('price')).toHaveText('$12.50')` passes on first paint. Tell gone.
