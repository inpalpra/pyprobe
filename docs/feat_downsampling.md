TITLE
Viewport-Aware Min–Max Downsampling with Pixel-Column Aligned Aggregation

OBJECTIVE
Render dense traces by aggregating samples per screen pixel column within the current viewport, while guaranteeing:
- Exact inclusion of first and last visible samples
- No time-axis distortion or misalignment
- No dropped boundary samples
- No artificial x-values
- Stable ordering

------------------------------------------------------------------------------

HIGH-LEVEL ALGORITHM

INPUTS
- x: 1D strictly monotonic increasing array of sample positions (float or int)
- y: 1D array of sample values (same length as x)
- xmin, xmax: current viewport bounds in data coordinates
- W: integer screen width in pixels (W >= 1)

OUTPUTS
- xd, yd: downsampled arrays for rendering

STEPS

1. Validate inputs
   - len(x) == len(y)
   - x strictly increasing
   - xmin < xmax
   - W >= 1

2. Clip to visible region
   - Identify indices i0, i1 such that:
       x[i0] >= xmin (first visible)
       x[i1] <= xmax (last visible)
   - If no visible samples → return empty arrays
   - Extract:
       xv = x[i0:i1+1]
       yv = y[i0:i1+1]

3. If len(xv) <= W
   - Return xv, yv unchanged (no downsampling)

4. Compute projection scale
   scale = (W - 1) / (xmax - xmin)

5. Map samples to pixel columns
   pixel_index = floor((xv - xmin) * scale)
   Clamp pixel_index into [0, W-1]

6. For each pixel column k in ascending order:
   - Find contiguous block of samples with pixel_index == k
   - If block is empty → skip
   - Within block:
       find index of minimum y
       find index of maximum y
   - Emit:
       if min_index <= max_index:
           append (x[min], y[min])
           append (x[max], y[max])
       else:
           append (x[max], y[max])
           append (x[min], y[min])

7. Boundary enforcement
   - Ensure first emitted sample equals (xv[0], yv[0])
     If not, prepend it.
   - Ensure last emitted sample equals (xv[-1], yv[-1])
     If not, append it.

8. Return xd, yd

------------------------------------------------------------------------------

DETAILED REQUIREMENTS

Functional Requirements

FR1: Viewport Awareness
- Only samples within [xmin, xmax] shall be considered.

FR2: Pixel-Column Alignment
- Aggregation shall be based on projection into screen pixel columns.
- Bucketing must be derived from screen mapping, not uniform index slicing.

FR3: Boundary Preservation
- The first visible sample must appear exactly in output.
- The last visible sample must appear exactly in output.
- No boundary truncation permitted.

FR4: No Artificial X Values
- All output x values must be original sample x values.
- No interpolated or synthetic x positions allowed.

FR5: Monotonic X Order
- xd must be strictly increasing or non-decreasing consistent with input.
- No reordering of time.

FR6: No Time-Warping
- Relative horizontal spacing between samples must reflect original x.
- No rescaling of x beyond viewport projection.

FR7: Deterministic Output
- Same inputs must always produce identical output.
- No dependence on hash ordering or unstable grouping.

FR8: Correct Handling of Small Data
- If visible sample count <= W, return original visible samples unchanged.

FR9: Numerical Stability
- Pixel mapping must clamp indices into [0, W-1].
- No out-of-bounds array access permitted.

FR10: Performance
- Time complexity must be O(N_visible).
- No nested per-pixel full scans.

------------------------------------------------------------------------------

MUST-NOT-HAVE FAILURE MODES

MF1: Dropped Tail Samples
- Last visible sample missing from output.

MF2: Dropped Head Samples
- First visible sample missing from output.

MF3: Synthetic Edge Clamping
- Artificial x= xmin or x= xmax inserted if not real sample.

MF4: Index-Based Chunking
- No use of uniform len(data)//n_chunks partitioning.

MF5: Reordered Min/Max
- Emitting max before min when min occurs first in time.

MF6: Pixel Drift
- Mapping that causes rightmost sample to map outside last pixel.

MF7: Hidden Downsampling
- Downsampling when visible_samples <= W.

MF8: Phase/Time Misalignment
- Any x offset introduced relative to original.

------------------------------------------------------------------------------

ACCEPTANCE CRITERIA

AC1: Boundary Identity
Given any valid input:
- xd[0] == first visible x
- xd[-1] == last visible x

AC2: Subset Guarantee
- Every xd element must exist in original x array.

AC3: Ordering Guarantee
- xd must be sorted ascending exactly as original ordering.

AC4: No Time Compression
For any two consecutive output points i, j:
- Their x difference equals original x difference between those samples.

