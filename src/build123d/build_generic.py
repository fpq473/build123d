"""
BuildGeneric

name: build_generic.py
by:   Gumyr
date: July 12th 2022

desc:
    This python module is a library of generic classes used by other
    build123d builders.

license:

    Copyright 2022 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""
from typing import Union
import logging
from cadquery import Matrix
from build123d import (
    BuildLine,
    BuildSketch,
    BuildPart,
    Mode,
    RotationLike,
    Rotation,
    Builder,
    LocationList,
    Kind,
    Keep,
    PlaneLike,
    Shape,
    Vertex,
    Plane,
    Compound,
    Edge,
    Wire,
    Face,
    Solid,
    Location,
    Vector,
    validate_inputs,
)

logging.getLogger("build123d").addHandler(logging.NullHandler())
logger = logging.getLogger("build123d")


#
# Objects
#


class Add(Compound):
    """Generic Object: Add Object to Part or Sketch

    Add an object to the builder.

    if BuildPart:
        Edges and Wires are added to pending_edges. Compounds of Face are added to
        pending_faces. Solids or Compounds of Solid are combined into the part.
    elif BuildSketch:
        Edges and Wires are added to pending_edges. Compounds of Face are added to sketch.
    elif BuildLine:
        Edges and Wires are added to line.

    Args:
        objects (Union[Edge, Wire, Face, Solid, Compound]): sequence of objects to add
        rotation (Union[float, RotationLike], optional): rotation angle for sketch,
            rotation about each axis for part. Defaults to None.
        mode (Mode, optional): combine mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid, Compound],
        rotation: Union[float, RotationLike] = None,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()
        validate_inputs(self, context, objects)

        if isinstance(context, BuildPart):
            rotation_value = (0, 0, 0) if rotation is None else rotation
            rotate = (
                Rotation(*rotation_value)
                if isinstance(rotation_value, tuple)
                else rotation
            )
            new_faces = [obj for obj in objects if isinstance(obj, Face)]
            new_solids = [
                obj.moved(rotate) for obj in objects if isinstance(obj, Solid)
            ]
            for compound in filter(lambda o: isinstance(o, Compound), objects):
                new_faces.extend(compound.get_type(Face))
                new_solids.extend(compound.get_type(Solid))
            new_objects = [obj for obj in objects if isinstance(obj, Edge)]
            for new_wires in filter(lambda o: isinstance(o, Wire), objects):
                new_objects.extend(new_wires.Edges())

            # Add to pending faces and edges
            context._add_to_pending(*new_faces)
            context._add_to_pending(*new_objects)

            # Can't use get_and_clear_locations because the solid needs to be
            # oriented to the workplane after being moved to a local location
            new_objects = [
                solid.moved(location)
                for solid in new_solids
                for location in LocationList._get_context().locations
            ]
            context.locations = [Location(Vector())]
            context._add_to_context(*new_objects, mode=mode)
        elif isinstance(context, (BuildLine, BuildSketch)):
            rotation_angle = rotation if isinstance(rotation, (int, float)) else 0.0
            new_objects = []
            for obj in objects:
                new_objects.extend(
                    [
                        obj.rotate(
                            Vector(0, 0, 0), Vector(0, 0, 1), rotation_angle
                        ).moved(location)
                        for location in LocationList._get_context().locations
                    ]
                )
            context._add_to_context(*new_objects, mode=mode)
        else:
            raise RuntimeError(
                f"Add does not support builder {context.__class__.__name__}"
            )
        super().__init__(Compound.makeCompound(new_objects).wrapped)


#
# Operations
#


