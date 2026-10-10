---
name: api-debugging
description: Reproduce one failing HTTP call with curl and read its status, headers, body and request ID. Use when a named endpoint fails with the request in hand: "works in Postman but not in code", 401/403/404/415/422/429 with a body, CORS, "need the request ID for support". Do not use with no request and the layer unknown (error-triage), once the fault is in your own handler (debug-from-raw-logs), or to file it (bug-report-writing).
---

# API Debugging

An API bug argued from the client's error message is argued from a paraphrase: the SDK swallowed the body, the browser hid the preflight, the retry layer changed the method. Reproduce the one call outside the application, read everything the server sent, then change one variable per call. A *probe* is one curl invocation that differs from the failing request in exactly one variable.

Entry condition: the user can name the endpoint and the client that calls it. Without that (a `502` from "somewhere", "the app is down"): Call the Skill tool with "error-triage" and return with its layer.

## 1. Capture the request as a curl command

Get the request exactly as the failing client sends it, not as the docs describe it:

| Client | How to get it verbatim |
| --- | --- |
| Browser | DevTools, Network, right-click the request, Copy as cURL (bash). Includes cookies, `Origin`, `Sec-Fetch-*`. |
| Postman, Insomnia, Bruno | Code snippet, cURL. The "works in Postman" request is the control; keep it. |
| Your own code | Log method, final URL, every header name (values redacted) and the raw body bytes at the HTTP layer: `DEBUG=*` (Node `undici`/`axios`), `logging.getLogger("urllib3").setLevel(logging.DEBUG)` (Python), `-Djdk.httpclient.HttpClient.log=requests,headers` (Java), `curl -v` equivalent in Dart `HttpClient` via `HttpOverrides`. |
| Mobile or server-to-server | A HAR or proxy capture (`mitmproxy`, Charles); export the single entry. |

Redact credential *values*, keep header *names* and value lengths: an `Authorization` header of 31 characters when a JWT is 800 is a finding.

Run it with the status and the timing breakdown, body to a file:

```sh
curl -sS -o resp.body -D resp.headers --fail-with-body \
  -w 'status=%{http_code} redirects=%{num_redirects} dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' \
  -X POST 'https://api.example.com/v2/payments' -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' --data-binary @req.json
```

`--fail-with-body` (curl 7.76+) keeps the error body and still exits 22; older curl needs `-f` dropped or the body is printed but exit is 0. `-sS` hides progress, shows errors. `--data-binary` sends the file byte for byte; `-d` strips newlines.

**Done when** one curl command on disk returns the same status (or the same curl exit code, e.g. `curl: (28)`) as the failing client, run twice.

## 2. Read the whole response

Three places, in order: `resp.headers` (status line, `content-type`, request-ID header, rate-limit headers, `www-authenticate`, `allow`, `retry-after`, `access-control-*`), `resp.body` (first 20 lines: `head -20 resp.body | jq .` when `content-type` is JSON; RFC 9457 `application/problem+json` carries `type`, `title`, `detail`, `instance`), the `-w` timing line (`ttfb` near `total` and both near the client timeout means the server, not the network).

Find the request ID; it is the key for the server's logs and the vendor's support ticket:

| Header (case-insensitive) | Who sets it |
| --- | --- |
| `x-request-id`, `x-correlation-id` | Most frameworks, nginx, Envoy, Spring Cloud Sleuth, Rails, Express `express-request-id` |
| `x-amzn-requestid`, `x-amz-request-id`, `x-amz-cf-id`, `x-amzn-trace-id` | AWS API Gateway, S3, CloudFront, ALB |
| `cf-ray` | Cloudflare (edge and the `<ray>-<colo>` suffix names the POP) |
| `x-ms-request-id`, `x-ms-correlation-request-id` | Azure |
| `x-github-request-id`, `x-stripe-request-id`, `request-id` (Stripe), `x-request-id` (OpenAI, Anthropic) | Vendor APIs; quote it verbatim in a support ticket |
| `traceparent` (`00-<trace-id>-<span-id>-01`) | W3C Trace Context; the `trace-id` is the search key in Jaeger, Tempo, Datadog |

No request-ID header on an error: the error came from a hop before the API (WAF, CDN, load balancer, corporate proxy); compare `server` and `via` headers with a known-good response.

**Done when** five values are written down: status, `content-type`, request ID or `none`, the first line of the body, and which hop answered (API, gateway, CDN, proxy).

## 3. Probe one variable per call

Diff the failing request against the control (the Postman request, yesterday's HAR, the docs' example) header by header and byte by byte (`diff <(sort fail.headers) <(sort ok.headers)`), then flip one variable per curl run and note the status after each.

