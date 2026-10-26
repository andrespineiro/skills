#!/usr/bin/env python3
"""Resume un HAR para mapear pasos de navegador a llamadas de API, sin exponer secretos.

- Descarta estáticos y analítica (nunca fetch/xhr ni respuestas JSON) e informa de lo descartado.
- Agrupa peticiones por método + ruta con ids normalizados ({id}).
- Redacta auth, cookies, tokens en URL (query, fragmento, ruta, URLs anidadas) y valores de bodies:
  de los bodies solo muestra la forma (claves y tipos).
- Distingue operaciones GraphQL (tipo + operationName).

Uso: har-summary.py captura.har [--all] [--limit N]
"""
import argparse
import base64
import json
import re
import sys
from collections import Counter
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

SENSITIVE_TOKENS = {
    "auth", "authorization", "token", "secret", "apikey", "key", "password", "passwd", "pwd", "pass",
    "session", "sessionid", "sid", "jsessionid", "cookie", "csrf", "xsrf", "sig", "signature", "jwt",
    "bearer", "credential", "credentials", "otp", "nonce", "assertion", "passcode", "pin",
}
SENSITIVE_EXACT = {"code", "state", "access", "s", "t"}
AUTH_SCHEMES = {"bearer", "basic", "digest", "token", "negotiate", "ntlm", "hawk", "aws4-hmac-sha256", "dpop"}
BORING_HEADERS = {
    "accept", "accept-encoding", "accept-language", "cache-control", "connection", "content-length",
    "content-type", "dnt", "host", "origin", "pragma", "priority", "referer", "te", "user-agent",
    "upgrade-insecure-requests", "if-none-match", "if-modified-since",
}
KEEP_TYPES = {"fetch", "xhr", "websocket", "eventsource"}
STATIC_TYPES = {"image", "font", "stylesheet", "media", "manifest", "texttrack", "script", "document"}
STATIC_EXT = re.compile(r"\.(png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot|css|js|mjs|map|mp4|webm|mp3)$", re.I)
ANALYTICS_DOMAINS = (
    "google-analytics.com", "googletagmanager.com", "doubleclick.net", "segment.io", "segment.com",
    "sentry.io", "hotjar.com", "mixpanel.com", "clarity.ms", "amplitude.com", "intercom.io",
    "datadoghq.com", "datadoghq.eu", "nr-data.net", "newrelic.com", "fullstory.com", "facebook.net",
)
ID_SEGMENT = re.compile(
    r"^(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{16,})$", re.I
)
OPAQUE = re.compile(r"^[A-Za-z0-9_\-.~+/=%]{20,}$")
GRAPHQL_OP = re.compile(r"^\s*(query|mutation|subscription)\b\s*(\w*)", re.I)


def name_tokens(name):
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t]


def is_sensitive_name(name):
    tokens = name_tokens(name)
    return "".join(tokens) in SENSITIVE_EXACT | SENSITIVE_TOKENS or any(t in SENSITIVE_TOKENS for t in tokens)


def looks_opaque(value):
    """Token, hash o firma: largo, sin espacios, con letras y dígitos."""
    return bool(OPAQUE.match(value)) and re.search(r"\d", value) and re.search(r"[A-Za-z]", value)


def redact_value(name, value):
    if is_sensitive_name(name):
        return "<redacted>"
    if re.match(r"https?://", unquote(value)):
        return redact_url(unquote(value))
    if "@" in value:
        return "<email>"
    if looks_opaque(value):
        return "<opaque>"
    return value


def redact_pairs(text):
    pairs = parse_qsl(text, keep_blank_values=True)
    return urlencode([(k, redact_value(k, v)) for k, v in pairs], safe="<>/:{}")


def redact_path(path, template=False):
    out = []
    for segment in path.split("/"):
        segment, _, params = segment.partition(";")
        if template and (ID_SEGMENT.match(segment) or looks_opaque(segment)):
            segment = "{id}"
        elif looks_opaque(segment) and not ID_SEGMENT.match(segment):
            segment = "<opaque>"
        out.append(segment + (";<redacted>" if params else ""))
    return "/".join(out)


def redact_url(url):
    parts = urlsplit(url)
    netloc = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, netloc, redact_path(parts.path), redact_pairs(parts.query), redact_pairs(parts.fragment)))


def header_list(headers):
    return [h for h in headers or [] if h.get("name") and not h["name"].startswith(":")]


def request_signals(headers):
    signals = []
    for h in header_list(headers):
        name, value = h["name"].lower(), h.get("value") or ""
        if name in ("authorization", "proxy-authorization"):
            scheme = value.split(" ", 1)[0]
            shown = f"{scheme} <redacted>" if " " in value and scheme.lower() in AUTH_SCHEMES else "<redacted>"
            signals.append(f"{name}: {shown}")
        elif name == "cookie":
            names = sorted({c.split("=", 1)[0].strip() for c in value.split(";") if c.strip()})
            signals.append(f"cookie: {', '.join(names)}")
        elif name not in BORING_HEADERS and not name.startswith("sec-"):
            signals.append(f"{name}: <redacted>")
    return signals


def response_signals(headers):
    signals = []
    for h in header_list(headers):
        name, value = h["name"].lower(), h.get("value") or ""
        if name == "set-cookie":
            signals.append(f"set-cookie: {value.split('=', 1)[0].strip()}")
        elif name == "location":
            signals.append(f"location: {redact_url(value)}")
    return signals


