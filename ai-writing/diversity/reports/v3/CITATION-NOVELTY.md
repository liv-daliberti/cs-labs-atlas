# Citation-based novelty and diversity of lab papers (Experiment A)

Generated 2026-11-06T03:31:51Z by `ai-writing/citnovelty/cn_report.py`; data: OpenAlex bulk snapshot 2026-10-14 (S3, no API credits), 1,561,078 referenced works characterised; sampling factor for n_k = 16. Years 2016-2025 only (owner rule); 2026 is in no table.

## Summary

**Coverage.** 87% of 2016-2021 lab papers have >= 5 references in the snapshot, 63% of 2023-2025 papers (2025: 56%); Uzzi z exists for 81% / 61%; CD1 for 48% / 37% (2023-2024); CD5 only for 2016-2020.
**Rao-Stirling diversity.** Within labs, 2023-2025 against 2016-2021: 0.009 [0.006, 0.011]; the placebo break at 2019 within 2016-2021 gives 0.009 [0.007, 0.011].
**cited-venue entropy.** Within labs, 2023-2025 against 2016-2021: 0.154 [0.132, 0.173]; the placebo break at 2019 within 2016-2021 gives 0.126 [0.110, 0.146].
**Uzzi z p10.** Within labs, 2023-2025 against 2016-2021: -0.282 [-0.453, -0.094]; the placebo break at 2019 within 2016-2021 gives -1.708 [-1.867, -1.596].
**within-lab reference overlap (cosine).** Within labs, 2023-2025 against 2016-2021: -0.006 [-0.008, -0.004]; the placebo break at 2019 within 2016-2021 gives -0.005 [-0.007, -0.003].
**AI dose, within lab x year (2023-2025, per unit of ai_share):** Uzzi z, 10th percentile (low = atypical) -0.849 [-1.652, 0.002]; Uzzi z, median (high = conventional) -0.379 [-0.636, -0.092]; CD1 disruption (low = consolidating when high) 0.001 [-0.000, 0.004]; CD to end-2025 (variable window) 0.002 [0.000, 0.003]; Rao-Stirling (subfields) 0.025 [0.013, 0.036]; cited-venue entropy (bits) 0.093 [0.011, 0.160].
Read with the placebo rows: where the post-period interval does not lie beyond the 2016-2021 placebo spread there is no evidence of an AI-related change.

## 1. Data coverage

Share of lab papers with a usable reference list (>= 5 references in the snapshot) and with each measure, by year (all schools):

| year | papers | refs5 | meta | z | cd1 | cd3 | cd5 | rs | mean_refs |
|---|---|---|---|---|---|---|---|---|---|
| 2016 | 9668 | 88.7 | 88.4 | 81.2 | 46.7 | 69.4 | 74.9 | 88.4 | 33.8 |
| 2017 | 10384 | 86.4 | 86.2 | 79.9 | 47.3 | 68.7 | 73.6 | 86.1 | 34.8 |
| 2018 | 11680 | 85.2 | 84.8 | 77.5 | 45.4 | 64.7 | 69.0 | 84.8 | 34.7 |
| 2019 | 11689 | 86.1 | 85.7 | 80.7 | 50.1 | 68.3 | 72.5 | 85.7 | 38.4 |
| 2020 | 12337 | 87.8 | 87.6 | 83.2 | 52.2 | 69.5 | 73.6 | 87.5 | 41.5 |
| 2021 | 12757 | 88.0 | 87.7 | 83.8 | 46.9 | 66.7 | 1.6 | 87.7 | 45.0 |
| 2022 | 11582 | 75.9 | 75.7 | 72.7 | 42.3 | 60.7 | 0.4 | 75.7 | 45.8 |
| 2023 | 12456 | 71.3 | 71.1 | 68.4 | 39.1 | 0.2 | 0.1 | 71.1 | 46.2 |
| 2024 | 13258 | 62.9 | 62.6 | 60.0 | 34.8 | 0.0 | 0.0 | 62.6 | 45.2 |
| 2025 | 14308 | 55.7 | 55.5 | 53.5 | 0.0 | 0.0 | 0.0 | 55.5 | 41.9 |

(percentages; `refs5` papers with >= 5 listed references; `meta` of those references characterised; `z` Uzzi z defined (>= 10 venue pairs); `cd1/cd3/cd5` disruption defined with a window that fits inside 2025 and >= 3 citing works; `rs` Rao-Stirling defined.) **Reference lists of recent papers are less complete in OpenAlex** (the share with >= 5 references falls after 2021): all trend comparisons below use year fixed effects, but a drop in coverage is a selection risk for the post-2022 years, so every post-period result has a `refs >= 15` robustness row.

## 2. Trends by school, 2016-2025

Mean per paper (95% interval); papers with the measure defined. CD windows: CD1 needs year <= 2024, CD3 <= 2022, CD5 <= 2020 (a window that fits); CD to end-2025 uses every citation up to 2025, so it is comparable only within a year.

### Uzzi z, 10th percentile (low = atypical)

