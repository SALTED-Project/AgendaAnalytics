#!/bin/sh

# Generate the schema in the project's Python virtual environment (venv) using Poetry
cd app || exit
poetry run python -m prisma generate --schema ./schemas/schema.prisma
