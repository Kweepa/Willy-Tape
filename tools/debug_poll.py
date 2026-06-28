#!/usr/bin/env python3
"""Deprecated — use debug_dump.py instead (polling halts VICE emulation)."""

import sys

print("debug_poll.py is deprecated: polling the VICE remote monitor halts the CPU.")
print("Use debug_dump.py once after Willy dies instead.")
print("  python tools\\debug_dump.py")
raise SystemExit(1 if len(sys.argv) > 1 and sys.argv[1] != "--help" else 0)
