#!/usr/bin/env bash
export PYTHONPATH=.
export PYTHONUNBUFFERED=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export MPLBACKEND=Agg
cd /root/paper3_audit_rerun_20260830
exec "$@"