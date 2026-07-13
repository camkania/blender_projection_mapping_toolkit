# State-of-the-Art Workflow Guide — Projection & LED Content

**Companion to** [`CONTENT_OUTPUT_SPEC.md`](CONTENT_OUTPUT_SPEC.md). This is the end-to-end pipeline
from physical surface to pixels-on-surface, tuned for **ride/attraction scenic pieces**, **building
facades**, and **LED surfaces**, playing back in **disguise / TouchDesigner**, with a realtime
**Unreal Engine** expansion.

> Read the spec first — it defines the *targets*. This guide is the *process* that hits them.

---

## Pipeline at a glance

```
[1] Capture & model  →  [2] Author (Blender)  →  [3] Master & transcode
        ↓                                              ↓
[4] Calibrate & align (on the real surface)  ←  [5] Media-server integration
        ↓
[6] QC / show-control / troubleshooting        [7] Realtime UE (optional, additive)
```

---

## 1. Site capture & modeling

The single biggest determinant of registration quality. Content can only be as accurate as the model.

- **Ride scenic pieces:** **3D-scan the physical piece** (structured-light or photogrammetry) — do not
  model from CAD drawings alone; as-built differs from as-designed. Retopologize to a clean, low-poly,
  watertight mesh. Preserve real-world scale and a **physical fiducial** as the origin datum.
- **Building facades:** **LiDAR or photogrammetry survey** (or accurate architectural drawings for
  simple planar work). Model window reveals/undercuts explicitly if they'll be lit.
- **LED surfaces:** the "model" is the **pixel map** from the LED processor plus a 3D shell if content
  is spatially mapped. Get the exact physical pixel dimensions per surface.
- **Deliver:** OBJ/FBX, real-world scale, named sub-parts, documented up-axis and origin
  (spec §5). Establish UVs here if using the UV-baked strategy.
- **Calibration-point readiness (TouchDesigner/CamSchnappr):** ensure the mesh has clean vertices at
  **≥6 identifiable, well-distributed, non-coplanar** physical landmarks (corners/edges). CamSchnappr's
  camera solve [4] corresponds those vertices to projector pixels — all-coplanar or feature-poor meshes
  give a weak/degenerate solve.

**Gate:** model overlaid on a survey photo / point cloud aligns within tolerance; scale verified against
a known real-world dimension.

---

## 2. Authoring in Blender

- **Choose strategy per surface** (spec §1): UV-baked (your `bake_fames.py` per-frame texture bake) or
  camera-projection. For scenic, UV-baked keeps content "on the object"; for facades with a dominant
  viewpoint, camera-projection is often simpler to align.
- **Where the existing baker fits:** `bake_fames.py` renders the mesh's active image texture per frame
  (Cycles) and writes an image sequence — that is exactly the **master sequence** in spec §6. Point its
  output at `masters/<surface>/<clip>/` and hold the project framerate.
- **Alpha/matte for scenic:** author a matte so only the object is lit and spill is controlled — this
  becomes the deliverable's alpha (HAP Alpha [5] / NotchLC [6]). Black ≠ mask; use real alpha.
- **Color (ACES CG):** work in **ACEScg** [7] under the **pinned ACES OCIO config** [8]; set per-texture input
  transforms (color → Input – sRGB, data maps → Raw); master to **ACEScg 16-bit EXR**; preview through
  the **ACES Output Transform** for the target (Rec.709 SDR) — not Standard/AgX/Filmic (spec §4).
- **Render to the spec:** canvas resolution from texel density, codec-legal dimensions, correct fps.

**Gate:** UV grid / checker render lands crisp and correctly scaled on the model in a preview.

---

## 2a. Multi-object & spatially-continuous content

Some content must **track across several separately-UV'd objects at once** — a wipe sweeping the
proscenium → walls → scenic flats, a flythrough, any unified field. Playing a clip into each object's UVs
**breaks this**: every object's UVs are a local 0–1 space [1], so a UV-space wipe runs 0→1 *independently*
on each object instead of tracking through the room.

**Principle — decouple *content space* from *delivery space*.** The effect must be a function of a
**shared coordinate frame** (world position, or position in one master canvas framing the whole set), not
of any object's UVs. This requires every object to sit in **one world coordinate system at correct
real-world scale/position** — which the §1 model discipline already guarantees. Three ways to realize it:

