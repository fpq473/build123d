"""

name: din_rail.py
by:   Gumyr
date: July 14th 2022

desc:

    This example demonstrates multiple vertex filtering techniques including
    a fully custom filter. It also shows how a workplane can be replaced
    with another in a different orientation for further work.

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
import logging
from build123d import *

logging.basicConfig(
    filename="din_rail.log",
    level=logging.INFO,
    format="%(name)s-%(levelname)s %(asctime)s - [%(filename)s:%(lineno)s - %(funcName)20s() ] - %(message)s",
)
logging.info("Starting to create din rail")

# 35x7.5mm DIN Rail Dimensions
overall_width, top_width, height, thickness, fillet = 35, 27, 7.5, 1, 0.8
rail_length = 1000
slot_width, slot_length, slot_pitch = 6.2, 15, 25

with BuildPart(workplane="XZ") as rail:
    with BuildSketch() as din:
        Rectangle(overall_width, thickness, centered=(True, False))
        Rectangle(top_width, height, centered=(True, False))
        Rectangle(
            top_width - 2 * thickness,
            height - thickness,
            centered=(True, False),
            mode=Mode.SUBTRACT,
        )
        inside_vertices = (
            din.vertices()
            .filter_by_position(Axis.Y, 0.0, height, inclusive=(False, False))
            .filter_by_position(
                Axis.X,
                -overall_width / 2,
                overall_width / 2,
                inclusive=(False, False),
            )
        )
        Fillet(*inside_vertices, radius=fillet)
        outside_vertices = filter(
            lambda v: (v.Y == 0.0 or v.Y == height)
            and -overall_width / 2 < v.X < overall_width / 2,
            din.vertices(),
        )
        Fillet(*outside_vertices, radius=fillet + thickness)
    Extrude(amount=rail_length)
    with Workplanes(rail.faces().filter_by_axis(Axis.Z)[-1]):
        with BuildSketch() as slots:
            with GridLocations(0, slot_pitch, 1, rail_length // slot_pitch - 1):
                SlotOverall(slot_length, slot_width, rotation=90)
    Extrude(amount=-height, mode=Mode.SUBTRACT)

if "show_object" in locals():
    show_object(rail.part, name="rail")
