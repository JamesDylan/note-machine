# Capture-source feasibility spike: system-audio tap mechanism

Type: prototype
Blocked by: —

## Question

Does the macOS Core Audio process tap (14.2+) actually work, as a small Swift helper piping to stdout, for note-machine's purposes? Specifically: can PyObjC (or the Python side generally) consume the tap's real-time callback without audio glitches; what's the true minimum macOS version (Apple's docs say 14.2, AudioCap's README says 14.4); and does AudioCap behave as documented when driven from this codebase.

## Context

- Carried over from ticket 13 (capture-source split), where these were flagged as empirical unknowns a grilling session can't resolve — they need code run against real hardware, not a decision.
- From 02 (Local-first peer architectures): the clean route for a Python tool is a small Swift helper based on AudioCap (BSD-2) piping to stdout, not BlackHole (GPL-3.0, manual driver install). AudioTee has no licence file — treat as a design reference only, don't build on it directly.
- Ticket 13's decisions (binary source split, headphone gate, shared Whisper instance, whole-system tap scope, visible degrade-on-failure) all assume this mechanism can deliver a usable `system` source. None of them validate that it does — they're what gets built once this spike confirms it's viable, or what has to change if it doesn't.

## Why split from 13

13 was scoped as a grilling session — decisions only, resolvable through conversation. These questions are answerable only by running code against real hardware. Type: prototype, not grilling.
