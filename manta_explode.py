# -*- coding: utf-8 -*-
"""MANTA — exploded view + parts-arrangement render (for the board)."""
import os, re, glob, math, numpy as np, vtk
from PIL import Image, ImageDraw, ImageFont
import manta_ribbon as st

OUT = "_deliver"; SRC = "MANTA_RIBBON"
_CUTS = st.cut_stations()


def zone_for_file(path):
    """(colour 0-1 tuple, zone index) for a SEG_NNx.stl, from its real cut
    position — same zones as the Board's 'Lay out by zone' step and the key
    grid, so the colour means the same thing everywhere it appears."""
    k = int(re.match(r"SEG_(\d+)", os.path.basename(path)).group(1))
    smid = 0.5 * (_CUTS[k] + _CUTS[k + 1])
    z = st.zone_of(smid)
    return st.ZONE_COLORS[z], z

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

def scene(actors, fname, size, elev, azim, parallel=True, labels=(), legend=None):
    # labels are drawn as a flat 2D pass AFTER rendering (not as 3D billboard
    # actors) — a billboard actor still depth-tests against the meshes, so in
    # a tightly packed exploded cluster a neighbouring part can fully hide a
    # label behind it. Projecting to 2D and drawing on top guarantees every
    # number stays visible regardless of what else is nearby in 3D.
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

    if labels:
        img = Image.open(f"{OUT}/{fname}").convert("RGB")
        dr = ImageDraw.Draw(img)
        try: font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 30)
        except Exception: font = ImageFont.load_default()
        w, h = size
        pts = []
        for pos, text in labels:
            ren.SetWorldPoint(pos[0], pos[1], pos[2], 1.0)
            ren.WorldToDisplay()
            dx, dy, dz = ren.GetDisplayPoint()
            pts.append((dx, h - dy, text))
        # nudge apart labels that land within a few px of each other in 2D
        # (two segments exploded to almost the same screen position)
        for i in range(len(pts)):
            xi, yi, ti = pts[i]
            for j in range(i):
                xj, yj, tj = pts[j]
                if abs(xi - xj) < 26 and abs(yi - yj) < 26:
                    xi += 30; yi -= 6
            pts[i] = (xi, yi, ti)
        for px, py, text in pts:
            r = 17
            dr.ellipse((px - r, py - r, px + r, py + r), fill=(255, 255, 255), outline=(90, 92, 96), width=2)
            dr.text((px, py), text, font=font, fill=(20, 20, 20), anchor="mm")
        img.save(f"{OUT}/{fname}")

    if legend:
        img = Image.open(f"{OUT}/{fname}").convert("RGB")
        dr = ImageDraw.Draw(img)
        try:
            lfont = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 26)
        except Exception:
            lfont = ImageFont.load_default()
        lx, ly = 24, size[1] - 24 - 26 * len(legend)
        for name, col in legend:
            rgb = tuple(int(round(c * 255)) for c in col)
            dr.rectangle((lx, ly, lx + 22, ly + 22), fill=rgb, outline=(90, 92, 96))
            dr.text((lx + 32, ly + 1), name, font=lfont, fill=(40, 40, 40))
            ly += 26
        img.save(f"{OUT}/{fname}")
    print(fname, size)

# ---- exploded: each segment offset outward from the chair's centre ----
segs = sorted(glob.glob(f"{SRC}/SEG_*.stl"))
pds = [read(p) for p in segs]
allb = np.array([pd.GetBounds() for pd in pds])
C = np.array([allb[:, 0].min()+allb[:, 1].max(), allb[:, 2].min()+allb[:, 3].max(),
              allb[:, 4].min()+allb[:, 5].max()]) / 2
acts, num_labels = [], []
used_zones = set()
for i, (pd, bnd, path) in enumerate(zip(pds, allb, segs), start=1):
    c = np.array([(bnd[0]+bnd[1])/2, (bnd[2]+bnd[3])/2, (bnd[4]+bnd[5])/2])
    d = c - C
    d[1] *= 2.6                       # spread mainly sideways (L/R)
    off = d * 0.9 + np.array([0, 0, 0])
    tf = vtk.vtkTransform(); tf.Translate(*off)
    tp = vtk.vtkTransformPolyDataFilter(); tp.SetInputData(pd); tp.SetTransform(tf); tp.Update()
    col, zi = zone_for_file(path)
    used_zones.add(zi)
    acts.append(actor(tp.GetOutput(), col=col))
    # number every part, matching the Board key / template cell numbering
    out_bnd = tp.GetOutput().GetBounds()
    lp = ((out_bnd[0]+out_bnd[1])/2, (out_bnd[2]+out_bnd[3])/2, out_bnd[5] + 30)
    num_labels.append((lp, str(i)))
legend = [(st.ZONE_NAMES[z], st.ZONE_COLORS[z]) for z in sorted(used_zones)]
scene(acts, "b_exploded.png", (2600, 2200), 16, -62, parallel=True, labels=num_labels, legend=legend)

# ---- parts arrangement (Assembly.stl from above) ----
asm = read(f"{SRC}/MANTA_Assembly.stl")
scene([actor(asm)], "b_parts.png", (2600, 2400), 88, -90, parallel=True)
print("done")
