#!/bin/bash
# Create additional databases beyond POSTGRES_DB (which postgres creates automatically)
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE evolution_api;
    GRANT ALL PRIVILEGES ON DATABASE evolution_api TO $POSTGRES_USER;
EOSQL
