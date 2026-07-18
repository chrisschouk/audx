# Pattern Language

## Goal

Terse, composable, live-patchable. No PhD required.

## Examples

```
kick 4/4                  # four-on-the-floor kick drum
hh 12x8                   # 12 evenly-spaced hi-hats across the bar
snare 2/8                 # snare on beats 2 and 4 (backbeat)
bass e(5,16) | tune -7st  # euclidean bassline, pitched down 7 semitones
```

`NxM` places **N** evenly-spaced hits across the bar (the count is the first
number). See the modifier and base-rhythm reference in the
[README](../README.md#pattern-dsl).