class BoundingBox(Compound):
    """Generic Operation: Add Bounding Box

    Applies to: BuildSketch and BuildPart

    Add the 2D or 3D bounding boxes of the object sequence

    Args:
        objects (Shape): sequence of objects
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Shape,
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()

        validate_inputs(self, context, objects)

        if isinstance(context, BuildPart):
            new_objects = []
            for obj in objects:
                if isinstance(obj, Vertex):
                    continue
                bounding_box = obj.BoundingBox()
                new_objects.append(
                    Solid.makeBox(
                        bounding_box.xlen,
                        bounding_box.ylen,
                        bounding_box.zlen,
                        pnt=(bounding_box.xmin, bounding_box.ymin, bounding_box.zmin),
                    )
                )
            context._add_to_context(*new_objects, mode=mode)
            super().__init__(Compound.makeCompound(new_objects).wrapped)

        elif isinstance(context, BuildSketch):
            new_faces = []
            for obj in objects:
                if isinstance(obj, Vertex):
                    continue
                bounding_box = obj.BoundingBox()
                vertices = [
                    (bounding_box.xmin, bounding_box.ymin),
                    (bounding_box.xmin, bounding_box.ymax),
                    (bounding_box.xmax, bounding_box.ymax),
                    (bounding_box.xmax, bounding_box.ymin),
                    (bounding_box.xmin, bounding_box.ymin),
                ]
                new_faces.append(
                    Face.makeFromWires(Wire.makePolygon([Vector(v) for v in vertices]))
                )
            for face in new_faces:
                context._add_to_context(face, mode=mode)
            super().__init__(Compound.makeCompound(new_faces).wrapped)

        else:
            raise RuntimeError(
                f"BoundingBox does not support builder {context.__class__.__name__}"
            )


class Chamfer(Compound):
    """Generic Operation: Chamfer

    Applies to: BuildSketch and BuildPart

    Chamfer the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to chamfer
        length (float): chamfer size
        length2 (float, optional): asymmetric chamfer size. Defaults to None.
    """

    def __init__(
        self, *objects: Union[Edge, Vertex], length: float, length2: float = None
    ):
        context: Builder = Builder._get_context()

        validate_inputs(self, context, objects)

        if isinstance(context, BuildPart):
            new_part = context.part.chamfer(length, length2, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.Vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.chamfer2D(length, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Chamfer does not support builder {context.__class__.__name__}"
            )


class Fillet(Compound):
    """Generic Operation: Fillet

    Applies to: BuildSketch and BuildPart

    Fillet the given sequence of edges or vertices.

    Args:
        objects (Union[Edge,Vertex]): sequence of edges or vertices to fillet
        radius (float): fillet size - must be less than 1/2 local width
    """

    def __init__(self, *objects: Union[Edge, Vertex], radius: float):
        context: Builder = Builder._get_context()

        validate_inputs(self, context, objects)

        if isinstance(context, BuildPart):
            new_part = context.part.fillet(radius, list(objects))
            context._add_to_context(new_part, mode=Mode.REPLACE)
            super().__init__(new_part.wrapped)
        elif isinstance(context, BuildSketch):
            new_faces = []
            for face in context.faces():
                vertices_in_face = [v for v in face.Vertices() if v in objects]
                if vertices_in_face:
                    new_faces.append(face.fillet2D(radius, vertices_in_face))
                else:
                    new_faces.append(face)
            new_sketch = Compound.makeCompound(new_faces)
            context._add_to_context(new_sketch, mode=Mode.REPLACE)
            super().__init__(new_sketch.wrapped)
        else:
            raise RuntimeError(
                f"Fillet does not support builder {context.__class__.__name__}"
            )


class Mirror(Compound):
    """Generic Operation: Mirror

    Applies to: BuildLine, BuildSketch, and BuildPart

    Mirror a sequence of objects over the given plane.

    Args:
        objects (Union[Edge, Face,Compound]): sequence of edges or faces to mirror
        about (PlaneLike, optional): reference plane. Defaults to "XZ".
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Compound],
        about: PlaneLike = "XZ",
        mode: Mode = Mode.ADD,
    ):
        context: Builder = Builder._get_context()

        validate_inputs(self, context, objects)

        if not objects:
            objects = [context._obj]

        self.objects = objects
        self.about = about
        self.mode = mode

        mirror_plane = about if isinstance(about, Plane) else Plane.named(about)
        scale_matrix = Matrix(
            [
                [1.0, 0.0, 00.0, 0.0],
                [0.0, 1.0, 00.0, 0.0],
                [0.0, 0.0, -1.0, 0.0],
                [0.0, 0.0, 00.0, 1.0],
            ]
        )
        localized = [mirror_plane.toLocalCoords(o) for o in objects]
        local_mirrored = [o.transformGeometry(scale_matrix) for o in localized]
        mirrored = [mirror_plane.fromLocalCoords(o) for o in local_mirrored]

        context._add_to_context(*mirrored, mode=mode)
        super().__init__(Compound.makeCompound(mirrored).wrapped)


class Offset(Compound):
    """Generic Operation: Offset

    Applies to: BuildLine, BuildSketch, and BuildPart

    Offset the given sequence of Edges, Faces, Compound of Faces, or Solids.
    The kind parameter controls the shape of the transitions. For Solid
    objects, the openings parameter allows selected faces to be open, like
    a hollow box with no lid.

    Args:
        objects: Union[Edge, Face, Solid, Compound], sequence of objects
        amount (float): positive values external, negative internal
        openings (list[Face], optional), sequence of faces to open in part.
            Defaults to None.
        kind (Kind, optional): transition shape. Defaults to Kind.ARC.
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.

    Raises:
        ValueError: Invalid object type
    """

    def __init__(
        self,
        *objects: Union[Edge, Face, Solid, Compound],
        amount: float,
        openings: Union[Face, list[Face]] = None,
        kind: Kind = Kind.ARC,
        mode: Mode = Mode.REPLACE,
    ):
        context: Builder = Builder._get_context()

        validate_inputs(self, context, objects)

        if not objects:
            objects = [context._obj]

        self.objects = objects
        self.amount = amount
        self.openings = openings
        self.kind = kind
        self.mode = mode

        edges = []
        faces = []
        edges = []
        solids = []
        for obj in objects:
            if isinstance(obj, Compound):
                edges.extend(obj.get_type(Edge))
                faces.extend(obj.get_type(Face))
                solids.extend(obj.get_type(Solid))
            elif isinstance(obj, Solid):
                solids.append(obj)
            elif isinstance(obj, Face):
                faces.append(obj)
            elif isinstance(obj, Edge):
                edges.append(obj)

        new_faces = []
        for face in faces:
            new_faces.append(
                Face.makeFromWires(
                    face.outerWire().offset2D(amount, kind=kind.name.lower())[0]
                )
            )
        if edges:
            if len(edges) == 1:
                raise ValueError("At least two edges are required")
            new_wires = Wire.assembleEdges(edges).offset2D(
                amount, kind=kind.name.lower()
            )
        else:
            new_wires = []

        if isinstance(openings, Face):
            openings = [openings]

        new_solids = []
        for solid in solids:
            if openings:
                openings_in_this_solid = [o for o in openings if o in solid.Faces()]
            else:
                openings_in_this_solid = []
            new_solids.append(
                solid.shell(
                    openings_in_this_solid, amount, kind=kind.name.lower()
                ).fix()
            )

        new_objects = new_wires + new_faces + new_solids
        context._add_to_context(*new_objects, mode=mode)
        super().__init__(Compound.makeCompound(new_objects).wrapped)


