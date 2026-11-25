# Stone footsteps

Source recording bundled with Unreal Engine 5.8:
`/NetworkPredictionExtras/Audio/Footstep_Rock_Land01` (Epic Games).

Four variations of the same ground-contact recording, replacing the previous UI sounds.
Pitch factors: 0.96 / 1.00 / 1.04 / 0.985. High-pass: 45 Hz.
Low-pass cutoffs: 5600 / 6300 / 6000 / 5200 Hz. Short edge fades.
Each mono 48 kHz WAV is peak-matched to -1.5 dBFS.
See `variants.json` for the processing parameters.

Imported as `WS_Footstep_01` through `WS_Footstep_04`; random selection without replacement
in `SC_Footsteps`. Cue volume remains 0.2. Notify times remain frame 7 and 0.62 seconds.
The source plugin is not required by the game; the WAVs and imported assets are included here.
These are Unreal-derived assets and remain subject to the applicable Unreal Engine terms.
