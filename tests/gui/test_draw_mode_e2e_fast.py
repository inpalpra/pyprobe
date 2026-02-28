"""
Fast E2E GUI tests for Draw Mode.
Uses the Megascript pattern to avoid spawning Qt and creating widgets per-test.
All actual Qt instantiation happens once in `draw_mode_megascript.py`.
"""

import pytest
import os
import sys
import subprocess
import json
import math

def _assert_mode_data(curve_dict, mode_str):
    if mode_str == "LINE":
        assert curve_dict["has_pen"] is True
        assert curve_dict["has_symbol"] is False
    elif mode_str == "DOTS":
        assert curve_dict["has_pen"] is False
        assert curve_dict["has_symbol"] is True
        assert curve_dict["symbol"] == "s"
    elif mode_str == "BOTH":
        assert curve_dict["has_pen"] is True
        assert curve_dict["has_symbol"] is True
        assert curve_dict["symbol"] == "s"

ALL_TRANSITIONS = [
    ("LINE", "DOTS"),
    ("LINE", "BOTH"),
    ("DOTS", "LINE"),
    ("DOTS", "BOTH"),
    ("BOTH", "LINE"),
    ("BOTH", "DOTS"),
]

def assert_isclose(a, b, rel_tol=1e-6):
    assert math.isclose(a, b, rel_tol=rel_tol), f"{a} not close to {b}"

@pytest.fixture(scope="session")
def e2e_data():
    script_path = os.path.join(os.path.dirname(__file__), "data", "draw_mode_megascript.py")
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# 1. WaveformWidget — real 1D data
# ---------------------------------------------------------------------------
class TestWaveformE2E:
    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"]["WaveformWidget_1D"]

    @pytest.fixture
    def sums(self, e2e_data):
        return e2e_data["sums"]

    def test_initial_line(self, state):
        cur = state["initial"]
        _assert_mode_data(cur, "LINE")
        assert cur["has_data"]

    def test_set_dots(self, state):
        _assert_mode_data(state["set_dots"], "DOTS")

    def test_set_both(self, state):
        _assert_mode_data(state["set_both"], "BOTH")

    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS)
    def test_transitions(self, state, from_mode, to_mode):
        trans = state["transitions"][f"{from_mode}->{to_mode}"]
        _assert_mode_data(trans["from"], from_mode)
        _assert_mode_data(trans["to"], to_mode)

    def test_data_update_preserves_mode(self, state):
        cur = state["data_update"]
        _assert_mode_data(cur, "DOTS")
        assert cur["mode"] == "DOTS"

    def test_data_correct_after_mode_change(self, state, sums):
        assert_isclose(state["data_update"]["y_sum"], sums["real_data_x2"])

# ---------------------------------------------------------------------------
# 2. WaveformWidget — 2D multi-row data
# ---------------------------------------------------------------------------
class TestWaveform2DE2E:
    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"]["WaveformWidget_2D"]

    def test_two_curves_exist(self, state):
        assert state["num_curves"] == 2

    def test_independent_modes(self, state):
        cur = state["independent_modes"]
        _assert_mode_data(cur["c0"], "DOTS")
        _assert_mode_data(cur["c1"], "LINE")

    def test_all_modes_per_row(self, state):
        cur = state["all_modes_per_row"]
        _assert_mode_data(cur["c0"], "BOTH")
        _assert_mode_data(cur["c1"], "DOTS")

    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS)
    def test_row_transitions(self, state, from_mode, to_mode):
        trans = state["row_transitions"][f"{from_mode}->{to_mode}"]
        _assert_mode_data(trans["c0"], to_mode)
        _assert_mode_data(trans["c1"], "LINE")


# ---------------------------------------------------------------------------
# 3. ComplexRIWidget — Real & Imaginary
# ---------------------------------------------------------------------------
class TestComplexRIE2E:
    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"]["ComplexRIWidget"]

    @pytest.fixture
    def sums(self, e2e_data):
        return e2e_data["sums"]

    def test_initial_line(self, state):
        _assert_mode_data(state["initial"]["real"], "LINE")
        _assert_mode_data(state["initial"]["imag"], "LINE")

    def test_real_dots_imag_line(self, state):
        _assert_mode_data(state["real_dots_imag_line"]["real"], "DOTS")
        _assert_mode_data(state["real_dots_imag_line"]["imag"], "LINE")

    def test_real_line_imag_both(self, state):
        _assert_mode_data(state["real_line_imag_both"]["real"], "LINE")
        _assert_mode_data(state["real_line_imag_both"]["imag"], "BOTH")

    def test_both_series_dots(self, state):
        _assert_mode_data(state["both_series_dots"]["real"], "DOTS")
        _assert_mode_data(state["both_series_dots"]["imag"], "DOTS")

    @pytest.mark.parametrize("series", ['Real', 'Imag'])
    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS)
    def test_all_transitions(self, state, series, from_mode, to_mode):
        trans = state["transitions"][series][f"{from_mode}->{to_mode}"]
        _assert_mode_data(trans["from"], from_mode)
        _assert_mode_data(trans["to"], to_mode)

    def test_data_update_preserves_mode(self, state):
        _assert_mode_data(state["data_update"]["real"], "DOTS")
        _assert_mode_data(state["data_update"]["imag"], "BOTH")

    def test_data_correct_after_mode_change(self, state, sums):
        assert_isclose(state["real_dots_data"]["y_sum"], sums["complex_real"])