| Method | Content space | Reaches the objects via | Best when |
|---|---|---|---|
| **1. Master content camera** | one flat canvas framing the set from the design viewpoint | project that canvas onto all geometry, or bake with **Project From View** UVs [11] | front-viewed 2D effects; a dominant sightline |
| **2. World-space procedural** *(default)* | `f(world_position, time)` — e.g. a wipe plane sweeping world +X | evaluate in world space, bake each object's own UVs | physically-correct tracking at all angles; wrap-around scenic; respecting real gaps |
| **3. Unified UV atlas** | one shared, spatially-arranged unwrap → one clip | every object samples the same video | static set always driven as one surface |

**Recommended default: Method 2.** A wipe becomes "a plane at world-X = f(time); brightness = distance from
that plane." Evaluated in world space it crosses each wall and flat at the physically correct instant, with
no perspective stretch, and the empty gaps between flats stay correctly timed. It **keeps the per-object UV
deliverable** — you still bake per object with `bake_fames.py`; only the *shader* changes:

- **Minimal change to the bake:** drive the effect from a **Texture Coordinate → Object (or World)** output
  instead of UVs — an animated **empty** moving through the set becomes the wipe's position, shared
  identically across every object's material [12]. Bake each object's UVs as before; every clip is now a
  spatially-coherent slice of one world-space effect.
- **Method 1 (offline):** `Project From View` (orthographic, from the master/design camera) generates UVs
  for all objects from one viewpoint so a flat canvas maps continuously — note it **stretches where
  surfaces recede** from that camera [11].

**Live alternative (skip baking; generative/realtime).** Do the spatial mapping on the server:
- **disguise:** **Parallel Mapping** emits one unified image across multiple surfaces, treating the group as
  a single canvas [13]; **Direct Mapping** can also apply one content across multiple screens [14]; **Mesh
  Mapping** stays surface-aware across UV-mapped objects [2]. One canvas → tracks across the group.
- **TouchDesigner:** render **all** geometry in one 3D scene, apply the wipe as a world-space field, and
  render through the **CamSchnappr-calibrated camera(s)** [4] — a single 3D render tracks across everything
  for free. A strong reason to run cross-object effects through the camera-projection render path rather
  than per-object clip playback.

**Gate:** a diagonal wipe rendered across the whole set reaches each object at the physically correct moment
(verify against a top-down/world reference); no object restarts the wipe in its own UV space; the gaps
between flats read as continuous timing.

---

## 3. Master & transcode

- Keep **lossless ACEScg/ACES2065-1 EXR masters** archived; they let you re-transcode (or re-grade the
  ODT) when a codec, server, or delivery target changes without re-rendering.
- **Apply the ACES Output Transform once** (→ Rec.709 SDR or target display ODT), then transcode to the
  **house playout codec** — HAP Q (Alpha) [5] or NotchLC [6] (spec §2, §4, §7). Enforce the **mult-of-8
  dimension guard** before batching.
- Name and package per spec §6; write the `manifest.json`.

**Gate:** every playout clip conforms to codec + dimension + fps + alpha rules; manifest validates.

---

## 4. Calibration & alignment (on the real surface)

This is where authored content is made to physically register. Done on-site, captured as data (spec §5).

- **Projection — warp & blend:**
  - **disguise:** **OmniCal** [3] (camera-based auto-calibration using structured-light capture) aligns
    projectors to the 3D stage model and generates warp/blend; manual refinement as needed. _[verify]_
    against your disguise version.
  - **TouchDesigner — CamSchnappr:** the primary calibration path. Assign the surface **SOP geometry**
    and a **Camera COMP**; pick **≥6 well-distributed, non-coplanar** vertices at identifiable physical
    features and drag each to its real-world position in the projector output. CamSchnappr runs OpenCV
    `calibrateCamera` [4] to solve the projector-as-camera (intrinsics + extrinsics), stored as two Table
    DATs **inside the Camera COMP** — this is the TD analog of disguise OmniCal, but manual
    point-correspondence rather than auto camera-based. Content then reaches the object through the
    **model's UVs** (assigned via the **Color Map**), rendered through the calibrated camera — so the
    UV-baked master (spec §1a) is exactly the right input. Multi-projector **edge-blending** is handled on
    CamSchnappr's **Auto Blend** page (per-channel gamma/luminance/blend power). `kantanMapper` remains
    an option for direct mesh-warp mapping on simpler pieces.
  - **Soft-edge blending** across overlapping projectors; balance brightness/black levels in overlaps.
