# Content Output Specification — Projection & LED Media

**Scope:** Media authored for playback on custom physical surfaces — ride/attraction scenic pieces,
building facades, and LED surfaces — inside **disguise**, **TouchDesigner**, or comparable media
servers, with a defined expansion path to realtime **Unreal Engine** sources.

**Status:** v0.1 draft spec. Values are recommendations with rationale; where a value depends on
hardware, a decision rule is given instead of a single number. Items flagged _[verify]_ are
version- or vendor-dependent and should be confirmed against the deployed toolchain.

---

## 0. Assumptions

- Surfaces are **non-planar and object-specific** (scenic pieces, articulated facades), not flat screens.
- Content is **authored, rendered, and composited in an ACES pipeline (ACEScg working space)**; the
  delivery target is **SDR Rec.709** via an ACES Output Transform, unless a project explicitly calls for
  HDR/wide-gamut LED (a different ODT).
- Playback is **pre-rendered media** for the baseline spec; realtime UE is an additive path (§8).
- The physical surface has (or will have) an **accurate 3D model** in real-world scale — for scenic,
  from a 3D scan; for facades, from survey/LiDAR/photogrammetry or architectural drawings.

---

## 1. Canvas & Geometry Model

Two authoring strategies. Pick per surface; they can coexist in one show.

| Strategy | What it is | Use when | Registration method |
|---|---|---|---|
| **UV-baked** | Content lives in the surface's UV space (your `bake_fames.py` path) | Content is "painted onto" the object; complex/wrapped geometry | UV layout travels with media; server maps texture → mesh UVs |
| **Camera-projection (perspective)** | Content authored from the audience/projector viewpoint; server projects it onto the 3D model | Facades, single dominant viewing angle, projector-native framing | Projector/camera calibration; server projects 2D canvas through virtual frustum |

### Texel density (the number that sets your canvas resolution)
Author so that **content pixels ≥ device pixels on the surface**. Undershoot = soft; large overshoot =
wasted render/storage.

- **Projection:** `pixels_per_meter = projector_horizontal_res / surface_width_covered_by_that_projector`.
  Compute per projector (throw and coverage differ), then size the canvas to the **densest** region so
  no area is starved. For edge-blended arrays, the canvas covers the **union** of coverage; blend
  overlap regions are authored once in the shared canvas, not duplicated.
- **LED:** map **1:1 to physical pixels**. Canvas resolution = the LED's real pixel count for that
  surface (from the processor's pixel map). Never scale LED content — non-integer scaling causes moiré
  and softening. Pitch (mm) only matters for viewing-distance/quality judgement, not canvas math.

### Non-planar geometry, seams, occlusion
- Keep the surface model **watertight and single-scale**; name sub-parts (e.g., `facade_L`, `dragon_head`).
- Recessed/occluded areas (window reveals, undercuts): decide per surface whether they are **lit**
  (needs its own projector/UV coverage) or **masked off**. Mark masked regions in the alpha/matte, not
  by relying on black.
- Author UV seams in hidden or low-attention areas; avoid seams crossing high-detail motion.

**Acceptance check:** Render a 1-px checker or a labeled UV grid to the canvas, load on the surface —
every physical region shows crisp, correctly-scaled squares with no visible seam stretch or aliasing.

---

## 1a. UV Authoring for Media Servers

When using the **UV-baked** strategy, the unwrap *is* the content coordinate system: the media server
samples a single flat video into the mesh's UVs [3] (in `bake_fames.py`, the object's UVs and active image
texture the artist paints to are exactly what the server reads back). This inverts several habits from
game/VFX UV work, where UVs are optimized to save texture memory.

### Rules that invert from normal 3D art

| Normal 3D art | Media-server UV |
|---|---|
| Overlap/mirror islands to save texels | **No overlap, ever** — every physical point needs its own pixel; mirrored/stacked islands play identical content on multiple regions |
| UDIM tiles for high res | **Single 0–1 tile per surface** [3] — most servers don't do UDIM; one texture = one clip |
| Texel density varies by importance | **Uniform texel density** across the unwrap — uneven density = some areas soft, others wasted |
| Seams hidden from the render camera | Seams hidden from **real audience sightlines**, and never crossing continuous motion |

