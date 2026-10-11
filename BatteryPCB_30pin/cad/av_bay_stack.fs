FeatureScript 3083;
import(path : "onshape/std/common.fs", version : "3083.0");

// AV bay stack (Onshape doc "Switchband Assembly", tab "AV Bay Stack feature (code)").
// Bottom disc = battery PCB (CamControl), middle disc = Aerolotl flight computer, on two
// 3/8-16 threaded rods; each disc is clamped by an SAE washer + hex nut on both faces.
// Both discs get two screw holes near the bottom edge and small edge cutouts for wires.
// Every dimension is a dialog value. Bay floor is z = 0; "bottom" of a disc is -Y.

annotation { "Feature Type Name" : "AV bay stack",
             "Feature Type Description" : "Battery PCB + Aerolotl discs on two 3/8-16 threaded rods, with screw holes and wire cutouts" }
export const avBayStack = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Disc diameter" }
        isLength(definition.discDiameter, { (inch) : [0.1, 5.82, 100] } as LengthBoundSpec);

        annotation { "Name" : "Bottom disc (battery PCB) thickness" }
        isLength(definition.bottomThickness, { (millimeter) : [0.1, 1.6, 100] } as LengthBoundSpec);

        annotation { "Name" : "Middle disc (Aerolotl) thickness" }
        isLength(definition.middleThickness, { (inch) : [0.01, 0.125, 10] } as LengthBoundSpec);

        annotation { "Name" : "Gap between discs" }
        isLength(definition.gap, { (inch) : [0.1, 4, 100] } as LengthBoundSpec);

        annotation { "Name" : "Bottom disc height above bay floor" }
        isLength(definition.bottomZ, { (millimeter) : [0, 12, 1000] } as LengthBoundSpec);

        annotation { "Name" : "Bay inner diameter" }
        isLength(definition.bayDiameter, { (inch) : [0.1, 5.78, 100] } as LengthBoundSpec);

        annotation { "Name" : "Bay usable length" }
        isLength(definition.bayLength, { (inch) : [0.1, 7.32, 100] } as LengthBoundSpec);

        annotation { "Name" : "Rod spacing (center to center)" }
        isLength(definition.rodSpacing, { (millimeter) : [1, 120, 1000] } as LengthBoundSpec);

        annotation { "Name" : "Rod diameter" }
        isLength(definition.rodDiameter, { (inch) : [0.01, 0.375, 10] } as LengthBoundSpec);

        annotation { "Name" : "Rod clearance hole" }
        isLength(definition.holeDiameter, { (inch) : [0.01, 0.40625, 10] } as LengthBoundSpec);

        annotation { "Name" : "Hex nut across flats" }
        isLength(definition.nutAcrossFlats, { (inch) : [0.01, 0.5625, 10] } as LengthBoundSpec);

        annotation { "Name" : "Hex nut thickness" }
        isLength(definition.nutThickness, { (inch) : [0.01, 0.328, 10] } as LengthBoundSpec);

        annotation { "Name" : "Washer OD (3/8 SAE = 13/16 in)" }
        isLength(definition.washerOd, { (inch) : [0.01, 0.8125, 10] } as LengthBoundSpec);

        annotation { "Name" : "Washer thickness" }
        isLength(definition.washerThickness, { (inch) : [0.001, 0.065, 10] } as LengthBoundSpec);

        annotation { "Name" : "Screw holes: diameter" }
        isLength(definition.screwHoleDiameter, { (millimeter) : [0.5, 4.5, 50] } as LengthBoundSpec);

        annotation { "Name" : "Screw holes: spacing (center to center)" }
        isLength(definition.screwHoleSpacing, { (millimeter) : [0, 17.4, 200] } as LengthBoundSpec);

        annotation { "Name" : "Screw holes: distance below disc center" }
        isLength(definition.screwHoleOffset, { (millimeter) : [0, 50, 200] } as LengthBoundSpec);

        annotation { "Name" : "Small cutouts: width" }
        isLength(definition.cutoutWidth, { (millimeter) : [0.5, 10, 100] } as LengthBoundSpec);

        annotation { "Name" : "Small cutouts: depth (in from the edge)" }
        isLength(definition.cutoutDepth, { (millimeter) : [0.5, 6, 100] } as LengthBoundSpec);

        annotation { "Name" : "Cutout on both discs: angle (lower left)" }
        isAngle(definition.cutoutAngleBoth, { (degree) : [-360, 230, 360] } as AngleBoundSpec);

        annotation { "Name" : "Battery PCB cutout 2: angle (bottom)" }
        isAngle(definition.cutoutAngleB2, { (degree) : [-360, 270, 360] } as AngleBoundSpec);

        annotation { "Name" : "Battery PCB cutout 2: width" }
        isLength(definition.cutoutB2Width, { (millimeter) : [0.5, 40, 150] } as LengthBoundSpec);

        annotation { "Name" : "Battery PCB cutout 2: depth (in from the edge)" }
        isLength(definition.cutoutB2Depth, { (millimeter) : [0.5, 14, 100] } as LengthBoundSpec);

        annotation { "Name" : "Battery PCB cutout 3: angle (lower right)" }
        isAngle(definition.cutoutAngleB3, { (degree) : [-360, 327, 360] } as AngleBoundSpec);

        annotation { "Name" : "End discs: diameter" }
        isLength(definition.endDiameter, { (inch) : [0.1, 5.998, 100] } as LengthBoundSpec);

        annotation { "Name" : "End discs: thickness" }
        isLength(definition.endThickness, { (inch) : [0.01, 0.125, 10] } as LengthBoundSpec);

        annotation { "Name" : "Bottom end disc underside to battery PCB top" }
        isLength(definition.bottomSection, { (inch) : [0.1, 1.5, 100] } as LengthBoundSpec);

        annotation { "Name" : "Aerolotl disc underside to top end disc top" }
        isLength(definition.topSection, { (inch) : [0.1, 1.5, 100] } as LengthBoundSpec);
    }
    {
        const discR = definition.discDiameter / 2;
        // two rods on one line through the center (X axis), as in the original av bay
        const rods = [vector(definition.rodSpacing / 2, 0 * meter), vector(-definition.rodSpacing / 2, 0 * meter)];
        // two screw holes side by side below the center, same spot on both discs
        const screws = [vector(definition.screwHoleSpacing / 2, -definition.screwHoleOffset),
                        vector(-definition.screwHoleSpacing / 2, -definition.screwHoleOffset)];

        const zB0 = definition.bottomZ;
        const zB1 = zB0 + definition.bottomThickness;
        const zM0 = zB1 + definition.gap;
        const zM1 = zM0 + definition.middleThickness;
        // end discs: the whole bay is bottomSection + gap + topSection (outer face to outer face)
        const zE0 = zB1 - definition.bottomSection;          // underside of the bottom end disc
        const zE1 = zM0 + definition.topSection;             // top of the top end disc
        const endR = definition.endDiameter / 2;

        makeFlatDisc(context, id + "bottomDisc", zB0, definition.bottomThickness, discR, rods, definition.holeDiameter / 2);
        nameAndColor(context, id + "bottomDisc" + "ex", "Bottom disc - Battery PCB (CamControl)", color(0.12, 0.45, 0.22));
        cutDisc(context, id + "bottomCuts", qCreatedBy(id + "bottomDisc" + "ex", EntityType.BODY), zB0, definition.bottomThickness, discR,
                screws, definition.screwHoleDiameter / 2,
                [cutout(definition.cutoutAngleBoth, definition.cutoutWidth, definition.cutoutDepth),
                 cutout(definition.cutoutAngleB2, definition.cutoutB2Width, definition.cutoutB2Depth),
                 cutout(definition.cutoutAngleB3, definition.cutoutWidth, definition.cutoutDepth)]);

        makeFlatDisc(context, id + "middleDisc", zM0, definition.middleThickness, discR, rods, definition.holeDiameter / 2);
        nameAndColor(context, id + "middleDisc" + "ex", "Middle disc - Aerolotl flight computer", color(0.80, 0.80, 0.82));
        cutDisc(context, id + "middleCuts", qCreatedBy(id + "middleDisc" + "ex", EntityType.BODY), zM0, definition.middleThickness, discR,
                screws, definition.screwHoleDiameter / 2,
                [cutout(definition.cutoutAngleBoth, definition.cutoutWidth, definition.cutoutDepth)]);

        makeFlatDisc(context, id + "endBottom", zE0, definition.endThickness, endR, rods, definition.holeDiameter / 2);
        nameAndColor(context, id + "endBottom" + "ex", "Bottom end disc", color(0.82, 0.70, 0.50));
        makeFlatDisc(context, id + "endTop", zE1 - definition.endThickness, definition.endThickness, endR, rods, definition.holeDiameter / 2);
        nameAndColor(context, id + "endTop" + "ex", "Top end disc", color(0.82, 0.70, 0.50));

        // rods run through all four discs, 3 mm past the outer nuts
        const nutStack = definition.washerThickness + definition.nutThickness;
        const rodZ0 = zE0 - nutStack - 3 * millimeter;
        const rodLength = (zE1 + nutStack + 3 * millimeter) - rodZ0;
        for (var i = 0; i < size(rods); i += 1)
        {
            const rid = id + ("rod" ~ i);
            const sk = newSketchOnPlane(context, rid + "sk", { "sketchPlane" : zPlane(rodZ0) });
            skCircle(sk, "c", { "center" : rods[i], "radius" : definition.rodDiameter / 2 });
            skSolve(sk);
            extrudeUp(context, rid + "ex", rid + "sk", rodLength);
            opDeleteBodies(context, rid + "del", { "entities" : qCreatedBy(rid + "sk", EntityType.BODY) });
            nameAndColor(context, rid + "ex", "Threaded rod 3/8-16", color(0.55, 0.55, 0.58));
        }

        const levels = [[zE0, -1], [zE0 + definition.endThickness, 1], [zB0, -1], [zB1, 1], [zM0, -1], [zM1, 1],
                        [zE1 - definition.endThickness, -1], [zE1, 1]];
        var n = 0;
        for (var lv in levels)
        {
            for (var i = 0; i < size(rods); i += 1)
            {
                n += 1;
                const zFace = lv[0];
                const up = lv[1] > 0;
                const washerZ = up ? zFace : zFace - definition.washerThickness;
                const nutZ = up ? zFace + definition.washerThickness : zFace - definition.washerThickness - definition.nutThickness;
                makeWasher(context, id + ("washer" ~ n), rods[i], washerZ, definition.washerThickness, definition.washerOd / 2, definition.holeDiameter / 2);
                makeHexNut(context, id + ("nut" ~ n), rods[i], nutZ, definition.nutThickness, definition.nutAcrossFlats, definition.rodDiameter / 2);
            }
        }

        const envLow = newSketchOnPlane(context, id + "bayFloor", { "sketchPlane" : zPlane(zE0) });
        skCircle(envLow, "c", { "center" : vector(0, 0) * meter, "radius" : definition.bayDiameter / 2 });
        skSolve(envLow);
        const envHigh = newSketchOnPlane(context, id + "bayTop", { "sketchPlane" : zPlane(zE1) });
        skCircle(envHigh, "c", { "center" : vector(0, 0) * meter, "radius" : definition.bayDiameter / 2 });
        skSolve(envHigh);

        const rodRadius = definition.rodSpacing / 2;
        const washerReach = rodRadius + definition.washerOd / 2;
        const total = zE1 - zE0;
        var problems = "";
        var note = "";
        if (definition.discDiameter >= definition.bayDiameter)
            note = "Disc is " ~ roundToPrecision((definition.discDiameter - definition.bayDiameter) / millimeter, 2) ~ " mm wider than the bay ID entered - confirm the bay ID. ";
        if (washerReach > discR)
            problems = problems ~ "washers stick out " ~ roundToPrecision((washerReach - discR) / millimeter, 2) ~ " mm past the disc edge. ";
        if (washerReach > definition.bayDiameter / 2)
            problems = problems ~ "washers reach " ~ roundToPrecision((washerReach - definition.bayDiameter / 2) / millimeter, 2) ~ " mm into the bay wall. ";
        if (definition.endDiameter > definition.bayDiameter)
            problems = problems ~ "end discs are wider than the bay ID entered. ";
        if (zE0 + definition.endThickness + nutStack > zB0 - nutStack || zM1 + nutStack > zE1 - definition.endThickness - nutStack)
            problems = problems ~ "rod nuts of the end discs run into the inner discs' nuts. ";
        if (problems != "")
            reportFeatureWarning(context, id, "Check: " ~ problems ~ note);
        else
            reportFeatureInfo(context, id, note ~ "Washers end " ~ roundToPrecision((discR - washerReach) / millimeter, 2) ~ " mm inside the disc edge. End disc to end disc " ~
                    roundToPrecision(total / inch, 3) ~ " in; clear gaps " ~ roundToPrecision((zB0 - zE0 - definition.endThickness) / inch, 3) ~ " / " ~
                    roundToPrecision((zM0 - zB1) / inch, 3) ~ " / " ~ roundToPrecision((zE1 - definition.endThickness - zM1) / inch, 3) ~ " in; rods " ~
                    roundToPrecision(rodLength / inch, 2) ~ " in long.");
    });

