import argparse
import json
import socket
import statistics
import time
import urllib.request
import subprocess
import sys
import os

def tcp_call(host, port, line):
    t0 = time.perf_counter()
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall((line + "\r\n").encode())
        data = b""
        s.settimeout(1.0)
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                # stop early if we have a complete simple response
                if b"\r\n" in data and not data.startswith(b"*"):
                    break
                if data.startswith(b"*"):
                    # crude: read a bit more
                    if data.count(b"\r\n") >= 3:
                        break
        except socket.timeout:
            pass
    t1 = time.perf_counter()
    return data.decode(errors="replace"), (t1 - t0) * 1000.0

def rest_call(host, port, payload):
    t0 = time.perf_counter()
    req = urllib.request.Request(
        f"http://{host}:{port}/command",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode()
    t1 = time.perf_counter()
    return body, (t1 - t0) * 1000.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["tcp", "rest"], default="tcp")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=6381)
    args = ap.parse_args()

    latencies = []
    results = []

    def record(name, ok, ms, detail=""):
        latencies.append(ms)
        results.append((name, ok, ms, detail))
        print(f"{name:24} ok={ok!s:5} {ms:8.3f} ms {detail}")

    if args.mode == "tcp":
        # strings
        d, ms = tcp_call(args.host, args.port, "FLUSHALL")
        record("FLUSHALL", d.startswith("+"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "SET foo bar")
        record("SET", d.startswith("+"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "GET foo")
        record("GET", "bar" in d, ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "EXISTS foo")
        record("EXISTS", d.startswith(":1"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "INCR counter")
        record("INCR", d.startswith(":1"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "INCR counter")
        record("INCR2", d.startswith(":2"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "APPEND foo baz")
        record("APPEND", d.startswith(":6"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "STRLEN foo")
        record("STRLEN", d.startswith(":6"), ms, d.strip())
        # lists
        d, ms = tcp_call(args.host, args.port, "RPUSH mylist a b c")
        record("RPUSH", d.startswith(":3"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "LLEN mylist")
        record("LLEN", d.startswith(":3"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "LPOP mylist")
        record("LPOP", "a" in d, ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "LRANGE mylist 0 -1")
        record("LRANGE", "b" in d and "c" in d, ms, d.strip().replace("\r\n", " "))
        # sets
        d, ms = tcp_call(args.host, args.port, "SADD myset x y x")
        record("SADD", d.startswith(":2"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "SCARD myset")
        record("SCARD", d.startswith(":2"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "SISMEMBER myset x")
        record("SISMEMBER", d.startswith(":1"), ms, d.strip())
        # hashes
        d, ms = tcp_call(args.host, args.port, "HSET myhash f v")
        record("HSET", d.startswith(":"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "HGET myhash f")
        record("HGET", "v" in d, ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "HLEN myhash")
        record("HLEN", d.startswith(":1"), ms, d.strip())
        # json
        d, ms = tcp_call(args.host, args.port, 'JSON.SET myjson "{\\"a\\":1}"')
        record("JSON.SET", d.startswith("+"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "JSON.GET myjson")
        record("JSON.GET", "a" in d, ms, d.strip())
        # sorted set
        d, ms = tcp_call(args.host, args.port, "ZADD z 2 b")
        record("ZADD", d.startswith(":"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "ZADD z 1 a")
        record("ZADD2", d.startswith(":"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, "ZRANGE z 0 -1")
        record("ZRANGE", "a" in d, ms, d.strip().replace("\r\n", " "))
        # type
        d, ms = tcp_call(args.host, args.port, "TYPE foo")
        record("TYPE", "string" in d, ms, d.strip())
        # injection attempts
        d, ms = tcp_call(args.host, args.port, "SET bad-key! value")
        record("INJECT_KEY", d.startswith("-"), ms, d.strip())
        d, ms = tcp_call(args.host, args.port, 'SET foo "bar"; FLUSHALL')
        record("INJECT_CMD", d.startswith("-") or "OK" not in d, ms, d.strip())
        # ping
        d, ms = tcp_call(args.host, args.port, "PING")
        record("PING", "PONG" in d, ms, d.strip())
    else:
        def post(payload):
            return rest_call(args.host, args.port, payload)
        body, ms = post({"cmd": "FLUSHALL"})
        record("FLUSHALL", "OK" in body, ms, body)
        body, ms = post({"cmd": "SET", "args": ["foo", "bar"]})
        record("SET", "OK" in body, ms, body)
        body, ms = rest_call(args.host, args.port, None) if False else (None, 0)
        # GET via command
        body, ms = post({"cmd": "GET", "args": ["foo"]})
        record("GET", "bar" in body, ms, body)
        body, ms = post({"cmd": "INCR", "args": ["counter"]})
        record("INCR", '"value":1' in body or ":1" in body, ms, body)
        body, ms = post({"cmd": "LPUSH", "args": ["mylist", "a", "b", "c"]})
        record("LPUSH", "3" in body, ms, body)
        body, ms = post({"cmd": "LRANGE", "args": ["mylist", "0", "-1"]})
        record("LRANGE", "a" in body, ms, body)
        body, ms = post({"cmd": "JSON.SET", "args": ["myjson", '{"a":1}']})
        record("JSON.SET", "OK" in body, ms, body)
        body, ms = post({"cmd": "JSON.GET", "args": ["myjson"]})
        record("JSON.GET", "a" in body, ms, body)
        body, ms = post({"cmd": "PING"})
        record("PING", "PONG" in body, ms, body)
        # injection
        body, ms = post({"cmd": "SET", "args": ["bad-key!", "value"]})
        record("INJECT_KEY", "ok\":false" in body or "invalid" in body, ms, body)
        # health
        t0 = time.perf_counter()
        with urllib.request.urlopen(f"http://{args.host}:{args.port}/health", timeout=5) as r:
            hb = r.read().decode()
        record("HEALTH", "ok" in hb, (time.perf_counter()-t0)*1000, hb)

    # metrics summary
    print("\n--- METRICS ---")
    print(f"commands: {len(latencies)}")
    print(f"min: {min(latencies):.3f} ms")
    print(f"max: {max(latencies):.3f} ms")
    print(f"avg: {statistics.mean(latencies):.3f} ms")
    print(f"median: {statistics.median(latencies):.3f} ms")
    if len(latencies) >= 2:
        print(f"p95: {statistics.quantiles(latencies, n=20)[18]:.3f} ms")
    failed = [r for r in results if not r[1]]
    print(f"failed: {len(failed)}")
    for r in failed:
        print("  FAIL", r[0], r[3])

if __name__ == "__main__":
    main()