- **LED:** alignment is handled at the **processor** (pixel map, gamma, color) — content is 1:1, so the
  work is processor config and color calibration, not warping.
- **Capture the calibration as versioned data** and store under `calibration/` — it is part of the
  deliverable set, not something to redo blindly each day.

**Gate:** a registration test pattern (labeled UV grid + edge markers) lands within tolerance on every
surface region; blends are invisible at viewing distance.

---

## 5. Media-server integration

- **Import** the surface model + playout clips into disguise/TD; map each clip to its **named surface
  part** per the manifest.
- **disguise:** content mapped onto the 3D stage/scenic model; use UV mapping [1] or Mesh Mapping [2] to
  match the authoring strategy; set up layers/transport.
- **TouchDesigner:** *Movie File In* TOP (GPU HAP/NotchLC) [5] → apply to the surface geometry as its
  **Color Map** with an **unlit/constant (emissive) material** so the authored frames project faithfully
  without being re-shaded → render through the **CamSchnappr-calibrated Camera COMP** [4] → projector output.
  Version the Camera COMP calibration DATs as part of the calibration deliverable. Generative networks
  feed the same Color Map for realtime elements.
- **Preview vs. show machine:** validate on a preview/understudy before the show machine; keep them
  configuration-matched.

**Gate:** every clip plays on the correct surface part, correct scale/orientation, correct color, at rate.

---

## 6. QC, show control & troubleshooting

### Show-control, timecode & sync (critical for rides)

**Timecode and genlock are two different jobs — you usually need both [17]:**
- **Timecode** is a positional *address* (`HH:MM:SS:FF`) that names each frame and tells the server *where
  in the show* to be. On its own it does **not** keep devices frame-aligned; independent clocks drift [16][17].
- **Genlock / frame-lock** is a timing *reference* that makes every output scan its frames at the same
  instant — preventing tearing across multi-output surfaces and render nodes [17]. Genlock *phases* frames;
  timecode *positions* them. Any multi-projector/LED surface or realtime cluster needs **both**.

**Who is master:** in an attraction the **ride PLC / show controller is the timecode master** and the media
server **chases** it. disguise can chase external **LTC** or **MTC**, and respond to **Art-Net / OSC / MSC /
MIDI** cues [15]. Compensate FOH/system latency with a global chase **offset** (seconds), and a per-track
**TC adjust** where needed [15].

**Distribution transports on site — tradeoffs:**

| Transport | Runs over | Pros | Cons / watch-for |
|---|---|---|---|
| **LTC** (SMPTE, audio biphase) [16] | an audio channel / XLR | ubiquitous; readable by anything with an audio input; robust; easy to jam-sync/distribute | occupies an audio channel; degrades over long/poor cable; needs clean regeneration |
| **MTC** (SMPTE over MIDI) [16] | MIDI / USB-MIDI | native to DAWs / QLab show-control | MIDI distance & cabling limits; less common in large rigs |
| **Art-Net / OSC / MSC cues** [15] | Ethernet | already present in lighting rigs; carries triggers as well as clock | network reliability; Art-Net TC is **not** genlock — still genlock the video |

**Frame rate & drop-frame — lock this before any media is authored [16]:**
- The **timecode frame rate must match the show/media frame rate**; mixing (e.g., 30 TC against 25 media) drifts.
- Prefer **non-drop-frame at an integer rate** (24/25/30/50/60) for installations. Reserve **drop-frame**
  (29.97 DF, written `hh:mm:ss;ff`) for broadcast-derived 29.97 material — DF skips frame *numbers*, not
  frames, to track wall-clock [16].
- Record the one chosen standard (rate + NDF/DF) everywhere.

**How timecode should travel *with* the media as it's developed.** Fix the temporal contract at authoring
time so each clip has a known address the server can place deterministically:

