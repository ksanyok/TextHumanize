# Security Policy

TextHumanize processes user text locally and is designed to avoid network calls
in the default path. Security reports are still important because the project
ships parsers, CLI tools, web/API examples, PHP and TypeScript ports, and text
normalization logic that may be embedded in production systems.

## Supported Versions

| Version | Status |
| ------- | ------ |
| `0.34.x` | Supported |
| `< 0.34` | Best-effort fixes only |

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Preferred reporting channels:

- GitHub private vulnerability reporting, if available for this repository.
- Email: ksanyok@me.com

Include as much detail as you safely can:

- Affected package or surface: Python, PHP, TypeScript, WordPress plugin, CLI,
  REST API, Docker image, documentation example, or build/release tooling.
- A minimal proof of concept or reproduction steps.
- Expected impact, such as denial of service, data exposure, path traversal,
  code execution, dependency confusion, or unsafe HTML/Markdown handling.
- Version, commit hash, operating system, and runtime versions.

Do not include confidential third-party text unless you have permission to share
it. Redacted or synthetic samples are preferred.

## Response Targets

- Initial acknowledgement: within 7 days.
- Triage decision: within 14 days when enough information is provided.
- Fix timeline: depends on severity, exploitability, and release scope.

## Scope

In scope:

- ReDoS or CPU/memory exhaustion from crafted text inputs.
- Unsafe file, path, archive, or model-weight handling.
- Unsafe HTML, Markdown, or Unicode normalization behavior that can cause XSS,
  spoofing, data loss, or security boundary confusion in integrations.
- CLI, REST API, Docker, WordPress, PHP, TypeScript, or CI/CD vulnerabilities.
- Supply-chain issues in release artifacts or package metadata.

Out of scope:

- Generic requests to bypass external AI detectors.
- Claims that a detector verdict is inaccurate without a security impact.
- Social engineering, spam, or automated abuse against project maintainers.
- Denial-of-service tests against public project infrastructure without prior
  approval.

## REST API hardening (network safety)

The bundled REST API (`python -m texthumanize.api`) is **unauthenticated** and
intended for local/trusted deployment. As of `0.34.0` it ships secure defaults:

- **Binds to `127.0.0.1` by default.** Exposing it on all interfaces requires an
  explicit `--host 0.0.0.0`, which prints a warning. Put it behind
  authentication and a reverse proxy before exposing it.
- **Remote AI backends are disabled by default.** Client-supplied backend
  parameters (`backend`, `oss_api_url`, `openai_api_key`, `ollama_url`) are
  rejected with HTTP `403` unless the operator sets
  `TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS=1`. This closes the unauthenticated
  SSRF vector (CWE-918) where a caller could point the server at an internal URL.
- **Outbound URLs are SSRF-validated.** Even when remote backends are enabled,
  any user-supplied URL is checked by `texthumanize.validate_outbound_url()`,
  which resolves the host and rejects loopback, private (RFC1918/ULA),
  link-local (including the `169.254.169.254` cloud-metadata endpoint),
  reserved, and multicast targets. HTTP `400` is returned for unsafe URLs.

If you embed the library behind your own HTTP surface, reuse
`validate_outbound_url()` for any endpoint you let end users influence. Note it
validates at resolve time; pin the resolved IP through the connection if your
threat model includes DNS rebinding.

## Safe Harbor

Good-faith security research is welcome when it avoids privacy violations,
service disruption, data destruction, and public disclosure before maintainers
can investigate. We will not pursue action against researchers who follow this
policy and report responsibly.
