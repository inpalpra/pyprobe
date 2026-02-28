import sys
import json
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from pyprobe.plots.draw_mode import DrawMode
from pyprobe.plugins.builtins.waveform import WaveformWidget, WaveformPlugin
from pyprobe.plugins.builtins.complex_plots import (
    ComplexRIWidget, ComplexRIPlugin,
    ComplexMAWidget, ComplexMAPlugin,
    SingleCurveWidget,
    LogMagPlugin, LinearMagPlugin, PhaseRadPlugin, PhaseDegPlugin,
)
from pyprobe.core.data_classifier import (
    DTYPE_ARRAY_1D, DTYPE_ARRAY_2D, DTYPE_ARRAY_COMPLEX,
)

def _has_pen(curve) -> bool:
    pen = curve.opts.get('pen')
    if pen is None:
        return False
    if hasattr(pen, 'style'):
        return pen.style() != Qt.PenStyle.NoPen
    return True

def _has_symbol(curve) -> bool:
    return curve.opts.get('symbol') is not None

def extract_curve(curve):
    _, y = curve.getData()
    return {
        "has_pen": _has_pen(curve),
        "has_symbol": _has_symbol(curve),
        "symbol": curve.opts.get('symbol'),
        "has_data": y is not None and len(y) > 0,
        "y_sum": float(np.sum(y)) if y is not None else 0.0,
        "is_plotdataitem": isinstance(curve, pg.PlotDataItem)
    }

