#!/bin/bash
# Generate more data: each scenario with several seeds
CONF=examples/rpl-udp/project-conf.h
CSC=/home/user/contiki-ng/examples/rpl-udp/exp_bal_10n_s1.csc

run_sim() {
  local seed=$1
  local outfile=$2
  sudo docker run --rm -v ~/contiki-ng:/home/user/contiki-ng contiker/contiki-ng bash -c \
    "cd /home/user/contiki-ng/tools/cooja && ./gradlew run --args='--no-gui --random-seed=$seed --logdir=/home/user/contiki-ng/examples/rpl-udp $CSC' 2>&1 | tail -1"
  python3 ~/rpl-tsch-ids/scripts/fix_time.py examples/rpl-udp/COOJA.testlog >/dev/null 2>&1
  cp examples/rpl-udp/COOJA.testlog "$outfile"
  echo "  saved: $outfile ($(wc -l < $outfile) lines)"
}

build() {
  sudo docker run --rm -v ~/contiki-ng:/home/user/contiki-ng contiker/contiki-ng bash -c \
    "cd /home/user/contiki-ng/examples/rpl-udp && rm -rf build && make udp-server.cooja udp-client.cooja TARGET=cooja 2>&1 | tail -1" >/dev/null 2>&1
}

# ===== normal (no attack) =====
echo "=== generating: normal ==="
sed -i 's|#define RPL_ATTACK_TYPE 9|/* NORMAL */|' $CONF
build
for s in 4 5 6 7; do run_sim $s "data_normal_s$s.txt"; done
sed -i 's|/\* NORMAL \*/|#define RPL_ATTACK_TYPE 1|' $CONF

# ===== rank (type 1) =====
echo "=== generating: rank ==="
sed -i 's|#define RPL_ATTACK_TYPE 1|#define RPL_ATTACK_TYPE 1|' $CONF
build
for s in 2 3 4 5; do run_sim $s "data_rank_s$s.txt"; done

# ===== version (type 2) =====
echo "=== generating: version ==="
sed -i 's|#define RPL_ATTACK_TYPE 1|#define RPL_ATTACK_TYPE 2|' $CONF
build
for s in 2 3 4 5; do run_sim $s "data_version_s$s.txt"; done

# ===== flood (type 3) =====
echo "=== generating: flood ==="
sed -i 's|#define RPL_ATTACK_TYPE 2|#define RPL_ATTACK_TYPE 3|' $CONF
build
for s in 2 3 4 5; do run_sim $s "data_flood_s$s.txt"; done

echo "=== done ==="
ls -la data_*_s*.txt | tail -20