| Status or tell | Variable to flip first | Probe |
| --- | --- | --- |
| `401` + `www-authenticate: Bearer error="invalid_token"` | the credential | Same call with a token minted now; decode the old one (`jwt decode`, `cut -d. -f2 \| base64 -d`) and read `exp`, `aud`, `iss`. |
| `403` with a body, token is valid | scope, tenant, signed headers | Same token on a known-permitted endpoint; for signed requests, compare `Content-Type` and `Host` byte for byte with the signing input (`application/json` versus `application/json; charset=utf-8` breaks AWS SigV4 and HMAC schemes). |
| `403`/`503` with HTML body and `cf-ray` or `server: awselb` | WAF or bot rule on `User-Agent`, missing `Accept` | Add `-A 'Mozilla/5.0'` and `-H 'Accept: */*'`; a flip means a WAF rule, not the API. |
| `404` in code, 200 in Postman | URL encoding, trailing slash, `Host`/base URL per environment | `-w '%{url_effective}\n'`; percent-encode reserved characters in path segments (`jq -rn '"<v>" \| @uri'`). |
| `405` + `allow:` header | method changed by a redirect or proxy | `-L` turns `POST` into `GET` after `301`/`302`; use `--post301 --post302` or the final URL directly. |
| `411`, `413`, `417` | body framing | `417`: add `-H 'Expect:'` (curl adds `Expect: 100-continue` above 1 KiB, some proxies reject it). `413`: `-w '%{size_upload}'` against the documented limit. |
| `415`, `422`, `400` with a field-level body | content type, body shape | Send the docs' example body as is; then your body with `Content-Type` copied from the control. |
| `429` + `retry-after` or `ratelimit-remaining: 0` (IETF draft, vendor variants `x-ratelimit-*`) | request rate, shared key | Read `retry-after` (seconds or HTTP date); one key shared across workers exhausts the bucket. `curl --retry 3 --retry-delay 0` honours `retry-after` on 429 and 503. |
| CORS error in the browser console, 200 in curl | preflight | `curl -i -X OPTIONS <url> -H 'Origin: https://app.example.com' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: authorization,content-type'`; the fix is server-side `access-control-allow-*`, never a curl flag. |
| `curl: (28)` on one endpoint, others fast | server-side latency | `-m 60`; `ttfb` close to `total` is the handler: Call the Skill tool with "performance-profiling" with that `ttfb` as its baseline. `--http1.1` rules out an HTTP/2 stream limit; `--resolve api.example.com:443:<ip>` pins one backend behind a load balancer. |
| `curl: (35)`/`(60)` TLS | SNI, CA, mTLS | `--cacert <bundle>` or `--cert client.pem --key client.key`; `-k` only to confirm the diagnosis, never as the fix. |
| `302` to a login page from an API call | cookie or session auth expected | `-c jar -b jar` round trip; an API that redirects wants a session, not a bearer. |

Keep a two-column log of probes (`<variable>: <status before> -> <status after>`); three probes with no flip means the variable is not in the request: go to the server side with the request ID.

**Done when** one variable flips the status (or the log shows every table row for that status tried) and the log is in the reply.

## 4. Report and hand off

```
Endpoint: <METHOD URL>. Request ID: <id or none>. Status: <code> from <hop>. Cause: <variable>: <failing value> -> <working value>. Fix: <one change in the client, server, or config>.
Probe log: <variable: before -> after> (one per line)
```

- The flip is a client header, URL, body or encoding: apply it in the client code and rerun the curl from phase 1 to show the new status.
- The server answered wrongly with the right request (request ID found in your own service's logs): Call the Skill tool with "debug-from-raw-logs" with the request ID and the probe log as evidence.
- The server is a vendor's and the user wants it reported: Call the Skill tool with "bug-report-writing" with the curl command, request ID and probe log as the repro.
- The probe log shows no HTTP response at all (`curl: (6)`, `(7)`, `(28)` on every endpoint): Call the Skill tool with "error-triage".

**Done when** the report block is in the reply and exactly one of the four above has happened.

## Anti-patterns

- Debugging from the SDK's exception message instead of the wire response (`AxiosError: Request failed with status code 403` carries none of the body).
- Changing two headers in one probe; a flip then has two candidate causes.
- Sending `-k`, `-L`, or a hard-coded `User-Agent` as "the fix" when they were diagnostics.
- Asking a vendor for help without the request ID and the exact UTC timestamp.

## Example

**Report:** "Our Node service gets `403 Forbidden` from the partner's `/v2/payments` endpoint; the identical body works in Postman with the same API key."

1. Capture: Postman "Code, cURL" is the control. The service logs its outgoing request with `DEBUG=undici*`; curl rebuilt from it returns `status=403 ttfb=0.09 total=0.09` twice.
2. Read: `content-type: application/problem+json`, body `{"type":"https://partner.example/errors/signature","title":"Forbidden","detail":"signature mismatch"}`, `x-request-id: 7f3c…`, `server: nginx` (the API itself, not a WAF).
3. Probe: `diff` of header names shows the service sends `content-type: application/json; charset=utf-8`, Postman sends `application/json`. Probe log: `content-type charset: 403 -> 200`. The HMAC signature covers the `Content-Type` string.
4. Report: `Endpoint: POST https://partner.example/v2/payments. Request ID: 7f3c…. Status: 403 from API. Cause: content-type: "application/json; charset=utf-8" -> "application/json". Fix: set the header explicitly in the client; axios appends charset by default.` Applied in the client; phase 1 curl now returns 200.
