# Attacker-Agnostic Detection of RPL Routing Attacks in TSCH Networks

This repository contains the code, simulation configuration, and dataset that
reproduce the results in the paper "Attacker-Agnostic Detection of RPL Routing
Attacks in TSCH Networks Using Machine Learning."

The detector classifies an RPL-over-TSCH network into benign, decreased rank,
version number, and DIS flooding states from features that summarize the
collective behavior of the routing layer over 30-second windows, rather than
the behavior of any single node. The central result is that a Random Forest
trained on attacks launched from one set of node positions still detects the
same attacks when they are launched from a node position held out from
training, evidence that the model learns the mechanism of each attack rather
than the identity or location of its source.

## REPOSITORY LAYOUT

    feature-extraction/build_grouped_dataset.py   raw logs -> 21-feature windowed CSV, tagged by run
    feature-extraction/make_network_dataset.py    original single-file dataset builder
    feature-extraction/fix_time.py                normalize Cooja timestamp format
    machine-learning/evaluate_classifiers.py      Tables III, IV, VI (models, per-class, ablation)
    machine-learning/attacker_held_out.py         Table V + fair node-level baseline (three positions)
    machine-learning/compare_models.py            legacy six-classifier comparison
    machine-learning/build_fair_baseline.py       legacy node-level baseline
    cooja-simulations/project-conf.h              TSCH/RPL and attack configuration
    cooja-simulations/exp_bal_*.csc               Cooja topologies (10/20/40 nodes)
    contiki-modifications/*.c                     patched RPL and application source (full files)
    attack-implementations/README.md              documented excerpts of the three attack mechanisms
    raw-logs/data_*.txt                           per-scenario Cooja FEATURES logs
    dataset/dataset_large.csv                     final balanced dataset (1118 windows)
    dataset_large_grouped.csv                     dataset with a per-run "group" column (used by scripts)
    gen_more_data.sh                              regenerate 10-node logs (multiple seeds)
    gen_size_data.sh                              regenerate 20- and 40-node logs

## DATASET

The main dataset contains 1118 balanced network-level windows (280 benign, 280
decreased rank, 278 version number, 280 DIS flooding), drawn from 28 independent
Cooja runs, 7 per class, spanning several attacker positions (5, 8, 11) and
random seeds. Each row in dataset_large_grouped.csv carries a "group" column
identifying the simulation run it came from; every evaluation splits by run, so
no window from a given run ever appears in both training and test.

## EVALUATION PROTOCOL

All results use a run-independent, class-balanced protocol rather than a naive
per-window split, which would leak correlated windows from the same run across
the train-test boundary. For the model comparison and ablation, two of the
seven runs per class are held out for testing in each of twenty repetitions,
and the mean and standard deviation are reported. The attacker-held-out
experiment is repeated once for each of the three attacker positions, training
on the other two and testing on the held-out one.

## KEY RESULTS

    Internal (run-independent, 20 repetitions):   Random Forest 98.69% mean accuracy, SD 0.44%
    Attacker-held-out (mean over 3 positions):    98.26% accuracy
    Node-level baseline (identical protocol):     63.37% accuracy (mean gap ~34.9 points)
    Cross-size (train 10 nodes):                  collapses on 20/40 nodes (version-number attack persists)

## REQUIREMENTS

Python 3.9+ with the packages in requirements.txt (`pip install -r requirements.txt`).
Contiki-NG with the Cooja simulator is needed only to regenerate the raw logs;
reproducing the ML results from the provided dataset needs Python only.

## QUICK START (reproduce the ML results from the provided data)

    # from the repository root, build the grouped dataset from the raw logs
    python3 feature-extraction/build_grouped_dataset.py dataset_large_grouped.csv

    # Tables III, IV, VI: model comparison, per-class performance, feature ablation
    python3 machine-learning/evaluate_classifiers.py dataset_large_grouped.csv

    # Table V and the fair node-level baseline across three attacker positions
    python3 machine-learning/attacker_held_out.py

The scripts expect the raw logs in raw-logs/ (used by build_grouped_dataset.py
and attacker_held_out.py). If a freshly generated log yields zero windows,
normalize its timestamps first with feature-extraction/fix_time.py.

## THE 21 NETWORK-LEVEL FEATURES

Per 30-second window, aggregated across all active client nodes (the DODAG root
runs the server and is excluded): node count; rank mean/std/max/min; rank-change
mean/std/max; DIS mean/std/max; DIO mean/max; DIS-received mean/max; version
spread; TX-energy mean/std; RX-energy mean; PDR mean/min.

## ATTACK IMPLEMENTATIONS

Each attack is compiled in through a single `RPL_ATTACK_TYPE` flag in
cooja-simulations/project-conf.h, with `RPL_ATTACKER_ID` naming the malicious
node. An optional `RPL_ATTACK_ONSET_SEC` delays the onset of malicious behavior
(default 0, i.e. active from boot) and is used only for the detection-latency
experiment. See attack-implementations/README.md for the exact code of each
mechanism.

## LICENSE

Released under the MIT License.