### Texel density — even, and matched to physical pixels
- After unwrapping, **Average Islands Scale** then pack [5], so a square meter of surface gets the same
  texel count everywhere. Uneven density is the top cause of "why is that panel soft?"
- Allocate UV area **proportional to real-world surface area**, not perceived importance (a 6 m² wall vs.
  a 1 m² prop should hold ~6:1 UV area for matched sharpness).
- Higher density on a close-viewed foreground prop is allowed but **deliberate and documented** — it
  spends canvas resolution taken from elsewhere. Tie the target to `pixels_per_meter` from §1.

### Seams, margins & bleed
- Leave an **island margin/gutter**; HAP/DXV compress in **4×4 blocks** [1][2] and bilinear sampling reads
  across island edges, so tight packing bleeds neighbors onto seams. More margin if the server mip-maps [6].
- Run a **dilate / edge-pad** pass [6][7] so content bleeds into the gutter and edges don't fringe to black.
  Keep gutters at least **twice the edge-padding width** so neighbors don't bleed together in lower mips [6].
- Place seams on **real-world edges**, in occluded/low-attention areas, and **never down the middle of a
  surface a continuous animation crosses** (the seam reads as a tear in the motion).
- Prefer **fewer, larger islands** — fewer seams, easier even density, less bleed surface.

### Layout & orientation
- **Relax to minimize stretch** (conformal/angle-based unwrap [5] for organic scenic, then relax); straighten
  near-planar architectural strips to clean rectangles.
- **Orient islands to the content, not just packing efficiency** — keep an effect's dominant motion axis
  aligned in UV so motion and directional/compression artifacts read with the grain.
- Don't chase 100% packing efficiency at the cost of even density or motion orientation.

### Round-trip integrity (author ↔ server)
- Export OBJ/FBX **with UVs, single UV set**, from the same file that produced the content; the baked
  UVs must be byte-for-byte the UVs the server reads.
- **UV origin/flip:** Blender's UV origin is bottom-left [5]; some video pipelines treat top-left as origin,
  so content can arrive **V-flipped**. Bake a "TOP" arrow into a test frame, confirm the server's
  convention once, and hold it show-wide.
- Keep consistent **winding/normals**; flipped normals or a stray second UV channel silently mis-sample
  on some servers.

### Platform notes
- **disguise:** import the surface as a 3D object and drive it in **UV mapping mode** (mesh UVs
  authoritative) [3] vs. **Mesh Mapping** / spatial-projection mode [4]. _[verify]_ exact mapping-mode UI
  and UV-set limits per version.
- **TouchDesigner (+ CamSchnappr):** the UV-baked master is applied to the surface geometry as its
  **Color Map** and rendered through a **CamSchnappr-calibrated Camera COMP** [11], so the mesh's UVs are
  authoritative and the **same model + UV set must round-trip Blender → TD** (calibration is solved
  against that geometry). CamSchnappr calibrates the projector, not the content, so all UV rules above
  apply unchanged. Use an **unlit/constant material** for faithful playback. UVs can be remapped live —
  lock them once verified so on-site edits don't drift from the master.

**Acceptance check (labeled-UV-checker pattern):** render a numbered/colored UV grid + a "TOP" arrow +
per-part labels through the real `bake_fames.py` → transcode → server path and load it on the physical
surface. Verify in one pass: squares square and equal-sized (even density, no stretch); orientation
correct (no V-flip); no seam on a bad line and no gutter bleed; each named part shows its expected label
(no overlap/mis-assignment). Passing this catches the large majority of UV defects before content render.

---

## 2. File & Codec Formats

Baseline principle: **GPU-decoded intra-frame codecs for playout; lossless sequences for mastering.**
Avoid long-GOP H.264/H.265 for show playout (scrub/seek jitter, decode spikes), even though modern
servers can play it.

