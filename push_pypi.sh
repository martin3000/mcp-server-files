#!/bin/bash
set -e

rm -rf dist/
python -m build
python -m twine upload dist/*
echo "PyPI: fertig."
