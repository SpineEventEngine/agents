# 🚨 Advanced safety rules

- **Never commit secrets** — private keys, service-account JSON, tokens. The
  decrypted `*.gpg` twins (e.g. `spine-dev.json`) must stay gitignored; the
  shared `secret-scan` pre-commit hook is a backstop, not a licence to bypass.
  See `.agents/guidelines/safety-rules.md` → *Secrets and credentials*.
- Do **not** auto-update external dependencies without explicit request.
- Do **not** inject analytics or telemetry code.
- Flag any usage of unsafe constructs (e.g., reflection, I/O on the main thread).
- Avoid generating blocking calls inside coroutines.
