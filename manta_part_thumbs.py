# -*- coding: utf-8 -*-
"""MANTA — small individual-part thumbnails (one per numbered key box on the
board) so the official ".STL parts arrangement" key shows a picture of each
part next to its number, like a real furniture assembly manual."""
import vtk

SRC = "MANTA_RIBBON"
OUT = "_deliver/thumbs"
import os
os.makedirs(OUT, exist_ok=True)


def parts_list():
    names = []
    with open(f"{SRC}/PARTS_LIST.txt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or not line[0].isdigit() or "." not in line.split()[0]:
                continue
            names.append(line.split(".", 1)[1].split()[0])
    return names


def render_thumb(stl_path, out_path, size=300):
    r = vtk.vtkSTLReader(); r.SetFileName(stl_path); r.Update()
    m = vtk.vtkPolyDataMapper(); m.SetInputConnection(r.GetOutputPort())
    a = vtk.vtkActor(); a.SetMapper(m)
    p = a.GetProperty()
    try:
        p.SetInterpolationToPBR(); p.SetMetallic(0.1); p.SetRoughness(0.55)
    except Exception:
        p.SetInterpolationToPhong()
    p.SetColor(0.42, 0.46, 0.52)

    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    ren.AddActor(a)
    for vec, inten in [((-0.5, -0.7, 0.6), 1.1), ((0.6, -0.2, 0.4), 0.6), ((0.1, 0.8, 0.5), 0.6)]:
        L = vtk.vtkLight(); L.SetLightTypeToSceneLight()
        import numpy as np
        d = np.array(vec, float); d /= np.linalg.norm(d)
        L.SetPosition(*(d * 2000)); L.SetFocalPoint(0, 0, 0); L.SetIntensity(inten)
        ren.AddLight(L)
    ren.ResetCamera()
    cam = ren.GetActiveCamera(); cam.ParallelProjectionOn()
    cam.Elevation(-18); cam.Azimuth(35)
    ren.ResetCameraClippingRange()
    # zoom in a bit so the part fills the frame
    cam.Zoom(1.25)

    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren); rw.SetSize(size, size); rw.SetMultiSamples(8); rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff(); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(out_path)
    wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()


names = parts_list()
print(f"{len(names)} parts")
for i, nm in enumerate(names, start=1):
    out = f"{OUT}/{i:02d}.png"
    render_thumb(f"{SRC}/{nm}.stl", out)
    print(i, nm, "->", out)
print("done")
