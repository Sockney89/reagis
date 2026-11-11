# Reagis

Reagis is a showcase project for the [Aegis](https://github.com/Sockney89/aegis-dist) programming language: a small, native, type-safe reimplementation of a subset of the Redis command surface in two serving modes (TCP command ingestion and REST API).

This is **not** a competitor to Redis and not a drop-in replacement. Redis is an exceptional piece of engineering with decades of work behind it; Reagis exists to demonstrate Aegis capabilities (structs, enums, pattern matching, closures, HTTP/TCP stdlib, FFI-friendly design) in a realistic, non-trivial application. Full credit and respect to the Redis creators and maintainers.

## Features

- Dual serving mode selected by argument: `tcp` (line-based command protocol) or `rest` (HTTP/JSON).
- Type-safe value engine using an `RValue` enum: strings, lists, sets, hashes, JSON, sorted sets.
- Command dispatch with strict argument counts and key validation to resist injection.
- RESP-like TCP responses and JSON responses for REST.
- Performance-conscious implementation: `StrBuf` builders, O(n) list pushes, closure-based sorting.

## Supported commands

Strings: `PING`, `ECHO`, `SET`, `GET`, `DEL`, `EXISTS`, `INCR`, `DECR`, `APPEND`, `STRLEN`

Lists: `LPUSH`, `RPUSH`, `LPOP`, `RPOP`, `LLEN`, `LRANGE`, `LINDEX`

Sets: `SADD`, `SREM`, `SMEMBERS`, `SCARD`, `SISMEMBER`

Hashes: `HSET`, `HGET`, `HDEL`, `HGETALL`, `HLEN`

JSON: `JSON.SET`, `JSON.GET`

Sorted sets: `ZADD`, `ZSCORE`, `ZRANGE`

Utility: `TYPE`, `DBSIZE`, `FLUSHALL`

## Requirements

Install Aegis from the official distribution repository:

- Repository: https://github.com/Sockney89/aegis-dist
- Follow the install instructions published there (Windows x64 and Linux x86_64). The toolchain provides `aegis` (compiler front-end) and `aegis-mcp`.

A C compiler compatible with clang is required for the final link step (`AEGIS_CC`).

## Build

From the project root:

```powershell
aegis src\reagis.aegis --main App::main --emit-exe reagis
```

This produces `reagis.exe` (Windows) or `reagis` (Linux).

## Usage

```text
reagis [tcp|rest] [port]
```

- Mode defaults to `tcp`.
- TCP port defaults to `6380`.
- REST port defaults to `8080`.

Examples:

```powershell
# TCP command mode
.\reagis.exe tcp 6399

# REST API mode
.\reagis.exe rest 8099
```

TCP protocol (one command per line):

```text
SET foo bar
GET foo
LPUSH mylist a b c
LRANGE mylist 0 -1
```

REST API (POST `/command` with JSON):

```json
{"cmd":"SET","args":["foo","bar"]}
```

Health check: `GET /health`. Convenience: `GET /get?key=foo`.

## Test application

A Python test client is included under `tests/test_reagis.py`. It exercises the command surface and collects latency/response-time metrics.

```powershell
# TCP
python tests\test_reagis.py --mode tcp --port 6399

# REST
python tests\test_reagis.py --mode rest --port 8099
```

## Measured performance

Environment: local Windows machine, single client, one command per connection (client opens a new connection per request). Median values are more representative than averages because a few first-request outliers dominate the mean.

TCP mode (27 commands):

- Median latency: ~0.54-0.59 ms
- Minimum: ~0.50 ms
- Maximum observed: ~12-62 ms (first requests / OS scheduling outliers)
- Mean: ~1.4-4.8 ms (outlier-skewed)

REST mode (11 commands):

- Median latency: ~0.96-1.39 ms
- Minimum: ~0.83-0.89 ms
- Maximum observed: ~39-98 ms (first requests / OS scheduling outliers)
- Mean: ~4.5-10.5 ms (outlier-skewed)

These numbers are a showcase of Aegis throughput on a small workload, not a benchmark against Redis. Redis remains substantially faster and far more complete.

## Project layout

```text
src/reagis.aegis    # Aegis source (engine, TCP server, REST server, app entry)
tests/test_reagis.py # Python test client with metrics
.gitignore          # ignores build artifacts
```