| Method | How it carries TC | Pros | Cons |
|---|---|---|---|
| **Embedded TC track** (playout MOV) [18] | QuickTime timecode track — start TC + frame rate + frame count baked into the HAP/NotchLC `.mov` | server reads start TC and self-places on the timeline; travels inside the file | must set the correct **start TC** at export; encoder must write a TC track |
| **Frame number = TC** (image-sequence masters) | documented **start-frame ↔ start-TC** mapping; frame *N* = start_TC + *N* | transparent, lossless, trivially verifiable | fragile to renumbering; the mapping must be recorded, not implicit |
| **Manifest sidecar** (spec §6) | `timecode_in/out`, `fps`, `df/ndf` fields per clip | explicit, automatable, import-agnostic | only helps if the importer reads it |
| **BITC burn-in** (review only) | visible TC window burned into a **review** copy | unambiguous for eyeballing sync in QC | **never** ship to show — it's lit pixels; keep it out of `playout/` |

- **Recommended:** choose **one project frame rate + NDF/DF standard first**; author every clip against a
  **known start timecode**; **embed a TC track in playout MOVs** (or record the start-frame↔TC mapping for
  sequences) [18]; and mirror `timecode_in/out` + `fps` + drop-frame in the **manifest** (spec §6) so import
  is deterministic. Keep a **BITC review copy** separate from the show deliverable, for sync QC only.

**24/7 reliability:** solid-state media, redundant/understudy playback, watchdog/auto-restart, scheduled
content integrity checks. Record the reliability design in the package.

### Media-over-IP / SMPTE ST 2110 (PTP sync) — forward-looking

Where the section above assumes SDI + genlock + LTC, high-end and broadcast-adjacent rigs are moving to
**SMPTE ST 2110**, which carries video, audio, and ancillary data as **separate IP essence streams**
(ST 2110-20 / -30 / -40) over standard networking [19]. Two implications for this pipeline:
- **Sync:** ST 2110 replaces black-burst/tri-level **genlock** with **PTP (IEEE 1588), distributed via the
  ST 2059-2 profile** — sub-microsecond timing carried on the same network as the media rather than a
  separate sync rig [20]. The genlock-vs-timecode logic above still holds; PTP is *how* the frame-lock is
  delivered.
- **Redundancy & discovery:** dual-network **ST 2022-7** seamless protection switching and **NMOS** stream
  discovery are part of a real deployment.

**When it's relevant to you — the trigger is LED / realtime, not projectors.** LED processors (e.g.,
Megapixel Helios) now accept ST 2110 input, and virtual-production / ICVFX volumes are increasingly
specified end-to-end 2110 [21][22]; disguise has run full ST 2110 media-server → LED shows at scale [21].
For a **projector-based scenic show it is not required** — SDI + genlock + LTC remains standard. Treat
ST 2110 as the IP-native evolution of this sync section, most applicable on the **realtime/LED path (§7)**.

**Pre-show checklist:**
1. Framerate consistent author→server→output→device; genlock locked.
2. Color matches approved reference; no view-transform shift; no banding on gradients.
3. Registration within tolerance on every surface part; blends invisible.
4. Alpha correct (object-only lighting for scenic; no black-vs-alpha errors on LED).
5. Timecode/trigger tested end-to-end from the show controller; TC frame rate matches media rate; chase offset set; each clip's start TC places it correctly.
6. No dropped/doubled frames over a full loop (1-px pan test).
7. Redundancy/watchdog verified.

**Common failure modes → cause → fix**

| Symptom | Likely cause | Fix |
|---|---|---|
| Colors desaturated/off vs. reference | Wrong OCIO config, non-ACES view transform, double ODT/LUT, or ACES config-version mismatch | Use pinned ACES config; apply ACES Output Transform once; match config across all tools (spec §4) |
| Saturated emissive elements dull/clipped | ACES tone scale + gamut compression on bright screen content | Check vs. reference; document display-rendering/ODT choice (spec §4) — stay in ACES |
| Soft / moiré, esp. LED | Non-integer scaling | Author 1:1 to device pixels; codec-legal dims |
| Stutter / dropped frames | Long-GOP codec, disk bandwidth, no genlock | Use HAP/NotchLC; check IO; enable genlock |
| Misregistration / drift | Model ≠ as-built; stale calibration | Re-scan/re-survey; recapture calibration data |
| Show drifts out of sync over runtime | Timecode without genlock; mismatched TC/media frame rate; DF vs NDF mixup | Genlock all outputs [17]; match TC rate to media; lock one NDF/DF standard [16] |
| Clip starts at the wrong moment | Missing/incorrect start TC; wrong chase offset | Set start TC on export [18]; verify manifest `timecode_in`; adjust offset [15] |
| Visible blend seams | Overlap brightness/black mismatch | Rebalance soft-edge blend & black level |
| Banding on facade gradients | 8-bit throughout | 10-bit+ masters; NotchLC playout [6] |
| Spill / whole area lit on scenic | Missing/incorrect alpha matte | Deliver straight alpha; verify premult flag |