# ---------------------------------------------------------------------------
# 4. ComplexMAWidget — Magnitude & Phase (dual axis)
# ---------------------------------------------------------------------------
class TestComplexMAE2E:
    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"]["ComplexMAWidget"]

    def test_initial_line(self, state):
        _assert_mode_data(state["initial"]["mag"], "LINE")
        _assert_mode_data(state["initial"]["phase"], "LINE")

    def test_mag_dots_phase_line(self, state):
        _assert_mode_data(state["mag_dots_phase_line"]["mag"], "DOTS")
        _assert_mode_data(state["mag_dots_phase_line"]["phase"], "LINE")

    def test_mag_line_phase_both(self, state):
        _assert_mode_data(state["mag_line_phase_both"]["mag"], "LINE")
        _assert_mode_data(state["mag_line_phase_both"]["phase"], "BOTH")

    @pytest.mark.parametrize("series", ['Log Mag', 'Phase'])
    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS)
    def test_all_transitions(self, state, series, from_mode, to_mode):
        trans = state["transitions"][series][f"{from_mode}->{to_mode}"]
        _assert_mode_data(trans["from"], from_mode)
        _assert_mode_data(trans["to"], to_mode)

    def test_phase_curve_is_plotdataitem(self, state):
        assert state["initial"]["phase"]["is_plotdataitem"]


# ---------------------------------------------------------------------------
# 5. Plugin-level E2E — LogMag, LinearMag, PhaseRad, PhaseDeg
# ---------------------------------------------------------------------------
class _SingleCurvePluginMixin:
    PLUGIN_KEY = None
    SERIES_KEY = None

    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"][self.PLUGIN_KEY]

    def test_is_single_curve(self, state):
        assert state["is_single"]
        assert len(state["series_keys"]) == 1
        assert state["series_keys"][0] == self.SERIES_KEY

    def test_initial_line(self, state):
        _assert_mode_data(state["initial"], "LINE")

    def test_set_dots(self, state):
        _assert_mode_data(state["set_dots"], "DOTS")

    def test_set_both(self, state):
        _assert_mode_data(state["set_both"], "BOTH")

    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS)
    def test_transitions(self, state, from_mode, to_mode):
        trans = state["transitions"][f"{from_mode}->{to_mode}"]
        _assert_mode_data(trans["from"], from_mode)
        _assert_mode_data(trans["to"], to_mode)

    def test_data_update_preserves_mode(self, state):
        _assert_mode_data(state["data_update"], "BOTH")

    def test_data_on_curve(self, state):
        assert state["initial"]["has_data"]

class TestLogMagE2E(_SingleCurvePluginMixin):
    PLUGIN_KEY = "LogMagPlugin"
    SERIES_KEY = "Magnitude (dB)"

class TestLinearMagE2E(_SingleCurvePluginMixin):
    PLUGIN_KEY = "LinearMagPlugin"
    SERIES_KEY = "Magnitude"

class TestPhaseRadE2E(_SingleCurvePluginMixin):
    PLUGIN_KEY = "PhaseRadPlugin"
    SERIES_KEY = "Phase (rad)"

class TestPhaseDegE2E(_SingleCurvePluginMixin):
    PLUGIN_KEY = "PhaseDegPlugin"
    SERIES_KEY = "Phase (deg)"


# ---------------------------------------------------------------------------
# 6. WaveformPlugin full pipeline
# ---------------------------------------------------------------------------
class TestWaveformPluginE2E:
    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"]["WaveformPlugin"]
    
    @pytest.fixture
    def sums(self, e2e_data):
        return e2e_data["sums"]

    def test_initial_line(self, state):
        _assert_mode_data(state["initial"], "LINE")

    @pytest.mark.parametrize("mode", ["LINE", "DOTS", "BOTH"])
    def test_each_mode(self, state, mode):
        _assert_mode_data(state["each_mode"][mode], mode)

    def test_round_trip(self, state):
        for mode in ["LINE", "DOTS", "BOTH"]:
            item = state["round_trip"]["current_" + mode]
            _assert_mode_data(item["curve"], mode)
            assert item["mode"] == mode

    def test_plugin_update_after_mode_change(self, state, sums):
        _assert_mode_data(state["plugin_update"], "DOTS")
        assert_isclose(state["plugin_update"]["y_sum"], sums["real_data_x3"])


# ---------------------------------------------------------------------------
# 7. ComplexRIPlugin full pipeline
# ---------------------------------------------------------------------------
class TestComplexRIPluginE2E:
    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"]["ComplexRIPlugin"]

    def test_initial_line(self, state):
        _assert_mode_data(state["initial"]["real"], "LINE")
        _assert_mode_data(state["initial"]["imag"], "LINE")

    def test_mixed_modes(self, state):
        _assert_mode_data(state["mixed"]["real"], "BOTH")
        _assert_mode_data(state["mixed"]["imag"], "DOTS")

    def test_plugin_update_preserves(self, state):
        _assert_mode_data(state["plugin_update"], "DOTS")


# ---------------------------------------------------------------------------
# 8. ComplexMAPlugin full pipeline
# ---------------------------------------------------------------------------
class TestComplexMAPluginE2E:
    @pytest.fixture
    def state(self, e2e_data):
        return e2e_data["state"]["ComplexMAPlugin"]

    def test_initial_line(self, state):
        _assert_mode_data(state["initial"]["mag"], "LINE")
        _assert_mode_data(state["initial"]["phase"], "LINE")

    def test_mixed_modes(self, state):
        _assert_mode_data(state["mixed"]["mag"], "DOTS")
        _assert_mode_data(state["mixed"]["phase"], "BOTH")

    def test_plugin_update_preserves(self, state):
        _assert_mode_data(state["plugin_update"], "DOTS")