def shape(value, depth=0):
    if depth > 5:
        return "…"
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(v, dict) for v in value[:20]):
            merged = {}
            for v in value[:20]:
                merged.update(v)
            return [shape(merged, depth + 1), f"×{len(value)}"]
        return [shape(value[0], depth + 1), f"×{len(value)}"]
    return type(value).__name__


def graphql_ops(body):
    items = body if isinstance(body, list) else [body]
    ops = []
    for item in items:
        if not isinstance(item, dict) or not ({"query", "operationName"} & item.keys()):
            continue
        match = GRAPHQL_OP.match(item.get("query") or "")
        kind = match.group(1).lower() if match else ("query" if item.get("query") else "persisted")
        ops.append(f"{kind} {item.get('operationName') or (match.group(2) if match else '') or '<anónima>'}")
    return ops


def decoded_text(content):
    text = content.get("text")
    if text and content.get("encoding") == "base64":
        try:
            return base64.b64decode(text).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
    return text


def body_summary(text, mime, params=None, attached=False):
    """Devuelve (shape, operaciones graphql)."""
    mime = (mime or "").lower()
    if attached:
        return "en archivo adjunto (_file); inspecciona solo sus claves", []
    if not text:
        return (sorted({p.get("name") for p in params if p.get("name")}), []) if params else (None, [])
    if "json" in mime or text.lstrip()[:1] in ("{", "["):
        try:
            data = json.loads(text)
            return shape(data), graphql_ops(data)
        except ValueError:
            pass
    if "x-www-form-urlencoded" in mime:
        return sorted({k for k, _ in parse_qsl(text, keep_blank_values=True)}), []
    return f"{mime or 'desconocido'}, {len(text)} chars (contenido omitido)", []


def noise_reason(entry):
    url = urlsplit(entry["request"]["url"])
    rtype = (entry.get("_resourceType") or "").lower()
    mime = ((entry.get("response") or {}).get("content") or {}).get("mimeType") or ""
    host = (url.hostname or "").lower()
    if any(host == d or host.endswith("." + d) for d in ANALYTICS_DOMAINS):
        return "analítica"
    if rtype in KEEP_TYPES or "json" in mime.lower():
        return None
    if rtype in STATIC_TYPES or STATIC_EXT.search(url.path):
        return "estático"
    return None


def group_key(entry, ops):
    url = urlsplit(entry["request"]["url"])
    return (entry["request"]["method"], url.hostname or "", redact_path(url.path, template=True), tuple(ops))


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("har")
    parser.add_argument("--all", action="store_true", help="no descartar estáticos ni analítica (la redacción se mantiene)")
    parser.add_argument("--limit", type=int, default=100, help="máximo de grupos a mostrar (por defecto 100)")
    args = parser.parse_args()

    try:
        with open(args.har, encoding="utf-8-sig") as f:
            entries = json.load(f)["log"]["entries"]
    except (OSError, UnicodeDecodeError, ValueError) as e:
        die(f"no se pudo leer el HAR: {e}")
    except (KeyError, TypeError):
        die("no es un HAR válido: falta log.entries")

    dropped, groups = Counter(), {}
    for e in entries:
        if not isinstance(e, dict) or not (e.get("request") or {}).get("url"):
            continue
        reason = None if args.all else noise_reason(e)
        if reason:
            dropped[f"{reason}: {urlsplit(e['request']['url']).hostname}"] += 1
            continue
        req = e["request"]
        post = req.get("postData") or {}
        req_shape, ops = body_summary(post.get("text"), post.get("mimeType"), post.get("params"), "_file" in post)
        if not ops and req["method"] == "GET":
            q = dict(parse_qsl(urlsplit(req["url"]).query))
            if "operationName" in q:
                ops = [f"get {q['operationName']}"]
        key = group_key(e, ops)
        if key in groups:
            groups[key]["count"] += 1
        else:
            groups[key] = {"count": 1, "entry": e, "req_shape": req_shape}

    print(f"# {sum(g['count'] for g in groups.values())} de {len(entries)} peticiones en {len(groups)} grupos")
    for reason, n in dropped.most_common():
        print(f"#   descartadas {n} — {reason}")
    print()

    for i, ((method, host, path, ops), g) in enumerate(groups.items(), 1):
        if i > args.limit:
            print(f"… {len(groups) - args.limit} grupos más (usa --limit)")
            break
        e = g["entry"]
        res = e.get("response") or {}
        content = res.get("content") or {}
        print(f"## {i}. {method} {host}{path}  ×{g['count']}")
        print(f"   ejemplo: {redact_url(e['request']['url'])}")
        for op in ops:
            print(f"   graphql {op}")
        print(f"   status: {res.get('status')}  type: {content.get('mimeType')}  size: {content.get('size')}")
        for s in request_signals(e["request"].get("headers")):
            print(f"   req   {s}")
        for s in response_signals(res.get("headers")):
            print(f"   res   {s}")
        if g["req_shape"] is not None:
            print(f"   body  {json.dumps(g['req_shape'], ensure_ascii=False)}")
        resp_shape, _ = body_summary(decoded_text(content), content.get("mimeType"), attached="_file" in content)
        if resp_shape is not None:
            print(f"   resp  {json.dumps(resp_shape, ensure_ascii=False)}")
        print()


if __name__ == "__main__":
    main()
