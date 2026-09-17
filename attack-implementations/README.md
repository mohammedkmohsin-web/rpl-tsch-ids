# Attack Implementations

Each attack is compiled in via a single preprocessor flag, `RPL_ATTACK_TYPE`, defined in
`examples/rpl-udp/project-conf.h`, together with `RPL_ATTACKER_ID` (or an
`RPL_ATTACKER_ID_MIN` / `RPL_ATTACKER_ID_MAX` range) naming which node(s) carry the
behavior. Setting `RPL_ATTACK_TYPE` to a different value moves the attack between the
files below without touching the rest of the codebase.

## 1. Decreased Rank (RPL_ATTACK_TYPE == 1)
File: `os/net/routing/rpl-lite/rpl-dag.c`, in the rank update logic.

```c
#if RPL_ATTACK_TYPE == 1
  /* Decreased Rank: advertise a falsely low rank */
  if(curr_instance.dag.rank != RPL_INFINITE_RANK) {
    curr_instance.dag.rank = ROOT_RANK + curr_instance.min_hoprankinc;
  }
#endif
```

The attacker overwrites its own computed rank with the smallest value structurally
possible, one hop-increment above the root, immediately after the normal rank update, so
every DIO it sends afterward advertises this artificially low rank.

## 2. Version Number (RPL_ATTACK_TYPE == 2)
File: `os/net/routing/rpl-lite/rpl-icmp6.c`, in DIO construction.

```c
#if defined(RPL_ATTACK_TYPE) && (RPL_ATTACK_TYPE == 2)
  if(node_id >= RPL_ATTACKER_ID_MIN && node_id <= RPL_ATTACKER_ID_MAX
     && !rpl_dag_root_is_root()) {
    buffer[pos++] = curr_instance.dag.version + 5; /* inflated version */
```

The attacker writes the current DODAG version plus five into its own outgoing DIO
messages, forcing every neighbor that accepts the update to believe a new global repair
has been triggered.

## 3. DIS Flooding (RPL_ATTACK_TYPE == 3)
File: `examples/rpl-udp/udp-client.c`, in the periodic application timer callback.

```c
#if defined(RPL_ATTACK_TYPE) && (RPL_ATTACK_TYPE == 3)
  if(node_id >= RPL_ATTACKER_ID_MIN && node_id <= RPL_ATTACKER_ID_MAX) {
    int f;
    for(f = 0; f < 10; f++) {
      rpl_icmp6_dis_output(NULL); /* multicast DIS flood */
    }
```

On every application cycle (roughly every eight seconds), the attacker sends ten
multicast DIS messages in immediate succession instead of its normal single data packet,
soliciting a burst of DIO replies from every neighbor in range.

## Attacker selection
`RPL_ATTACKER_ID` (or the `_MIN` / `_MAX` range) is set alongside `RPL_ATTACK_TYPE` in
`project-conf.h`. This is how the letter relocates the same attack across node positions
5, 8, and 11 without recompiling any logic beyond changing these two constants.

Two additional, unused attack types also exist in the codebase for completeness:
`RPL_ATTACK_TYPE == 4` (Worst Parent) and `== 7` (Sinkhole) in `rpl-dag.c`, and `== 8` and
`== 9` in `udp-client.c`. None of these four are evaluated in this study.
