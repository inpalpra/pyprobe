# PyProbe - Agent Guide

## Overview

PyProbe is a **Variable probing based debugger for Python DSP debugging**. It provides real-time visualization of variables while a Python script executes, enabling developers to inspect waveforms, constellation diagrams, and scalar values without modifying their code.

Think of it as a visual debugger specifically designed for Digital Signal Processing (DSP) workflows, where you need to see arrays and complex signals updating in real-time.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    GUI Process (PyQt6)                       │
│  ┌───────────┐  ┌─────────────────────────────────────────┐ │
│  │Watch List │  │         Probe Panels                    │ │
│  │           │  │  ┌──────────┐  ┌────────────┐          │ │
│  │ signal_i  │  │  │ Waveform │  │Constellation│          │ │
│  │ symbols   │  │  │   Plot   │  │   Plot     │          │ │
│  └───────────┘  │  └──────────┘  └────────────┘          │ │
└────────┬────────┴───────────────────────▲────────────────────┘
         │ Commands                        │ Data
         ▼                                 │
┌─────────────────────────────────────────────────────────────┐
│                  Runner Subprocess                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              VariableTracer (sys.settrace)             │ │
│  │   - Intercepts variable assignments                    │ │
│  │   - Rate-limits data capture (throttling)              │ │
│  │   - Classifies data types                              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Target Python Script                       │ │
│  │   (e.g., dsp_demo.py running QAM signal processing)   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Flow

1. **User loads a Python script** via the GUI
2. **Script executes in a subprocess** with `sys.settrace` enabled
3. **VariableTracer intercepts assignments** to watched variables
4. **Data is sent to GUI via IPC** (queues for small data, shared memory for large arrays)
5. **GUI auto-creates appropriate plots** based on data type classification
6. **Real-time updates at ~60 FPS** with throttling to prevent GUI flooding

## Architecture

### Core Components

| Module | Purpose |
|--------|---------|
| `pyprobe/core/tracer.py` | Heart of the system - implements `sys.settrace` to intercept variables |
| `pyprobe/core/runner.py` | Manages subprocess execution, receives commands, sends data |
| `pyprobe/core/data_classifier.py` | Classifies numpy arrays/scalars for automatic plot selection |
| `pyprobe/ipc/channels.py` | Bidirectional IPC: queues + shared memory for large arrays |
| `pyprobe/ipc/messages.py` | Message protocol between GUI and Runner |

### GUI Components

| Module | Purpose |
|--------|---------|
| `pyprobe/gui/main_window.py` | Main window, orchestrates panels and IPC polling |
| `pyprobe/gui/watch_list.py` | Left panel showing watched variables |
| `pyprobe/gui/probe_panel.py` | Container for individual probe visualizations |
| `pyprobe/gui/control_bar.py` | Toolbar with Open/Run/Pause/Stop controls |
| `pyprobe/gui/theme/cyberpunk.py` | Dark cyberpunk theme styling |

### Visualization (pyqtgraph-based)

| Module | Data Type | Use Case |
|--------|-----------|----------|
| `pyprobe/plots/waveform_plot.py` | 1D real arrays | Time-domain signals, spectra |
| `pyprobe/plots/constellation.py` | 1D/2D complex arrays | I/Q data, QAM symbols |
| `pyprobe/plots/scalar_display.py` | int/float/complex | SNR, power levels, counters |
| `pyprobe/plots/plot_factory.py` | — | Creates appropriate plot based on dtype |

## Data Type Classification

The system auto-selects visualizations based on data type:

```python
DTYPE_SCALAR       # int, float, complex scalar → ScalarDisplay
DTYPE_ARRAY_1D     # 1D real numpy array → WaveformPlot  
DTYPE_ARRAY_COMPLEX # 1D/2D complex array → ConstellationPlot
DTYPE_ARRAY_2D     # 2D real array → (WaveformPlot, flattened)
```

## Throttling Strategies

To prevent overwhelming the GUI with rapid updates:

- **TIME_BASED** (default): Send at most every N milliseconds
- **SAMPLE_EVERY_N**: Send every Nth iteration
- **CHANGE_DETECT**: Only send when value changes significantly
- **NONE**: No throttling (use with caution)

## IPC Design

- **Small data (<10KB)**: Sent via `multiprocessing.Queue`
- **Large arrays (>10KB)**: Uses `shared_memory` for zero-copy transfer
- **Commands (GUI→Runner)**: Add/remove watch, pause/resume/stop
- **Data (Runner→GUI)**: Variable values, stdout/stderr, exceptions

## Running

```bash
# Run with a script
python -m pyprobe examples/dsp_demo.py

# Run GUI only (load script via File menu)
python -m pyprobe

# Watch specific variables
python -m pyprobe script.py -w my_signal -w output_data
```

## Common Development Tasks

### Adding a new plot type

1. Create class in `pyprobe/plots/` extending `BasePlot`
2. Implement `update_data(value, dtype, shape, source_info)`
3. Add dtype constant to `data_classifier.py` if needed
4. Register in `plot_factory.py`

### Adding a new throttle strategy

1. Add enum value to `ThrottleStrategy` in `tracer.py`
2. Implement logic in `_should_capture()` and optionally `_value_changed()`

### Modifying the GUI theme

Edit `pyprobe/gui/theme/cyberpunk.py` - uses PyQt6 stylesheets

## Performance Considerations

- **Trace function is hot path**: Every line of traced code calls `_trace_func`
- **Early exits are critical**: Filter files/functions before accessing `frame.f_locals`
- **Throttling before value access**: Check if we should capture before reading the value
- **Numpy array copies**: Made to prevent mutation issues during transfer
- **Downsampling in plots**: Large arrays are decimated for display (preserving min/max)

## Dependencies

- **PyQt6**: GUI framework
- **pyqtgraph**: Fast scientific plotting
- **numpy**: Array processing

## Example Use Case

The included `examples/dsp_demo.py` demonstrates probing a QAM-16 simulation:

- `received_symbols`: Complex array → Constellation diagram
- `signal_i`, `signal_q`: Real arrays → Waveform plots  
- `snr_db`, `power_db`: Scalars → Numeric displays
