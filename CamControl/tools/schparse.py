"""Minimal KiCad schematic reader: ref -> value, footprint, KIID path, sheet name/file."""
import os, re

def tokenize(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            yield c; i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1; buf = []
            while s[j] != '"':
                if s[j] == "\\":
                    buf.append(s[j + 1]); j += 2
                else:
                    buf.append(s[j]); j += 1
            yield ("S", "".join(buf)); i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in "()":
                j += 1
            yield ("A", s[i:j]); i = j

def parse(s):
    stack = [[]]
    for t in tokenize(s):
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop(); stack[-1].append(x)
        else:
            stack[-1].append(t[1])
    return stack[0][0]

def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]

def prop(node, name):
    for p in kids(node, "property"):
        if p[1] == name:
            return p[2]
    return None

def read(project_dir, root="camcontrol.kicad_sch"):
    rootp = parse(open(os.path.join(project_dir, root)).read())
    out = {}
    for sh in kids(rootp, "sheet"):
        suuid = kids(sh, "uuid")[0][1]
        sname, sfile = prop(sh, "Sheetname"), prop(sh, "Sheetfile")
        sp = parse(open(os.path.join(project_dir, sfile)).read())
        for sym in kids(sp, "symbol"):
            ref = prop(sym, "Reference")
            if not ref or ref.startswith("#"):
                continue
            out[ref] = {"value": prop(sym, "Value"), "footprint": prop(sym, "Footprint"),
                        "path": "/%s/%s" % (suuid, kids(sym, "uuid")[0][1]),
                        "sheetname": sname, "sheetfile": os.path.basename(sfile) if False else sfile,
                        "lib_id": kids(sym, "lib_id")[0][1]}
    return out

if __name__ == "__main__":
    import sys, json
    d = read(sys.argv[1] if len(sys.argv) > 1 else ".")
    for r in sorted(d, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))):
        v = d[r]
        print("%-4s %-18s %-48s %s | %s" % (r, v["value"], v["footprint"], v["sheetname"], v["path"]))