function zPlane(z is ValueWithUnits) returns Plane
{
    return plane(vector(0 * meter, 0 * meter, z), vector(0, 0, 1));
}

function extrudeUp(context is Context, id is Id, sketchId is Id, depth is ValueWithUnits)
{
    opExtrude(context, id, {
            "entities" : qSketchRegion(sketchId, true),
            "direction" : vector(0, 0, 1),
            "endBound" : BoundingType.BLIND,
            "endDepth" : depth
    });
}

function nameAndColor(context is Context, featureId is Id, name is string, col)
{
    setProperty(context, { "entities" : qCreatedBy(featureId, EntityType.BODY), "propertyType" : PropertyType.NAME, "value" : name });
    setProperty(context, { "entities" : qCreatedBy(featureId, EntityType.BODY), "propertyType" : PropertyType.APPEARANCE, "value" : col });
}

function makeFlatDisc(context is Context, id is Id, z0 is ValueWithUnits, t is ValueWithUnits, r is ValueWithUnits, holes is array, holeR is ValueWithUnits)
{
    const sk = newSketchOnPlane(context, id + "sk", { "sketchPlane" : zPlane(z0) });
    skCircle(sk, "outer", { "center" : vector(0, 0) * meter, "radius" : r });
    for (var k = 0; k < size(holes); k += 1)
        skCircle(sk, "hole" ~ k, { "center" : holes[k], "radius" : holeR });
    skSolve(sk);
    extrudeUp(context, id + "ex", id + "sk", t);
    opDeleteBodies(context, id + "del", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
}

function cutout(angle is ValueWithUnits, width is ValueWithUnits, depth is ValueWithUnits) returns map
{
    return { "angle" : angle, "width" : width, "depth" : depth };
}

// Subtract round screw holes and rectangular edge cutouts (each centered on its angle, measured
// counter-clockwise from +X; depth measured in from the edge at its center) from a disc body.
function cutDisc(context is Context, id is Id, disc is Query, z0 is ValueWithUnits, t is ValueWithUnits, r is ValueWithUnits,
    screws is array, screwR is ValueWithUnits, cutouts is array)
{
    const sk = newSketchOnPlane(context, id + "sk", { "sketchPlane" : zPlane(z0 - 1 * millimeter) });
    for (var k = 0; k < size(screws); k += 1)
        skCircle(sk, "screw" ~ k, { "center" : screws[k], "radius" : screwR });
    const rOut = r + 2 * millimeter;
    for (var k = 0; k < size(cutouts); k += 1)
    {
        const a = cutouts[k].angle;
        const rIn = r - cutouts[k].depth;
        const u = vector(cos(a), sin(a));
        const w = vector(-sin(a), cos(a)) * (cutouts[k].width / 2);
        skPolyline(sk, "cut" ~ k, { "points" : [u * rIn + w, u * rIn - w, u * rOut - w, u * rOut + w, u * rIn + w] });
    }
    skSolve(sk);
    extrudeUp(context, id + "ex", id + "sk", t + 2 * millimeter);
    opDeleteBodies(context, id + "del", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
    opBoolean(context, id + "cut", {
            "tools" : qCreatedBy(id + "ex", EntityType.BODY),
            "targets" : disc,
            "operationType" : BooleanOperationType.SUBTRACTION
    });
}

function makeWasher(context is Context, id is Id, c is Vector, z0 is ValueWithUnits, t is ValueWithUnits, outerR is ValueWithUnits, innerR is ValueWithUnits)
{
    const sk = newSketchOnPlane(context, id + "sk", { "sketchPlane" : zPlane(z0) });
    skCircle(sk, "outer", { "center" : c, "radius" : outerR });
    skCircle(sk, "inner", { "center" : c, "radius" : innerR });
    skSolve(sk);
    extrudeUp(context, id + "ex", id + "sk", t);
    opDeleteBodies(context, id + "del", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
    nameAndColor(context, id + "ex", "Washer 3/8 SAE", color(0.72, 0.72, 0.75));
}

function makeHexNut(context is Context, id is Id, c is Vector, z0 is ValueWithUnits, t is ValueWithUnits, acrossFlats is ValueWithUnits, boreR is ValueWithUnits)
{
    const sk = newSketchOnPlane(context, id + "sk", { "sketchPlane" : zPlane(z0) });
    const cornerR = acrossFlats / sqrt(3);
    skRegularPolygon(sk, "hex", { "center" : c, "firstVertex" : c + vector(cornerR, 0 * meter), "sides" : 6 });
    skCircle(sk, "bore", { "center" : c, "radius" : boreR });
    skSolve(sk);
    extrudeUp(context, id + "ex", id + "sk", t);
    opDeleteBodies(context, id + "del", { "entities" : qCreatedBy(id + "sk", EntityType.BODY) });
    nameAndColor(context, id + "ex", "Hex nut 3/8-16", color(0.62, 0.62, 0.66));
}