| Codec | Decode | Alpha | Best for | Notes |
|---|---|---|---|---|
| **HAP** | GPU (DXT1) | No | General playout, high layer counts | Cheapest GPU cost; lowest quality of the family |
| **HAP Q** | GPU (chunked DXT5-YCoCg) | No | Higher-quality playout, gradients | ~higher disk bandwidth; preferred quality/perf balance |
| **HAP Alpha** | GPU | Yes | **Scenic / object content needing transparency** | Use for ride pieces where only the object is lit |
| **HAP Q Alpha** | GPU | Yes | High-quality + alpha | Highest HAP disk bandwidth |
| **NotchLC** | GPU | Yes | High-res facades, higher fidelity, HDR-ish | 12-bit luma / 8-bit chroma / 8-bit alpha; excellent quality/size; disguise & Notch native [8] _[verify encoder path]_ |
| **ProRes 422 / 4444** | CPU | 4444: yes | Editorial intermediate, short-form, alpha master | CPU decode limits concurrent layers; fine as a master, not ideal for heavy multi-layer playout |
| **EXR sequence** | CPU | Yes | **Mastering** (ACEScg / ACES2065-1 scene-linear, HDR, 16-bit half) | Transcode to HAP/NotchLC after applying the ACES Output Transform (§4); heavy on disk/IO |
| **DPX / TIFF / PNG seq** | CPU | TIFF/PNG: yes | Lossless mastering, film pipelines | Master format; not a playout format |

**Platform preferences**
- **disguise:** HAP family and NotchLC are the native playout codecs; keep masters as sequences and
  transcode. _[verify]_ confirm codec support against your disguise software version.
- **TouchDesigner:** HAP via *Movie File In* TOP (GPU); NotchLC supported. Generative/realtime content
  bypasses codec entirely.
- **Resolume (if used):** DXV3 or HAP.

**Hard requirement for HAP:** pixel dimensions must be **multiples of 4** (DXT compresses 4×4 blocks) [1][2];
**multiples of 8** recommended. Non-conforming dimensions get padded/softened.

**Alpha discipline (critical for scenic):** deliver **straight (unassociated) alpha** unless the target
explicitly wants premultiplied; be consistent and document which. For projection, black = no light, but
alpha still matters for **layer compositing** on the server and is mandatory for **LED** where black is a
lit pixel.

---

## 3. Resolution, Framerate & Timing

- **Canvas resolution:** from §1 texel density. Round **up** to codec-legal dimensions (mult-of-8 for HAP).
- **Integer scaling only** between authoring and device, especially LED (1:1).
- **Framerate:** choose one project rate and hold it across the entire chain (author → transcode →
  server → output → device). Common: 30/60 (or 25/50, or 24/48 by region/show). The rate must match the
  **genlock/sync** rate (§ workflow guide). Mismatch → judder/tearing.
- **Show length & loop:** for looping content, author a **seamless loop** (first/last frame continuity)
  and document exact frame count; for timeline shows, deliver exact in/out frames to timecode.

**Acceptance check:** A moving 1-px vertical line panning across the surface shows no tearing, stutter,
or frame doubling over a full loop.

---

## 4. Color & Bit Depth — ACES CG Pipeline

All content is authored, rendered, and composited in **ACES**, with **ACEScg** (linear, AP1 primaries) [9]
as the working/render space. The final media-server deliverable is still **display-referred** — you
apply an **ACES Output Transform** to the target display at the final/transcode step. The most common
defect in Blender→media-server pipelines is a **view-transform / OCIO-config mismatch**; the rules below
exist to prevent it.

### Color-managed roles

| Role | Space | Notes |
|---|---|---|
| Working / render | **ACEScg** (linear, AP1) | All Cycles rendering and comp math |
| Archival / interchange master | **ACES2065-1** (linear, AP0) or ACEScg EXR | AP0 for long-term/facility exchange; ACEScg fine in-house |
| Grading (if needed) | **ACEScct** | Log grading space; convert back for output |
| Delivery (playout) | **Rec.709 SDR** via ACES Output Transform | Or a display-specific ODT for HDR/wide-gamut LED |

