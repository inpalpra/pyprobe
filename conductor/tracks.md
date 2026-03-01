# Project Tracks

This file tracks all major tracks for the project. Each track has its own detailed plan in its respective folder.

---

- [x] **Track: if i create a bunch of markers on a waveform graph, then switch view to FFT mag and phase, and then switch back to waveform view, i lose all my markers and must set them up again. i don't want to lose my markers just because i switched views/lenses**
*Link: [./tracks/marker_persistence_20260225/](./tracks/marker_persistence_20260225/)*

---

- [x] **Track: similar to how keysight PXA or keysight VNA have equation editor, i want pyprobe to have an equation editor as well.**
*Link: [./tracks/equation_editor_20260225/](./tracks/equation_editor_20260225/)*

---

- [ ] **Track: Upgraded Step Recorder & Scene Graph**
*Link: [./tracks/upgraded_step_recorder_20260227/](./tracks/upgraded_step_recorder_20260227/)*

---

- [x] **Track: test_downsample_bug.py::test_zoom_in_shows_raw_data -> Expected ~1000 raw points, got 5000 (downsampling not triggering); test_downsample_bug.py::test_intermediate_zoom_redownsamples -> x starts at 0, expected >= 2000 (zoom range not applied); test_reset_zoom_bug.py::test_reset_view_range_does_not_drift -> View range assertion failure. find root causes and fix them. these failed in test-workflow-fixes branch when test-only github workflow was run. You have access to gh cli tool to run github commands**
*Link: [./tracks/fix_downsampling_zoom_reset_20260301/](./tracks/fix_downsampling_zoom_reset_20260301/)*
