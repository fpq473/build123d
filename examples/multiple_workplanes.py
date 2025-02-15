from build123d import *

with BuildPart() as obj:
    Box(5, 5, 1)
    with Workplanes(*obj.faces().filter_by_axis(Axis.Z)):
        Sphere(1.8, mode=Mode.SUBTRACT)

if "show_object" in locals():
    show_object(obj.part)
