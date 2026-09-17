# Attacker-Agnostic Detection of RPL Routing Attacks in TSCH Networks

This repository contains the code, simulation configuration, and dataset that
reproduce the results in the letter "Attacker-Agnostic Detection of RPL
Routing Attacks in TSCH Networks Using Machine Learning."

The detector classifies an RPL-over-TSCH network into benign, decreased
rank, version number, and DIS flooding states from features that summarize
the collective behavior of the routing layer over 30-second windows, rather
than the behavior of any single node. The central result is that a Random
Forest trained on attacks launched from one set of node positions still
detects the same attacks when launched from a node position held out from
training, evidence that the model learns the mechanism of each attack rather
than the identity of its source.

## REPOSITORY LAYOUT

  scripts/make_network_dataset.py   logs to 21-feature windowed CSV
  scripts/fix_time.py               normalize Cooja timestamp format
  scripts/compare_models.py         compare six classifiers
  scripts/build_fair_baseline.py    node-level vs network-level comparison
  simulation/project-conf.h         TSCH/RPL and attack configuration
  simulation/exp_bal_*.csc          Cooja topologies (10/20/40 nodes)
  contiki-modifications/*.c         patched RPL and application source
  data/data_*.txt                   per-scenario Cooja FEATURES logs
  data/dataset_large.csv            final balanced dataset (1118 windows)
  gen_more_data.sh                  regenerate 10-node logs (multiple seeds)
  gen_size_data.sh                  regenerate 20- and 40-node logs

## DATASET

data/dataset_large.csv contains 1118 balanced network-level windows: 280
benign, 280 decreased rank, 278 version number, 280 DIS flooding. Windows come
from multiple attacker positions (8, 5, 11) and several random seeds.

## KEY RESULTS

  Internal stratified split (30% test):  Random Forest 97.92% accuracy,
                                          5-fold CV F1 98.57%, SD 0.91%
  Attacker-held-out (test attacker 11):   99.38% accuracy
  Node-level baseline (same protocol):    66.25% accuracy
  Cross-size (train 10 nodes):            collapses on 20/40 nodes

## REQUIREMENTS

  Python 3.9+ with the packages in requirements.txt
    (pip install -r requirements.txt)
  Contiki-NG with Cooja, only to regenerate the raw logs. Reproducing the ML
  results from the provided dataset needs Python only.

## QUICK START

From the data/ directory:

  python3 ../scripts/compare_models.py        # six classifiers
  python3 ../scripts/build_fair_baseline.py   # network-level vs node-level

## THE 21 NETWORK-LEVEL FEATURES

Per 30-second window, aggregated across all active nodes: node count; rank
mean/std/max/min; rank-change mean/std/max; DIS mean/std/max; DIO mean/max;
DIS-received mean/max; version spread; TX-energy mean/std; RX-energy mean;
PDR mean/min.

## LICENSE

Released under the MIT License.

## REPOSITORY STRUCTURE (reviewer-requested layout)

  project/contiki-modifications/    patched RPL and application source (full files)
  project/attack-implementations/   documented excerpts of the three attack mechanisms
  project/cooja-simulations/        topology files and TSCH/RPL configuration
  project/raw-logs/                 sixty raw Cooja FEATURES logs
  project/dataset/                  final balanced dataset (1118 windows)
  project/feature-extraction/       scripts turning raw logs into the feature CSV
  project/machine-learning/         model comparison and fair-baseline scripts