### Blender / OCIO setup
- Point Blender at an **ACES OCIO config** [10] (set the `OCIO` environment variable to the ACES config's
  `config.ocio` — e.g., the ACES **CG Config**). **Pin the exact ACES config version** (see below) and
  use the identical config in Nuke/AE/Resolve/UE.
- Render/working space resolves to **ACEScg** (the config's `scene_linear` role).
- **Input transforms are mandatory and per-texture:** color/albedo textures → **Input – sRGB**; HDRIs →
  linear/ACEScg utility; **data maps (normal, roughness, masks, displacement) → Raw / Non-Color**.
  A wrong input transform corrupts color at the root before a single frame renders.
- **Preview/View transform:** the **ACES Output Transform for the target display** (Rec.709 SDR for SDR
  delivery) — **not** Standard, AgX, or Filmic.

### Delivery
- Render/master in **ACEScg EXR** (16-bit half). Apply the **ACES Output Transform (→ Rec.709 SDR, or the
  target display ODT)** exactly **once** — either baked into a final render or at the transcode step —
  then encode to the playout codec. **Never double-apply** an output transform or LUT.
- **ACES tone scale & gamut compression:** the Output Transform applies a filmic tone curve and gamut
  mapping. For bright, saturated **emissive/screen** content (LED-blue, saturated reds, hot highlights)
  this changes highlight rolloff and saturation versus a naive sRGB export. **Check saturated/bright
  elements against approved reference**; if a more literal look is required, evaluate a display-rendering/
  custom ODT choice and **document it — the pipeline stays ACES**.

### Bit depth
- Masters: **16-bit half EXR** (ACEScg/ACES2065-1). Playout: HAP is effectively **8-bit** (DXT) *after*
  the ODT; use **NotchLC or 10-bit sequences** to preserve gradient headroom on large facades before
  final transcode.

### LED & realtime
- **LED processor** (Brompton / NovaStar) color management must match the delivery target; for HDR/wide
  gamut, agree the target space and ODT with the LED vendor **before** mastering.
- **Unreal (realtime):** manage color in-engine via **OCIO using the same pinned ACES config**, output
  to the same delivery space (see §8). ICVFX/LED-volume pipelines are natively ACES-oriented.

### Config version pinning (critical)
- **ACES 1.x and ACES 2.0 Output Transforms differ materially.** Mismatched config versions between
  Blender, comp, UE, and the LED processor shift color. **Pin one ACES config version project-wide** and
  record it in the manifest (`aces_config` / `output_transform`). _[verify]_ which config version your
  facility standardizes on.

**Acceptance check:** an ACEScg-rendered reference frame (color chart + gradient ramp + saturated
emissive swatches + skin tone), after the target ACES Output Transform, matches the approved reference on
a calibrated display; no banding on the ramp; saturated/bright elements show no unexpected
desaturation or clipping from the Output Transform; the transform is applied exactly once (no double LUT).

---

## 5. Coordinate / Mapping Metadata (travels WITH the media)

Media alone doesn't register to a surface — this metadata must ship with it.

| Item | Format | Purpose |
|---|---|---|
| Surface model | **OBJ or FBX**, real-world scale, correct origin, named parts | Server's 3D stage/scenic model for mapping & calibration |
| UV layout | PNG/SVG UV snapshot + the model's UVs | Verifies UV-baked content aligns to model |
| Virtual camera(s) | FBX/exported camera or documented intrinsics/extrinsics | Reproduces camera-projection framing on the server |
| Calibration data | Server-native (disguise **OmniCal** dataset; TD **CamSchnappr** Camera COMP Table DATs) | Warp/blend & projector alignment; not authored, captured on-site, versioned per projector |
| Content regions | Naming + manifest (§6) | Which clip lights which named surface part |

**Scale & origin convention:** meters, Z-up or Y-up documented once and held everywhere; origin at a
physically identifiable datum on the piece (for scenic, a scan fiducial). disguise stage imports expect
consistent real-world scale.

---

## 6. Naming, Packaging & Handoff

```
show_<name>/
├─ manifest.json                # machine-readable index (see below)
├─ models/
│  └─ <surface>_v03.obj         # real-world scale, named parts
├─ masters/                     # lossless, for re-transcode
│  └─ <surface>/<clip>/<clip>.####.exr
├─ playout/                     # server-ready codec
│  └─ <surface>/<clip>_HAPQAlpha.mov   (or NotchLC)
├─ calibration/                 # captured on-site, versioned
└─ reference/                   # approved stills, LUTs, color refs
```

- **Frame numbering:** zero-padded, fixed width (`_####` / `_0000`), documented start frame.
- **Versioning:** `_vNN` on models/clips; never overwrite an approved version.
- **Clip naming:** `<surface>_<content>_<res>_<fps>_<codec>` e.g. `dragonHead_fireLoop_2048x2048_30_HAPQAlpha.mov`.
- **Manifest (`manifest.json`):** minimum fields per clip — `surface_part`, `strategy`
  (uv|camera-projection), `canvas_res`, `fps`, `codec`, `alpha` (straight|premult|none), `color_space`
  (delivery, e.g. Rec.709), `aces_config` (pinned version) + `output_transform` (ODT applied),
  `loop` (bool)/`frame_count`, `timecode_in/out` (if timeline), `model_ref`, `version`. This is the file
  an automated importer (or future exporter script) consumes.

---

## 7. Automatable Export Blocks (copy-paste for operators)

**Blender → ACEScg master sequence:**
- `OCIO` env var → the **pinned ACES OCIO config** (`config.ocio`); same config version across all tools
- Render engine: Cycles (matches existing bake path); working space **ACEScg**
- Input transforms set per texture: color → Input – sRGB; data maps → Raw/Non-Color
- Color Management → View/Display: **ACES Output Transform** for the target (Rec.709 SDR) for preview
- Master output: **OpenEXR, 16-bit half, ACEScg** (or ACES2065-1), RGBA if alpha needed
- Resolution: canvas from §1; ensure **mult-of-8** if it will become HAP
- File name: `<surface>/<clip>/<clip>_` with frame padding `####`
- FPS: project rate (§3)

**Apply the ACES Output Transform once** (→ Rec.709 SDR or target display ODT) on final render or at
transcode — never both — before encoding to the playout codec below.

**Master → disguise/TD playout (HAP Q Alpha example, ffmpeg):**
```
ffmpeg -framerate <FPS> -i <clip>_%04d.png \
  -c:v hap -format hap_q -chunks 4 \
  -pix_fmt rgba <clip>_HAPQAlpha.mov
```
_[verify]_ HAP alpha via ffmpeg requires an alpha-capable build/flags; for **NotchLC** use the Notch/
vendor encoder rather than stock ffmpeg. Confirm the exact encoder against your toolchain before batch runs.

**Dimension guard (pre-transcode):** reject any canvas whose width or height is not a multiple of 8.

---

## 8. What Changes for Realtime (Unreal Engine) Sources

The pre-rendered spec above still governs the **surface model, scale, color target, framerate, and
sync**. Realtime replaces the *codec/clip* layer with a live frame stream. Deltas:

| Aspect | Pre-rendered | Realtime UE |
|---|---|---|
| Source | HAP/NotchLC clip | UE render via **RenderStream** (into disguise) or **nDisplay** cluster |
| Framing | Baked camera/UV | disguise drives the **camera frustum**; UE renders to it live |
| Canvas | Fixed file res | **Per-node canvas slicing** across render machines (nDisplay/cluster) |
| Sync | File fps + genlock | **Genlock/frame-lock across all render nodes** + timecode; latency budget matters |
| Color | ACEScg render → ODT baked to Rec.709 | Managed in UE via **OCIO with the same pinned ACES config** → same delivery ODT |
| Alpha/mask | In the clip | Handled by frustum/mask in engine or server |

**New acceptance concerns for realtime:** end-to-end **latency** within budget; **no frame tearing
across cluster nodes** (requires genlock, e.g. Quadro Sync + house tri-level sync); UE **OCIO** uses the
**same pinned ACES config version** as the pre-rendered pipeline and outputs the same delivery ODT;
frustum registration matches the same surface model used for pre-rendered content.

---

## 9. Open Questions (resolve before locking the spec)

1. Per surface: **UV-baked or camera-projection** (or both)?
2. **Projector array vs. LED** per surface — sets the texel-density math and whether alpha is
   compositing-only or mandatory.
3. **Project framerate** and the **genlock/timecode master** (ride PLC? show controller? house sync?).
4. **SDR vs. HDR/wide-gamut** — especially for any high-end LED.
5. **NotchLC vs. HAP Q** as the house playout codec (drives encoder tooling and disk bandwidth).
6. Reliability target for ride operation (24/7, redundancy, watchdog) — affects packaging/delivery, not
   pixels, but should be recorded here.
```

---

## 10. Basis & Confidence

- **High confidence:** HAP family behavior and mult-of-4 constraint; GPU-vs-CPU decode tradeoffs;
  1:1 LED mapping; ACEScg-working / display-referred-ODT-delivery structure and the config-pinning
  requirement; genlock necessity for multi-node realtime.
- **Verify against deployed versions:** which **ACES config version** (1.x vs 2.0) the facility
  standardizes on and its exact OCIO config; exact codec support lists per disguise/TD version; NotchLC
  and HAP-alpha encoder command lines; disguise OmniCal dataset specifics; UE nDisplay/RenderStream
  plugin versions and OCIO setup.
- Nothing here should be treated as vendor documentation — confirm command-line flags and version
  features before a production batch or load-in.

---

## References

Citations back the **falsifiable** technical claims — codec/dimension constraints, documented tool
behaviors, and color-space definitions. The **judgement/best-practice** items in §1a — the "no overlap,
ever" rule, uniform-texel-density guidance, seam-placement, and "orient islands to the content" — are
field practice and first-principles reasoning about how servers sample textures, **not** vendor-documented,
and are presented in-text as recommendations. Cited pages accessed 2026-07-12; verify against the software
versions you deploy.

1. Vidvox — *Hap Video* format specification (draft). https://github.com/Vidvox/hap/blob/master/documentation/HapVideoDRAFT.md — HAP frames stored as GPU S3TC/DXT textures; block-based compression.
2. Derivative — *Hap* (TouchDesigner documentation). https://docs.derivative.ca/Hap — HAP support and the multiple-of-4 dimension requirement (DXT 4×4 blocks).
3. disguise — *UV mapping overview* / *How does Designer sample UV maps?* https://help.disguise.one/workflows/3d-modelling/uv-mapping/uv-mapping-overview — a UV map translates 2D source content ↔ the mesh's 3D polygons; normalising to 0–1 UV space.
4. disguise — *Mesh Mapping.* https://help.disguise.one/designer/mapping/mapping-types/mesh-mapping — surface-aware perspective mapping mode.
5. Blender Manual — *UV editing / unwrapping operators* (Angle-Based Flattening, Average Islands Scale, Pack Islands; UV space origin). https://docs.blender.org/manual/en/latest/modeling/meshes/editing/uv.html
6. Polycount Wiki — *Edge padding.* http://wiki.polycount.com/wiki/Edge_padding — edge padding/dilation; keep gutters ≥ 2× edge-padding width to prevent mip bleed.
7. Adobe — *Substance 3D Painter: Texture dilation / padding.* https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/technical-support/workflow-issues/export-issues/texture-dilation-or-padding
8. Notch — *NotchLC* (Notch Manual). https://manual.notch.one/2026.1/en/docs/reference/notchlc/ — GPU codec; 12-bit luma / 8-bit chroma / 8-bit alpha.
9. Academy — *ACEScg encoding* (ACES Central). https://docs.acescentral.com/encodings/acescg/ — AP1 primaries, linear, 16/32-bit float working space for CG rendering & compositing.
10. Blender Manual — *Color Management / Color Spaces* (OCIO, ACES configs). https://docs.blender.org/manual/en/latest/render/color_management/color_spaces.html
11. Derivative — *Palette:camSchnappr.* https://docs.derivative.ca/Palette:camSchnappr — projector calibration via OpenCV `calibrateCamera` from ≥6 3D–2D correspondences; Color Map; Auto Blend edge-blending.
