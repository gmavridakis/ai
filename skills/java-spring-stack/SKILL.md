---
name: java-spring-stack
description: Write, review, or fix code in a Java / Spring Boot / Spring / Hibernate-JPA / JAX-RS / JAX-WS project, or interpret a stack-specific symptom (LazyInitializationException, N+1 query storms, @Transactional not rolling back, javax→jakarta compile errors, Jackson serializing a Hibernate proxy, HikariCP pool exhaustion). Use as soon as a pom.xml or build.gradle names org.springframework.boot, hibernate-core, jersey, or cxf. Do not use while the failing layer (network/auth/config/code/data) is still unknown — error-triage runs first and hands off here once the layer is code or data in a Java project — nor for the generic reproduce/bisect procedure, which stays with debug-from-raw-logs; other stacks (Node.js, Django, Angular, React) get their own skills.
---

# Java / Spring stack

Spring problems are rarely Java problems: they are proxy, session, and classpath problems whose stack traces name the symptom, not the cause. Pin the versions first (fixes differ by major), then match the symptom in the table before touching code.

## 1. Pin the versions (30 s, before any fix)

```sh
./mvnw -q help:evaluate -Dexpression=project.parent.version -DforceStdout; echo   # Boot version (parent POM)
./mvnw dependency:tree -Dincludes=org.hibernate.orm:hibernate-core,org.hibernate:hibernate-core,org.glassfish.jersey.core,org.apache.cxf
./gradlew dependencies --configuration runtimeClasspath | grep -E 'spring-boot:|hibernate-core|jersey-server|cxf-rt'   # Gradle
java -version 2>&1 | head -1
```

| Boot line | Namespace | Hibernate | Java | Other majors | Consequence for fixes |
| --- | --- | --- | --- | --- | --- |
| 2.x | `javax.*` | 5.x | 8–17 | Jackson 2, Jersey 2, CXF 3 | `@MockBean`, `spring-boot-starter-web`, SQL bind log key is `org.hibernate.type.descriptor.sql.BasicBinder` |
| 3.x | `jakarta.*` | 6.x | 17+ | Jackson 2, Jersey 3, CXF 4 | `javax.persistence`/`javax.servlet` imports are compile errors; `@MockBean` deprecated from 3.4 |
| 4.x | `jakarta.*` (EE 11, Servlet 6.1) | 7.x | 17+ | Jackson 3 (`tools.jackson`), Spring Framework 7 | starters renamed (`-web`→`-webmvc`, `-aop`→`-aspectj`), `@MockBean` removed → `@MockitoBean`, Flyway/Liquibase need `spring-boot-starter-flyway` / `-liquibase`, `hibernate-jpamodelgen`→`hibernate-processor`, Undertow gone |

Never propose a fix that belongs to another row (e.g. `@MockitoBean` on Boot 2, `javax.persistence` on Boot 3+). Renamed properties: run once with `spring-boot-properties-migrator` on the classpath and fix every line it reports, then remove it.

## 2. Symptom → cause → fix

