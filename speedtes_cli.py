#!/usr/bin/env python3
"""Compatibility launcher for the signed distribution speedtest-cli package."""
import os
os.execv("/usr/bin/speedtest-cli", ["speedtest-cli", *__import__("sys").argv[1:]])
