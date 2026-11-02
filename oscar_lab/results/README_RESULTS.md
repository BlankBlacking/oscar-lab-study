# results/ notes

- Simulation is deterministic: `cfg_seed` does not create independent replicates.
- `e1_phase.csv` / `e2_qtarget.csv` ship **seed=0 only** (`n_unique=1`). Earlier dual-seed dumps were bit-identical across seeds.
