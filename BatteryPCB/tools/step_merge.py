"""Merge STEP AP214 files into one, optionally raising the first file's whole assembly in z.

usage: step_merge.py OUT.step KICAD.step DZ_MM OTHER.step [OTHER2.step ...]

Used for the SSI AVBay1 import: the KiCad board export (board bottom at z = 0) is raised DZ_MM so it lands in the
Onshape "AV Bay Stack - REAL PCB" frame (board bottom at z = 18 mm), and the exact pin-switch stack parts exported
from that Part Studio are appended unchanged. The KiCad root SHAPE_REPRESENTATION holds the placement frames of
every component, so only those frames move; the component shapes stay as written."""
import re
import sys


def tokens_outside_strings(s):
    """Split s into (is_string, text) runs; STEP strings are '...' with '' as an escaped quote."""
    out, i, n = [], 0, len(s)
    while i < n:
        j = s.find("'", i)
        if j < 0:
            out.append((False, s[i:])); break
        out.append((False, s[i:j]))
        k = j + 1
        while True:
            k = s.find("'", k)
            if k < 0 or k + 1 >= n or s[k + 1] != "'":
                break
            k += 2
        out.append((True, s[j:k + 1])); i = k + 1
    return out


def read(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    head, data = txt.split("\nDATA;", 1)
    data = data.rsplit("ENDSEC;", 1)[0]
    # drop /* */ comments outside strings, then split into entities on ';' outside strings
    clean = "".join(t if s else re.sub(r"/\*.*?\*/", "", t, flags=re.S) for s, t in tokens_outside_strings(data))
    ents, buf = {}, []
    for s, t in tokens_outside_strings(clean):
        if s:
            buf.append(t); continue
        parts = t.split(";")
        for p in parts[:-1]:
            buf.append(p)
            e = "".join(buf).strip()
            buf = []
            if e:
                m = re.match(r"#(\d+)\s*=\s*(.*)$", e, re.S)
                ents[int(m.group(1))] = m.group(2).strip()
        buf.append(parts[-1])
    return head, ents


def refs(body):
    return [int(x) for s, t in tokens_outside_strings(body) if not s for x in re.findall(r"#(\d+)", t)]


def renumber(body, off):
    return "".join(t if s else re.sub(r"#(\d+)", lambda m: "#%d" % (int(m.group(1)) + off), t)
                   for s, t in tokens_outside_strings(body))


def raise_root(ents, dz):
    """Move every placement frame of the root assembly representation up by dz (mm)."""
    sdr = [b for b in ents.values() if b.startswith("SHAPE_DEFINITION_REPRESENTATION")]
    # the root product is the one not used by any NEXT_ASSEMBLY_USAGE_OCCURRENCE as a child
    child_pd = {refs(b)[1] for b in ents.values() if b.startswith("NEXT_ASSEMBLY_USAGE_OCCURRENCE")}
    root_rep = None
    for b in sdr:
        pds, rep = refs(b)[:2]
        if refs(ents[pds])[0] not in child_pd:
            root_rep = rep
    # the parent-side frame (transform_item_2) of every child placed in the root; transform_item_1 is the shared
    # origin frame that KiCad reuses in every representation, so it must not move
    axes = []
    for b in ents.values():
        if "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION" in b:
            r = refs(b)
            if r[1] == root_rep:
                axes.append(refs(ents[r[2]])[1])
    users = {}
    for i, b in ents.items():
        for r in refs(b):
            users.setdefault(r, set()).add(i)
    nxt = max(ents) + 1
    for a in axes:
        pt = refs(ents[a])[0]
        x, y, z = [float(v) for v in re.search(r"\(([^()]*)\)\s*\)\s*$", ents[pt]).group(1).split(",")]
        new = "CARTESIAN_POINT('',(%r,%r,%r))" % (x, y, z + dz)
        if users.get(pt, set()) <= {a}:
            ents[pt] = new
        else:                                  # shared point: give this frame its own
            ents[nxt] = new
            ents[a] = ents[a].replace("#%d" % pt, "#%d" % nxt, 1)
            nxt += 1
    return len(axes)


def main():
    out, base, dz, others = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4:]
    head, ents = read(base)
    n = raise_root(ents, dz)
    merged = dict(ents)
    for path in others:
        _, e2 = read(path)
        off = max(merged) + 1 - min(e2)
        for i, b in e2.items():
            merged[i + off] = renumber(b, off)
    with open(out, "w") as f:
        f.write(head.rstrip() + "\nDATA;\n")
        for i in sorted(merged):
            f.write("#%d = %s;\n" % (i, merged[i]))
        f.write("ENDSEC;\nEND-ISO-10303-21;\n")
    print("raised %d root frames by %g mm, merged %d files, %d entities -> %s" % (n, dz, 1 + len(others), len(merged), out))


if __name__ == "__main__":
    main()
