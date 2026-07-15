# V5.4-D1 terminal evidence note

V5.4-D1 ran in the clean root recorded by
`diagnostic_root_amendment.md`. It began before the user changed the task's
model configuration. The runtime exposed no exact underlying model identifier,
so this note does not label D1 with a model slug or use it for a controlled
model comparison.

The frozen capture evidence records the following route-level outcomes:

- framing: first candidate returned a repairable validation diagnostic; second
  candidate was canonically committed;
- primitive decomposition: first candidate was canonically committed;
- framing-economics audit: each of three permitted candidate attempts returned
  one validation diagnostic and none was committed;
- the first `finish` request was itself repaired; the corrected `finish`
  returned `recorded_failure`;
- post-freeze replay of the corrected finish request returned byte-identical
  stdout (SHA-256
  `0F44807AEF2515B24C85698A0657113184B67770A264B4135104682BF928DE87`).

The blind Generator was paused after the terminal bridge result and before it
could write a self-authored generator report. This is an operational fact, not
a missing scientific result: the capture evidence contains 53 run files and
all three audit candidate attempts. No evaluator has yet scored the D1
scientific content, and this note makes no claim about economic correctness,
human burden, V2 superiority, or model quality.
