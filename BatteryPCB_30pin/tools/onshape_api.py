"""Tiny Onshape REST client for this project.

Keys are read from ~/.config/onshape/keys.env (ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY),
which you create yourself. They are never printed. Every call counts toward the account's
annual API limit, so callers should keep requests few.

usage:  python3 tools/onshape_api.py test
"""
import base64, json, os, sys, urllib.error, urllib.parse, urllib.request

BASE = "https://cad.onshape.com/api/v6"
KEYFILE = os.path.expanduser("~/.config/onshape/keys.env")
# the av bay document (Switchband Assembly)
DID, WID = "9fd23a0d7b785ceaa293370c", "4891bf56e294a579db58c9fb"

calls = 0


def _auth():
    vals = {}
    with open(KEYFILE) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                vals[k] = v
    tok = base64.b64encode(("%s:%s" % (vals["ONSHAPE_ACCESS_KEY"], vals["ONSHAPE_SECRET_KEY"])).encode()).decode()
    return "Basic " + tok


def request(method, path, params=None, body=None, accept="application/json;charset=UTF-8; qs=0.09"):
    global calls
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": _auth(), "Accept": accept, "Content-Type": "application/json"})
    calls += 1
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "")
            return json.loads(raw) if "json" in ctype else raw
    except urllib.error.HTTPError as e:
        raise SystemExit("Onshape API %s %s -> HTTP %d: %s" % (method, path, e.code, e.read()[:300].decode("utf-8", "replace")))


def get(path, **params):
    return request("GET", path, params or None)


if __name__ == "__main__" and sys.argv[1:] == ["test"]:
    if not os.path.exists(KEYFILE):
        raise SystemExit("no key file at %s yet" % KEYFILE)
    mode = oct(os.stat(KEYFILE).st_mode & 0o777)
    doc = get("/documents/%s" % DID)
    print("key file permissions:", mode)
    print("document:", doc.get("name"), "| owner:", (doc.get("owner") or {}).get("name"))
    els = get("/documents/d/%s/w/%s/elements" % (DID, WID))
    for e in els:
        print("  %-14s %s" % (e.get("elementType"), e.get("name")))
    print("API calls used:", calls)
