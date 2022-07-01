import builtins
from math import pi, sin
from typing import Union, Iterable, Sequence, Callable
from enum import Enum, auto
import cadquery as cq
from cadquery.hull import find_hull
from cadquery import (
    Edge,
    Face,
    Wire,
    Vector,
    Shape,
    Location,
    Vertex,
    Compound,
    Solid,
    Plane,
)
from cadquery.occ_impl.shapes import VectorLike, Real
import cq_warehouse.extensions

z_axis = (Vector(0, 0, 0), Vector(0, 0, 1))


def __matmul__custom(e: Union[Edge, Wire], p: float):
    return e.positionAt(p)


def __mod__custom(e: Union[Edge, Wire], p: float):
    return e.tangentAt(p)


Edge.__matmul__ = __matmul__custom
Edge.__mod__ = __mod__custom
line = Edge.makeLine(Vector(0, 0, 0), Vector(10, 0, 0))
# print(f"position of line at 1/2: {line @ 0.5=}")
# print(f"tangent of line at 1/2: {line % 0.5=}")


def by_x(obj: Shape) -> float:
    return obj.Center().x


def _by_x_shape(self) -> float:
    return self.Center().x


Shape.by_x = _by_x_shape


def by_y(obj: Shape) -> float:
    return obj.Center().y


def _by_y_shape(self) -> float:
    return self.Center().y


Shape.by_y = _by_y_shape


def by_z(obj: Shape) -> float:
    return obj.Center().z


def _by_z_shape(self) -> float:
    return self.Center().z


Shape.by_z = _by_z_shape


def by_length(obj: Union[Edge, Wire]) -> float:
    return obj.Length()


def _by_length_edge_or_wire(self) -> float:
    return self.Length()


Edge.by_length = _by_length_edge_or_wire
Wire.by_length = _by_length_edge_or_wire


def by_radius(obj: Union[Edge, Wire]) -> float:
    return obj.radius()


def _by_radius_edge_or_wire(self) -> float:
    return self.radius()


Edge.by_radius = _by_radius_edge_or_wire
Wire.by_radius = _by_radius_edge_or_wire


def by_area(obj: cq.Shape) -> float:
    return obj.Area()


def _by_area_shape(self) -> float:
    return self.Area()


Shape.by_area = _by_area_shape


class SortBy(Enum):
    NONE = auto()
    X = auto()
    Y = auto()
    Z = auto()
    LENGTH = auto()
    RADIUS = auto()
    AREA = auto()
    VOLUME = auto()
    DISTANCE = auto()


class Mode(Enum):
    """Combination Mode"""

    ADDITION = auto()
    SUBTRACTION = auto()
    INTERSECTION = auto()
    CONSTRUCTION = auto()


class BuildAssembly:
    def add(self):
        pass


def _null(self):
    return self


Solid.null = _null
Compound.null = _null


class Until(Enum):
    NEXT = auto()
    LAST = auto()


class CqObject(Enum):
    EDGE = auto()
    FACE = auto()
    VERTEX = auto()


