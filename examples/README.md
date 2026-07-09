# Khnum examples

`showcase/` contains real, committed Khnum output so you can inspect the product
without running anything:

| files | command that made them |
|---|---|
| `khnum_sram_1rw_256x32_be.*` | `python3 -m khnum gen --kind sram_1rw --depth 256 --width 32 --byte-en -o examples/showcase` |
| `khnum_sram_2r1w_64x64.*` | `python3 -m khnum gen --kind sram_2r1w --depth 64 --width 64 -o examples/showcase` |

Run one yourself (needs Verilator):

```bash
cd examples/showcase
verilator --binary --timing -j 2 -Wno-fatal \
  --top khnum_sram_1rw_256x32_be_tb \
  khnum_sram_1rw_256x32_be.v khnum_sram_1rw_256x32_be_tb.v -o sim
./obj_dir/sim        # prints KHNUM_TB_PASS
```
