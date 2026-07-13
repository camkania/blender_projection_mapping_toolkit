# Research & Authoring Prompt — Projection-Mapping Content Pipeline

> **How to use:** Paste the block below into a deep-research / reasoning model (or hand it to a
> research subagent). It is designed to produce two artifacts: (1) a **Content Output
> Specification** and (2) a **State-of-the-Art Workflow Guide**, with a realtime/Unreal
> expansion path. Fill the `<< >>` placeholders first — the more concrete they are, the less the
> model has to assume.

---

## The Prompt

You are a senior projection-mapping / media-server technical director with shipping experience on
large-format architectural mapping, immersive installations, and live events. You have deep hands-on
knowledge of **disguise** (Designer, RenderStream, gx/vx hardware), **TouchDesigner**, generic media
servers (Resolume, Watchout, Pandoras Box/Christie, Modulo Pi, Hippotizer), and **Unreal Engine**
realtime workflows (nDisplay, Notch blocks, RenderStream). You understand the full chain from 3D
content authoring through pixel delivery onto a physical surface: canvas/UV planning, codecs,
color management, calibration/warp-and-blend, genlock/timecode sync, and projector/LED constraints.

### Context — the system I am building
I have a Blender-based toolkit that currently bakes per-frame textures onto the UVs of a modeled
surface (see `bake_fames.py`: it renders a mesh's texture per frame via Cycles and writes an image
sequence). I want to extend this into a **content-generation system** that outputs media guaranteed
to play back correctly on a custom physical surface (e.g., a building facade) inside disguise,
TouchDesigner, or comparable tools — and that can later ingest **realtime** content from Unreal
Engine instead of, or alongside, pre-rendered media.

Project specifics (use these; if a field is blank, state the assumption you make and proceed):
- Target surface(s): `<< e.g., 3-story building facade, ~24m × 12m, non-planar with recessed windows >>`
- Number/type of projectors or LED: `<< e.g., 4× 20k laser projectors, edge-blended >>` OR `<< LED wall, pitch, controller >>`
- Primary playback platform(s): `<< disguise / TouchDesigner / other >>`
- Authoring tools I control: `<< Blender 4.5 LTS (Cycles), + ? >>`
- Realtime ambition: `<< Unreal 5.x via RenderStream? Notch? timeframe? >>`
- Show constraints: `<< target framerate, show length, live vs. timeline, DMX/timecode master? >>`
- Hardware/render budget: `<< media server model, GPU, storage/bandwidth ceiling >>`

### Your task
Produce **two deliverables**, in this order, as clearly separated Markdown sections.

**DELIVERABLE 1 — Content Output Specification.**
A precise, testable spec that any content author (or automated exporter) can target so media plays back
correctly the first time. It must define, with concrete recommended values and the reasoning/tradeoffs
behind each:
1. **Canvas & geometry model** — how the physical surface maps to a content canvas: UV-unwrap vs.
   camera-projection (perspective-correct) authoring; recommended texel density (pixels-per-meter on the
   surface) derived from projector/LED resolution and throw; canvas resolution and aspect; how to handle
   non-planar geometry, seams, and occluded/recessed areas.
2. **File & codec formats** — for each target platform, the preferred container/codec for pre-rendered
   playout (e.g., **HAP / HAP Q / HAP Alpha**, **NotchLC**, **DXV**, image sequences — EXR/PNG/DPX/TIFF,
   ProRes) with explicit guidance on when to use each, GOP/intra-frame considerations, alpha handling,
   and per-clip vs. sequence tradeoffs. Include disguise- and TouchDesigner-specific codec preferences.
3. **Resolution, framerate & timing** — canvas sizing rules, integer-scaling guidance, frame rate
   selection and its relationship to **genlock/timecode**, and how to avoid judder/tearing.
4. **Color & bit depth** — working space, delivery transfer function (typically display-referred /
   sRGB or Rec.709; note when to go scene-linear EXR), bit depth (8/10/12/16), gamma/LUT handoff to the
   media server, and how to keep Blender's Filmic/AgX view transform from corrupting deliverables.