---

## 7. Realtime expansion — Unreal Engine (additive)

The pre-rendered pipeline (§1–6) still governs surface model, scale, color target, framerate, and sync.
Realtime swaps the *clip* for a *live engine stream*.

- **RenderStream (into disguise):** [9] UE renders frames on render nodes; **disguise owns the
  camera/frustum and timeline**; content maps onto the same surface model. Good for interactive/updatable
  show content.
- **nDisplay (UE cluster):** [10] for multi-projector/LED clusters and volumes; each node renders its
  frustum slice of the canvas. Used for LED volumes/ICVFX and large multi-output surfaces.
- **Notch blocks:** `.dfx` blocks run inside disguise/TD for GPU-generative realtime layers (disguise
  offers first-party Notch support via RenderStream [9]) — a lighter path than a full UE cluster.
- **Sync is non-negotiable:** **genlock/frame-lock across every render node** (e.g., Quadro Sync + house
  tri-level sync) + timecode; watch the **latency budget** for interactive triggers. On IP/LED deployments
  this frame-lock may instead be delivered via **SMPTE ST 2110 / PTP** rather than tri-level genlock (§6).
- **Color:** manage in UE via **OCIO using the same pinned ACES config version** [7][8] as the
  pre-rendered pipeline, outputting the same delivery ODT so realtime and playout match (spec §4, §8).
- **Registration:** UE frustum must reference the **same real-world surface model** used for pre-rendered
  content so realtime and playback register identically.

**Realtime gates:** end-to-end latency within budget; no tearing across cluster nodes (genlock verified);
OCIO output matches delivery space; frustum registration matches the pre-rendered model.

---

## Where this repo plugs in

- `bake_fames.py` is the **§2 authoring / §3 master** step for UV-baked content. A natural next build-out:
  a small **exporter** that (a) enforces spec §7 export settings, (b) runs the mult-of-8 dimension guard,
  (c) transcodes to the house codec, and (d) emits `manifest.json` — turning the spec into an automated
  gate rather than a checklist.

---

## Basis & confidence

- **High confidence:** capture-before-model discipline; genlock/timecode necessity; HAP/NotchLC playout;
  1:1 LED mapping; ACEScg-working / display-referred-ODT color structure and config-pinning; the Blender
  OCIO/view-transform pitfall; nDisplay/RenderStream/Notch roles at a conceptual level.
- **Verify against deployed versions:** disguise OmniCal specifics, codec support, exact TD mapping
  components, UE plugin versions and OCIO configuration. Treat vendor docs as authoritative for command
  lines and version features.

---

## References

Citations back the **falsifiable** claims — documented tool behaviors, calibration methods, codec and
color-space facts. **Judgement/practice** items — capture-before-model discipline, seam/alpha handling,
show-control and 24/7 reliability design, genlock necessity — are field practice and first-principles
reasoning, not vendor-documented, and are presented as recommendations. Numbering is local to this guide
(the companion spec keeps its own list). Pages accessed 2026-07-12; verify against deployed versions.

