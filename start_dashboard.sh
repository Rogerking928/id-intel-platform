#!/usr/bin/env bash
# Convenience launcher for the dashboard (WSL/Linux/macOS).
# Windows users: just run  streamlit run app/Home.py
cd "$(dirname "$0")" || exit 1
[ -f .env ] && { set -a; source .env; set +a; }
exec streamlit run app/Home.py "$@"
