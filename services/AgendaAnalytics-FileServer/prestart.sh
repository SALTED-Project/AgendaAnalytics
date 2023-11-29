#! /usr/bin/env bash

# # Increase verbosity for prisma commands
PRISMA_PY_DEBUG=1
DEBUG="*"

# # Generate client
prisma generate --schema /app/schemas/schema.prisma

# Let the DB start
python /app/backend_pre_start.py

# # Apply DB migrations
prisma db push --schema /app/schemas/schema.prisma #--skip-generate