| school | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| all | -5.056 [-5.178, -4.934] | -6.205 [-6.347, -6.063] | -7.758 [-7.920, -7.596] | -6.981 [-7.155, -6.806] | -7.139 [-7.324, -6.954] | -6.038 [-6.188, -5.887] |
| berkeley | -5.702 [-6.099, -5.306] | -7.699 [-8.207, -7.191] | -9.289 [-9.857, -8.721] | -9.765 [-10.546, -8.983] | -8.395 [-9.096, -7.693] | -7.232 [-7.821, -6.644] |
| cmu | -5.776 [-6.077, -5.475] | -7.071 [-7.392, -6.750] | -9.146 [-9.582, -8.710] | -8.150 [-8.610, -7.690] | -9.406 [-9.945, -8.866] | -7.015 [-7.411, -6.619] |
| epfl | -4.370 [-4.706, -4.034] | -4.955 [-5.343, -4.568] | -6.294 [-6.787, -5.802] | -5.854 [-6.330, -5.379] | -6.253 [-6.750, -5.756] | -5.876 [-6.318, -5.434] |
| gatech | -3.874 [-4.150, -3.599] | -4.969 [-5.284, -4.655] | -5.971 [-6.301, -5.640] | -5.676 [-6.047, -5.306] | -5.874 [-6.261, -5.486] | -4.659 [-4.927, -4.391] |
| michigan | -5.290 [-5.729, -4.852] | -5.398 [-5.812, -4.985] | -6.017 [-6.446, -5.588] | -5.722 [-6.226, -5.218] | -6.062 [-6.603, -5.521] | -5.158 [-5.611, -4.706] |
| mit | -5.195 [-5.482, -4.908] | -6.778 [-7.158, -6.398] | -8.785 [-9.240, -8.330] | -7.423 [-7.863, -6.983] | -7.243 [-7.711, -6.775] | -6.464 [-6.886, -6.041] |
| princeton | -5.322 [-5.796, -4.848] | -5.699 [-6.206, -5.192] | -7.370 [-7.938, -6.802] | -6.687 [-7.256, -6.118] | -5.786 [-6.300, -5.272] | -5.839 [-6.454, -5.223] |
| stanford | -5.053 [-5.426, -4.680] | -6.513 [-7.001, -6.024] | -8.763 [-9.229, -8.298] | -7.055 [-7.566, -6.545] | -7.521 [-8.099, -6.944] | -6.604 [-7.066, -6.143] |
| uchicago | -4.745 [-5.537, -3.953] | -5.133 [-5.894, -4.372] | -6.366 [-7.047, -5.685] | -6.259 [-7.015, -5.502] | -7.029 [-8.009, -6.049] | -5.362 [-6.074, -4.651] |

### Uzzi z, median (high = conventional)

| school | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| all | 1.490 [1.437, 1.542] | 1.234 [1.177, 1.292] | 0.985 [0.927, 1.044] | 1.087 [1.030, 1.143] | 1.015 [0.956, 1.075] | 1.208 [1.157, 1.260] |
| berkeley | 1.257 [1.089, 1.425] | 0.789 [0.597, 0.981] | 0.446 [0.242, 0.649] | 0.355 [0.094, 0.615] | 0.587 [0.375, 0.800] | 0.864 [0.667, 1.060] |
| cmu | 1.285 [1.167, 1.403] | 0.939 [0.815, 1.063] | 0.591 [0.445, 0.737] | 0.888 [0.747, 1.028] | 0.392 [0.229, 0.556] | 0.969 [0.846, 1.092] |
| epfl | 1.791 [1.648, 1.934] | 1.745 [1.572, 1.917] | 1.375 [1.182, 1.568] | 1.302 [1.140, 1.465] | 1.346 [1.168, 1.524] | 1.253 [1.099, 1.407] |
| gatech | 1.886 [1.756, 2.016] | 1.676 [1.534, 1.818] | 1.550 [1.420, 1.680] | 1.366 [1.255, 1.477] | 1.360 [1.233, 1.488] | 1.549 [1.447, 1.652] |
| michigan | 1.422 [1.228, 1.617] | 1.322 [1.145, 1.498] | 1.426 [1.273, 1.580] | 1.379 [1.206, 1.553] | 1.166 [0.990, 1.341] | 1.326 [1.157, 1.496] |
| mit | 1.419 [1.282, 1.556] | 0.967 [0.821, 1.113] | 0.525 [0.369, 0.681] | 0.799 [0.655, 0.943] | 0.946 [0.798, 1.094] | 1.007 [0.864, 1.150] |
| princeton | 1.433 [1.217, 1.649] | 1.709 [1.450, 1.968] | 1.455 [1.201, 1.708] | 1.643 [1.406, 1.880] | 1.738 [1.523, 1.954] | 1.702 [1.445, 1.959] |
| stanford | 1.360 [1.208, 1.511] | 1.088 [0.905, 1.271] | 0.675 [0.511, 0.838] | 1.055 [0.894, 1.215] | 0.868 [0.694, 1.043] | 1.072 [0.935, 1.209] |
| uchicago | 1.659 [1.324, 1.995] | 1.501 [1.192, 1.809] | 1.600 [1.320, 1.880] | 1.192 [0.964, 1.419] | 0.984 [0.673, 1.296] | 1.294 [1.033, 1.556] |

### CD1 disruption (low = consolidating when high)

