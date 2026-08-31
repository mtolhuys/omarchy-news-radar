# Dependency contract

## Runtime platform

Radar targets the maintained Omarchy Quattro third-party plugin contract selected by the disposable Plugin Lab: `schemaVersion: 1`, paired `panel` and `bar-widget` entry points, current shell-injected properties, current `Color`/`Style`/`Border` UI tokens, shell IPC, Hyprland, and Quickshell/QML modules shipped by Omarchy.

A public minimum Omarchy release must not be claimed until clean-clone installation and runtime acceptance pass against that exact release.

## Required runtime commands

The implementation may use commands supplied by the tested Omarchy environment:

- the system `python3` and its standard library for feed retrieval, validation, cache/state mutation, collection, and static publication;
- `omarchy-shell` for maintained shell IPC;
- `hyprctl` for explicit shortcut status, installation validation, and removal validation;
- `uwsm-app` and `xdg-open` for explicit source opening;
- ordinary POSIX/GNU file utilities only where Python would not provide a clearer structural operation.

Do not assume Node.js, npm, a Python virtual environment, pip packages, a browser engine, SQLite service, Redis, systemd unit, compiler, or resident daemon at plugin runtime.

## Python policy

Use the Python 3 version shipped by the current supported Omarchy environment. Prefer dataclasses, enums, pathlib, urllib, hashlib, json, html, xml, tempfile, datetime, and `unittest` from the standard library.

Code must have complete useful type annotations, deterministic serialization, explicit exception boundaries, and no import-time network or filesystem mutation. Optional developer type checking may use a locally available checker, but the required source gate cannot depend on downloading one.

## QML policy

QML owns rendering, focus, input, window lifecycle, and launching fixed helper commands. Shared transformations that must exactly match publisher/client validation belong in Python rather than duplicated JavaScript.

Inspect the current Omarchy source selected by Plugin Lab before importing shell components. Do not copy private implementation details when a maintained public component or token exists. Entry-point and nested dependency paths remain relative to the plugin root; do not add versioned QML directories solely as a cache buster.

## Collector and CI

Production collection uses GitHub’s REST API, the raw marketplace catalog, and catalog-declared thumbnails at the official marketplace origin over HTTPS. Image inspection is implemented with Python standard-library byte parsing and hashing; Pillow/ImageMagick are not required. GitHub Actions may use the repository-provided `GITHUB_TOKEN` with least privilege. No personal access token is required for ordinary operation.

Build and tests require only:

- Python 3;
- GNU Make;
- Git;
- Bash for test harnesses and Plugin Lab scenarios;
- optional ShellCheck when present;
- optional `qmllint` and a selected Omarchy source checkout for development validation.

Unit and integration tests must not require internet access. Network adapters use committed fixtures and an in-process loopback HTTP server.

## Dependency review

A proposed dependency requires a recorded decision covering:

- the capability that cannot be met clearly with existing contracts;
- runtime versus development scope;
- package size and transitive graph;
- maintenance and release cadence;
- license compatibility;
- security and update behavior;
- offline testability;
- removal and migration plan.

Convenience, fashionable tooling, or reducing a small amount of straightforward code is not sufficient.
