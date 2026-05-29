#!/usr/bin/env bash
# Reproduce all PBCP experiments from scratch.
# Outputs are written to results/figures/ and results/tables/.
# See REPRODUCIBILITY.md for expected values.

set -e

echo "=== PBCP Reproducibility Script ==="
echo "Running all experiments. This may take a few minutes."
echo ""

run_exp() {
    local name="$1"
    local script="$2"
    echo "--- $name ---"
    python "$script"
    echo "Done."
    echo ""
}

run_exp "Exp 0: Simulation Calibration"   experiments/exp0_simulation_calibration.py
run_exp "Exp 1: Pre-Provision Intervention" experiments/exp1_pre_provision.py
run_exp "Exp 2: Runtime Governance"        experiments/exp2_runtime_prevention.py
run_exp "Exp 3: IBD Anomaly Detection"     experiments/exp3_ibd_detection.py
run_exp "Exp 5: System Roll-Up"            experiments/exp5_system_rollup.py
run_exp "Exp 6: Policy Learning"           experiments/exp6_phase3_convergence.py

echo "=== All experiments complete ==="
echo ""
echo "Key results to verify:"
echo "  Exp 0  Utilization MAE  → target 0.054"
echo "  Exp 3  IFS F1           → target 0.7608"
echo "  Exp 6  Peak CPS         → target 0.733"
echo ""
echo "Figures: results/figures/"
echo "Tables:  results/tables/"