| school | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| all | -0.003 [-0.004, -0.002] | -0.003 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.002, -0.001] | -0.001 [-0.002, -0.001] | - |
| berkeley | -0.002 [-0.006, 0.002] | -0.002 [-0.003, -0.001] | -0.002 [-0.003, -0.001] | -0.002 [-0.002, -0.001] | -0.003 [-0.004, -0.001] | - |
| cmu | -0.003 [-0.004, -0.002] | -0.003 [-0.004, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.001 [-0.002, 0.000] | - |
| epfl | -0.003 [-0.005, -0.002] | -0.003 [-0.004, -0.002] | -0.003 [-0.004, -0.002] | 0.001 [-0.004, 0.006] | -0.002 [-0.003, -0.002] | - |
| gatech | -0.003 [-0.005, -0.002] | -0.003 [-0.004, -0.002] | -0.003 [-0.004, -0.002] | -0.002 [-0.003, -0.002] | -0.001 [-0.002, -0.000] | - |
| michigan | -0.004 [-0.006, -0.002] | -0.003 [-0.004, -0.002] | -0.003 [-0.003, -0.002] | 0.001 [-0.004, 0.005] | -0.002 [-0.004, -0.001] | - |
| mit | -0.002 [-0.005, 0.001] | -0.003 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.002, -0.001] | - |
| princeton | -0.007 [-0.014, -0.001] | -0.006 [-0.010, -0.002] | -0.004 [-0.004, -0.003] | -0.002 [-0.003, -0.002] | -0.002 [-0.003, -0.000] | - |
| stanford | -0.003 [-0.003, -0.002] | -0.003 [-0.004, -0.001] | -0.001 [-0.002, -0.001] | -0.002 [-0.002, -0.001] | -0.001 [-0.001, -0.000] | - |
| uchicago | -0.003 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.003 [-0.004, -0.002] | -0.003 [-0.006, -0.000] | -0.001 [-0.001, -0.000] | - |

### CD3

