TLB results HTML dashboard / GitHub Pages site
==============================================

Data inputs
-----------

The dashboard consumes experiment data only from the compact tlbsim archive:

  ../tlbsim2/archive/hosam.morad/common_smt_workloads.py
  ../tlbsim2/archive/hosam.morad/linear_models/smt/coefficients.csv
  ../tlbsim2/archive/hosam.morad/linear_models/smt/training_data.csv
  ../tlbsim2/archive/hosam.morad/results/smt/shared/lru/all_workloads.csv
  ../tlbsim2/archive/hosam.morad/results/smt/uniform_ownership/lru/pi_5ms_dw3_oi10p/all_workloads.csv

The uniform result CSV contains:

  benchmark,mpki,cpi,stlb_shared_percent,stlb_thread1_only_percent,stlb_thread2_only_percent

The dashboard does not read raw simulations, mode_selection.log, weights, or
analysis/windowed_uniform_speedup/speedup.csv.

Benchmark display names are static presentation metadata kept in
  generator/benchmark_names.py
so the dashboard has no non-archive tlbsim file dependency.

Generate
--------

From the tlb-results repository run:

  make

Before rendering, make asks tlbsim to refresh the compact simulation archive:

  make -C ../tlbsim2 archive/hosam.morad/results/smt

The publishable website is generated directly in the tlb-results repository:

  index.html
  style.css
  results.json
  .nojekyll
  figures/*.svg
  figures/*.pdf

The HTML embeds the SVG figures. Clicking a figure opens its PDF version.

Simulation MPKI/CPI
-------------------

MPKI and CPI are read directly from the archived shared and uniform
all_workloads.csv files.

Directional mosmodel
--------------------

For workload A+B:

  A uses the A+B mosmodel.
  B uses the B+A mosmodel.

For each focal benchmark:

  speedup = (CPI_shared / CPI_uniform - 1) * 100

Uniform STLB state percentages
------------------------------

The archive stores pair-level percentages of the active modes:

  stlb_shared_percent
  stlb_thread1_only_percent
  stlb_thread2_only_percent

The dashboard maps them directionally:

  focal is thread1: Focal-only=Thread1Only, Co-runner-only=Thread2Only
  focal is thread2: Focal-only=Thread2Only, Co-runner-only=Thread1Only

Clean generated output with:

  make tlb-results/clean
