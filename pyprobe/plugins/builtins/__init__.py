"""Builtin visualization plugins."""
from typing import List
from ..base import ProbePlugin


def get_builtin_plugins() -> List[ProbePlugin]:
    """Return all builtin plugin instances.
    
    Each plugin is instantiated once and reused.
    Order doesn't matter - priority determines default selection.
    """
    from .waveform import WaveformPlugin, WaveformFftMagAnglePlugin
    from .constellation import ConstellationPlugin
    from .complex_plots import (
        ComplexRIPlugin, ComplexMAPlugin, 
        LogMagPlugin, LinearMagPlugin, 
        PhaseRadPlugin, PhaseDegPlugin,
        ComplexFftMagAnglePlugin
    )
    from .scalar_history import ScalarHistoryPlugin
    from .scalar_display import ScalarDisplayPlugin
    
    return [
        WaveformPlugin(),
        WaveformFftMagAnglePlugin(),
        ConstellationPlugin(),
        ComplexRIPlugin(),
        ComplexMAPlugin(),
        LogMagPlugin(),
        LinearMagPlugin(),
        PhaseRadPlugin(),
        PhaseDegPlugin(),
        ComplexFftMagAnglePlugin(),
        ScalarHistoryPlugin(),
        ScalarDisplayPlugin(),
    ]