class Build3D:
    @property
    def workplane_count(self) -> int:
        return len(self.workplanes)

    @property
    def pending_face_count(self) -> int:
        return len(self.pending_faces)

    def __init__(
        self,
        parent: BuildAssembly = None,
        mode: Mode = Mode.ADDITION,
        workplane: Plane = Plane.named("XY"),
    ):
        self.parent = parent
        self.working_solid: Solid = None
        self.workplanes: list[Plane] = [workplane]
        self.pending_faces: dict[int : list[Face]] = {0: []}
        self.pending_edges: dict[int : list[Edge]] = {0: []}
        self.locations: dict[int : list[Location]] = {0: []}
        self.last_operation: dict[CqObject : list[Shape]] = {}
        # self.last_operation_edges: list[Edge] = []

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def push_locations(self, *pts: Union[VectorLike, Location]):
        new_locations = [
            Location(Vector(pt)) if not isinstance(pt, Location) else pt for pt in pts
        ]
        for i in range(len(self.workplanes)):
            self.locations[i].extend(new_locations)
        print(f"{len(self.locations[i])=}")
        return new_locations[0] if len(new_locations) == 1 else new_locations

    def add(self, obj: Union[Edge, Face], mode: Mode = Mode.ADDITION):
        print(f"Add before: {self.locations=}")
        print(f"Add before: {self.pending_faces=}")
        for i, workplane in enumerate(self.workplanes):
            if not self.locations:
                self.locations[i] = Location(Vector())
            for loc in self.locations[i]:
                # located_loc = workplane.fromLocalCoords(loc)
                print(f"{loc=}")
                localized_location = loc * Location(workplane)
                print(f"{localized_location=}")
                # if i in self.workplanes:
                if isinstance(obj, Face):
                    self.pending_faces[i].append(
                        # workplane.fromLocalCoords(obj.located(localized_location))
                        obj.located(localized_location)
                    )
                else:
                    self.pending_edges[i].append(
                        # workplane.fromLocalCoords(obj.located(localized_location))
                        obj.located(localized_location)
                    )
                # else:
                #     if isinstance(obj, Face):
                #         self.pending_faces[i] = [
                #             # workplane.fromLocalCoords(obj.located(localized_location))
                #             obj.located(localized_location)
                #         ]
                #     else:
                #         self.pending_edges[i] = [
                #             # workplane.fromLocalCoords(obj.located(localized_location))
                #             obj.located(localized_location)
                #         ]
        print(f"Add after: {self.pending_faces=}")

    def workplane(self, workplane: Plane = Plane.named("XY"), replace=True):
        if replace:
            self.workplanes = [workplane]
        else:
            self.workplanes.append(workplane)
            self.locations[len(self.workplanes) - 1] = [Location()]
        return workplane

    def faces_to_workplanes(self, *faces: Sequence[Face], replace=False):
        new_planes = []
        for face in faces:
            new_plane = Plane(origin=face.Center(), normal=face.normalAt(face.Center()))
            new_planes.append(new_plane)
            self.workplane(new_plane, replace)
        return new_planes[0] if len(new_planes) == 1 else new_planes

    def edges(self, sort_by: SortBy = SortBy.NONE, reverse: bool = False) -> list[Edge]:
        if sort_by == SortBy.NONE:
            edges = self.working_solid.Edges()
        elif sort_by == SortBy.X:
            edges = sorted(
                self.working_solid.Edges(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            edges = sorted(
                self.working_solid.Edges(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            edges = sorted(
                self.working_solid.Edges(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.LENGTH:
            edges = sorted(
                self.working_solid.Edges(),
                key=lambda obj: obj.Length(),
                reverse=reverse,
            )
        elif sort_by == SortBy.RADIUS:
            edges = sorted(
                self.working_solid.Edges(),
                key=lambda obj: obj.radius(),
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            edges = sorted(
                self.working_solid.Edges(),
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")

        return edges

    def faces(self, sort_by: SortBy = SortBy.NONE, reverse: bool = False) -> list[Face]:
        if sort_by == SortBy.NONE:
            faces = self.working_solid.Faces()
        elif sort_by == SortBy.X:
            faces = sorted(
                self.working_solid.Faces(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            faces = sorted(
                self.working_solid.Faces(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            faces = sorted(
                self.working_solid.Faces(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.AREA:
            faces = sorted(
                self.working_solid.Faces(), key=lambda obj: obj.Area(), reverse=reverse
            )
        elif sort_by == SortBy.DISTANCE:
            faces = sorted(
                self.working_solid.Faces(),
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")
        return faces

    def vertices(
        self, sort_by: SortBy = SortBy.NONE, reverse: bool = False
    ) -> list[Vertex]:
        if sort_by == SortBy.NONE:
            vertices = self.working_solid.Vertices()
        elif sort_by == SortBy.X:
            vertices = sorted(
                self.working_solid.Vertices(),
                key=lambda obj: obj.Center().x,
                reverse=reverse,
            )
        elif sort_by == SortBy.Y:
            vertices = sorted(
                self.working_solid.Vertices(),
                key=lambda obj: obj.Center().y,
                reverse=reverse,
            )
        elif sort_by == SortBy.Z:
            vertices = sorted(
                self.working_solid.Vertices(),
                key=lambda obj: obj.Center().z,
                reverse=reverse,
            )
        elif sort_by == SortBy.DISTANCE:
            vertices = sorted(
                self.working_solid.Vertices(),
                key=lambda obj: obj.Center().Length,
                reverse=reverse,
            )
        else:
            raise ValueError(f"Unable to sort edges by {sort_by}")
        return vertices

    def place_solids(
        self,
        new_solids: list[Solid, Compound],
        mode: Mode = Mode.ADDITION,
        clean: bool = True,
    ):

        Solid.clean_op = Solid.clean if clean else Solid.null
        Compound.clean_op = Compound.clean if clean else Compound.null

        before_vertices = (
            set() if self.working_solid is None else set(self.working_solid.Vertices())
        )
        before_edges = (
            set() if self.working_solid is None else set(self.working_solid.Edges())
        )
        before_faces = (
            set() if self.working_solid is None else set(self.working_solid.Faces())
        )

        if mode == Mode.ADDITION:
            if self.working_solid is None:
                if len(new_solids) == 1:
                    self.working_solid = new_solids[0]
                else:
                    self.working_solid = new_solids.pop().fuse(*new_solids)
            else:
                self.working_solid = self.working_solid.fuse(*new_solids).clean_op()
        elif mode == Mode.SUBTRACTION:
            if self.working_solid is None:
                raise ValueError("Nothing to subtract from")
            self.working_solid = self.working_solid.cut(*new_solids).clean_op()
        elif mode == Mode.INTERSECTION:
            if self.working_solid is None:
                raise ValueError("Nothing to intersect with")
            self.working_solid = self.working_solid.intersect(*new_solids).clean_op()

        self.last_operation[CqObject.VERTEX] = list(
            set(self.working_solid.Vertices()) - before_vertices
        )
        self.last_operation[CqObject.EDGE] = list(
            set(self.working_solid.Edges()) - before_edges
        )
        self.last_operation[CqObject.FACE] = list(
            set(self.working_solid.Faces()) - before_faces
        )

    def extrude(
        self,
        until: Union[float, Until, Face],
        both: bool = False,
        taper: float = None,
        mode: Mode = Mode.ADDITION,
        clean: bool = True,
    ):

        new_solids: list[Solid] = []
        for plane_index, faces in self.pending_faces.items():
            for face in faces:
                new_solids.append(
                    Solid.extrudeLinear(
                        face, self.workplanes[plane_index].zDir * until, 0
                    )
                )
                if both:
                    new_solids.append(
                        Solid.extrudeLinear(
                            face,
                            self.workplanes[plane_index].zDir * until * -1.0,
                            0,
                        )
                    )

        self.place_solids(new_solids, mode, clean)

        return new_solids[0] if len(new_solids) == 1 else new_solids

    def revolve(
        self,
        angle_degrees: float = 360.0,
        axis_start: VectorLike = None,
        axis_end: VectorLike = None,
        mode: Mode = Mode.ADDITION,
        clean: bool = True,
    ):
        # Make sure we account for users specifying angles larger than 360 degrees, and
        # for OCCT not assuming that a 0 degree revolve means a 360 degree revolve
        angle = angle_degrees % 360.0
        angle = 360.0 if angle == 0 else angle

        new_solids = []
        for i, workplane in enumerate(self.workplanes):
            axis = []
            if axis_start is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 0, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_start)))

            if axis_end is None:
                axis.append(workplane.fromLocalCoords(Vector(0, 1, 0)))
            else:
                axis.append(workplane.fromLocalCoords(Vector(axis_end)))
            print(f"Revolve: {axis=}")

            for face in self.pending_faces[i]:
                print(f"{type(face)=}")
                print(f"{face.Area()=}")
                print(f"{face.Center()=}")
                print(f"{face.normalAt(face.Center())=}")
                new_solids.append(Solid.revolve(face, angle, *axis))

        self.place_solids(new_solids, mode, clean)

        return new_solids[0] if len(new_solids) == 1 else new_solids

    def loft(self, ruled: bool = False, mode: Mode = Mode.ADDITION, clean: bool = True):

        new_solids = []
        for i in range(len(self.workplanes)):
            new_wires = []
            for face in self.faces[i]:
                new_wires.append(face.outerWire())
            print(f"{len(new_wires)=}")
            new_solids.append(Solid.makeLoft(new_wires, ruled))

        self.place_solids(new_solids, mode, clean)

        return new_solids[0] if len(new_solids) == 1 else new_solids

    def fillet(self, *edges: Sequence[Edge], radius: float):
        self.working_solid = self.working_solid.fillet(radius, [e for e in edges])


class Build2D:
    def __init__(self, parent: Build3D = None, mode: Mode = Mode.ADDITION):
        self.working_surface = Compound.makeCompound(())
        self.pending_edges: list[Edge] = []
        # self.tags: dict[str, Face] = {}
        self.parent = parent
        self.locations: list[Location] = []
        self.mode = mode

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        print(f"Exit: Area of generated Face: {self.working_surface.Area()}")
        if self.parent is not None:
            self.parent.add(self.working_surface, self.mode)

    def add(self, f: Face, mode: Mode = Mode.ADDITION):
        new_faces = self.place_face(f, mode)
        return new_faces if len(new_faces) > 1 else new_faces[0]

    def push_locations(self, *pts: Sequence[Union[VectorLike, Location]]):
        new_locations = [
            Location(Vector(pt)) if not isinstance(pt, Location) else pt for pt in pts
        ]
        self.locations.extend(new_locations)
        return new_locations

    def assemble_edges(self, mode: Mode = Mode.ADDITION, tag: str = None) -> Face:
        pending_face = Face.makeFromWires(Wire.assembleEdges(self.pending_edges))
        self.add(pending_face, mode, tag)
        self.pending_edges = []
        # print(f"Area of generated Face: {pending_face.Area()}")
        return pending_face

    def hull_edges(self, mode: Mode = Mode.ADDITION, tag: str = None) -> Face:
        pending_face = find_hull(self.pending_edges)
        self.add(pending_face, mode, tag)
        self.pending_edges = []
        # print(f"Area of generated Face: {pending_face.Area()}")
        return pending_face

    def rect(
        self,
        width: float,
        height: float,
        angle: float = 0,
        mode: Mode = Mode.ADDITION,
    ) -> Face:
        """
        Construct a rectangular face.
        """

        new_faces = self.place_face(
            Face.makePlane(height, width).rotate(*z_axis, angle), mode
        )

        return new_faces if len(new_faces) > 1 else new_faces[0]

    def circle(self, radius: float, mode: Mode = Mode.ADDITION) -> Face:
        """
        Construct a circular face.
        """

        new_faces = self.place_face(
            Face.makeFromWires(Wire.makeCircle(radius, *z_axis)), mode
        )

        return new_faces if len(new_faces) > 1 else new_faces[0]

    def place_face(self, face: Face, mode: Mode = Mode.ADDITION):

        if not self.locations:
            self.locations = [Location(Vector())]
        new_faces = [face.located(location) for location in self.locations]

        if mode == Mode.ADDITION:
            self.working_surface = self.working_surface.fuse(*new_faces).clean()
        elif mode == Mode.SUBTRACTION:
            self.working_surface = self.working_surface.cut(*new_faces).clean()
        elif mode == Mode.INTERSECTION:
            self.working_surface = self.working_surface.intersect(*new_faces).clean()
        elif mode == Mode.CONSTRUCTION:
            pass
        else:
            raise ValueError(f"Invalid mode: {mode}")

        self.locations = []
        return new_faces


class Build1D:
    def __init__(self, parent: Build2D = None, mode: Mode = Mode.ADDITION):
        self.edge_list = []
        self.tags: dict[str, Edge] = {}
        self.parent = parent
        self.mode = mode

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pending_face = Face.makeFromWires(Wire.assembleEdges(self.edge_list))
        print(f"Exit: Area of generated Face: {pending_face.Area()}")
        # print(self.tags)
        self.parent.add(pending_face, self.mode)

    def edges(self) -> list[Edge]:
        return self.edge_list

    def vertices(self) -> list[Vertex]:
        vertex_list = []
        for e in self.edge_list:
            vertex_list.extend(e.Vertices())
        return list(set(vertex_list))

    def polyline(
        self,
        *pts: VectorLike,
        mode: Mode = Mode.ADDITION,
        tag: str = None,
    ):
        if len(pts) < 2:
            raise ValueError("polyline requires two or more pts")

        lines_pts = [Vector(p) for p in pts]

        new_edges = [
            Edge.makeLine(lines_pts[i], lines_pts[i + 1])
            for i in range(len(lines_pts) - 1)
        ]

        for e in new_edges:
            e.forConstruction = mode == Mode.CONSTRUCTION
        self.edge_list.extend(new_edges)

        return_value = (
            new_edges[0] if len(new_edges) == 1 else Wire.assembleEdges(new_edges)
        )

        if tag:
            if len(new_edges) > 1:
                for i, edge in enumerate(new_edges):
                    self.tags[f"{tag}-{i}"] = edge
            else:
                self.tags[tag] = new_edges[0]

        return return_value


# with Build2D() as f:
#     # Start with a central circle with a square quarter
#     c6 = f.circle(6)
#     print(f"{type(c6)=}, {c6.Center()=}")
#     f.push((3, 3))
#     r6 = f.rect(6, 6)
#     print(f"{type(r6)=}, {r6.Center()=}")
#     # Create some locations for the cutouts
#     polar_locations = [
#         Location(Vector(3, 0, 0).rotateZ(a), Vector(0, 0, 1), a)
#         for a in range(0, 360, 45)
#     ]
#     f.push(*polar_locations)
#     # Cutout a set of diamonds
#     with Build1D(parent=f, mode=Mode.SUBTRACTION) as e:
#         # Instantiate a simple line
#         l = e.polyline((0, 0), (1, 1))
#         print(f"Type of line: {type(l)}")
#         # Instantiate a polyline
#         m = e.polyline(l.endPoint(), (2, 0), (1, -1))
#         print(f"Type of polyline: {type(m)}")
#         # Create another line but don't assign a global to it
#         e.polyline(m.endPoint(), l.startPoint())
#         # Extract all of the vertices - two for each Edge
#         all_vertices = e.vertices()
#         print(f"Type of vertices: {type(all_vertices)}")
#         print(f"Total number of vertices: {len(all_vertices)}")
#         # Sort these vertices by Y value
#         corners_sorted_by_Y = sorted(all_vertices, key=lambda v: v.Y)
#         # Filter the sorted value to extract just those on the X axis
#         side_corners = list(filter(lambda v: abs(v.Y) < 1e-5, corners_sorted_by_Y))
#         print(f"Number of vertices after filter: {len(side_corners)}")
#         print("Corner vertices at X axis:")
#         for v in side_corners:
#             print(v.toTuple())

# with Build2D() as f2:
#     with Build1D(parent=f2) as c2:
#         pts = [Vector(10, 0, 0).rotateZ(a) for a in range(0, 360, 60)]
#         c2.polyline(*pts)
# print(f"{type(c2.face)=}")

# with Build3D() as s1:
#     with Build2D(s1) as f1:
#         f1.rect(10, 10)
#     box = s1.extrude(10)
#     s1.faces_to_workplanes(*box.Faces())
#     with Build2D(s1) as f2:
#         f2.circle(3)
#     s1.extrude(-1, mode=Mode.SUBTRACTION)
#     # edges_by_z = sorted(s1.edges(), key=by_z, reverse=True)[0:1]
#     # edges_by_z = s1.edges(sort_by=SortBy.Z, reverse=True)[0:1]
#     edges_by_z = s1.edges(SortBy.Z, reverse=True)[0:1]
#     # print(f"{edges_by_z}")
#     # top_circle = sorted(s1.last_operation_edges, key=by_z, reverse=True)[0]
#     # top_circle = filter(lambda f: abs(f.by_z() - 5) < 1e-5, s1.last_operation_edges)
#     # s1.fillet(*s1.last_operation[CqObject.EDGE], radius=0.2)
#     s1.fillet(*edges_by_z, radius=0.2)

# print(s1.solid.Volume())

# with Build2D() as f1:
#     f1.push_locations((-5, -5), (-5, 5), (5, 5), (5, -5))
#     # f1.rect(1, 1)
#     f1.circle(1)
# faces = [f for list in s1.faces.values() for f in list]

# with Build3D() as s2:
#     with Build2D(s2) as f1:
#         f1.push_locations((4, 3))
#         rect = f1.rect(6, 6)
#     revolve = s2.pending_faces
#     s2.revolve()

with Build3D() as s2:
    # s2.push_locations((-5, -5), (-5, 5), (5, 5), (5, -5))
    with Build2D(s2) as f1:
        f1.circle(1)


# with Build3D() as s3:
#     for i in range(21):
#         r = 10 * sin(i * pi / 20) + 5
#         s3.push((0, 0, i))
#         with Build2D(s3) as f1:
#             f1.circle(r)
#     print(f"{len(s3.faces[0])=}")
#     s3.loft()

if "show_object" in locals():
    show_object(s2.pending_faces[0])
    # show_object(rect, name="rect")
    # show_object(f1.working_surface, name="working_surface")
    # show_object(revolve, name="revolve")
    # show_object(f1.face_list)
    # show_object(s1.working_solid, name="s1")
    # show_object(s1.last_operation_edges, name="last edges")
    # show_object(s2.solid, name="s2")
    # show_object(f1.faces, name="f1")
    # show_object(rface, name="rface")
    # show_object(faces, name="circles")
    # show_object(bumps, name="bumps")
    # show_object(f.faces, name="f")
    # show_object(f2.faces, name="f2")