| school | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| all | -0.003 [-0.003, -0.002] | -0.003 [-0.003, -0.002] | -0.002 [-0.002, -0.002] | -0.002 [-0.002, -0.001] | -0.001 [-0.002, 0.000] | - |
| berkeley | -0.003 [-0.004, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.002, -0.001] | -0.002 [-0.003, -0.001] | - | - |
| cmu | -0.003 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.002, -0.002] | - | - |
| epfl | -0.004 [-0.005, -0.002] | -0.002 [-0.004, -0.001] | -0.003 [-0.003, -0.002] | -0.001 [-0.003, 0.001] | - | - |
| gatech | -0.003 [-0.004, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.001 [-0.002, 0.001] | - | - |
| michigan | -0.002 [-0.005, 0.001] | -0.003 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.000 [-0.003, 0.003] | - | - |
| mit | -0.002 [-0.004, -0.001] | -0.003 [-0.005, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.003, -0.001] | - | - |
| princeton | -0.005 [-0.009, -0.002] | -0.004 [-0.005, -0.002] | -0.003 [-0.004, -0.003] | -0.002 [-0.003, -0.002] | - | - |
| stanford | -0.003 [-0.004, -0.002] | -0.002 [-0.003, -0.001] | -0.001 [-0.002, -0.001] | -0.002 [-0.002, -0.001] | - | - |
| uchicago | -0.003 [-0.004, -0.001] | -0.002 [-0.003, -0.001] | -0.002 [-0.003, -0.002] | -0.003 [-0.005, -0.000] | - | - |

### CD5

| school | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| all | -0.002 [-0.003, -0.002] | -0.002 [-0.003, -0.002] | -0.002 [-0.002, -0.002] | -0.002 [-0.003, -0.001] | - | - |
| berkeley | -0.003 [-0.004, -0.002] | -0.002 [-0.003, -0.001] | -0.001 [-0.002, -0.001] | -0.001 [-0.001, -0.000] | - | - |
| cmu | -0.002 [-0.003, -0.002] | -0.002 [-0.002, -0.001] | -0.002 [-0.002, -0.001] | -0.002 [-0.007, 0.002] | - | - |
| epfl | -0.002 [-0.003, -0.001] | -0.002 [-0.003, -0.001] | -0.002 [-0.003, -0.001] | - | - | - |
| gatech | -0.002 [-0.003, -0.001] | -0.002 [-0.002, -0.001] | -0.002 [-0.002, -0.001] | - | - | - |
| michigan | -0.002 [-0.003, -0.000] | -0.002 [-0.003, -0.002] | -0.002 [-0.002, -0.001] | - | - | - |
| mit | -0.002 [-0.004, -0.001] | -0.003 [-0.005, -0.001] | -0.002 [-0.002, -0.001] | -0.001 [-0.002, -0.000] | - | - |
| princeton | -0.004 [-0.005, -0.002] | -0.003 [-0.004, -0.002] | -0.003 [-0.004, -0.002] | - | - | - |
| stanford | -0.003 [-0.003, -0.002] | -0.002 [-0.003, -0.001] | -0.001 [-0.002, -0.001] | -0.005 [-0.009, -0.000] | - | - |
| uchicago | -0.002 [-0.003, -0.001] | -0.002 [-0.003, -0.001] | -0.002 [-0.003, -0.001] | - | - | - |

### Rao-Stirling (subfields)

| school | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| all | 0.238 [0.236, 0.241] | 0.246 [0.244, 0.248] | 0.252 [0.250, 0.254] | 0.258 [0.255, 0.260] | 0.268 [0.265, 0.270] | 0.268 [0.265, 0.270] |
| berkeley | 0.242 [0.234, 0.249] | 0.239 [0.232, 0.246] | 0.236 [0.230, 0.243] | 0.248 [0.239, 0.256] | 0.255 [0.246, 0.264] | 0.264 [0.255, 0.272] |
| cmu | 0.243 [0.237, 0.248] | 0.243 [0.238, 0.247] | 0.252 [0.247, 0.257] | 0.251 [0.245, 0.256] | 0.267 [0.261, 0.273] | 0.269 [0.263, 0.275] |
| epfl | 0.230 [0.223, 0.238] | 0.243 [0.235, 0.251] | 0.246 [0.238, 0.254] | 0.261 [0.253, 0.269] | 0.266 [0.258, 0.274] | 0.265 [0.257, 0.274] |
| gatech | 0.234 [0.228, 0.241] | 0.243 [0.237, 0.249] | 0.250 [0.244, 0.255] | 0.258 [0.252, 0.263] | 0.267 [0.262, 0.273] | 0.263 [0.257, 0.269] |
| michigan | 0.233 [0.225, 0.241] | 0.232 [0.224, 0.240] | 0.246 [0.239, 0.253] | 0.248 [0.240, 0.256] | 0.263 [0.255, 0.271] | 0.253 [0.246, 0.261] |
| mit | 0.243 [0.237, 0.250] | 0.255 [0.249, 0.261] | 0.268 [0.262, 0.273] | 0.271 [0.265, 0.277] | 0.275 [0.268, 0.281] | 0.284 [0.277, 0.290] |
| princeton | 0.222 [0.213, 0.231] | 0.239 [0.230, 0.249] | 0.232 [0.224, 0.240] | 0.232 [0.223, 0.241] | 0.256 [0.247, 0.265] | 0.255 [0.245, 0.265] |
| stanford | 0.252 [0.244, 0.259] | 0.270 [0.263, 0.276] | 0.273 [0.267, 0.279] | 0.281 [0.275, 0.288] | 0.278 [0.271, 0.285] | 0.278 [0.270, 0.285] |
| uchicago | 0.225 [0.208, 0.242] | 0.249 [0.235, 0.264] | 0.243 [0.231, 0.255] | 0.251 [0.236, 0.265] | 0.275 [0.261, 0.289] | 0.273 [0.260, 0.287] |

### cited-venue entropy (bits)

| school | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| all | 3.489 [3.471, 3.507] | 3.535 [3.517, 3.552] | 3.680 [3.664, 3.697] | 3.795 [3.776, 3.814] | 3.846 [3.826, 3.866] | 3.880 [3.859, 3.900] |
| berkeley | 3.475 [3.424, 3.525] | 3.437 [3.385, 3.488] | 3.547 [3.497, 3.596] | 3.677 [3.615, 3.740] | 3.718 [3.649, 3.788] | 3.720 [3.654, 3.787] |
| cmu | 3.505 [3.466, 3.543] | 3.408 [3.372, 3.445] | 3.606 [3.567, 3.645] | 3.737 [3.692, 3.782] | 3.739 [3.690, 3.787] | 3.848 [3.799, 3.896] |
| epfl | 3.453 [3.397, 3.508] | 3.566 [3.509, 3.624] | 3.748 [3.689, 3.807] | 3.792 [3.725, 3.859] | 3.875 [3.812, 3.938] | 3.929 [3.861, 3.997] |
| gatech | 3.473 [3.428, 3.518] | 3.572 [3.531, 3.614] | 3.717 [3.677, 3.758] | 3.823 [3.778, 3.869] | 3.862 [3.815, 3.908] | 3.924 [3.875, 3.974] |
| michigan | 3.360 [3.297, 3.424] | 3.484 [3.426, 3.541] | 3.715 [3.660, 3.771] | 3.779 [3.720, 3.839] | 3.834 [3.769, 3.900] | 3.863 [3.800, 3.926] |
| mit | 3.506 [3.458, 3.553] | 3.589 [3.544, 3.633] | 3.680 [3.637, 3.723] | 3.837 [3.787, 3.887] | 3.887 [3.834, 3.941] | 3.905 [3.847, 3.963] |
| princeton | 3.496 [3.416, 3.575] | 3.617 [3.542, 3.691] | 3.671 [3.614, 3.728] | 3.767 [3.694, 3.839] | 3.897 [3.823, 3.970] | 3.875 [3.794, 3.956] |
| stanford | 3.583 [3.527, 3.639] | 3.675 [3.621, 3.729] | 3.752 [3.706, 3.798] | 3.871 [3.815, 3.926] | 3.923 [3.863, 3.982] | 3.879 [3.819, 3.940] |
| uchicago | 3.633 [3.529, 3.738] | 3.746 [3.638, 3.853] | 3.753 [3.666, 3.840] | 3.894 [3.790, 3.997] | 3.962 [3.857, 4.067] | 3.999 [3.901, 4.097] |

## 3. Within labs, before and after 2023

Lab-year means (lab fixed effects, year fixed effects; 2022 dropped; cluster bootstrap over labs). `post` = 2023-2025 against 2016-2021 within the same lab; placebo breaks at 2019-2021 use 2016-2021 only. `sd` is the standard deviation of the lab-year outcome.

| outcome | spec | estimate | n | labs | sd |
|---|---|---|---|---|---|
| Uzzi z, 10th percentile (low = atypical) | post2023_vs_2016_21 | -0.282 [-0.453, -0.094] | 11871 | 2119 | 5.491 |
| Uzzi z, 10th percentile (low = atypical) | placebo2019 | -1.708 [-1.867, -1.596] | 7808 | 1820 | 5.209 |
| Uzzi z, 10th percentile (low = atypical) | placebo2020 | -1.636 [-1.812, -1.497] | 7808 | 1820 | 5.209 |
| Uzzi z, 10th percentile (low = atypical) | placebo2021 | -1.543 [-1.757, -1.393] | 7808 | 1820 | 5.209 |
| Uzzi z, median (high = conventional) | post2023_vs_2016_21 | -0.153 [-0.213, -0.085] | 11871 | 2119 | 1.82 |
| Uzzi z, median (high = conventional) | placebo2019 | -0.290 [-0.340, -0.248] | 7808 | 1820 | 1.824 |
| Uzzi z, median (high = conventional) | placebo2020 | -0.176 [-0.241, -0.130] | 7808 | 1820 | 1.824 |
| Uzzi z, median (high = conventional) | placebo2021 | -0.171 [-0.239, -0.110] | 7808 | 1820 | 1.824 |
| CD1 disruption (low = consolidating when high) | post2023_vs_2016_21 | 0.000 [-0.000, 0.001] | 8199 | 1866 | 0.01 |
| CD1 disruption (low = consolidating when high) | placebo2019 | 0.001 [0.000, 0.001] | 6232 | 1668 | 0.009 |
| CD1 disruption (low = consolidating when high) | placebo2020 | 0.000 [0.000, 0.001] | 6232 | 1668 | 0.009 |
| CD1 disruption (low = consolidating when high) | placebo2021 | 0.001 [0.000, 0.001] | 6232 | 1668 | 0.009 |
| CD to end-2025 (variable window) | post2023_vs_2016_21 | -0.000 [-0.001, 0.000] | 10037 | 2006 | 0.007 |
| CD to end-2025 (variable window) | placebo2019 | 0.000 [-0.000, 0.000] | 7559 | 1804 | 0.006 |
| CD to end-2025 (variable window) | placebo2020 | 0.000 [-0.000, 0.000] | 7559 | 1804 | 0.006 |
| CD to end-2025 (variable window) | placebo2021 | 0.000 [0.000, 0.001] | 7559 | 1804 | 0.006 |
| Rao-Stirling (subfields) | post2023_vs_2016_21 | 0.009 [0.006, 0.011] | 12099 | 2137 | 0.075 |
| Rao-Stirling (subfields) | placebo2019 | 0.009 [0.007, 0.011] | 7959 | 1839 | 0.074 |
| Rao-Stirling (subfields) | placebo2020 | 0.008 [0.005, 0.010] | 7959 | 1839 | 0.074 |
| Rao-Stirling (subfields) | placebo2021 | 0.008 [0.005, 0.010] | 7959 | 1839 | 0.074 |
| cited-venue entropy (bits) | post2023_vs_2016_21 | 0.154 [0.132, 0.173] | 12035 | 2133 | 0.573 |
| cited-venue entropy (bits) | placebo2019 | 0.126 [0.110, 0.146] | 7915 | 1834 | 0.543 |
| cited-venue entropy (bits) | placebo2020 | 0.136 [0.117, 0.155] | 7915 | 1834 | 0.543 |
| cited-venue entropy (bits) | placebo2021 | 0.132 [0.113, 0.148] | 7915 | 1834 | 0.543 |
| lab reference overlap, Jaccard | post2023_vs_2016_21 | -0.004 [-0.005, -0.003] | 10488 | 2052 | 0.029 |
| lab reference overlap, Jaccard | placebo2019 | -0.003 [-0.004, -0.002] | 7066 | 1750 | 0.03 |
| lab reference overlap, Jaccard | placebo2020 | -0.003 [-0.004, -0.001] | 7066 | 1750 | 0.03 |
| lab reference overlap, Jaccard | placebo2021 | -0.003 [-0.004, -0.001] | 7066 | 1750 | 0.03 |
| lab reference overlap, cosine | post2023_vs_2016_21 | -0.006 [-0.008, -0.004] | 10488 | 2052 | 0.045 |
| lab reference overlap, cosine | placebo2019 | -0.005 [-0.007, -0.003] | 7066 | 1750 | 0.047 |
| lab reference overlap, cosine | placebo2020 | -0.005 [-0.007, -0.003] | 7066 | 1750 | 0.047 |
| lab reference overlap, cosine | placebo2021 | -0.005 [-0.007, -0.002] | 7066 | 1750 | 0.047 |
| overlap with lab's previous 3 years, Jaccard | post2023_vs_2016_21 | -0.004 [-0.005, -0.003] | 9022 | 1954 | 0.016 |
| overlap with lab's previous 3 years, Jaccard | placebo2019 | -0.005 [-0.006, -0.005] | 5711 | 1637 | 0.017 |
| overlap with lab's previous 3 years, Jaccard | placebo2020 | -0.004 [-0.005, -0.003] | 5711 | 1637 | 0.017 |
| overlap with lab's previous 3 years, Jaccard | placebo2021 | -0.003 [-0.004, -0.003] | 5711 | 1637 | 0.017 |
| overlap with previous 3 years, cosine | post2023_vs_2016_21 | -0.007 [-0.008, -0.006] | 9022 | 1954 | 0.027 |
| overlap with previous 3 years, cosine | placebo2019 | -0.009 [-0.010, -0.008] | 5711 | 1637 | 0.029 |
| overlap with previous 3 years, cosine | placebo2020 | -0.007 [-0.008, -0.006] | 5711 | 1637 | 0.029 |
| overlap with previous 3 years, cosine | placebo2021 | -0.006 [-0.007, -0.005] | 5711 | 1637 | 0.029 |

### Lab AI dose and the change (difference-in-differences)

y(lab, year) = lab FE + year FE + b * Post * Dose_lab, Dose = the lab's mean `ai_share` of 2023-2025 full-text papers (>= 4 scored; `abs_dose`: flagged-abstract share, no full-text selection). b is per unit of dose (0 to 1). Placebo rows: the same with breaks at 2019, 2020, 2021 inside 2016-2021 (detector noise as "dose"). A post estimate counts only if it lies beyond the placebo spread.

| outcome | dose | did | placebo2019 | placebo2020 | placebo2021 | within_lab_year |
|---|---|---|---|---|---|---|
| CD to end-2025 (variable window) | abs_dose | 0.001 [-0.003, 0.006] | -0.002 [-0.004, 0.000] | -0.002 [-0.003, -0.000] | -0.001 [-0.003, 0.000] | - |
| CD to end-2025 (variable window) | ai_share_lt | - | - | - | - | -0.005 [-0.013, 0.000] |
| CD to end-2025 (variable window) | dose | -0.003 [-0.018, 0.007] | -0.001 [-0.003, 0.002] | -0.002 [-0.004, 0.001] | -0.000 [-0.003, 0.002] | - |
| CD1 disruption (low = consolidating when high) | abs_dose | 0.002 [-0.003, 0.006] | -0.002 [-0.005, 0.001] | -0.002 [-0.004, 0.001] | -0.003 [-0.006, 0.001] | - |
| CD1 disruption (low = consolidating when high) | ai_share_lt | - | - | - | - | 0.002 [-0.011, 0.019] |
| CD1 disruption (low = consolidating when high) | dose | -0.001 [-0.016, 0.010] | -0.002 [-0.007, 0.004] | -0.001 [-0.007, 0.004] | -0.001 [-0.009, 0.005] | - |
| Rao-Stirling (subfields) | abs_dose | 0.021 [0.001, 0.042] | 0.002 [-0.018, 0.022] | -0.009 [-0.025, 0.008] | 0.004 [-0.014, 0.023] | - |
| Rao-Stirling (subfields) | ai_share_lt | - | - | - | - | -0.012 [-0.037, 0.013] |
| Rao-Stirling (subfields) | dose | 0.056 [0.028, 0.095] | 0.003 [-0.030, 0.035] | -0.006 [-0.046, 0.029] | 0.011 [-0.030, 0.053] | - |
| Uzzi z, 10th percentile (low = atypical) | abs_dose | -0.740 [-1.843, 0.319] | -2.291 [-3.719, -1.200] | -2.184 [-3.562, -0.775] | -2.480 [-4.046, -1.139] | - |
| Uzzi z, 10th percentile (low = atypical) | ai_share_lt | - | - | - | - | 0.680 [-0.884, 2.058] |
| Uzzi z, 10th percentile (low = atypical) | dose | -1.686 [-3.831, 0.209] | -4.784 [-7.768, -2.172] | -4.680 [-7.751, -2.173] | -5.490 [-8.591, -2.127] | - |
| Uzzi z, median (high = conventional) | abs_dose | 0.170 [-0.281, 0.475] | -0.421 [-0.872, -0.003] | -0.484 [-0.970, -0.094] | -0.520 [-1.054, 0.041] | - |
| Uzzi z, median (high = conventional) | ai_share_lt | - | - | - | - | 0.049 [-0.549, 0.601] |
| Uzzi z, median (high = conventional) | dose | 0.151 [-0.795, 0.938] | -0.642 [-1.588, 0.261] | -0.913 [-1.857, -0.054] | -1.039 [-2.152, 0.042] | - |
| cited-venue entropy (bits) | abs_dose | 0.134 [0.001, 0.276] | -0.030 [-0.188, 0.116] | 0.081 [-0.052, 0.197] | 0.122 [-0.009, 0.249] | - |
| cited-venue entropy (bits) | ai_share_lt | - | - | - | - | 0.001 [-0.218, 0.247] |
| cited-venue entropy (bits) | dose | 0.234 [-0.025, 0.491] | 0.012 [-0.180, 0.254] | 0.251 [0.058, 0.476] | 0.229 [-0.027, 0.482] | - |
| lab reference overlap, Jaccard | abs_dose | -0.004 [-0.014, 0.006] | 0.007 [-0.005, 0.019] | 0.009 [-0.001, 0.022] | 0.009 [-0.006, 0.027] | - |
| lab reference overlap, Jaccard | ai_share_lt | - | - | - | - | -0.003 [-0.013, 0.008] |
| lab reference overlap, Jaccard | dose | -0.006 [-0.025, 0.011] | 0.001 [-0.019, 0.016] | 0.002 [-0.014, 0.019] | 0.004 [-0.014, 0.023] | - |
| lab reference overlap, cosine | abs_dose | -0.007 [-0.025, 0.009] | 0.008 [-0.010, 0.026] | 0.014 [-0.003, 0.032] | 0.013 [-0.009, 0.037] | - |
| lab reference overlap, cosine | ai_share_lt | - | - | - | - | -0.005 [-0.022, 0.014] |
| lab reference overlap, cosine | dose | -0.014 [-0.046, 0.016] | 0.002 [-0.031, 0.028] | 0.006 [-0.020, 0.033] | 0.010 [-0.021, 0.038] | - |
| overlap with lab's previous 3 years, Jaccard | abs_dose | -0.007 [-0.012, -0.001] | -0.001 [-0.007, 0.005] | 0.000 [-0.006, 0.005] | 0.001 [-0.005, 0.006] | - |
| overlap with lab's previous 3 years, Jaccard | ai_share_lt | - | - | - | - | -0.009 [-0.015, -0.005] |
| overlap with lab's previous 3 years, Jaccard | dose | -0.013 [-0.021, -0.005] | -0.001 [-0.011, 0.007] | 0.003 [-0.007, 0.010] | -0.002 [-0.014, 0.009] | - |
| overlap with previous 3 years, cosine | abs_dose | -0.011 [-0.022, -0.001] | -0.002 [-0.012, 0.009] | 0.002 [-0.009, 0.010] | 0.001 [-0.009, 0.012] | - |
| overlap with previous 3 years, cosine | ai_share_lt | - | - | - | - | -0.015 [-0.025, -0.008] |
| overlap with previous 3 years, cosine | dose | -0.022 [-0.037, -0.008] | -0.000 [-0.017, 0.013] | 0.005 [-0.011, 0.018] | -0.002 [-0.022, 0.015] | - |

## 4. A paper's AI dose and its citation measures

Paper-level fits of the measure on `ai_share` (full-text-scored papers; per unit of share, 0 to 1), 2023-2025 (`post`) and the 2017-2021 placebo (`pre`: the dose is detector noise). Controls as the dose report: year, school and OpenAlex-topic FE, log team size, venue type, open-access status, and log(number of references); within-lab = lab x year FE. Intervals clustered by first lab.

| measure | design | n | y_sd | post | pre |
|---|---|---|---|---|---|
| CD to end-2025 (variable window) | pooled | 9057 | 0.013 | 0.001 [-0.001, 0.002] | - |
| CD to end-2025 (variable window) | pooled | 15262 | 0.01 | - | 0.010 [-0.003, 0.026] |
| CD to end-2025 (variable window) | withinlab | 9057 | 0.013 | 0.002 [0.000, 0.003] | - |
| CD to end-2025 (variable window) | withinlab | 15262 | 0.01 | - | 0.004 [-0.010, 0.025] |
| CD1 disruption (low = consolidating when high) | pooled | 7162 | 0.016 | 0.001 [-0.002, 0.003] | - |
| CD1 disruption (low = consolidating when high) | pooled | 10785 | 0.011 | - | 0.010 [-0.001, 0.021] |
| CD1 disruption (low = consolidating when high) | withinlab | 7162 | 0.016 | 0.001 [-0.000, 0.004] | - |
| CD1 disruption (low = consolidating when high) | withinlab | 10785 | 0.011 | - | 0.009 [-0.002, 0.022] |
| Rao-Stirling (subfields) | pooled | 16278 | 0.113 | 0.017 [0.006, 0.025] | - |
| Rao-Stirling (subfields) | pooled | 17832 | 0.113 | - | -0.036 [-0.186, 0.087] |
| Rao-Stirling (subfields) | withinlab | 16278 | 0.113 | 0.025 [0.013, 0.036] | - |
| Rao-Stirling (subfields) | withinlab | 17832 | 0.113 | - | 0.022 [-0.149, 0.159] |
| Uzzi z, 10th percentile (low = atypical) | pooled | 15898 | 8.843 | 0.125 [-0.539, 0.870] | - |
| Uzzi z, 10th percentile (low = atypical) | pooled | 16992 | 8.355 | - | 14.750 [6.020, 23.346] |
| Uzzi z, 10th percentile (low = atypical) | withinlab | 15898 | 8.843 | -0.849 [-1.652, 0.002] | - |
| Uzzi z, 10th percentile (low = atypical) | withinlab | 16992 | 8.355 | - | 13.344 [5.294, 22.071] |
| Uzzi z, median (high = conventional) | pooled | 15898 | 2.743 | -0.169 [-0.395, 0.086] | - |
| Uzzi z, median (high = conventional) | pooled | 16992 | 2.941 | - | 5.703 [2.269, 9.835] |
| Uzzi z, median (high = conventional) | withinlab | 15898 | 2.743 | -0.379 [-0.636, -0.092] | - |
| Uzzi z, median (high = conventional) | withinlab | 16992 | 2.941 | - | 3.675 [0.901, 6.872] |
| cited-venue entropy (bits) | pooled | 16182 | 0.906 | 0.143 [0.072, 0.190] | - |
| cited-venue entropy (bits) | pooled | 17472 | 0.842 | - | 0.043 [-0.759, 0.629] |
| cited-venue entropy (bits) | withinlab | 16182 | 0.906 | 0.093 [0.011, 0.160] | - |
| cited-venue entropy (bits) | withinlab | 17472 | 0.842 | - | -0.060 [-0.840, 0.665] |

### All designs (post period, `ai_share`; robustness: no-LLM-topic papers, topic x year FE, papers with >= 15 references)

| measure | nollm | pooled | raw | refs15 | topicyear | withinlab |
|---|---|---|---|---|---|---|
| CD to end-2025 (variable window) | 0.001 [-0.001, 0.002] | 0.001 [-0.001, 0.002] | 0.002 [0.001, 0.004] | 0.001 [0.000, 0.001] | 0.001 [-0.001, 0.002] | 0.002 [0.000, 0.003] |
| CD1 disruption (low = consolidating when high) | 0.001 [-0.002, 0.003] | 0.001 [-0.002, 0.003] | 0.002 [-0.000, 0.005] | 0.000 [-0.000, 0.001] | 0.001 [-0.001, 0.004] | 0.001 [-0.001, 0.003] |
| Rao-Stirling (subfields) | 0.016 [0.006, 0.026] | 0.017 [0.007, 0.026] | 0.038 [0.023, 0.054] | 0.015 [0.005, 0.025] | 0.014 [0.004, 0.025] | 0.025 [0.014, 0.037] |
| Uzzi z, 10th percentile (low = atypical) | -0.020 [-0.767, 0.727] | 0.125 [-0.597, 0.847] | -3.039 [-4.112, -1.966] | -0.050 [-0.791, 0.690] | -0.414 [-1.169, 0.341] | -0.849 [-1.718, 0.020] |
| Uzzi z, median (high = conventional) | -0.221 [-0.484, 0.043] | -0.169 [-0.408, 0.071] | -1.038 [-1.356, -0.719] | -0.191 [-0.434, 0.052] | -0.270 [-0.522, -0.018] | -0.379 [-0.669, -0.089] |
| cited-venue entropy (bits) | 0.151 [0.089, 0.212] | 0.143 [0.081, 0.204] | -0.058 [-0.189, 0.072] | 0.139 [0.075, 0.204] | 0.113 [0.047, 0.178] | 0.093 [0.016, 0.170] |

### Same, placebo period (2017-2021)

| measure | nollm | pooled | raw | refs15 | topicyear | withinlab |
|---|---|---|---|---|---|---|
| CD to end-2025 (variable window) | 0.010 [-0.003, 0.024] | 0.010 [-0.003, 0.023] | 0.014 [-0.001, 0.029] | 0.002 [-0.005, 0.009] | 0.007 [-0.004, 0.017] | 0.004 [-0.011, 0.019] |
| CD1 disruption (low = consolidating when high) | 0.010 [-0.000, 0.020] | 0.010 [-0.000, 0.020] | 0.015 [0.003, 0.027] | 0.006 [-0.000, 0.013] | 0.007 [-0.001, 0.015] | 0.009 [-0.004, 0.022] |
| Rao-Stirling (subfields) | -0.035 [-0.164, 0.094] | -0.036 [-0.164, 0.092] | 0.199 [0.059, 0.338] | -0.058 [-0.199, 0.084] | -0.061 [-0.197, 0.074] | 0.022 [-0.134, 0.177] |
| Uzzi z, 10th percentile (low = atypical) | 14.364 [6.631, 22.097] | 14.750 [6.941, 22.559] | 25.106 [15.485, 34.727] | 12.613 [4.331, 20.896] | 16.842 [8.035, 25.650] | 13.344 [5.218, 21.471] |
| Uzzi z, median (high = conventional) | 5.833 [2.679, 8.987] | 5.703 [2.573, 8.833] | 7.389 [3.662, 11.117] | 4.788 [1.572, 8.004] | 7.231 [3.831, 10.631] | 3.675 [0.571, 6.778] |
| cited-venue entropy (bits) | 0.029 [-0.644, 0.703] | 0.043 [-0.626, 0.712] | 0.898 [-0.177, 1.973] | -0.038 [-0.775, 0.699] | 0.008 [-0.692, 0.709] | -0.060 [-0.757, 0.638] |

### Abstract-flag exposure (post period; every paper with an abstract, no full-text selection)

| measure | pooled | raw | withinlab |
|---|---|---|---|
| CD to end-2025 (variable window) | 0.001 [-0.000, 0.001] | 0.001 [-0.000, 0.001] | 0.000 [-0.000, 0.001] |
| CD1 disruption (low = consolidating when high) | 0.001 [-0.000, 0.001] | 0.001 [-0.000, 0.001] | 0.000 [-0.000, 0.001] |
| Rao-Stirling (subfields) | 0.001 [-0.003, 0.005] | 0.007 [0.001, 0.012] | 0.002 [-0.002, 0.006] |
| Uzzi z, 10th percentile (low = atypical) | 0.140 [-0.108, 0.388] | -0.300 [-0.623, 0.023] | -0.104 [-0.395, 0.187] |
| Uzzi z, median (high = conventional) | 0.012 [-0.072, 0.096] | -0.107 [-0.211, -0.002] | -0.024 [-0.112, 0.065] |
| cited-venue entropy (bits) | 0.035 [0.014, 0.056] | -0.000 [-0.042, 0.041] | 0.014 [-0.008, 0.037] |

## 5. Method and limits

- **Data.** One streamed pass over all works of the OpenAlex snapshot (`cn_stream.py`; 128 CPU tasks, no API credits). For each lab paper: its reference list (from `oa_extra.sqlite`), the year, venue (source id and type) and primary subfield/field of every referenced work, and the citing works by year offset.
- **Atypicality (Uzzi et al. 2013).** Venue pairs are those of OpenAlex sources typed journal, conference or book series (repositories and unknown sources dropped). The null shuffles venue labels over the reference slots of the lab papers of the same year (10 permutations): it keeps every paper's reference count and every venue's total count. The reference population is the lab-paper set, not all of science, so z measures atypicality relative to these schools' own citing habits.
- **Disruption (CD_w).** n_i and n_j are exact over all citing works; n_k (works citing a reference of the paper but not the paper) is estimated from the works whose OpenAlex number is divisible by the sampling factor (scaled by it, minus n_j), so CD carries sampling noise that shrinks with n_k; windows count only if year + w <= 2025; at least 5 references and 3 citing works are required (papers with fewer citations drop out, which selects on citation count). CD5 exists only for 2016-2020 papers, CD1 for 2016-2024.
- **Rao-Stirling.** Distance between subfields (fields) = 1 - cosine similarity of their co-occurrence profiles over all lab-paper reference lists (a fixed matrix, all years).
- **Lab overlap.** Mean over pairs of a lab's papers in a year (>= 3 papers with >= 5 references) of Jaccard and cosine (bibliographic coupling normalised) of reference sets; `prev` compares with the lab's papers of the previous three years.
- **Citation time and coverage.** Citation-based measures need citation time and complete reference lists: the post-2022 years are the weakest. CD for 2025 papers rests on one year of citations; OpenAlex reference lists of recent papers are less complete (section 1). `AI dose` exists only for full-text papers (selection; the abstract-flag rows cover every paper).
