import pytest
from pyprobe.report.nomenclature import get_trace_components

def test_waveform_nomenclature():
    # Waveform lens (real data)
    assert get_trace_components("tr0", "Waveform") == ("tr0.val",)

def test_complex_ri_nomenclature():
    # Real & Imag lens
    assert get_trace_components("tr1", "Real & Imag") == ("tr1.real", "tr1.imag")

def test_complex_ma_nomenclature():
    # Mag & Phase lens
    # Spec says mag_db and phase_deg
    assert get_trace_components("tr2", "Mag & Phase") == ("tr2.mag_db", "tr2.phase_deg")

def test_unknown_lens_nomenclature():
    # Default fallback
    assert get_trace_components("tr3", "UnknownLens") == ("tr3.val",)

def test_constellation_nomenclature():
    # Constellation lens
    assert get_trace_components("tr4", "Constellation") == ("tr4.val",)
