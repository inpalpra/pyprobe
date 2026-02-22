"""Smoke tests that verify the installed package contains all expected resources."""

import os
import importlib


def test_icon_svgs_present():
    """All toolbar icon SVGs must be shipped in the wheel."""
    import pyprobe.gui.plot_toolbar as tb

    icon_dir = os.path.join(os.path.dirname(tb.__file__), "icons")
    assert os.path.isdir(icon_dir), f"Icon directory missing: {icon_dir}"

    expected = {
        "icon_pointer.svg",
        "icon_pan.svg",
        "icon_zoom.svg",
        "icon_zoom_x.svg",
        "icon_zoom_y.svg",
        "icon_reset.svg",
        "icon_lock_x.svg",
        "icon_lock_y.svg",
    }
    found = set(os.listdir(icon_dir))
    missing = expected - found
    assert not missing, f"Missing icon files: {missing}"


def test_all_subpackages_importable():
    """Every pyprobe subpackage must be importable."""
    subpackages = [
        "pyprobe",
        "pyprobe.core",
        "pyprobe.gui",
        "pyprobe.plots",
        "pyprobe.plugins",
        "pyprobe.analysis",
        "pyprobe.ipc",
    ]
    for pkg in subpackages:
        importlib.import_module(pkg)
