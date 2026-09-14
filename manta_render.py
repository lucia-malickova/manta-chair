# -*- coding: utf-8 -*-
"""MANTA — VTK render for the board/poster: ocean-gradient PBR material with
the fluted surface relief kept visible (matte, raking side-light, real depth)."""
import os, math, numpy as np, vtk

OUT = "_deliver"; os.makedirs(OUT, exist_ok=True)
HALVES = [f"MANTA_RIBBON/MANTA_Hero{t}.stl" for t in ("L", "R")]
if not all(os.path.exists(p) for p in HALVES):
    HALVES = ["MANTA_RIBBON/MANTA_Chair.stl"]


def poly(path):
    r = vtk.vtkSTLReader(); r.SetFileName(path); r.Update()
    cl = vtk.vtkCleanPolyData(); cl.SetInputConnection(r.GetOutputPort())
    sm = vtk.vtkWindowedSincPolyDataFilter()
    sm.SetInputConnection(cl.GetOutputPort())
    sm.SetNumberOfIterations(2); sm.SetPassBand(0.55)   # gentle — keeps the fine relief
    sm.BoundarySmoothingOff(); sm.NonManifoldSmoothingOn(); sm.NormalizeCoordinatesOn(); sm.Update()
    n = vtk.vtkPolyDataNormals(); n.SetInputConnection(sm.GetOutputPort())
    n.SplittingOff(); n.ConsistencyOn(); n.Update()
    return n.GetOutput()


PDS = [poly(p) for p in HALVES]
_app = vtk.vtkAppendPolyData()
for pd in PDS: _app.AddInputData(pd)
_app.Update()
b = _app.GetOutput().GetBounds()
ctr = ((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2)
diag = math.dist((b[0], b[2], b[4]), (b[1], b[3], b[5]))
zmin, zmax = b[4], b[5]
HGT = b[5] - b[4]
WID = max(b[1]-b[0], b[3]-b[2])

# --- colour gradient: deep-water teal (feet) -> pearlescent white (crown) ---
ctf = vtk.vtkColorTransferFunction()
stops = [
    (0.00, 0.02, 0.12, 0.16),   # the depths — near-black teal
    (0.28, 0.02, 0.30, 0.34),   # dark teal
    (0.55, 0.05, 0.55, 0.58),   # teal
    (0.78, 0.35, 0.80, 0.80),   # light teal / aquamarine
    (1.00, 0.93, 0.97, 0.96),   # pearl white (the surface / foam)
]
for t, r, g, bl in stops:
    ctf.AddRGBPoint(zmin + t * (zmax - zmin), r, g, bl)

for pd in PDS:
    pts = pd.GetPoints()
    n = pts.GetNumberOfPoints()
    zs = vtk.vtkFloatArray(); zs.SetName("z")
    for i in range(n):
        zs.InsertNextValue(pts.GetPoint(i)[2])
    pd.GetPointData().SetScalars(zs)


def render(fname, elev, azim, size, bg_top, bg_bot, zoom=1.0, focal=None, parallel=False):
    ren = vtk.vtkRenderer(); ren.GradientBackgroundOn()
    ren.SetBackground(*bg_bot); ren.SetBackground2(*bg_top)
    ren.SetUseDepthPeeling(1); ren.SetMaximumNumberOfPeels(12); ren.SetOcclusionRatio(0.02)
    ren.SetTwoSidedLighting(1); ren.AutomaticLightCreationOff()

    for pd in PDS:
        m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
        m.SetLookupTable(ctf); m.SetScalarModeToUsePointData()
        m.SetColorModeToMapScalars(); m.ScalarVisibilityOn()
        m.SetScalarRange(zmin, zmax)
        act = vtk.vtkActor(); act.SetMapper(m)
        p = act.GetProperty()
        try:
            p.SetInterpolationToPBR(); p.SetMetallic(0.03); p.SetRoughness(0.55)   # matte PETG, not glossy
            try:
                p.SetCoatStrength(0.15); p.SetCoatRoughness(0.4)
                p.SetCoatColor(1.0, 1.0, 1.0)
            except Exception:
                pass
        except Exception:
            p.SetInterpolationToPhong(); p.SetSpecular(0.2); p.SetSpecularPower(20)
        p.SetAmbient(0.22); p.SetDiffuse(0.85)
        ren.AddActor(act)

    for vec, inten, cc in [((-0.5, -0.8, 0.55), 1.1, (1.0, 0.98, 0.94)),
                           ((0.75, -0.2, 0.3), 0.5, (0.6, 0.85, 0.95)),
                           ((0.1, 0.9, 0.5), 0.6, (0.55, 0.9, 0.9)),
                           ((-0.2, 0.3, -1.0), 0.25, (0.7, 0.95, 1.0)),
                           ((-0.92, -0.35, 0.1), 1.5, (1.0, 1.0, 1.0)),     # strong raking side-light -> reveals the relief
                           ((0.3, -0.9, -0.35), 1.3, (1.0, 1.0, 1.0))]:     # low light from below -> catches the legs
        L = vtk.vtkLight(); L.SetLightTypeToSceneLight()
        d = np.array(vec, float); d /= np.linalg.norm(d)
        L.SetPosition(*(np.array(ctr) + d * diag * 3.0)); L.SetFocalPoint(*ctr)
        L.SetColor(*cc); L.SetIntensity(inten)
        ren.AddLight(L)

    cam = ren.GetActiveCamera()
    e, a = math.radians(elev), math.radians(azim)
    vd = np.array([math.cos(e)*math.cos(a), math.cos(e)*math.sin(a), math.sin(e)])
    fp = np.array(focal) if focal is not None else np.array([ctr[0], ctr[1], ctr[2] + HGT * 0.04])
    va = 22.0
    target = 1.9 * max(HGT, WID) / zoom
    dist = target / (2 * math.tan(math.radians(va) / 2))
    cam.SetViewAngle(va); cam.SetFocalPoint(*fp)
    cam.SetPosition(*(fp + vd * dist)); cam.SetViewUp(0, 0, 1)
    if parallel:
        cam.ParallelProjectionOn()
        cam.SetParallelScale(target / 2)
    cam.SetClippingRange(dist * 0.2, dist * 3)

    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren); rw.SetSize(*size); rw.SetMultiSamples(8); rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGB(); w2i.ReadFrontBufferOff(); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(f"{OUT}/{fname}")
    wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print(fname, size)


render("poster_hero.png", 8, -55, (4961, 7016),
       (0.03, 0.10, 0.14), (0.01, 0.03, 0.05), zoom=1.28)
render("b_hero.png", 11, -55, (2400, 2500),
       (0.03, 0.10, 0.14), (0.01, 0.03, 0.05), zoom=1.08)
render("b_side.png", 0, -90, (1700, 2400),
       (0.03, 0.10, 0.14), (0.01, 0.03, 0.05), zoom=1.08, parallel=True)
render("b_back.png", 12, 121, (1900, 2400),
       (0.03, 0.10, 0.14), (0.01, 0.03, 0.05), zoom=1.06)
render("b_top.png", 74, -90, (2400, 1700),
       (0.03, 0.10, 0.14), (0.01, 0.03, 0.05), zoom=1.08, parallel=True)
print("done")
