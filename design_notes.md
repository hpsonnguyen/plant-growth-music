# Design Notes

## The Premise

This piece treats plant growth as a slow score. The rows of the dataset become musical time; the three plant batches become three melodic presences; the measurements become forces that push the music upward, thicken its texture, brighten its register, and pull it toward rest.

The goal is not to make the dataset audible as a spreadsheet. The goal is to let the plants leave a musical trace: a line that grows, opens, blooms, and settles.

## Time

The dataset has `30,000` rows. The piece maps `100` rows to one beat, giving `300` beats total.

At `90 BPM`, that produces a `200 second` data-driven timeline. A final sustained tonic note extends the render to about `202.7 seconds`, giving the piece a clear cadence instead of simply stopping.

## Tonal World

The piece lives in `D Dorian`.

This mode was chosen because it keeps a rooted minor color while allowing a brighter, open fourth-degree harmony. It can sound earthy without becoming dark, and luminous without becoming sentimental.

The main harmonic colors are:

```text
Dm9, G9, Cmaj7, Fmaj7, Am7
```

## Plant Signals As Musical Forces

| Plant Signal | Musical Role |
|---|---|
| `growth_mass` | Note body, melodic direction, phrase weight |
| `leaf_energy` | Register, openness, vertical reach |
| `root_energy` | Tension, grounding, leap pressure |
| `vitality` | Dynamics and expressive intensity |
| `growth_speed` | Rhythmic activity and local motion |

The mapping avoids a naive growth-to-pitch line. Plant growth is often monotonic, and a literal pitch mapping would produce a dull staircase. Instead, pitch is generated as a contour: the data decides how the line moves, how far it reaches, when it leaps, and how strongly it returns.

## The Four-Part Arc

| Section | Bars | Musical Character |
|---|---:|---|
| Germination | `1-16` | Quiet, sparse, tentative |
| Growth | `17-40` | More active, more directional |
| Bloom | `41-60` | Dense, bright, climactic |
| Settling | `61-75` | Thinning texture, return, release |

The form gives the listener a path through the data. Local details remain data-driven, but the whole piece breathes like a single organism.

## The Three Plant Voices

| Batch | Instrument | Role |
|---|---|---|
| `R1` | Marimba | Grounded lower/mid plant melody |
| `R2` | Harp | Mid-register plant melody |
| `R3` | Celesta | Bright upper plant melody |

These are not conventional melody/accompaniment roles. They are three readings of growth, each drawn from a different batch.

## The Accompaniment

The plant melodies are supported by a separate piano-style broken-chord background.

For each active chord, the accompaniment repeats a simple shape:

```text
low chord tone -> middle chord tone -> high chord tone -> middle chord tone
```

The accompaniment is intentionally softer than the plant melody. It is not another lead voice. It is the harmonic weather around the plants.

When a chord repeats, the pattern changes slightly. During bloom, if vitality or growth speed crosses the climax threshold, the accompaniment accelerates and brightens. The result is a texture that moves continuously without sounding mechanically looped.

## Resolution

The piece ends with a sustained `D3`, the tonic of the scale. It is a small but important gesture: the data stops, but the music resolves.

## What The Listener Should Hear

The beginning should feel like a field before sunrise: sparse, low, half-awake.

The middle should feel increasingly animated, as if the plant measurements have become musical pressure.

The bloom should feel like the texture opening all at once: denser accompaniment, stronger dynamics, brighter register.

The ending should thin out and return to the root, leaving a final trace of D.
