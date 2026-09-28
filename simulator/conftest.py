"""Pytest configuration ensuring simulator package and backend are discoverable."""

import os
import sys

# Ensure simulator package root is on sys.path
simulator_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if simulator_dir not in sys.path:
    sys.path.insert(0, simulator_dir)

# Ensure repository root and backend directory are on sys.path if running in monorepo
repo_root = os.path.abspath(os.path.join(simulator_dir, ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

backend_dir = os.path.join(repo_root, "backend")
if os.path.isdir(backend_dir) and backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