class Scale(Compound):
    """Generic Operation: Scale

    Applies to: BuildLine, BuildSketch, and BuildPart

    Scale a sequence of objects.

    Args:
        objects (Union[Edge, Face, Compound, Solid]): sequence of objects
        by (Union[float, tuple[float, float, float]]): scale factor
        mode (Mode, optional): combination mode. Defaults to Mode.ADD.
    """

    def __init__(
        self,
        *objects: Shape,
        by: Union[float, tuple[float, float, float]],
        mode: Mode = Mode.REPLACE,
    ):
        context: Builder = Builder._get_context()

        validate_inputs(self, context, objects)

        if not objects:
            objects = [context._obj]

        self.objects = objects
        self.by = by
        self.mode = mode

        if isinstance(by, (int, float)):
            factor = Vector(by, by, by)
        elif (
            isinstance(by, (tuple))
            and len(by) == 3
            and all(isinstance(s, (int, float)) for s in by)
        ):
            factor = Vector(by)
        else:
            raise ValueError("by must be a float or a three tuple of float")

        scale_matrix = Matrix(
            [
                [factor.x, 0.0, 0.0, 0.0],
                [0.0, factor.y, 0.0, 0.0],
                [0.0, 0.0, factor.z, 0.0],
                [0.0, 0.0, 00.0, 1.0],
            ]
        )
        new_objects = []
        for obj in objects:
            current_location = obj.location()
            obj_at_origin = obj.located(Location(Vector()))
            new_objects.append(
                obj_at_origin.transformGeometry(scale_matrix).locate(current_location)
            )

        context._add_to_context(*new_objects, mode=mode)

        super().__init__(Compound.makeCompound(new_objects).wrapped)


class Split(Compound):
    """Generic Operation: Split

    Applies to: BuildLine, BuildSketch, and BuildPart

    Bisect object with plane and keep either top, bottom or both.

    Args:
        objects (Union[Edge, Wire, Face, Solid]), objects to split
        bisect_by (PlaneLike, optional): plane to segment part. Defaults to Plane.named("XZ").
        keep (Keep, optional): selector for which segment to keep. Defaults to Keep.TOP.
        mode (Mode, optional): combination mode. Defaults to Mode.INTERSECT.
    """

    def __init__(
        self,
        *objects: Union[Edge, Wire, Face, Solid],
        bisect_by: PlaneLike = Plane.named("XZ"),
        keep: Keep = Keep.TOP,
        mode: Mode = Mode.REPLACE,
    ):
        def build_cutter(keep: Keep, max_size: float) -> Solid:
            cutter_center = (
                Vector(-max_size, -max_size, 0)
                if keep == Keep.TOP
                else Vector(-max_size, -max_size, -2 * max_size)
            )
            return bisect_plane.fromLocalCoords(
                Solid.makeBox(2 * max_size, 2 * max_size, 2 * max_size).moved(
                    Location(cutter_center)
                )
            )

        context: Builder = Builder._get_context()

        validate_inputs(self, context, objects)

        if not objects:
            objects = [context._obj]

        bisect_plane = (
            bisect_by if isinstance(bisect_by, Plane) else Plane.named(bisect_by)
        )

        self.objects = objects
        self.bisect_by = bisect_by
        self.keep = keep
        self.mode = mode

        new_objects = []
        for obj in objects:
            max_size = obj.BoundingBox().DiagonalLength

            cutters = []
            if keep == Keep.BOTH:
                cutters.append(build_cutter(Keep.TOP, max_size))
                cutters.append(build_cutter(Keep.BOTTOM, max_size))
            else:
                cutters.append(build_cutter(keep, max_size))
            new_objects.append(obj.intersect(*cutters))

        context._add_to_context(*new_objects, mode=mode)
        super().__init__(Compound.makeCompound(new_objects).wrapped)
