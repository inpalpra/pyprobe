# TO MY PAST SELF: A WARNING FROM THE FUTURE

Do not ignore this. I am you, writing from a timeline where you burned hours upon hours staring at empty traces and debugging layout geometry that was perfectly fine. I have chronicled the exact traps you are about to walk into while implementing the "FFT Mag (dB)" lens for PyProbe. 

Learn from my misery. Do not tread the paths I have already suffered.

## WARNING 1: The UI lies. Always check the Plugin Name Collisions!
**The Nightmare:** You will see the UI Lens Dropdown confidently state "FFT Mag (dB)". But beneath it, a Constellation scatter plot will mock you. You will think it's a layout caching bug. You will trace `_on_lens_changed` UI swaps. You will question your sanity.
**The Truth:** The UI is lying. You are going to name both `ComplexFftMagPlugin` and `WaveformFftMagPlugin` with the exact same `name = "FFT Mag (dB)"` in the registry.
- `PluginRegistry.get_plugin_by_name(name)` only checks strings, and it's going to blindly hand you the Waveform plugin every single time.
- When the complex data hits it, it will fail silently due to `can_handle=False`.
- PyProbe's fallback logic will quietly leave the Constellation widget active while the UI dropdown continues telling you the FFT lens is selected!
**Your Deliverance:** Change the `PluginRegistry` immediately. Make `get_plugin_by_name(name, dtype)` require the data type to disambiguate identical names. Otherwise, you'll be debugging ghosts.

## WARNING 2: PyQtGraph AutoRange Will Eat Your Widget
**The Nightmare:** You will successfully inject the new `PlotWidget` into the layout. But halfway through testing, the FFT line will completely vanish into a white void.
**The Truth:** Race conditions. You're triggering `autoRange(padding=0)` the precise microsecond the first dataframe arrives. At this exact moment, Qt is still arguing with the layout engine about the grid size. The widget's dimensions are mathematically `0x0`. PyQtGraph will permanently cache this `(0, 0, 0, 0)` bounding box and destroy your viewport visibility.
**Your Deliverance:** Add a delay. Use `QTimer.singleShot(50, self.reset_view)` when initializing `_first_data`. Give Qt 50 milliseconds to breathe and solve the layout topology before forcing an AutoRange.

## WARNING 3: Your print() statements are screaming into the void
**The Nightmare:** You will sprinkle `print()` debug traces everywhere in `set_data()` to track array dimensions. You will run the tests. You will see nothing. You will question if your code is even executing.
**The Truth:** You are running PyProbe under `--auto-quit`. Everything on `sys.stdout` is being violently intercepted by the JSON IPC transport wrapper connecting the runner and PyProbe. 
**Your Deliverance:** Use `sys.stderr`. You must print your debug traces with `print(..., file=sys.stderr)`, or standard `logger` warnings. Otherwise, your logs are just becoming invisible IPC noise.

## WARNING 4: Mathematical correctness is not visual aesthetics
**The Nightmare:** You will get the FFT correctly calculated and windowed. But the physical plot will look incredibly blocky—a jagged, terrible line that feels amateurish.
**The Truth:** You ran a 500-sample raw FFT. Without interpolation, those bins are massive. 
**Your Deliverance:** Zero-Pad aggressively. Force your resolution up with `nfft = max(8192, 2**int(np.ceil(np.log2(n))))`. Padding to a minimum of 8,192 points interpolates the spectrum cleanly, rendering the buttery-smooth peaks users expect from an oscilloscope.

## WARNING 5: You must shift, or you will suffer
**The Nightmare:** Your FFT plot will look bizarre, with a single aggressive horizontal line drawing across the entire plot connecting the far right to the far left.
**The Truth:** FFT output is discontinuous (from $0$ to positive Nyquist, then jumping to negative Nyquist back to $-1$). Plotting it linearly as-is creates physical wraparound artifacts.
**Your Deliverance:** Suffer not the wraparound! Always apply `np.fft.fftshift()`. Your X-axes must also shift symmetrically: 
- Use sequence bins: `np.arange(-nfft//2, nfft - nfft//2)`
- Use physical bins tracking `dt`: `np.fft.fftshift(np.fft.fftfreq(nfft, d=dt))`

## WARNING 6: QTimer.singleShot(0, ...) is a trap for your data
**The Nightmare:** You will see the correct Frame 1 data arrive in your logs. You will see it rendered. Then, a fraction of a second later, the plot will revert to Frame 0. You will suspect an IPC reversal. You will hunt for non-existent queue bugs.
**The Truth:** You used a `singleShot(0, ...)` to "defer" a data update during a lens change. But while that timer was waiting in the queue, Frame 1 arrived and was processed *synchronously*. The timer then fired, blindly overwriting your fresh Frame 1 data with the stale Frame 0 values it had captured in its closure.
**Your Deliverance:** Avoid deferred updates for data application. If you must recreate a widget, apply the data *synchronously* immediately after creation. Timers are for layout, not for state.

## WARNING 7: CI is a cold, heartless place
**The Nightmare:** Your tests pass 100/100 times on your Mac. You push to CI. It fails immediately. You run it again. It fails again. You will blame the Ubuntu runner's performance.
**The Truth:** Headless environments (Xvfb) and different OS event loops expose race conditions that your local machine hides with its faster GPU or different thread priority. If it fails in CI, it's a real bug, not a "CI flake."
**Your Deliverance:** Use targeted CI workflows. Don't wait for the full suite. Modify `test-only.yml` to run just the failing test. Capture everything to `stderr`. If you can't see the bug, your diagnostics aren't loud enough.

## THE GOLDEN RULE OF THIS TIMELINE:
**Never assume the widget being displayed is the widget you just wrote.** 
If it doesn't render, look at your `stderr` traces. Is `set_data` firing? No? Then the system has silently rejected your plugin using fallback logic, making your python logic bugs look like layout engine crashes. Follow the registry. 

Godspeed. Save yourself the hours I lost.