5. **Coordinate / mapping metadata** — what must travel *with* the media so it registers to the surface:
   UV layout export, projector calibration data, mesh/OBJ + camera export from Blender, naming
   conventions, per-surface content regions, and any sidecar/manifest format.
6. **Naming, packaging & handoff** — folder structure, frame-numbering, versioning, and a manifest that
   a media server or automated import can consume.

Present the core of this deliverable as a **reference table** (parameter → recommended value →
rationale → platform notes), followed by an explicit, copy-pasteable **"export settings" block** a
Blender/After Effects/Nuke operator could follow verbatim.

**DELIVERABLE 2 — State-of-the-Art Workflow Guide.**
An end-to-end pipeline from 3D authoring to pixels-on-surface, reflecting current best practice:
1. **Site capture & modeling** — LiDAR/photogrammetry → clean low-poly surface model; establishing a
   real-world scale and origin; building the UV/projection setup.
2. **Authoring in Blender** — how the existing per-frame bake fits in; camera-projection vs. UV-baked
   content; rendering to the spec from Deliverable 1.
3. **Calibration & alignment** — warp-and-blend, projector alignment (manual vs. auto-calibration such
   as disguise OmniCal / camera-based), soft-edge blending, LED processing; how content authored to the
   spec lands correctly.
4. **Media-server integration** — importing into disguise/TouchDesigner, mapping content to the surface,
   playback/transport, timecode/DMX triggering, preview vs. show machine.
5. **QC & on-site troubleshooting** — a pre-show checklist; common failure modes (color shifts, dropped
   frames, misregistration, codec stutter) and fixes.
6. **Realtime expansion — Unreal Engine.** A distinct section covering how to substitute or augment
   pre-rendered media with realtime UE content: **RenderStream** into disguise, **nDisplay** for
   multi-projector/LED, **Notch** blocks in TD/disguise, genlock/frame-lock and timecode sync across
   machines, and what changes in the Content Output Spec when the source is realtime (camera frustum,
   per-node canvas slicing, latency budget) vs. pre-rendered.

### Constraints & standards
- Prefer **current, real** industry practice, tool names, codecs, and features. Where a value depends on
  hardware, give a formula or decision rule rather than a single magic number, and show the arithmetic.
- Call out **platform divergences** explicitly (what differs between disguise, TouchDesigner, and Unreal).
- Distinguish **established best practice** from **your recommendation / opinion** and flag anything you
  are **uncertain** about or that has changed recently — do not present guesses as fact.
- Make both deliverables **testable**: include acceptance checks ("content is correct if…") and, where
  possible, a validation step the operator can run before load-in.
- Optimize for an author who wants an **automatable** spec — assume the export may eventually be script-driven.

### Output format
1. Short **Assumptions** list (anything you inferred from blank fields above).
2. **Deliverable 1 — Content Output Specification** (tables + export block).
3. **Deliverable 2 — State-of-the-Art Workflow Guide** (numbered pipeline + Unreal section).
4. **Open questions / decisions needed from me** before this can be finalized.
5. **Sources / basis** — note where guidance reflects documented platform behavior vs. field practice.

Before writing, restate in one or two sentences your understanding of the goal and the single most
important tradeoff you will optimize for. Then produce the deliverables.
```

---

## Notes on tuning this prompt
- **Fill the `<< >>` placeholders.** Surface size, projector/LED spec, and target platform change almost
  every recommended value (texel density, canvas resolution, codec). Blank fields force the model to
  guess.
- **Run it twice if you want breadth then depth:** once as-is for the full spec, once narrowed to a
  single platform (e.g., "disguise only") for a deeper, less hedged answer.
- **The realtime/Unreal section is deliberately scoped as an expansion** so the pre-rendered spec stays
  usable on its own and the realtime path is additive, matching your "ideally expandable" goal.
