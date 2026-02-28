"""
Nomenclature and naming conventions for traces and their components.
"""

def get_trace_components(trace_id: str, lens_name: str) -> tuple[str, ...]:
    """
    Return the list of component names for a trace given its ID and the lens used.
    
    Examples:
        tr0, Waveform -> (tr0.val,)
        tr1, Real & Imag -> (tr1.real, tr1.imag)
        tr2, Mag & Phase -> (tr2.mag_db, tr2.phase_deg)
    """
    if lens_name == "Real & Imag":
        return (f"{trace_id}.real", f"{trace_id}.imag")
    elif lens_name == "Mag & Phase":
        return (f"{trace_id}.mag_db", f"{trace_id}.phase_deg")
    elif lens_name in ("FFT Mag & Phase", "FFT Mag (dB)"):
        return (f"{trace_id}.fft_mag_db", f"{trace_id}.fft_angle_deg")
    elif lens_name == "Log Mag (dB)":
        return (f"{trace_id}.mag_db",)
    elif lens_name == "Linear Mag":
        return (f"{trace_id}.mag",)
    elif lens_name == "Phase (rad)":
        return (f"{trace_id}.phase_rad",)
    elif lens_name == "Phase (deg)":
        return (f"{trace_id}.phase_deg",)
    else:
        # Default for most plots (Waveform, Constellation, Scalar, etc.)
        return (f"{trace_id}.val",)
