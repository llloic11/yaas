#!/bin/bash
cd "$(dirname ${BASH_SOURCE})/downloads"
exec ../watch_download.py
