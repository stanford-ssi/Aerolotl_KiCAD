"""Write a simple STEP (AP214) solid made of axis-aligned boxes, for parts that have no 3D model.
usage (as a module): write_boxes(path, name, [(x0, y0, z0, x1, y1, z1), ...])   # mm, KiCad 3D-model frame (+y up)"""
import datetime


def write_boxes(path, name, boxes):
    ents = []

    def add(s):
        ents.append(s)
        return len(ents) + 99          # entity ids start at #100

    def P(x, y, z):
        return add("CARTESIAN_POINT('',(%.4f,%.4f,%.4f))" % (x, y, z))

    def D(x, y, z):
        return add("DIRECTION('',(%.1f,%.1f,%.1f))" % (x, y, z))

    def box(x0, y0, z0, x1, y1, z1):
        c = [(x1 if i & 1 else x0, y1 if i & 2 else y0, z1 if i & 4 else z0) for i in range(8)]
        vp = [add("VERTEX_POINT('',#%d)" % P(*p)) for p in c]
        edges = {}

        def edge(a, b):
            lo, hi = min(a, b), max(a, b)
            if (lo, hi) not in edges:
                pa, pb = c[lo], c[hi]
                d = [pb[k] - pa[k] for k in range(3)]
                ln = max(abs(v) for v in d)
                vec = add("VECTOR('',#%d,%.4f)" % (D(*[v / ln for v in d]), ln))
                line = add("LINE('',#%d,#%d)" % (P(*pa), vec))
                edges[(lo, hi)] = add("EDGE_CURVE('',#%d,#%d,#%d,.T.)" % (vp[lo], vp[hi], line))
            return add("ORIENTED_EDGE('',*,*,#%d,%s)" % (edges[(lo, hi)], ".T." if a < b else ".F."))

        # each face: outward normal, a reference direction in the face, and its corners counter-clockwise seen from outside
        faces = [((0, 0, -1), (1, 0, 0), (0, 2, 3, 1)), ((0, 0, 1), (1, 0, 0), (4, 5, 7, 6)),
                 ((0, -1, 0), (1, 0, 0), (0, 1, 5, 4)), ((0, 1, 0), (1, 0, 0), (3, 2, 6, 7)),
                 ((-1, 0, 0), (0, 1, 0), (2, 0, 4, 6)), ((1, 0, 0), (0, 1, 0), (1, 3, 7, 5))]
        fids = []
        for n, ref, loop in faces:
            oes = [edge(loop[k], loop[(k + 1) % 4]) for k in range(4)]
            el = add("EDGE_LOOP('',(%s))" % ",".join("#%d" % e for e in oes))
            fb = add("FACE_OUTER_BOUND('',#%d,.T.)" % el)
            ax = add("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)" % (P(*c[loop[0]]), D(*n), D(*ref)))
            pl = add("PLANE('',#%d)" % ax)
            fids.append(add("ADVANCED_FACE('',(#%d),#%d,.T.)" % (fb, pl)))
        shell = add("CLOSED_SHELL('',(%s))" % ",".join("#%d" % f for f in fids))
        return add("MANIFOLD_SOLID_BREP('%s',#%d)" % (name, shell))

    solids = [box(*bx) for bx in boxes]
    mm = add("( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) )")
    rad = add("( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.) )")
    sr = add("( NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT() )")
    unc = add("UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#%d,'distance_accuracy_value','confusion accuracy')" % mm)
    ctx = add("( GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#%d)) "
              "GLOBAL_UNIT_ASSIGNED_CONTEXT((#%d,#%d,#%d)) REPRESENTATION_CONTEXT('Context #1','3D Context with UNIT and UNCERTAINTY') )"
              % (unc, mm, rad, sr))
    origin = add("AXIS2_PLACEMENT_3D('',#%d,#%d,#%d)" % (P(0, 0, 0), D(0, 0, 1), D(1, 0, 0)))
    rep = add("ADVANCED_BREP_SHAPE_REPRESENTATION('',(#%d,%s),#%d)" % (origin, ",".join("#%d" % s for s in solids), ctx))
    appctx = add("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
    add("APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#%d)" % appctx)
    pctx = add("PRODUCT_CONTEXT('',#%d,'mechanical')" % appctx)
    prod = add("PRODUCT('%s','%s','',(#%d))" % (name, name, pctx))
    add("PRODUCT_RELATED_PRODUCT_CATEGORY('part',$,(#%d))" % prod)
    form = add("PRODUCT_DEFINITION_FORMATION('','',#%d)" % prod)
    pdctx = add("PRODUCT_DEFINITION_CONTEXT('part definition',#%d,'design')" % appctx)
    pdef = add("PRODUCT_DEFINITION('design','',#%d,#%d)" % (form, pdctx))
    pds = add("PRODUCT_DEFINITION_SHAPE('','',#%d)" % pdef)
    add("SHAPE_DEFINITION_REPRESENTATION(#%d,#%d)" % (pds, rep))

    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(path, "w") as f:
        f.write("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('%s placeholder'),'2;1');\n" % name)
        f.write("FILE_NAME('%s','%s',(''),(''),'step_boxes.py','','');\n" % (name, now))
        f.write("FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n")
        for i, e in enumerate(ents):
            f.write("#%d=%s;\n" % (i + 100, e))
        f.write("ENDSEC;\nEND-ISO-10303-21;\n")


if __name__ == "__main__":
    # Molex Micro-Fit 3.0 43650-0215 (2 ckt vertical header): body 9.65 x 4.37 mm, 10.15 mm tall (Molex),
    # outline from the KiCad footprint F.Fab; latch ramp on the +y_fp side. Origin = pin 1, model +y = footprint -y.
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3dmodels",
                       "Molex_Micro-Fit_3.0_43650-0215_1x02_P3.00mm_Vertical.step")
    write_boxes(out, "Molex_Micro-Fit_3.0_43650-0215",
                [(-3.325, -1.9, 0.0, 6.325, 2.47, 10.15),        # housing
                 (0.8, -3.3, 4.0, 2.2, -1.9, 10.15)])           # latch ramp
    print("wrote", os.path.normpath(out))
    # AMASS XT30UPB-F (vertical PCB female, J5/J6): KiCad has the footprint but no 3D model. Outline from its F.Fab
    # (10.2 x 5.2 mm, chamfered at pin 1 = minus), about 11 mm tall.
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "3dmodels",
                       "AMASS_XT30UPB-F_1x02_P5.0mm_Vertical.step")
    write_boxes(out, "AMASS_XT30UPB-F",
                [(-0.9, -2.6, 0.0, 7.6, 2.6, 11.0),             # housing
                 (-2.6, -1.3, 0.0, -0.9, 1.3, 11.0)])           # chamfered (minus) end
    print("wrote", os.path.normpath(out))
