---
name: python-django
description: Write, review, or fix Django code (Django, DRF, Celery/ASGI), or interpret a Django tell: ImproperlyConfigured settings, AppRegistryNotReady, "no such table", "Conflicting migrations", SynchronousOnlyOperation, TransactionManagementError, NoReverseMatch, TemplateDoesNotExist, staticfiles manifest entry, CSRF "Origin checking failed", DisallowedHost, naive datetime, hundreds of identical SELECTs. Use when manage.py, settings.py, or django in requirements/pyproject is present. Do not use while the failing layer is unknown (error-triage first); nodejs, java-spring-stack, and angular own their stacks.
---

# Python / Django

Django failures cluster in five places (settings loading, the app registry, migrations, the ORM's query count, and sync/async boundaries) and the traceback names the symptom, not the cause. *Pin* the versions first (the fix differs by Django line), then match the *tell* against every row of the table before editing code. Writing or reviewing code: pin, then use the table's Fix column as the review checklist.

Entry: the failing layer is known to be code or data. A timeout, 4xx/5xx, or "works on their machine" with no layer yet: Call the Skill tool with "error-triage" first. A Node service in the same system: Call the Skill tool with "nodejs". A Spring service: Call the Skill tool with "java-spring-stack". The Angular front end: Call the Skill tool with "angular"; a React or Next.js front end: Call the Skill tool with "react"; a Flutter app: Call the Skill tool with "flutter-dart". Plain Python with no Django has no stack skill yet: Call the Skill tool with "debug-from-raw-logs".

## 1. Pin the versions (30 s, before any fix)

```sh
python -V; python -m django --version
python -c "import sys,django; print(sys.version_info[:2], django.get_version())"
grep -iE "^(django|djangorestframework|celery|psycopg|mysqlclient)\b" requirements*.txt pyproject.toml 2>/dev/null
python manage.py diffsettings --output unified | grep -E "^\+ *(DEBUG|ALLOWED_HOSTS|DATABASES|INSTALLED_APPS|CSRF_TRUSTED_ORIGINS)"
python manage.py check --deploy --fail-level WARNING       # security.W0xx list; exit 1 on any warning
```

| Django line (Sep 2026) | Status | Python | Consequence for fixes |
| --- | --- | --- | --- |
| 4.2 LTS | EOL since 2026‑04‑07 | 3.8–3.12 | unpatched: the fix is an upgrade to 5.2; no `db_default`, no `GeneratedField`, `CONN_HEALTH_CHECKS` exists (4.1+) |
| 5.2 LTS | security fixes until 2028‑04‑30 | 3.10–3.13 | composite primary keys, `URLField(assume_scheme="https")`, psycopg 3 pool via `"OPTIONS": {"pool": True}` (5.1+); default `DEFAULT_AUTO_FIELD` still `AutoField` → `models.W042` unless set |
| 6.0 | bugfixes ended 2026‑08‑04, security until 2027‑04‑30 | 3.12–3.14 | `BigAutoField` default, `{% partialdef %}`, `@task` Tasks framework (dev backends only; production needs `django-tasks`), `ContentSecurityPolicyMiddleware` + `SECURE_CSP`; email positional args beyond four now warn |
| 6.1 | current, mainstream until 2027‑04‑30 | 3.12–3.14 | `QuerySet.fetch_mode(FETCH_PEERS / FETCH_RAISE)`, `on_delete=models.DB_CASCADE` (no `post_delete` signal), `MAILERS` replaces `EMAIL_*` settings (deprecated), bare `select_related()` deprecated; requires PostgreSQL 15+, MySQL 8.4+, MariaDB 10.11+, SQLite 3.37+ |
| 6.2 LTS (Apr 2027) → "Django 2028" | last old‑cycle release; from Jan 2028 one release a year, each supported 3 years (LTS label retired) | 3.12+ | `RemovedInDjango70Warning` is now `RemovedInDjango2028Warning`: grep for both when silencing |

Propose fixes only from the pinned row or older (`fetch_mode` needs 6.1, `DB_CASCADE` needs 6.1, `pool: True` needs 5.1). Surface pending removals before upgrading: `python -W error::PendingDeprecationWarning -W error::DeprecationWarning manage.py check`.

**Done when** the Django line, Python version, database backend, and DRF/Celery versions are written down and one row of the table is chosen.

## 2. Match the tell: symptom → cause → fix

| Symptom (verbatim tell) | Cause | Fix (in this order) |
| --- | --- | --- |
| `ImproperlyConfigured: Requested setting INSTALLED_APPS, but settings are not configured` | Django imported outside `manage.py` (script, notebook, pytest without `pytest-django`) | `export DJANGO_SETTINGS_MODULE=proj.settings` then `django.setup()` before the first model import; for pytest add `DJANGO_SETTINGS_MODULE` to `[tool.pytest.ini_options]` and install `pytest-django` |
| `AppRegistryNotReady: Apps aren't loaded yet` | a model imported at module top of `settings.py`, an `AppConfig.__init__`, or a package `__init__` | move the import into `AppConfig.ready()` or the function body; reference models by string (`"app.Model"`) in fields and `apps.get_model()` in signals |
| `RuntimeError: Model class app.models.X doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS` | app missing from `INSTALLED_APPS`, or the module imported under two paths (`app.models` vs `src.app.models`) | add the `AppConfig` dotted path; make every import use the same root: `python -c "import app.models, src.app.models"` must not yield two module objects |
| `OperationalError: no such table: app_x` / `ProgrammingError: relation "app_x" does not exist` | migration missing or unapplied on this DB | `python manage.py showmigrations app` (unapplied show `[ ]`); `python manage.py makemigrations --check --dry-run` (exit 1 = model changes without a migration); then `migrate`. `--run-syncdb` on a real DB is not a fix |
| `CommandError: Conflicting migrations detected; multiple leaf nodes in the migration graph: (0007_a, 0007_b in app)` | two branches each added a migration | `python manage.py makemigrations --merge app`; if both branches touched the same field, edit the merge migration by hand and `sqlmigrate app 0008` to verify the SQL |
| `IntegrityError: NOT NULL constraint failed` / `column "x" of relation … contains null values` **during migrate** | non‑null field added to a populated table without a default | 3‑step: add `null=True` → data migration (`RunPython`) backfills → `AlterField` to `null=False`; use `db_default=` (5.0+) when the DB should own the default |
| `ValueError: Related model 'app.Model' cannot be resolved` during migrate | migration `dependencies` list lacks the app that owns the FK target | add `("otherapp", "000N_…")` to `dependencies`; check the order with `showmigrations --plan` |
| `SynchronousOnlyOperation: You cannot call this from an async context - use a thread or sync_to_async` | ORM/cache/`render()` called in an `async def` view, consumer, or `@task` | use the `a*` API (`await Book.objects.aget()`, `async for b in qs`, `await qs.acount()`); otherwise `await sync_to_async(fn, thread_sensitive=True)()`. `DJANGO_ALLOW_ASYNC_UNSAFE=1` belongs in a notebook only |
| `TransactionManagementError: An error occurred in the current transaction. You can't execute queries until the end of the 'atomic' block.` | an `IntegrityError`/`DatabaseError` was caught inside `atomic()` and execution continued | wrap only the statement that may fail in its own `with transaction.atomic():` (a savepoint) so the outer block stays usable; in tests this also fires when using `TestCase` (wraps in a transaction) where `TransactionTestCase` is needed |
| Request runs 200–2000 identical `SELECT … WHERE "app_x"."id" = %s` (debug toolbar SQL panel, or `len(connection.queries)`) | N+1 from accessing a FK/M2M inside a loop or a serializer | `select_related("fk")` for FK/O2O, `prefetch_related("m2m", Prefetch("items", queryset=…))` for reverse/M2M; pin with `self.assertNumQueries(3)` in a test; on 6.1 run the suite once with `fetch_mode(models.FETCH_RAISE)` to make every lazy fetch a `FieldFetchBlocked` |
| `NoReverseMatch: Reverse for 'detail' with arguments '(…)' not found. 1 pattern(s) tried: ['shop/(?P<slug>[-a-zA-Z0-9_]+)/$']` | name, namespace, or kwarg type mismatch (`args` int vs `<slug:slug>`) | `reverse("shop:detail", kwargs={"slug": obj.slug})`: the `app_name` in `urls.py` is the namespace; the printed pattern tells you the expected converter |
| `TemplateDoesNotExist: shop/detail.html` with a *Template‑loader postmortem* listing tried paths | app not in `INSTALLED_APPS`, `APP_DIRS` False, or template in `templates/` not `templates/shop/` | read the postmortem paths in the debug page (or `django.template` logger at DEBUG); fix `TEMPLATES[0]["DIRS"]`/`APP_DIRS` or the folder nesting |
| `ValueError: Missing staticfiles manifest entry for 'css/app.css'` (only with `DEBUG=False`) | `ManifestStaticFilesStorage` and `collectstatic` not run, or the file not found by any finder | `python manage.py findstatic css/app.css`; `python manage.py collectstatic --noinput`; in Docker run it in the image build, not at container start |
| `403 Forbidden: CSRF verification failed … Origin checking failed - https://app.example.com does not match any trusted origins` | Django 4.0+ requires scheme in `CSRF_TRUSTED_ORIGINS`; or TLS terminated at a proxy so Django sees `http` | `CSRF_TRUSTED_ORIGINS = ["https://app.example.com"]`; behind a proxy `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` and make the proxy set that header |
| `DisallowedHost: Invalid HTTP_HOST header: 'api.internal:8000'. You may need to add 'api.internal' to ALLOWED_HOSTS` | host not listed (health checks by IP, k8s service names) | add the exact host (no port) or `.example.com` for subdomains; `["*"]` with `DEBUG=False` is what `check --deploy` flags |
| `RuntimeWarning: DateTimeField X.created received a naive datetime (2026-09-30 10:00:00) while time zone support is active` | `datetime.now()` or a parsed string stored with `USE_TZ=True` | `timezone.now()`, `timezone.make_aware(dt)`; run tests with `-W error::RuntimeWarning` to make it fail |
| `OperationalError: FATAL: sorry, too many clients already` / `connection already closed` under gunicorn/uvicorn | one connection per worker × workers × `CONN_MAX_AGE` > Postgres `max_connections`, or dead persistent connections | `CONN_MAX_AGE=60` + `CONN_HEALTH_CHECKS=True` (4.1+); on 5.1+ with psycopg 3 use `"OPTIONS": {"pool": {"min_size": 2, "max_size": 8}}`; beyond that PgBouncer in transaction mode with `DISABLE_SERVER_SIDE_CURSORS=True` |
| `AppConfig.ready()` / signal handlers run twice, log lines duplicated in dev | `runserver` autoreloader forks a child process | confirm with `runserver --noreload`; register signals in `ready()` with `dispatch_uid=`; move work out of import time |

No row matches the tell: Call the Skill tool with "debug-from-raw-logs" and bring the pinned versions with you.

**Done when** the tell matched one row, the row's fix was applied in its listed order, and the verbatim tell no longer appears when the failing command, request, or test is re-run; or no row matched and debug-from-raw-logs was called.

## See what Django actually does

```sh
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['ENGINE'])"
python manage.py showmigrations --plan | tail -20          # order in which migrate will apply
python manage.py sqlmigrate app 0007                        # exact SQL of one migration
python manage.py makemigrations --check --dry-run; echo $?  # 1 ⇒ models changed, migration missing
python manage.py check --deploy --fail-level WARNING
python -W error::DeprecationWarning manage.py test app --parallel auto --keepdb --failfast
python manage.py test app.tests.test_views.OrderViewTests.test_list -v 2
python manage.py dbshell                                    # psql/mysql/sqlite3 with the configured credentials
python manage.py shell -c "from django.urls import get_resolver; print(*sorted(str(p.pattern) for p in get_resolver().url_patterns), sep='\n')"
```

- Every SQL statement with timing: `LOGGING = {"loggers": {"django.db.backends": {"level": "DEBUG", "handlers": ["console"]}}}`, only with `DEBUG=True` (the logger is silent otherwise). Count in a shell: `from django.db import connection, reset_queries; reset_queries(); …; len(connection.queries)`.
- Which settings module won: `python manage.py shell -c "import os; print(os.environ['DJANGO_SETTINGS_MODULE'])"`; `diffsettings` prints only values that differ from defaults.
- `python -X dev manage.py runserver` turns on `ResourceWarning` (unclosed files/connections) and asyncio debug.
- DRF: `./manage.py shell -c "from rest_framework.settings import api_settings as s; print(s.DEFAULT_AUTHENTICATION_CLASSES, s.DEFAULT_PERMISSION_CLASSES)"`. A 401 vs 403 tells you whether authentication ran (`401` needs `WWW-Authenticate`, so `SessionAuthentication` alone always gives 403).

## Example

User: "Order list endpoint takes 6 s in prod on Django 5.2; fine locally with 20 orders."

1. Pin: `python -m django --version` → 5.2.17, Python 3.12, DRF 3.16, PostgreSQL 16 ⇒ row "5.2 LTS", so `fetch_mode` is off the table.
2. Measure: in `manage.py shell`, `reset_queries(); OrderSerializer(Order.objects.all()[:200], many=True).data; len(connection.queries)` → 601 queries: 1 for orders, 200 for `customer`, 200 for `shipping_address`, 200 for `items` ⇒ row "identical SELECTs".
3. Fix `get_queryset()`: `Order.objects.select_related("customer", "shipping_address").prefetch_related("items__product")` → 4 queries. Lock it in: `with self.assertNumQueries(4): self.client.get("/api/orders/")`.
4. Verify on prod‑like data with `django.db.backends` DEBUG logging for one request: 4 statements, 180 ms total. Tell gone; hand back with the test in the diff.
