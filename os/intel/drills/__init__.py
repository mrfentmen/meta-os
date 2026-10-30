"""Watchdog drill harnesses (Milo lane, WDG-020/021/022).

Each drill runs unattended on fixtures: no network, no Redis, no
bus posts. The watchdog itself is pure snapshot evaluation
(intel/watchdog.py), so a drill stages a snapshot the way a real
worker would stage it, runs a tick, and asserts the outcome.
"""
