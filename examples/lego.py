"""

name: lego.py
by:   Gumyr
date: September 12th 2022

desc:

    This example creates a model of a double wide lego block with a
    parametric length (pip_count).
    *** Don't edit this file without checking the lego tutorial ***

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
from build123d import *

pip_count = 6

lego_unit_size = 8
pip_height = 1.8
pip_diameter = 4.8
block_length = lego_unit_size * pip_count
block_width = 16
base_height = 9.6
block_height = base_height + pip_height
support_outer_diameter = 6.5
support_inner_diameter = 4.8
ridge_width = 0.6
ridge_depth = 0.3
wall_thickness = 1.2

with BuildPart() as lego:
    with BuildSketch():
        perimeter = Rectangle(block_length, block_width)
        Offset(
            perimeter,
            amount=-wall_thickness,
            kind=Kind.INTERSECTION,
            mode=Mode.SUBTRACT,
        )
        with GridLocations(0, lego_unit_size, 1, 2):
            Rectangle(block_length, ridge_width)
        with GridLocations(lego_unit_size, 0, pip_count, 1):
            Rectangle(ridge_width, block_width)
        Rectangle(
            block_length - 2 * (wall_thickness + ridge_depth),
            block_width - 2 * (wall_thickness + ridge_depth),
            mode=Mode.SUBTRACT,
        )
        with GridLocations(lego_unit_size, 0, pip_count - 1, 1):
            Circle(support_outer_diameter / 2)
            Circle(support_inner_diameter / 2, mode=Mode.SUBTRACT)
    Extrude(amount=base_height - wall_thickness)
    with Workplanes(
        Plane(origin=(0, 0, (lego.vertices() >> Axis.Z).Z), normal=(0, 0, 1))
    ):
        Box(
            block_length,
            block_width,
            wall_thickness,
            centered=(True, True, False),
        )
    with Workplanes(lego.faces() >> Axis.Z):
        with GridLocations(lego_unit_size, lego_unit_size, pip_count, 2):
            Cylinder(
                radius=pip_diameter / 2, height=pip_height, centered=(True, True, False)
            )


if "show_object" in locals():
    show_object(lego.part, name="lego")
