Lets get back to @filter-nonprobeable-symbols.md 

The side-effect of your fix is that now I can't probe arguments passed to functions, even if they are probe-able. Create a plan to fix this in the @filter-nonprobeable-symbols.md .

You asked "Should we allow probing function calls like `np.sin(...)` for their return value?"

Answer is yes. Anything that can be a reasonable candidate to be plotted, should be allowed to be probed. Perhaps all symbols should be allowed to be probed, just that the kind of probe need not always be a graph. 

In the future, we should add a way to probe scalar values by plotting their current and past values in a graph. Over multiple runs, this could be used to see how the value changes. 

For now, lets allow probing everything, but display "Nothing to show" in the probe panel if the symbol is not probeable.

In future, we could create custom probes for different types of symbols. For example, we could have a probe for function calls that displays the return value of the function, and a probe for module references that displays the module name etc.