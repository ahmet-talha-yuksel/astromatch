# Target replacement feasibility

The team chooses the targets; NASA did not prescribe this set. Keep Shackleton
(T-02) while evaluating replacements for Marius Hills (T-03) and the three Mars
targets (T-01, T-04, T-05). Do not change aliases or advertise new matches until
the replacement records pass the real-data readiness check.

| Slot | Proposed candidate | Why it fits | Source to investigate |
|---|---|---|---|
| T-03 | Mons Mouton | Artemis south-pole candidate region; different base-site setting from Shackleton. | NASA Artemis III candidate-region list; LOLA counts and south-pole terrain models. |
| T-01 | Gale Crater | Actual Curiosity landing/exploration area with varied crater terrain. | NASA/PDS CTX or HiRISE stereo DTM, with documented footprint and accuracy. |
| T-04 | Gusev Crater | Actual Spirit exploration area and a second crater context. | NASA/PDS stereo DTM or MOLA measured-bin regional product. |
| T-05 | Oxia Planum | Investigated Mars landing region with a different geological setting. | PDS stereo DTM and observation/quality metadata. |

These are **candidates, not approved data replacements**. The available repo
contains no validated feature record for any of them. A regional score requires
the same 50×50 km window, supported analysis resolution, documented coordinate
system and source footprint, source sampling or stereo quality evidence,
`resolution_validated=true`, and at least three non-null terrain features marked
`comparable=true`. Feature definitions and Earth comparison scale must match.
Measured-only versus interpolated sensitivity should be recorded per feature;
failed features remain non-comparable. Rebuild heightmaps and the target alias
table only after `engine.cli check` passes, then rerun all engine exports and
frontend smoke tests.

Selection must be based on mission relevance, coverage, and measurement quality.
It must not be tuned to produce a desired similarity percentage. Raw geometric
scores may still approach 100 when terrain features genuinely match; the
commonality-adjusted score and explanations provide the needed context.

Sources: [NASA Artemis III regions](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/), [NASA Curiosity/Gale](https://mars.nasa.gov/internal_resources/822/), [NASA Spirit/Gusev](https://science.nasa.gov/3d-resources/mars-spirit-landing-site/), [NASA Oxia Planum](https://science.nasa.gov/photojournal/clay-rich-terrain-in-oxia-planum-a-proposed-exomars-landing-site/).
