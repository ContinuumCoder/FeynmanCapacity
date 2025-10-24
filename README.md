# FeynmanCapacity: Nonperturbative Computable Bounds for Multi-loop Feynman Integrals

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the official implementation for the paper: **"Nonperturbative computable bounds for multi-loop Feynman integrals from Lorentzian Symanzik geometry"**.

---

### Repository Structure

-   `compare_bounds_visualization.py`: A script to explore and visualize the core concepts of capacity-optimized bounds versus a baseline for a wide range of graph topologies.
-   `generate_paper_figs_1-2_mosaics.py`: The script to reproduce Figures 1 and 2 from the paper, showcasing the capacity optimization for the Double Ladder and Wheel graphs.
-   `benchmark_pysecdec_speedup.py`: The script to reproduce the momentum-dependent bounds and numerical speedup benchmarks shown in Figure 3, using `pySecDec` for numerical integration.
---

### Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ContinuumCoder/FeynmanCapacity.git
    cd FeynmanCapacity
    ```

2.  **Install Python dependencies:**
    The core scripts require standard scientific computing libraries.
    ```bash
    pip install numpy networkx matplotlib scipy
    ```

3.  **Install `pySecDec` (for benchmark script only):**
    The script `benchmark_pysecdec_speedup.py` relies on the `pySecDec` package for numerical evaluation of Feynman integrals. `pySecDec` is a complex package that requires a C++ compiler (like g++) and other system libraries.

    **Please follow the official `pySecDec` installation guide carefully.**
    A typical installation might look like this, but refer to their documentation for details:
    ```bash
    pip install pysecdec
    ```
    You may also need to install dependencies like GSL (GNU Scientific Library) via your system's package manager (e.g., `sudo apt-get install libgsl-dev` on Debian/Ubuntu).

---

### Usage and Reproducing Results

#### Reproducing Figures 1 & 2

To generate the mosaic plots for the Double Ladder and Wheel graphs (Figures 1 & 2 in the paper), run:

```bash
python generate_paper_figs_1-2_mosaics.py
```
This will create a figs/ directory and save the following files inside it:
	•	Double_Ladder_4_rungs_mosaic.png
	•	Wheel_rim=6_D=3.2_mosaic.png
  
#### Reproducing Figure 3 and Performance Benchmarks
To generate the momentum-dependent bounds and timing comparison plot (Figure 3 in the paper), run:
```bash
python benchmark_pysecdec_speedup.py
```
Important Notes:
	•	This script requires pySecDec to be correctly installed.
	•	The first run will be very slow as it needs to:
	1	Compile C++ code for the Feynman integral using pySecDec.
	2	Perform expensive computations for the bounds and reference values.
	•	The script uses a cache/ directory to store results of the bound optimization (t3_cache.json) and reference integral evaluations (ref_cache.json). Subsequent runs will be significantly faster for these parts.
	•	The final output will be saved as momentum_bounds_speedup_2x2_fast.png and momentum_bounds_speedup_2x2_fast.pdf.
#### Exploratory Visualizations
To run the general-purpose visualization script on a wider variety of graphs:
```bash
python compare_bounds_visualization.py
```
This will generate multiple plots for each graph topology (e.g., 2L_Sunrise_D=2_theta_gamma.png, summary_improvement.png, etc.) in the figs/ directory.

#### Citation
If you use this code or the methods from our paper in your research, please cite:
```bash
@article{Zheng2025Feynman,
    author    = {Zheng, Dongzhe},
    title     = {{Nonperturbative computable bounds for multi-loop Feynman integrals from Lorentzian Symanzik geometry}},
    year      = {2025}
}
```

