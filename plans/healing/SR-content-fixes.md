# Healing Plan: Content Correctness Fixes (Post-Expansion Self-Review)

## Context

Self-review of the Phase 5–7 content expansion identified four gaps in the 25 pages written. None touch protected paths (`src/launcher/`, `configs/`, `specs/schemas/`).

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-01 | 3D Python `_index.md` not updated with camera/light/material/transform links | SR-01 |
| G-02 | `camera.md` documents setters as functional — source shows they are `pass` no-ops | SR-02 |
| G-03 | `how-to-add-images-python.md` uses `img.content_data` — not verified from source | SR-03 |
| G-04 | `how-to-connect-shapes-python.md` uses `isinstance(shape, Connector)` — import path unverified | SR-04 |

---

## SR-01 — Update 3D Python _index.md

- **Status**: Done
- **Gap**: G-01
- **File**: `publish/reference.aspose.org/3d/en/python/_index.md`
- **Fix**: Added page links to Camera, Light, LambertMaterial, PhongMaterial, Transform in class tables
- **Evidence**: `grep "/reference.aspose.org/3d/python/"` returns 5 matches (camera, light, material×2, transform)
- **Checklist**:
  - [x] `/reference.aspose.org/3d/python/camera/` present
  - [x] `/reference.aspose.org/3d/python/light/` present
  - [x] `/reference.aspose.org/3d/python/material/` present (×2: Lambert + Phong)
  - [x] `/reference.aspose.org/3d/python/transform/` present

## SR-02 — Fix camera.md stub caveat

- **Status**: Done
- **Gap**: G-02
- **File**: `publish/reference.aspose.org/3d/en/python/camera.md`
- **Fix**: Added "Implementation Notes" section; examples updated to remove no-op setter calls
- **Evidence**: `grep "stub\|no-op\|not retained"` → 3 matches in camera.md
- **Checklist**:
  - [x] "declaration stub" caveat present before constructor
  - [x] Perspective example removed non-functional setter assignments
  - [x] Read example note added re default values

## SR-03 — Fix how-to-add-images KB

- **Status**: Done
- **Gap**: G-03
- **File**: `publish/kb.aspose.org/slides/en/python/how-to-add-images-python.md`
- **Fix**: Removed "Read Images" section using `img.content_data`; replaced with simple `len(prs.images)` count
- **Evidence**: `grep "content_data"` → NOT FOUND (0 matches)
- **Checklist**:
  - [x] No `content_data` reference in file
  - [x] Replacement section uses only verified `len(prs.images)` API

## SR-04 — Verify Connector import and fix how-to-connect-shapes

- **Status**: Done
- **Gap**: G-04
- **File**: `publish/kb.aspose.org/slides/en/python/how-to-connect-shapes-python.md`
- **Fix**: No changes needed — verified `Connector` at line 59 of `__init__.py` and in `__all__`
- **Evidence**: `grep "Connector" aspose/slides_foss/__init__.py` → line 59: `from .Connector import Connector`; `Connector` in `__all__`
- **Checklist**:
  - [x] `from aspose.slides_foss import Connector` is a valid import
  - [x] `isinstance(shape, Connector)` example is correct as written
