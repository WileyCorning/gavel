#!/usr/bin/env sh

docker run -it -e POSTGRES_DB=gavel -e POSTGRES_USER=gavel -e POSTGRES_PASSWORD=123456 -p 5432:5432 postgres
