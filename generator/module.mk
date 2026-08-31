##### TLB results dashboard / GitHub Pages site
smt_results_html_dir := generator
smt_results_html_site_dir := .
smt_results_html_json := results.json
smt_results_html_html := index.html

##### tlbsim archive inputs
smt_results_html_tlbsim_root ?= ../tlbsim2
smt_results_html_archive_root ?= $(smt_results_html_tlbsim_root)/archive/hosam.morad
smt_results_html_workloads_script ?= \
	$(smt_results_html_archive_root)/common_smt_workloads.py

smt_results_html_baseline_results ?= \
	$(smt_results_html_archive_root)/results/smt/shared/lru/all_workloads.csv

smt_results_html_wptlb_results ?= \
	$(smt_results_html_archive_root)/results/smt/uniform_ownership/lru/pi_5ms_dw3_oi10p/all_workloads.csv

smt_results_html_coefficients_csv ?= \
	$(smt_results_html_archive_root)/linear_models/smt/coefficients.csv

smt_results_html_training_data_csv ?= \
	$(smt_results_html_archive_root)/linear_models/smt/training_data.csv

##### targets
.PHONY: tlb-results tlb-results/archive tlb-results/clean smt_results_html_force

tlb-results: $(smt_results_html_html)

# tlbsim owns raw simulation -> archive conversion. The dashboard only asks
# tlbsim to refresh that compact archive before reading it.
tlb-results/archive:
	$(MAKE) -C "$(smt_results_html_tlbsim_root)" archive/hosam.morad/results/smt

smt_results_html_force:

$(smt_results_html_json): \
	smt_results_html_force \
	tlb-results/archive \
	$(smt_results_html_dir)/collect.py \
	$(smt_results_html_dir)/archive_results.py \
	$(smt_results_html_dir)/benchmark_names.py \
	$(smt_results_html_dir)/mosmodel.py
	$(PYTHON) $(smt_results_html_dir)/collect.py \
		--baseline-results "$(smt_results_html_baseline_results)" \
		--wptlb-results "$(smt_results_html_wptlb_results)" \
		--coefficients-csv "$(smt_results_html_coefficients_csv)" \
		--training-data-csv "$(smt_results_html_training_data_csv)" \
		--archive-root "$(smt_results_html_archive_root)" \
		--workloads-script "$(smt_results_html_workloads_script)" \
		--output "$@"

$(smt_results_html_html): \
	$(smt_results_html_json) \
	$(smt_results_html_dir)/render.py \
	$(smt_results_html_dir)/plots.py \
	$(smt_results_html_dir)/template.html \
	$(smt_results_html_dir)/style.css
	$(PYTHON) $(smt_results_html_dir)/render.py \
		--input "$(smt_results_html_json)" \
		--output "$@" \
		--figures-dir "figures"

tlb-results/clean:
	rm -rf results.json index.html style.css .nojekyll figures