1. disguise — *UV mapping overview* / *How does Designer sample UV maps?* https://help.disguise.one/workflows/3d-modelling/uv-mapping/uv-mapping-overview
2. disguise — *Mesh Mapping.* https://help.disguise.one/designer/mapping/mapping-types/mesh-mapping
3. disguise — *OmniCal overview* (camera-based projection calibration via structured light). https://help.disguise.one/workflows/calibration-projection/omnical-overview
4. Derivative — *Palette:camSchnappr* (OpenCV `calibrateCamera` from ≥6 3D–2D correspondences; Color Map; Auto Blend). https://docs.derivative.ca/Palette:camSchnappr
5. Derivative — *Hap* (TouchDesigner HAP support, incl. HAP Alpha; multiple-of-4 dimensions). https://docs.derivative.ca/Hap
6. Notch — *NotchLC* (Notch Manual): GPU codec, 12-bit luma / 8-bit chroma / 8-bit alpha. https://manual.notch.one/2026.1/en/docs/reference/notchlc/
7. Academy — *ACEScg encoding* (ACES Central): AP1 primaries, linear working space for CG rendering/compositing. https://docs.acescentral.com/encodings/acescg/
8. Blender Manual — *Color Management / Color Spaces* (OCIO, ACES configs). https://docs.blender.org/manual/en/latest/render/color_management/color_spaces.html
9. disguise — *RenderStream — Unreal Engine* (control of UE render nodes from disguise; first-party UE/Unity/Notch support). https://help.disguise.one/workflows/renderstream/unreal-engine/renderstream-unreal
10. Epic Games — *Rendering to Multiple Displays with nDisplay* (synchronized multi-node cluster rendering). https://dev.epicgames.com/documentation/en-us/unreal-engine/rendering-to-multiple-displays-with-ndisplay-in-unreal-engine
11. Blender Manual — *UV Operators: Project From View* (projects faces onto the view/camera plane; stretches where surfaces recede). https://docs.blender.org/manual/en/latest/modeling/meshes/editing/uv.html
12. Blender Manual — *Texture Coordinate node* (Object/World-space outputs; an object/empty can be animated to move a texture through a surface). https://docs.blender.org/manual/en/latest/render/shader_nodes/input/texture_coordinate.html
13. disguise — *Parallel Mapping* (emits one unified image across multiple screens, treated as a single canvas). https://help.disguise.one/designer/mapping/mapping-types/parallel-mapping
14. disguise — *Direct Mapping* (content applied across one or multiple screens within one mapping). https://help.disguise.one/designer/mapping/mapping-types/direct-mapping
15. disguise — *Timecode Overview / Setup LTC / Setup MTC* (chase external LTC or MTC; Art-Net/OSC/MSC/MIDI cues; chase offset and per-track TC adjust). https://help.disguise.one/designer/timeline-tracks-transports/timecode/timecode-overview
16. *SMPTE timecode* (SMPTE 12M): HH:MM:SS:FF addressing, LTC (audio biphase) vs MTC (MIDI), drop-frame vs non-drop-frame at 29.97. https://en.wikipedia.org/wiki/SMPTE_timecode
17. Dataton — *Genlock, framelock & timecode sync: when do I need them?* (timecode names frames; genlock phases them; installations need both). https://newsandviews.dataton.com/genlock-framelock-timecode-sync-when-do-i-need-them
18. Apple — *QuickTime File Format: Timecode media / timed metadata* (timecode track stores start timecode, frame rate, and frame count). https://developer.apple.com/documentation/quicktime-file-format/timed_metadata_media
19. SMPTE — *ST 2110 standards suite* (professional media over IP; -20 video / -30 audio / -40 ancillary as separate essence streams). https://www.smpte.org/standards/st2110 · FAQ: https://www.smpte.org/smpte-st-2110-faq
20. SMPTE — *ST 2059-2: SMPTE Profile for Use of IEEE 1588 Precision Time Protocol* (PTP timing/sync for ST 2110; free PDF). https://pub.smpte.org/pub/st2059-2/st2059-2-2021.pdf
21. disguise — *Six reasons to use ST 2110* / *Full ST 2110 for Eurovision 2024* (media server → LED at scale; ST 2022-7 redundancy). https://www.disguise.one/en/insights/blog/six-reasons-use-st-2110-your-next-live-event-broadcast-or-immersive-experience · https://www.disguise.one/en/insights/news/disguise-enables-first-large-scale-live-broadcast-running-full-st-2110-eurovision
22. Puget Systems — *SMPTE 2110 and why it matters for ICVFX* (LED processors, e.g. Megapixel Helios, accepting ST 2110). https://www.pugetsystems.com/blog/2026/02/09/smpte-2110-and-why-it-matters-for-icvfx/
