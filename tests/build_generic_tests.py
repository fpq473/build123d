"""

build123d BuildGeneric tests

name: build_generic_tests.py
by:   Gumyr
date: July 30th 2022

desc: Unit tests for the build123d build_generic module

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
import unittest
from math import pi
from build123d import *
from cadquery import Compound, Vector, Edge, Face, Solid, Wire, Location
from build123d import LocationList, Builder


def _assertTupleAlmostEquals(self, expected, actual, places, msg=None):
    """Check Tuples"""
    for i, j in zip(actual, expected):
        self.assertAlmostEqual(i, j, places, msg=msg)


unittest.TestCase.assertTupleAlmostEquals = _assertTupleAlmostEquals


class TestBuilder(Builder):
    @property
    def _obj(self):
        return self.line

    @property
    def _obj_name(self):
        return "test"

    def __init__(self, mode: Mode = Mode.ADD):
        self.test = "test"
        super().__init__(mode)

    def _add_to_context(self):
        pass

    @classmethod
    def _get_context(cls) -> "BuildLine":
        return cls._current.get(None)


class AddTests(unittest.TestCase):
    """Test adding objects"""

    def test_add_to_line(self):
        # Add Edge
        with BuildLine() as test:
            Add(Edge.makeLine((0, 0, 0), (1, 1, 1)))
        self.assertTupleAlmostEquals((test.wires()[0] @ 1).toTuple(), (1, 1, 1), 5)
        # Add Wire
        with BuildLine() as wire:
            Polyline((0, 0, 0), (1, 1, 1), (2, 0, 0), (3, 1, 1))
        with BuildLine() as test:
            Add(wire.wires()[0])
        self.assertEqual(len(test.line.edges()), 3)

    def test_add_to_sketch(self):
        with BuildSketch() as test:
            Add(Face.makePlane(10, 10))
        self.assertAlmostEqual(test.sketch.Area(), 100, 5)

    def test_add_to_part(self):
        # Add Solid
        with BuildPart() as test:
            Add(Solid.makeBox(10, 10, 10))
        self.assertAlmostEqual(test.part.Volume(), 1000, 5)
        # Add Compound
        with BuildPart() as test:
            Add(
                Compound.makeCompound(
                    [
                        Solid.makeBox(10, 10, 10),
                        Solid.makeBox(5, 5, 5, pnt=(20, 20, 20)),
                    ]
                )
            )
        self.assertEqual(test.part.Volume(), 1125, 5)
        # Add Wire
        with BuildLine() as wire:
            Polyline((0, 0, 0), (1, 1, 1), (2, 0, 0), (3, 1, 1))
        with BuildPart() as test:
            Add(wire.wires()[0])
        self.assertEqual(len(test.pending_edges), 3)

    def test_errors(self):
        with self.assertRaises(RuntimeError):
            Add(Edge.makeLine((0, 0, 0), (1, 1, 1)))

    def test_unsupported_builder(self):
        with self.assertRaises(RuntimeError):
            with TestBuilder():
                Add(Edge.makeLine((0, 0, 0), (1, 1, 1)))


class TestOffset(unittest.TestCase):
    def test_single_line_offset(self):
        with self.assertRaises(ValueError):
            with BuildLine():
                Line((0, 0), (1, 0))
                Offset(amount=1)

    def test_line_offset(self):
        with BuildSketch() as test:
            with BuildLine():
                l = Line((0, 0), (1, 0))
                Line(l @ 1, (1, 1))
                Offset(amount=1)
            BuildFace()
        self.assertAlmostEqual(test.sketch.Area(), pi * 1.25 + 3, 5)

    def test_line_offset(self):
        with BuildSketch() as test:
            with BuildLine() as line:
                l = Line((0, 0), (1, 0))
                Line(l @ 1, (1, 1))
                Offset(*line.line.Edges(), amount=1)
            BuildFace()
        self.assertAlmostEqual(test.sketch.Area(), pi * 1.25 + 3, 5)

    def test_face_offset(self):
        with BuildSketch() as test:
            Rectangle(1, 1)
            Offset(amount=1, kind=Kind.INTERSECTION)
        self.assertAlmostEqual(test.sketch.Area(), 9, 5)

    def test_box_offset(self):
        with BuildPart() as test:
            Box(1, 1, 1)
            Offset(
                amount=1,
                kind=Kind.INTERSECTION,
            )
        self.assertAlmostEqual(test.part.Volume(), 3**3 - 1**3, 5)

    def test_box_offset_with_opening(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            Offset(
                amount=-1,
                openings=test.faces() >> Axis.Z,
                kind=Kind.INTERSECTION,
            )
        self.assertAlmostEqual(test.part.Volume(), 10**3 - 8**2 * 9, 5)


class BoundingBoxTests(unittest.TestCase):
    def test_boundingbox_to_sketch(self):
        """Test using bounding box to locate objects"""
        with BuildSketch() as mickey:
            Circle(10)
            with BuildSketch(mode=Mode.PRIVATE) as bb:
                BoundingBox(*mickey.faces())
                ears = (bb.vertices() > Axis.Y)[:-2]
            with Locations(*ears):
                Circle(7)
        self.assertAlmostEqual(mickey.sketch.Area(), 586.1521145312807, 5)
        """Test Vertices"""
        with BuildSketch() as test:
            Rectangle(10, 10)
            BoundingBox(*test.vertices())
        self.assertEqual(len(test.faces()), 1)

    def test_boundingbox_to_part(self):
        with BuildPart() as test:
            Sphere(1)
            BoundingBox(*test.solids())
        self.assertAlmostEqual(test.part.Volume(), 8, 5)
        with BuildPart() as test:
            Sphere(1)
            BoundingBox(*test.vertices())
        self.assertAlmostEqual(test.part.Volume(), (4 / 3) * pi, 5)

    def test_errors(self):
        with self.assertRaises(RuntimeError):
            with BuildLine():
                BoundingBox()


class ChamferTests(unittest.TestCase):
    def test_part_chamfer(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            Chamfer(*test.edges(), length=1)
        self.assertLess(test.part.Volume(), 1000)

    def test_sketch_chamfer(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            Chamfer(*test.vertices(), length=1)
        self.assertAlmostEqual(test.sketch.Area(), 100 - 4 * 0.5, 5)

        with BuildSketch() as test:
            with Locations((-10, 0), (10, 0)):
                Rectangle(10, 10)
            Chamfer(
                *test.vertices().filter_by_position(Axis.X, minimum=0, maximum=20),
                length=1
            )
        self.assertAlmostEqual(test.sketch.Area(), 200 - 4 * 0.5, 5)

    def test_errors(self):
        with self.assertRaises(RuntimeError):
            with BuildLine():
                Chamfer(length=1)


class FilletTests(unittest.TestCase):
    def test_part_chamfer(self):
        with BuildPart() as test:
            Box(10, 10, 10)
            Fillet(*test.edges(), radius=1)
        self.assertLess(test.part.Volume(), 1000)

    def test_sketch_chamfer(self):
        with BuildSketch() as test:
            Rectangle(10, 10)
            Fillet(*test.vertices(), radius=1)
        self.assertAlmostEqual(test.sketch.Area(), 100 - 4 + pi, 5)

        with BuildSketch() as test:
            with Locations((-10, 0), (10, 0)):
                Rectangle(10, 10)
            Fillet(
                *test.vertices().filter_by_position(Axis.X, minimum=0, maximum=20),
                radius=1
            )
        self.assertAlmostEqual(test.sketch.Area(), 200 - 4 + pi, 5)

    def test_errors(self):
        with self.assertRaises(RuntimeError):
            with BuildLine():
                Fillet(radius=1)


class HexArrayTests(unittest.TestCase):
    def test_hexarray_in_sketch(self):
        with BuildSketch() as test:
            Rectangle(70, 70)
            with HexLocations(20, 4, 3, centered=(True, True)):
                Circle(5, mode=Mode.SUBTRACT)
        self.assertAlmostEqual(test.sketch.Area(), 70**2 - 12 * 25 * pi, 5)

    def test_error(self):
        with self.assertRaises(ValueError):
            with BuildSketch():
                with HexLocations(20, 0, 3, centered=(True, True)):
                    pass
            with BuildSketch():
                with HexLocations(20, 1, -3, centered=(True, True)):
                    pass


class MirrorTests(unittest.TestCase):
    def test_mirror_line(self):
        edge = Edge.makeLine((1, 0, 0), (2, 0, 0))
        wire = Wire.makeCircle(1, center=(5, 0, 0), normal=(0, 0, 1))
        with BuildLine() as test:
            Mirror(edge, wire, about="YZ")
        self.assertEqual(
            len(test.edges().filter_by_position(Axis.X, minimum=0, maximum=10)), 0
        )
        self.assertEqual(
            len(test.edges().filter_by_position(Axis.X, minimum=-10, maximum=0)), 2
        )
        with BuildLine() as test:
            Line((1, 0), (2, 0))
            Mirror(about="YZ")
        self.assertEqual(len(test.edges()), 2)

    def test_mirror_sketch(self):
        edge = Edge.makeLine((1, 0), (2, 0))
        wire = Wire.makeCircle(1, center=(5, 0, 0), normal=(0, 0, 1))
        face = Face.makePlane(2, 2, basePnt=(8, 0))
        compound = Compound.makeCompound(
            [
                Face.makePlane(2, 2, basePnt=(8, 8)),
                Face.makePlane(2, 2, basePnt=(8, -8)),
            ]
        )
        with BuildSketch() as test:
            Mirror(edge, wire, face, compound, about="YZ")
        self.assertEqual(
            len(test.pending_edges.filter_by_position(Axis.X, minimum=0, maximum=10)), 0
        )
        self.assertEqual(
            len(test.faces().filter_by_position(Axis.X, minimum=0, maximum=10)), 0
        )
        self.assertEqual(
            len(test.pending_edges.filter_by_position(Axis.X, minimum=-10, maximum=0)),
            2,
        )
        self.assertEqual(
            len(test.faces().filter_by_position(Axis.X, minimum=-10, maximum=0)), 3
        )

    def test_mirror_part(self):
        cone = Solid.makeCone(2, 1, 2, pnt=(5, 4, 0))
        with BuildPart() as test:
            Mirror(cone, about="YZ")
        self.assertEqual(
            len(test.solids().filter_by_position(Axis.X, minimum=-10, maximum=0)), 1
        )


class ScaleTests(unittest.TestCase):
    def test_line(self):
        with BuildLine() as test:
            Line((0, 0), (1, 0))
            Scale(by=2, mode=Mode.REPLACE)
        self.assertAlmostEqual(test.edges()[0].Length(), 2.0, 5)

    def test_sketch(self):
        with BuildSketch() as test:
            Rectangle(1, 1)
            Scale(by=2, mode=Mode.REPLACE)
        self.assertAlmostEqual(test.sketch.Area(), 4.0, 5)

    def test_part(self):
        with BuildPart() as test:
            Box(1, 1, 1)
            Scale(by=(2, 2, 2), mode=Mode.REPLACE)
        self.assertAlmostEqual(test.part.Volume(), 8.0, 5)

    def test_external_object(self):
        line = Edge.makeLine((0, 0), (1, 0))
        with BuildLine() as test:
            Scale(line, by=2)
        self.assertAlmostEqual(test.edges()[0].Length(), 2.0, 5)

    def test_error_checking(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                Box(1, 1, 1)
                Scale(by="a")


class PolarLocationsTests(unittest.TestCase):
    def test_errors(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                with PolarLocations(10, 0, 360, 0):
                    pass


class LocationsTests(unittest.TestCase):
    def test_push_locations(self):
        with BuildPart():
            with Locations(Location(Vector())):
                self.assertTupleAlmostEquals(
                    LocationList._get_context().locations[0].toTuple()[0], (0, 0, 0), 5
                )

    def test_errors(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                with Locations(Edge.makeLine((1, 0), (2, 0))):
                    pass


class RectangularArrayTests(unittest.TestCase):
    def test_errors(self):
        with self.assertRaises(ValueError):
            with BuildPart():
                with GridLocations(5, 5, 0, 1):
                    pass


if __name__ == "__main__":
    unittest.main()