AC5: Visual Equivalence at Full Resolution
If visible_samples <= W:
- xd == xv
- yd == yv

AC6: Stable Pixel Mapping
Rightmost visible sample must map to pixel W-1 or earlier.
No pixel index >= W allowed.

AC7: Consistent Under Zoom
Zooming into a subrange must produce downsample consistent with that viewport only.
No dependency on off-screen samples.

------------------------------------------------------------------------------

TEST CASES

TC1: Exact Fit
- N = 1000, W = 1000
- Expect no downsampling
- Output identical to visible input

TC2: Large Dense Signal
- N = 1,000,000, W = 1200
- Verify:
    first and last preserved
    output length <= 2W + 2
    monotonic x

TC3: Random Signal Boundary Test
- x = np.arange(8193)
- y = random
- W = 500
- Assert xd[0] == 0
- Assert xd[-1] == 8192

TC4: Ramp Signal
- y = strictly increasing
- Verify:
    first and last preserved
    no artificial extra points beyond expected min/max

TC5: Single Pixel Case
- W = 1
- Output must contain:
    first visible sample
    last visible sample
- Order preserved

TC6: Partial Viewport
- x from 0..9999
- xmin = 2000
- xmax = 3000
- Ensure:
    no samples outside range
    boundaries preserved

TC7: Floating X Values
- x non-integer, e.g., time in seconds
- Ensure mapping stable and no precision-induced boundary loss

TC8: Non-Uniform Sampling
- x irregularly spaced
- Ensure no time warping or reordering

TC9: Degenerate Block
- All samples in one pixel column
- Ensure both min and max emitted in correct order

TC10: Extreme Zoom
- xmin and xmax span only 5 samples
- Ensure no downsampling

------------------------------------------------------------------------------

EDGE CASE ADDENDUM

The following edge behaviors are mandatory and override any ambiguous
interpretation of the core algorithm.

EC1: Single Pixel Width (W = 1)
- All visible samples map to pixel column 0.
- Output must include:
    - First visible sample
    - Last visible sample
    - Min and max within range (if distinct from boundaries)
- Output must remain strictly time-ordered.
- No duplicate identical samples permitted.
- No synthetic x values permitted.

EC2: Very Small Pixel Width (W = 2 or 3)
- Aggregation per pixel column must still follow projection mapping.
- Empty pixel columns must be ignored.
- No artificial pixel buckets may be created.
- Boundary enforcement must still guarantee exact first and last inclusion.

EC3: Visible Samples ≤ W
- No downsampling shall occur.
- Output must equal visible input exactly.
- No min/max duplication allowed.

EC4: Single Visible Sample
- If clipping results in exactly one visible sample:
    - Return that sample only.
    - No duplication.
    - No aggregation.

EC5: First and Last Sample in Same Pixel Column
- If both boundary samples map to same pixel column:
    - Both must still appear in output.
    - Order must remain time-ordered.
    - Boundary enforcement must not reorder samples.

EC6: Flat Signal Within Pixel Column
- If min(y) == max(y) within a pixel column:
    - Emit only one sample for that column (unless boundary enforcement adds distinct samples).
    - No duplicate emission of identical points.

EC7: Floating Point Projection Stability
- Pixel index calculation must clamp results into [0, W-1].
- No sample may map outside this range.
- Rightmost visible sample must never be lost due to floating point rounding.

EC8: Non-Uniform Sampling
- Aggregation must not assume uniform delta-x.
- Pixel assignment must use projection formula only.
- No index-based equal chunk partitioning allowed.

EC9: Extremely Narrow Viewport
- Clipping must use index-based search (e.g., binary search) when feasible.
- Full-array boolean masking over entire dataset is prohibited for large datasets.
- Downsampling must depend only on visible samples.

EC10: Large Visible Region Performance
- Implementation must not scan entire visible region repeatedly per pixel.
- Aggregation must operate in a single forward pass over visible samples.
- Nested per-pixel full scans are prohibited.


END EDGE CASE ADDENDUM

------------------------------------------------------------------------------

DEFINITION OF DONE

DOD1:
All acceptance criteria pass.

DOD2:
All test cases pass without boundary failures.

DOD3:
No use of index-based equal chunk partitioning exists in implementation.

DOD4:
Output arrays contain only original samples.

DOD5:
No regression in rendering correctness under:
- pan
- zoom in
- zoom out

DOD6:
Performance validated at 1M visible samples within acceptable UI latency.

DOD7:
Code review confirms:
- no synthetic endpoints
- no dropped boundary samples
- no artificial x spacing

DOD8:
Behavior consistent across:
- integer x
- float x
- irregular sampling

------------------------------------------------------------------------------

END SPECIFICATION