ALL_TRANSITIONS = [
    (DrawMode.LINE, DrawMode.DOTS),
    (DrawMode.LINE, DrawMode.BOTH),
    (DrawMode.DOTS, DrawMode.LINE),
    (DrawMode.DOTS, DrawMode.BOTH),
    (DrawMode.BOTH, DrawMode.LINE),
    (DrawMode.BOTH, DrawMode.DOTS),
]

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    
    probe_color = QColor("#00ffff")
    t = np.linspace(0, 2 * np.pi, 128)
    complex_data = np.exp(1j * t).astype(np.complex128)
    real_data = np.sin(np.linspace(0, 4 * np.pi, 100))
    
    # Checksums for validation
    real_data_sum = float(np.sum(real_data))
    real_data_x2_sum = float(np.sum(real_data * 2))
    real_data_x3_sum = float(np.sum(real_data * 3))
    complex_data_real_sum = float(np.sum(complex_data.real))
    complex_data_x05_real_sum = float(np.sum((complex_data * 0.5).real))
    
    state = {}

    # 1. WaveformWidget — real 1D data
    w = WaveformWidget("signal", probe_color)
    w.resize(600, 400)
    w.show()
    w.update_data(real_data, DTYPE_ARRAY_1D)
    app.processEvents()
    
    state["WaveformWidget_1D"] = {}
    state["WaveformWidget_1D"]["initial"] = extract_curve(w._curves[0])
    
    w.set_draw_mode(0, DrawMode.DOTS)
    state["WaveformWidget_1D"]["set_dots"] = extract_curve(w._curves[0])
    
    w.set_draw_mode(0, DrawMode.BOTH)
    state["WaveformWidget_1D"]["set_both"] = extract_curve(w._curves[0])
    
    state["WaveformWidget_1D"]["transitions"] = {}
    for from_mode, to_mode in ALL_TRANSITIONS:
        k = f"{from_mode.name}->{to_mode.name}"
        w.set_draw_mode(0, from_mode)
        start_state = extract_curve(w._curves[0])
        w.set_draw_mode(0, to_mode)
        end_state = extract_curve(w._curves[0])
        state["WaveformWidget_1D"]["transitions"][k] = {"from": start_state, "to": end_state}
        
    w.set_draw_mode(0, DrawMode.DOTS)
    w.update_data(real_data * 2, DTYPE_ARRAY_1D)
    state["WaveformWidget_1D"]["data_update"] = extract_curve(w._curves[0])
    state["WaveformWidget_1D"]["data_update"]["mode"] = w.get_draw_mode(0).name
    
    w.deleteLater()
    
    # 2. WaveformWidget — 2D multi-row data
    w = WaveformWidget("multi", probe_color)
    w.resize(600, 400)
    w.show()
    data2d = np.array([
        np.sin(np.linspace(0, 2*np.pi, 50)),
        np.cos(np.linspace(0, 2*np.pi, 50)),
    ])
    w.update_data(data2d, DTYPE_ARRAY_2D, shape=data2d.shape)
    app.processEvents()
    
    state["WaveformWidget_2D"] = {}
    state["WaveformWidget_2D"]["num_curves"] = len(w._curves)
    
    w.set_draw_mode(0, DrawMode.DOTS)
    state["WaveformWidget_2D"]["independent_modes"] = {
        "c0": extract_curve(w._curves[0]),
        "c1": extract_curve(w._curves[1])
    }
    
    w.set_draw_mode(0, DrawMode.BOTH)
    w.set_draw_mode(1, DrawMode.DOTS)
    state["WaveformWidget_2D"]["all_modes_per_row"] = {
        "c0": extract_curve(w._curves[0]),
        "c1": extract_curve(w._curves[1])
    }
    
    state["WaveformWidget_2D"]["row_transitions"] = {}
    for from_mode, to_mode in ALL_TRANSITIONS:
        k = f"{from_mode.name}->{to_mode.name}"
        w.set_draw_mode(0, from_mode)
        w.set_draw_mode(0, to_mode)
        state["WaveformWidget_2D"]["row_transitions"][k] = {
            "c0": extract_curve(w._curves[0]),
            "c1": extract_curve(w._curves[1]) # should stay LINE, but from_mode starts unconstrained here, wait!
            # The test says: row_transitions on row 0, row 1 stays LINE.
            # But the loop modifies row 0 and records it. We must reset row 1 to LINE to be safe.
        }
    w.deleteLater()
    
    # Let's fix row_transitions to correctly isolate c1
    w = WaveformWidget("multi2", probe_color)
    w.resize(600, 400)
    w.show()
    w.update_data(data2d, DTYPE_ARRAY_2D, shape=data2d.shape)
    app.processEvents()
    for from_mode, to_mode in ALL_TRANSITIONS:
        k = f"{from_mode.name}->{to_mode.name}"
        w.set_draw_mode(1, DrawMode.LINE)
        w.set_draw_mode(0, from_mode)
        w.set_draw_mode(0, to_mode)
        state["WaveformWidget_2D"]["row_transitions"][k] = {
            "c0": extract_curve(w._curves[0]),
            "c1": extract_curve(w._curves[1])
        }
    w.deleteLater()
    
    # 3. ComplexRIWidget
    w = ComplexRIWidget("z", probe_color)
    w.resize(600, 400)
    w.show()
    w.update_data(complex_data)
    app.processEvents()
    
    state["ComplexRIWidget"] = {}
    state["ComplexRIWidget"]["initial"] = {
        "real": extract_curve(w._real_curve),
        "imag": extract_curve(w._imag_curve)
    }
    
    w.set_draw_mode('Real', DrawMode.DOTS)
    state["ComplexRIWidget"]["real_dots_imag_line"] = {
        "real": extract_curve(w._real_curve),
        "imag": extract_curve(w._imag_curve)
    }
    
    w.set_draw_mode('Imag', DrawMode.BOTH)
    w.set_draw_mode('Real', DrawMode.LINE)
    state["ComplexRIWidget"]["real_line_imag_both"] = {
        "real": extract_curve(w._real_curve),
        "imag": extract_curve(w._imag_curve)
    }
    
    w.set_draw_mode('Real', DrawMode.DOTS)
    w.set_draw_mode('Imag', DrawMode.DOTS)
    state["ComplexRIWidget"]["both_series_dots"] = {
        "real": extract_curve(w._real_curve),
        "imag": extract_curve(w._imag_curve)
    }
    
    state["ComplexRIWidget"]["transitions"] = {"Real": {}, "Imag": {}}
    for series in ['Real', 'Imag']:
        for from_mode, to_mode in ALL_TRANSITIONS:
            k = f"{from_mode.name}->{to_mode.name}"
            curve = w._real_curve if series == 'Real' else w._imag_curve
            w.set_draw_mode(series, from_mode)
            start_state = extract_curve(curve)
            w.set_draw_mode(series, to_mode)
            end_state = extract_curve(curve)
            state["ComplexRIWidget"]["transitions"][series][k] = {"from": start_state, "to": end_state}
            
    w.set_draw_mode('Real', DrawMode.DOTS)
    w.set_draw_mode('Imag', DrawMode.BOTH)
    w.update_data(complex_data * 2)
    state["ComplexRIWidget"]["data_update"] = {
        "real": extract_curve(w._real_curve),
        "imag": extract_curve(w._imag_curve)
    }
    # Reset to DOTS to test correct data
    w.set_draw_mode('Real', DrawMode.DOTS)
    w.update_data(complex_data) # reset data
    state["ComplexRIWidget"]["real_dots_data"] = extract_curve(w._real_curve)
    w.deleteLater()
    
    # 4. ComplexMAWidget
    w = ComplexMAWidget("z", probe_color)
    w.resize(600, 400)
    w.show()
    w.update_data(complex_data)
    app.processEvents()
    
    state["ComplexMAWidget"] = {}
    state["ComplexMAWidget"]["initial"] = {
        "mag": extract_curve(w._mag_curve),
        "phase": extract_curve(w._phase_curve)
    }
    w.set_draw_mode('Log Mag', DrawMode.DOTS)
    state["ComplexMAWidget"]["mag_dots_phase_line"] = {
        "mag": extract_curve(w._mag_curve),
        "phase": extract_curve(w._phase_curve)
    }
    w.set_draw_mode('Log Mag', DrawMode.LINE)
    w.set_draw_mode('Phase', DrawMode.BOTH)
    state["ComplexMAWidget"]["mag_line_phase_both"] = {
        "mag": extract_curve(w._mag_curve),
        "phase": extract_curve(w._phase_curve)
    }
    
    state["ComplexMAWidget"]["transitions"] = {"Log Mag": {}, "Phase": {}}
    for series in ['Log Mag', 'Phase']:
        for from_mode, to_mode in ALL_TRANSITIONS:
            k = f"{from_mode.name}->{to_mode.name}"
            curve = w._mag_curve if series == 'Log Mag' else w._phase_curve
            w.set_draw_mode(series, from_mode)
            start_state = extract_curve(curve)
            w.set_draw_mode(series, to_mode)
            end_state = extract_curve(curve)
            state["ComplexMAWidget"]["transitions"][series][k] = {"from": start_state, "to": end_state}
            
    w.deleteLater()
    
    # 5. Plugins
    def _run_plugin_e2e(plugin_class, series_key):
        plugin = plugin_class()
        w = plugin.create_widget("z", probe_color)
        w.resize(600, 400)
        w.show()
        plugin.update(w, complex_data, DTYPE_ARRAY_COMPLEX)
        app.processEvents()
        
        p_state = {}
        p_state["is_single"] = isinstance(w, SingleCurveWidget)
        p_state["series_keys"] = w.series_keys
        
        p_state["initial"] = extract_curve(w._curve)
        
        w.set_draw_mode(series_key, DrawMode.DOTS)
        p_state["set_dots"] = extract_curve(w._curve)
        
        w.set_draw_mode(series_key, DrawMode.BOTH)
        p_state["set_both"] = extract_curve(w._curve)
        
        p_state["transitions"] = {}
        for from_mode, to_mode in ALL_TRANSITIONS:
            k = f"{from_mode.name}->{to_mode.name}"
            w.set_draw_mode(series_key, from_mode)
            start_state = extract_curve(w._curve)
            w.set_draw_mode(series_key, to_mode)
            end_state = extract_curve(w._curve)
            p_state["transitions"][k] = {"from": start_state, "to": end_state}
            
        w.set_draw_mode(series_key, DrawMode.BOTH)
        plugin.update(w, complex_data * 2, DTYPE_ARRAY_COMPLEX)
        p_state["data_update"] = extract_curve(w._curve)
        w.deleteLater()
        return p_state

    state["LogMagPlugin"] = _run_plugin_e2e(LogMagPlugin, "Magnitude (dB)")
    state["LinearMagPlugin"] = _run_plugin_e2e(LinearMagPlugin, "Magnitude")
    state["PhaseRadPlugin"] = _run_plugin_e2e(PhaseRadPlugin, "Phase (rad)")
    state["PhaseDegPlugin"] = _run_plugin_e2e(PhaseDegPlugin, "Phase (deg)")
    
    # 6. WaveformPlugin full pipeline
    plugin = WaveformPlugin()
    w = plugin.create_widget("sig", probe_color)
    w.resize(600, 400)
    w.show()
    plugin.update(w, real_data, DTYPE_ARRAY_1D)
    app.processEvents()
    
    state["WaveformPlugin"] = {}
    state["WaveformPlugin"]["initial"] = extract_curve(w._curves[0])
    
    state["WaveformPlugin"]["each_mode"] = {}
    for mode in list(DrawMode):
        w.set_draw_mode(0, mode)
        state["WaveformPlugin"]["each_mode"][mode.name] = extract_curve(w._curves[0])
        
    state["WaveformPlugin"]["round_trip"] = {}
    for mode in [DrawMode.LINE, DrawMode.DOTS, DrawMode.BOTH, DrawMode.LINE]:
        w.set_draw_mode(0, mode)
        m_name = mode.name
        state["WaveformPlugin"]["round_trip"]["current_" + m_name] = {
            "curve": extract_curve(w._curves[0]),
            "mode": w.get_draw_mode(0).name
        }
        
    w.set_draw_mode(0, DrawMode.DOTS)
    plugin.update(w, real_data * 3, DTYPE_ARRAY_1D)
    state["WaveformPlugin"]["plugin_update"] = extract_curve(w._curves[0])
    w.deleteLater()
    
    # 7. ComplexRIPlugin full pipeline
    plugin = ComplexRIPlugin()
    w = plugin.create_widget("iq", probe_color)
    w.resize(600, 400)
    w.show()
    plugin.update(w, complex_data, DTYPE_ARRAY_COMPLEX)
    app.processEvents()
    
    state["ComplexRIPlugin"] = {}
    state["ComplexRIPlugin"]["initial"] = {
        "real": extract_curve(w._real_curve),
        "imag": extract_curve(w._imag_curve)
    }
    
    w.set_draw_mode('Real', DrawMode.BOTH)
    w.set_draw_mode('Imag', DrawMode.DOTS)
    state["ComplexRIPlugin"]["mixed"] = {
        "real": extract_curve(w._real_curve),
        "imag": extract_curve(w._imag_curve)
    }
    
    w.set_draw_mode('Real', DrawMode.DOTS)
    plugin.update(w, complex_data * 0.5, DTYPE_ARRAY_COMPLEX)
    state["ComplexRIPlugin"]["plugin_update"] = extract_curve(w._real_curve)
    w.deleteLater()
    
    # 8. ComplexMAPlugin full pipeline
    plugin = ComplexMAPlugin()
    w = plugin.create_widget("iq", probe_color)
    w.resize(600, 400)
    w.show()
    plugin.update(w, complex_data, DTYPE_ARRAY_COMPLEX)
    app.processEvents()
    
    state["ComplexMAPlugin"] = {}
    state["ComplexMAPlugin"]["initial"] = {
        "mag": extract_curve(w._mag_curve),
        "phase": extract_curve(w._phase_curve)
    }
    
    w.set_draw_mode('Log Mag', DrawMode.DOTS)
    w.set_draw_mode('Phase', DrawMode.BOTH)
    state["ComplexMAPlugin"]["mixed"] = {
        "mag": extract_curve(w._mag_curve),
        "phase": extract_curve(w._phase_curve)
    }
    
    w.set_draw_mode('Phase', DrawMode.DOTS)
    plugin.update(w, complex_data * 2, DTYPE_ARRAY_COMPLEX)
    state["ComplexMAPlugin"]["plugin_update"] = extract_curve(w._phase_curve)
    w.deleteLater()
    
    out = {
        "sums": {
            "real_data": real_data_sum,
            "real_data_x2": real_data_x2_sum,
            "real_data_x3": real_data_x3_sum,
            "complex_real": complex_data_real_sum,
            "complex_x05_real": complex_data_x05_real_sum
        },
        "state": state
    }
    
    print(json.dumps(out))
    
    app.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
