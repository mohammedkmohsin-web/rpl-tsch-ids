#!/bin/bash
CONF=examples/rpl-udp/project-conf.h

run_sim() {
  local seed=$1
  local csc=$2
  local outfile=$3
  sudo docker run --rm -v ~/contiki-ng:/home/user/contiki-ng contiker/contiki-ng bash -c \
    "cd /home/user/contiki-ng/tools/cooja && ./gradlew run --args='--no-gui --random-seed=$seed --logdir=/home/user/contiki-ng/examples/rpl-udp /home/user/contiki-ng/examples/rpl-udp/$csc' 2>&1 | tail -1"
  python3 ~/rpl-tsch-ids/scripts/fix_time.py examples/rpl-udp/COOJA.testlog >/dev/null 2>&1
  cp examples/rpl-udp/COOJA.testlog "$outfile"
  echo "  saved: $outfile ($(wc -l < $outfile) lines)"
}

build() {
  sudo docker run --rm -v ~/contiki-ng:/home/user/contiki-ng contiker/contiki-ng bash -c \
    "cd /home/user/contiki-ng/examples/rpl-udp && rm -rf build && make udp-server.cooja udp-client.cooja TARGET=cooja 2>&1 | tail -1" >/dev/null 2>&1
}

for SIZE in 20 40; do
  CSC="exp_bal_${SIZE}n_s1.csc"
  echo "========== size $SIZE nodes =========="

  # normal
  echo "=== $SIZE nodes: normal ==="
  sed -i 's|#define RPL_ATTACK_TYPE [0-9]|/* NORMAL */|' $CONF
  build
  for s in 2 3 4; do run_sim $s "$CSC" "data_normal_${SIZE}n_s$s.txt"; done
  sed -i 's|/\* NORMAL \*/|#define RPL_ATTACK_TYPE 1|' $CONF

  # rank
  echo "=== $SIZE nodes: rank ==="
  build
  for s in 2 3 4; do run_sim $s "$CSC" "data_rank_${SIZE}n_s$s.txt"; done

  # version
  echo "=== $SIZE nodes: version ==="
  sed -i 's|#define RPL_ATTACK_TYPE 1|#define RPL_ATTACK_TYPE 2|' $CONF
  build
  for s in 2 3 4; do run_sim $s "$CSC" "data_version_${SIZE}n_s$s.txt"; done

  # flood
  echo "=== $SIZE nodes: flood ==="
  sed -i 's|#define RPL_ATTACK_TYPE 2|#define RPL_ATTACK_TYPE 3|' $CONF
  build
  for s in 2 3 4; do run_sim $s "$CSC" "data_flood_${SIZE}n_s$s.txt"; done

  sed -i 's|#define RPL_ATTACK_TYPE 3|#define RPL_ATTACK_TYPE 1|' $CONF
done

echo "========== done =========="
ls data_*_20n_s*.txt data_*_40n_s*.txt 2>/dev/null | wc -l
echo "size data files generated"
