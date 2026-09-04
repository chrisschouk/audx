# Security Policy

audx is local-first software. It should not make network requests during normal
music-making workflows.

## Reporting a Vulnerability

Please report security issues privately to:

`chrisschofield@totalaudiopromo.com`

Include:

- affected version or commit
- operating system
- reproduction steps
- whether local files, network access, or credentials are involved

## Local Network Surfaces

`audx serve` (and `audx open --serve`) hosts a **read-only** live monitor on
localhost by default. It exposes session state for convenience — keep the default
localhost binding unless you intentionally want another device on your network
to connect.

The static browser studio (`site/studio.html`) runs entirely in the browser and
does not read your local filesystem via the CLI server.

## AI and Network Features

AI-related features are opt-in and require user-provided credentials. API keys
must not be stored in `.audx` project files.