| Symptom (verbatim tell) | Cause | Fix (in this order) |
| --- | --- | --- |
| `LazyInitializationException: could not initialize proxy … no Session` / `failed to lazily initialize a collection of role` | lazy association touched after the transaction/session closed (controller, async thread, `toString`, Jackson) | 1. `JOIN FETCH` or `@EntityGraph(attributePaths = {...})` on the repository method that serves this use; 2. DTO projection (`select new …` or interface projection). Never "fix" with `spring.jpa.open-in-view=true` (it is the default; set it to `false` so the warning stops masking these) or `FetchType.EAGER` |
| N+1: `generate_statistics` prints `… queries executed to database: 51` for a page of 50 | per-row lazy load in a loop | same as above, or `@BatchSize(size = 50)` on the association / `spring.jpa.properties.hibernate.default_batch_fetch_size=50`. Threshold: queries ≥ top-level rows ⇒ N+1 (a correct page is 1–3 queries whatever the row count) |
| `MultipleBagFetchException: cannot simultaneously fetch multiple bags` | two `List` associations in one `JOIN FETCH` | make one of them a `Set`, or split into two queries in the same transaction |
| `@Transactional` has no effect: no `TransactionInterceptor` frame in the trace; `TransactionSynchronizationManager.isActualTransactionActive()` → `false` | self-invocation (same-class call bypasses the proxy), `private`/`final` method, or bean created with `new` | move the method to another bean, or use `TransactionTemplate.execute(...)` |
| Exception thrown, row still committed | checked exception: Spring rolls back only on `RuntimeException`/`Error` | `@Transactional(rollbackFor = Exception.class)` or wrap in an unchecked exception |
| `InvalidDefinitionException: No serializer found for class org.hibernate.proxy.pojo.bytebuddy.ByteBuddyInterceptor` | entity (with lazy proxy) returned from a controller | return a record/DTO; never `spring.jackson.serialization.fail-on-empty-beans=false` or `@JsonIgnore` scattered on entities |
| `package javax.persistence does not exist` / `ClassNotFoundException: javax.servlet.Filter` | Boot 3+/EE 9+ moved to `jakarta.*`; a library still on `javax` | `mvn -U org.openrewrite.maven:rewrite-maven-plugin:run -Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:RELEASE -Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_5` (Boot 4: `…boot4.UpgradeSpringBoot_4_0`; `mvn rewrite:discover` lists ids); then `dependency:tree` for any remaining `javax.*` artifact and bump it |
| `HikariPool-1 - Connection is not available, request timed out after 30000ms` | pool (default 10) exhausted by open-in-view holding a connection for the whole request, or long transactions | `spring.jpa.open-in-view=false`; `@Transactional(readOnly = true)` on reads; size the pool `cores × 2 + disks`, not 100; find holders with `spring.datasource.hikari.leak-detection-threshold=20000` |
| `The dependencies of some of the beans … form a cycle` | constructor-injection cycle (field injection hid it) | extract the shared part into a third bean or use `@Lazy` on one side; never `spring.main.allow-circular-references=true` |
| Schema changes "work locally", fail on deploy; `ddl-auto` is `update`/`create-drop` | Hibernate DDL in production | `spring.jpa.hibernate.ddl-auto=validate` + Flyway migration `V<n>__<desc>.sql` |
| `Set<Entity>` loses/duplicates elements across `persist` | `hashCode` uses the generated id (null before insert) | `equals`/`hashCode` on a business key, or `hashCode() { return getClass().hashCode(); }` with id-based `equals` |
| Jersey `@Path` resource returns 404 while `@RestController` works | resource not registered; Jersey servlet mapped at `/*` shadows MVC | `ResourceConfig` bean with `register(X.class)` or `packages("com.acme.api")`; `spring.jersey.application-path=/api` to keep MVC routes |
| JAX-WS `wsimport`/`jaxws-maven-plugin` fails on Java 11+ | JAX-WS removed from the JDK (JEP 320) | codegen with `org.apache.cxf:cxf-codegen-plugin` (`wsdl2java` goal) or `com.sun.xml.ws:jaxws-maven-plugin` 4.x; runtime `org.apache.cxf:cxf-spring-boot-starter-jaxws` (3.x = javax, 4.x = jakarta) — Spring ships no JAX-WS starter |
| SOAP client: `SOAPFaultException` vs `WebServiceException: Could not send Message` | first = server rejected the body (schema/auth), second = transport (URL, TLS, proxy) | log envelopes with `new LoggingFeature()` on the `JaxWsProxyFactoryBean`; transport errors → error-triage's network row |

## 3. See what Spring and Hibernate actually do

```properties
logging.level.org.hibernate.SQL=DEBUG                # every statement
logging.level.org.hibernate.orm.jdbc.bind=TRACE      # bound parameters (Hibernate 6/7); 5.x: org.hibernate.type.descriptor.sql.BasicBinder=TRACE
spring.jpa.properties.hibernate.generate_statistics=true
logging.level.org.hibernate.stat=DEBUG               # per-session query counts
spring.jpa.properties.hibernate.session.events.log.LOG_QUERIES_SLOWER_THAN_MS=50
```

- Why a bean did or did not load: `./mvnw spring-boot:run -Dspring-boot.run.arguments=--debug` → `CONDITIONS EVALUATION REPORT`, or `GET /actuator/conditions` when Actuator is on.
- Which `application-*.properties` won: `GET /actuator/env/<property>` shows the source per value.
- Run one test with its SQL: `./mvnw -q test -Dtest=OrderServiceTest#loadsOrders -Dlogging.level.org.hibernate.SQL=DEBUG`.
- Web slice vs full context: `@WebMvcTest(OrderController.class)` + `@MockitoBean` (Boot 3.4+/4) for controller logic; `@DataJpaTest` (replaces the datasource with H2 unless `@AutoConfigureTestDatabase(replace = NONE)`) for queries; `@SpringBootTest` only when wiring itself is the question.

## Example

User: "`/orders` takes 4 s for 200 orders on Boot 3.3; the query looks fine."

1. `./mvnw -q help:evaluate -Dexpression=project.parent.version -DforceStdout` → `3.3.4`; `dependency:tree -Dincludes=org.hibernate.orm:hibernate-core` → 6.5.2 ⇒ row "3.x", use `orm.jdbc.bind` log key.
2. Add `generate_statistics=true`, hit the endpoint once: `… 201 queries executed to database` for 200 rows ⇒ N+1 (201 ≥ 200). SQL log shows `select … from order_line where order_id=?` × 200.
3. `OrderRepository`: `@Query("select o from Order o join fetch o.lines where o.status = :s")` → re-run: `1 queries executed`, endpoint 180 ms. `lines` and `discounts` both `List` → second fetch would raise `MultipleBagFetchException`, so `discounts` gets `@BatchSize(size = 50)` instead.
4. `spring.jpa.open-in-view=false` in `application.properties`; startup warning gone; the controller still works because nothing lazy is touched after the service returns a DTO.
