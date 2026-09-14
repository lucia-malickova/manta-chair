# -*- coding: utf-8 -*-
"""MANTA — exploded view + parts-arrangement render (for the board)."""
import os, glob, math, numpy as np, vtk

OUT = "_deliver"; SRC = "MANTA_RIBBON"

def read(path):
    r = vtk.vtkSTLReader(); r.SetFileName(path); r.Update()
    return r.GetOutput()

def actor(pd, col=(0.60, 0.64, 0.74)):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
    a = vtk.vtkActor(); a.SetMapper(m)
    p = a.GetProperty()
    try: p.SetInterpolationToPBR(); p.SetMetallic(0.15); p.SetRoughness(0.5)
    except Exception: pass
    p.SetColor(*col); p.SetEdgeVisibility(1); p.SetEdgeColor(0.3, 0.32, 0.38); p.SetLineWidth(0.6)
    return a

def scene(actors, fname, size, elev, azim, parallel=True):
    ren = vtk.vtkRenderer(); ren.GradientBackgroundOn()
    ren.SetBackground(1, 1, 1); ren.SetBackground2(0.95, 0.96, 0.98)
    ren.SetUseDepthPeeling(1); ren.SetMaximumNumberOfPeels(10)
    for a in actors: ren.AddActor(a)
    for vec, inten in [((-0.5, -0.8, 0.6), 1.2), ((0.7, -0.2, 0.3), 0.6), ((0.2, 0.9, 0.4), 0.7)]:
        L = vtk.vtkLight(); d = np.array(vec, float); d /= np.linalg.norm(d)
        L.SetLightTypeToSceneLight(); L.SetPosition(*(d*4000)); L.SetFocalPoint(0, 0, 0)
        L.SetIntensity(inten); ren.AddLight(L)
    ren.ResetCamera()
    b = ren.ComputeVisiblePropBounds()
    ctr = ((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2)
    span = max(b[1]-b[0], b[3]-b[2], b[5]-b[4])
    cam = ren.GetActiveCamera()
    e, a = math.radians(elev), math.radians(azim)
    vd = np.array([math.cos(e)*math.cos(a), math.cos(e)*math.sin(a), math.sin(e)])
    cam.SetFocalPoint(*ctr); cam.SetPosition(*(np.array(ctr) + vd*span*3)); cam.SetViewUp(0, 0, 1)
    if parallel:
        cam.ParallelProjectionOn(); cam.SetParallelScale(span*0.62)
    cam.SetClippingRange(span*0.3, span*8)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren)
    rw.SetSize(*size); rw.SetMultiSamples(8); rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff(); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(f"{OUT}/{fname}")
    wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print(fname, size)

# ---- exploded: each segment offset outward from the chair's centre ----
segs = sorted(glob.glob(f"{SRC}/SEG_*.stl"))
pds = [read(p) for p in segs]
allb = np.array([pd.GetBounds() for pd in pds])
C = np.array([allb[:, 0].min()+allb[:, 1].max(), allb[:, 2].min()+allb[:, 3].max(),
              allb[:, 4].min()+allb[:, 5].max()]) / 2
acts = []
for pd, bnd in zip(pds, allb):
    c = np.array([(bnd[0]+bnd[1])/2, (bnd[2]+bnd[3])/2, (bnd[4]+bnd[5])/2])
    d = c - C
    d[1] *= 2.6                       # spread mainly sideways (L/R)
    off = d * 0.9 + np.array([0, 0, 0])
    tf = vtk.vtkTransform(); tf.Translate(*off)
    tp = vtk.vtkTransformPolyDataFilter(); tp.SetInputData(pd); tp.SetTransform(tf); tp.Update()
    acts.append(actor(tp.GetOutput()))
scene(acts, "b_exploded.png", (2600, 2200), 16, -62, parallel=True)

# ---- parts arrangement (Assembly.stl from above) ----
asm = read(f"{SRC}/MANTA_Assembly.stl")
scene([actor(asm)], "b_parts.png", (2600, 2400), 88, -90, parallel=True)
print("done")
