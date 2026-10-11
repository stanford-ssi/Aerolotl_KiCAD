// Pin switch stack: appended to the Onshape Feature Studio "AV Bay Stack feature (code)" on 2026-10-01.
// Uses nameAndColor() and makeHexNut() from av_bay_stack.fs. Onshape holds the full, current code
// (it also has probeParts, placeParts and cotsMountPlate, which this local folder does not).
// Instance "Pin switch stack 1" in "AV Bay Stack - REAL PCB": upside down (rails down), Pin axis X = 0, Pin-entry face Y = 68.88 mm,
// PCB top 19.51, PCB 1.51, spacer 0.4 mm (sits on the 0.3 mm battery solder tabs). Carriers / microswitches are exact copies (not trimmed).
annotation { "Feature Type Name" : "Pin switch stack", "Feature Type Description" : "Stacks the double pin switches (carrier + 2 microswitches each) on the battery PCB, pin holes facing the airframe; M3 bolts, spacers, nuts; reports clashes" }
export const pinSwitchStack = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Microswitch body (derived)", "Filter" : EntityType.BODY && BodyType.SOLID, "MaxNumberOfPicks" : 1 }
        definition.microswitch is Query;

        annotation { "Name" : "Carrier body (derived)", "Filter" : EntityType.BODY && BodyType.SOLID, "MaxNumberOfPicks" : 1 }
        definition.carrier is Query;

        annotation { "Name" : "Double pin switches (stacked)" }
        isInteger(definition.units, { (unitless) : [1, 2, 4] } as IntegerBoundSpec);

        annotation { "Name" : "Upside down (rails down)" }
        definition.flip is boolean;

        annotation { "Name" : "Pin axis X" }
        isLength(definition.pinX, { (millimeter) : [-80, 0, 80] } as LengthBoundSpec);

        annotation { "Name" : "Pin-entry face Y" }
        isLength(definition.outerY, { (millimeter) : [0, 71, 80] } as LengthBoundSpec);

        annotation { "Name" : "PCB top Z" }
        isLength(definition.pcbTopZ, { (millimeter) : [0, 19.6, 300] } as LengthBoundSpec);

        annotation { "Name" : "PCB thickness" }
        isLength(definition.pcbThick, { (millimeter) : [0.1, 1.6, 10] } as LengthBoundSpec);

        annotation { "Name" : "Spacer height under the stack" }
        isLength(definition.spacer, { (millimeter) : [0, 3, 100] } as LengthBoundSpec);


        annotation { "Name" : "Microswitch pair offset" }
        isLength(definition.pairOffset, { (millimeter) : [0, 14.24, 50] } as LengthBoundSpec);
    }
    {
        const cb = evBox3d(context, { "topology" : definition.carrier, "tight" : true });
        const xmin = cb.minCorner[0];
        const ymid = (cb.minCorner[1] + cb.maxCorner[1]) / 2;
        const thick = cb.maxCorner[2] - cb.minCorner[2];
        const baseZ = definition.pcbTopZ + definition.spacer;
        const topZ = baseZ + definition.units * thick;

        // As in the original Double Pin Switch: carrier local -X (pin entry) -> world +Y (out to the airframe).
        // Normal: local Y -> world -X, local Z -> world -Z (full face down, rails up). Flipped: local Y -> +X, Z -> +Z.
        var rot = matrix([[0, -1, 0], [-1, 0, 0], [0, 0, -1]]);
        var tx = definition.pinX + ymid;
        var tz0 = baseZ + cb.maxCorner[2];
        if (definition.flip)
        {
            rot = matrix([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]);
            tx = definition.pinX - ymid;
            tz0 = baseZ - cb.minCorner[2];
        }
        // second microswitch of each pair: 180 deg about X, offset in Y (from the Double Pin Switch assembly)
        const flipB = transform(vector(0 * meter, definition.pairOffset, 0 * meter)) * rotationAround(line(vector(0, 0, 0) * meter, vector(1, 0, 0)), 180 * degree);

        var carriers = [];
        for (var k = 0; k < definition.units; k += 1)
        {
            const place = transform(rot, vector(tx, definition.outerY + xmin, tz0 + k * thick));
            opPattern(context, id + ("c" ~ k), { "entities" : definition.carrier, "transforms" : [place], "instanceNames" : ["1"] });
            carriers = append(carriers, qCreatedBy(id + ("c" ~ k), EntityType.BODY));
            opPattern(context, id + ("a" ~ k), { "entities" : definition.microswitch, "transforms" : [place], "instanceNames" : ["1"] });
            nameAndColor(context, id + ("a" ~ k), "Pin switch " ~ (k + 1) ~ "A (microswitch)", color(0.15, 0.15, 0.15));
            opPattern(context, id + ("b" ~ k), { "entities" : definition.microswitch, "transforms" : [place * flipB], "instanceNames" : ["1"] });
            nameAndColor(context, id + ("b" ~ k), "Pin switch " ~ (k + 1) ~ "B (microswitch)", color(0.15, 0.15, 0.15));
        }

        // vertical M3 holes of the carrier (r 1.4..1.9 mm, axis Z), in world XY
        const place0 = transform(rot, vector(tx, definition.outerY + xmin, tz0));
        var holes = [];
        for (var f in evaluateQuery(context, qGeometry(qOwnedByBody(definition.carrier, EntityType.FACE), GeometryType.CYLINDER)))
        {
            const cyl = evSurfaceDefinition(context, { "face" : f });
            if (abs(cyl.coordSystem.zAxis[2]) > 0.99 && cyl.radius > 1.4 * millimeter && cyl.radius < 1.9 * millimeter)
            {
                const p = place0 * cyl.coordSystem.origin;
                var dup = false;
                for (var h in holes)
                    if (norm(h - vector(p[0], p[1])) < 0.2 * millimeter)
                        dup = true;
                if (!dup)
                    holes = append(holes, vector(p[0], p[1]));
            }
        }
        opDeleteBodies(context, id + "delSrc", { "entities" : qUnion([definition.carrier, definition.microswitch]) });

        // carriers are used exactly as built (no trimming): the physical parts exist
        for (var k = 0; k < definition.units; k += 1)
            nameAndColor(context, id + ("c" ~ k), "Double pin switch carrier " ~ (k + 1), color(0.95, 0.55, 0.10));

        // M3 bolts: head on top of the stack, spacer between PCB and stack, nut under the PCB
        const pcbBot = definition.pcbTopZ - definition.pcbThick;
        var holeText = "";
        for (var i = 0; i < size(holes); i += 1)
        {
            const c = holes[i];
            const c3 = vector(c[0], c[1], 0 * meter);
            const up = vector(0, 0, 1);
            fCylinder(context, id + ("head" ~ i), { "topCenter" : c3 + up * (topZ + 3 * millimeter), "bottomCenter" : c3 + up * topZ, "radius" : 2.75 * millimeter });
            fCylinder(context, id + ("shank" ~ i), { "topCenter" : c3 + up * topZ, "bottomCenter" : c3 + up * (pcbBot - 3.4 * millimeter), "radius" : 1.5 * millimeter });
            opBoolean(context, id + ("screw" ~ i), { "tools" : qUnion([qCreatedBy(id + ("head" ~ i), EntityType.BODY), qCreatedBy(id + ("shank" ~ i), EntityType.BODY)]), "operationType" : BooleanOperationType.UNION });
            const screwQ = qUnion([qCreatedBy(id + ("head" ~ i), EntityType.BODY), qCreatedBy(id + ("shank" ~ i), EntityType.BODY)]);
            setProperty(context, { "entities" : screwQ, "propertyType" : PropertyType.NAME, "value" : "M3 screw (nylon)" });
            setProperty(context, { "entities" : screwQ, "propertyType" : PropertyType.APPEARANCE, "value" : color(0.95, 0.95, 0.90) });
            if (definition.spacer > 0.01 * millimeter)
            {
                fCylinder(context, id + ("sp" ~ i), { "topCenter" : c3 + up * baseZ, "bottomCenter" : c3 + up * definition.pcbTopZ, "radius" : 3 * millimeter });
                fCylinder(context, id + ("spb" ~ i), { "topCenter" : c3 + up * (baseZ + 1 * millimeter), "bottomCenter" : c3 + up * (definition.pcbTopZ - 1 * millimeter), "radius" : 1.6 * millimeter });
                opBoolean(context, id + ("spc" ~ i), { "tools" : qCreatedBy(id + ("spb" ~ i), EntityType.BODY), "targets" : qCreatedBy(id + ("sp" ~ i), EntityType.BODY), "operationType" : BooleanOperationType.SUBTRACTION });
                nameAndColor(context, id + ("sp" ~ i), "M3 spacer (nylon)", color(0.95, 0.95, 0.90));
            }
            makeHexNut(context, id + ("nut" ~ i), c, pcbBot - 2.4 * millimeter, 2.4 * millimeter, 5.5 * millimeter, 1.5 * millimeter);
            nameAndColor(context, id + ("nut" ~ i) + "ex", "M3 nut (nylon)", color(0.95, 0.95, 0.90));
            holeText = holeText ~ "(" ~ roundToPrecision(c[0] / millimeter, 2) ~ ", " ~ roundToPrecision(c[1] / millimeter, 2) ~ ") ";
        }

        // M3 clearance holes through the PCB under the stack (same holes as in KiCad)
        var drills = [];
        for (var i = 0; i < size(holes); i += 1)
        {
            const d3 = vector(holes[i][0], holes[i][1], 0 * meter);
            fCylinder(context, id + ("drill" ~ i), { "topCenter" : d3 + vector(0, 0, 1) * (definition.pcbTopZ + 0.5 * millimeter), "bottomCenter" : d3 + vector(0, 0, 1) * (pcbBot - 0.5 * millimeter), "radius" : 1.6 * millimeter });
            drills = append(drills, qCreatedBy(id + ("drill" ~ i), EntityType.BODY));
        }
        var hit = [];
        for (var cl in evCollision(context, { "tools" : qUnion(drills), "targets" : qSubtraction(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), qCreatedBy(id, EntityType.BODY)) }))
            hit = append(hit, cl["targetBody"]);
        if (size(hit) > 0)
            opBoolean(context, id + "drillPcb", { "tools" : qUnion(drills), "targets" : qUnion(hit), "operationType" : BooleanOperationType.SUBTRACTION });
        else
            opDeleteBodies(context, id + "drillDel", { "entities" : qUnion(drills) });

        // clash check against everything that was already in the Part Studio
        const mine = qCreatedBy(id, EntityType.BODY);
        const others = qSubtraction(qBodyType(qEverything(EntityType.BODY), BodyType.SOLID), mine);
        var n = 0;
        var msg = "";
        for (var cl in evCollision(context, { "tools" : mine, "targets" : others }))
        {
            const t = toString(cl["type"]);
            if (!match(t, ".*ABUT.*").hasMatch && t != "NONE")
            {
                n += 1;
                if (n <= 15)
                    msg = msg ~ boxText(evBox3d(context, { "topology" : cl["toolBody"], "tight" : true })) ~ " x " ~
                        boxText(evBox3d(context, { "topology" : cl["targetBody"], "tight" : true })) ~ " [" ~ t ~ "]; ";
                debug(context, cl["targetBody"], DebugColor.RED);
            }
        }
        reportFeatureInfo(context, id, "PINSTACK clashes " ~ n ~ ": " ~ msg ~ " | M3 holes (x, y) mm: " ~ holeText ~ " | stack z " ~
                roundToPrecision(baseZ / millimeter, 2) ~ ".." ~ roundToPrecision(topZ / millimeter, 2));
    });

function boxText(b is Box3d) returns string
{
    return "(" ~ roundToPrecision(b.minCorner[0] / millimeter, 1) ~ "," ~ roundToPrecision(b.minCorner[1] / millimeter, 1) ~ "," ~ roundToPrecision(b.minCorner[2] / millimeter, 1) ~ ")-(" ~
           roundToPrecision(b.maxCorner[0] / millimeter, 1) ~ "," ~ roundToPrecision(b.maxCorner[1] / millimeter, 1) ~ "," ~ roundToPrecision(b.maxCorner[2] / millimeter, 1) ~ ")";
}
