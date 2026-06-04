# Lumina Layers Agent Notes

This repository is Lumina Studio: a multi-material FDM color system based on
physical calibration. The core flow is:

Image upload -> UI/API parameter collection -> LUT matching and image processing
-> mesh / 3MF / GLB generation -> preview or downloadable output.

## Architecture Overview

Think of the codebase in five layers:

1. Core algorithm layer: `core/`
   - Owns the real product behavior: image processing, color matching, LUT
     calibration, 3D mesh generation, and 3MF/GLB output.
   - Key files: `core/converter.py`, `core/image_processing.py`,
     `core/vector_engine.py`, `core/calibration.py`.

2. Utilities and configuration: `utils/` plus `config.py`
   - Owns printer configuration, LUT management, Bambu 3MF writing, statistics,
     and shared helpers.
   - Key files: `utils/bambu_3mf_writer.py`, `utils/lut_manager.py`,
     `config.py`.

3. Legacy Gradio app: `main.py` plus `ui/`
   - Traditional all-in-one desktop/web entry path.
   - `main.py` starts the Gradio app; `ui/layout_new.py` builds the interface
     and callback surface.
   - Docker currently runs `main.py`, so this path is still important.

4. New FastAPI backend: `api/`
   - Wraps the core algorithm layer as HTTP APIs.
   - `api/app.py` registers routers, CORS, worker-pool lifecycle, and session
     cleanup.
   - `api/routers/` is split by domain: converter, calibration, extractor, LUT,
     slicer, health, system, and five-color features.
   - CPU-heavy work is submitted through `api/worker_pool.py`.

5. New React frontend: `frontend/`
   - Vite + React + TypeScript + Zustand + Three.js.
   - The Vite dev server proxies `/api` to the FastAPI backend on port 8000.
   - Main surfaces include `frontend/src/App.tsx`,
     `frontend/src/components/widget/WidgetWorkspace.tsx`,
     `frontend/src/components/Scene3D.tsx`, and stores under
     `frontend/src/stores/`.

## Common Entry Points

- Legacy UI: `python main.py`
  - Starts Gradio, usually on port 7860 or the next available port.

- FastAPI backend: `python api_server.py`
  - Starts uvicorn on port 8000.

- React frontend:
  - `cd frontend`
  - `npm run dev`

## Maintenance Notes

- The project is in a transition period: the legacy Gradio UI and the newer
  FastAPI + React stack coexist.
- Prefer changes in `core/` for behavior shared by both UI paths.
- When touching API behavior, check the corresponding schemas in
  `api/schemas/`, routers in `api/routers/`, frontend API clients in
  `frontend/src/api/`, and relevant stores in `frontend/src/stores/`.
- Large complexity hotspots include `core/converter.py`, `ui/layout_new.py`,
  `api/routers/converter.py`, and `frontend/src/stores/converterStore.ts`.
- Avoid adding dependencies unless explicitly requested.
- Keep changes small and verify with the relevant backend tests, frontend tests,
  typecheck, or build depending on the touched area.

