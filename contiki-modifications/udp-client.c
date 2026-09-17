#include "contiki.h"
#include "net/routing/routing.h"
#include "random.h"
#include "net/netstack.h"
#include "net/ipv6/simple-udp.h"
#include <stdint.h>
#include <inttypes.h>
#include "sys/energest.h"
#include "sys/node-id.h"
#include "net/routing/rpl-lite/rpl.h"
#include "net/routing/rpl-lite/rpl-icmp6.h"
#include "net/ipv6/uip-ds6-route.h"
#include "sys/log.h"
#define LOG_MODULE "App"
#define LOG_LEVEL LOG_LEVEL_INFO
/* External RPL control-message counters (defined in rpl-icmp6.c) */
extern unsigned long rpl_stat_dio_sent;
extern unsigned long rpl_stat_dis_sent;
extern unsigned long rpl_stat_dao_sent;
extern unsigned long rpl_stat_dis_recv;
#define WITH_SERVER_REPLY  1
#define UDP_CLIENT_PORT 8765
#define UDP_SERVER_PORT 5678
#define SEND_INTERVAL   (8 * CLOCK_SECOND)
static struct simple_udp_connection udp_conn;
static uint32_t rx_count = 0;
static uint32_t tx_count = 0;
static uint32_t missed_tx_count = 0;
static rpl_rank_t last_rank = 0;
static uint32_t rank_changes = 0;
/*---------------------------------------------------------------------------*/
PROCESS(udp_client_process, "UDP client");
AUTOSTART_PROCESSES(&udp_client_process);
/*---------------------------------------------------------------------------*/
static void
udp_rx_callback(struct simple_udp_connection *c,
         const uip_ipaddr_t *sender_addr,
         uint16_t sender_port,
         const uip_ipaddr_t *receiver_addr,
         uint16_t receiver_port,
         const uint8_t *data,
         uint16_t datalen)
{
  rx_count++;
}
/*---------------------------------------------------------------------------*/
static void
print_features(void)
{
  rpl_rank_t rank = 0;
  uint16_t parent_id = 0;
  uint32_t num_routes = 0;
  uint64_t tx_energy, rx_energy;

  /* Current rank */
  if(curr_instance.used) {
    rank = curr_instance.dag.rank;
    if(curr_instance.dag.preferred_parent != NULL) {
      const linkaddr_t *lla = rpl_neighbor_get_lladdr(curr_instance.dag.preferred_parent);
      if(lla != NULL) {
        parent_id = lla->u8[LINKADDR_SIZE - 1];
      }
    }
  }
  /* Track rank changes */
  if(rank != last_rank) {
    rank_changes++;
    last_rank = rank;
  }
  /* Number of children (routes we forward for) */
  num_routes = uip_ds6_route_num_routes();
  /* Energy */
  energest_flush();
  tx_energy = energest_type_time(ENERGEST_TYPE_TRANSMIT);
  rx_energy = energest_type_time(ENERGEST_TYPE_LISTEN);

  /* Current DODAG version number */
  uint16_t version = 0;
  if(curr_instance.used) {
    version = curr_instance.dag.version;
  }

  /* Structured metrics line: everything needed for detection */
  LOG_INFO("FEATURES node=%u rank=%u parent=%u rank_changes=%lu tx=%lu rx=%lu missed=%lu routes=%lu tx_e=%lu rx_e=%lu dio=%lu dis=%lu dao=%lu disrx=%lu version=%u\n",
           node_id,
           (unsigned)rank,
           (unsigned)parent_id,
           (unsigned long)rank_changes,
           (unsigned long)tx_count,
           (unsigned long)rx_count,
           (unsigned long)missed_tx_count,
           (unsigned long)num_routes,
           (unsigned long)tx_energy,
           (unsigned long)rx_energy,
           rpl_stat_dio_sent,
           rpl_stat_dis_sent,
           rpl_stat_dao_sent,
           rpl_stat_dis_recv,
           (unsigned)version);
}
/*---------------------------------------------------------------------------*/
PROCESS_THREAD(udp_client_process, ev, data)
{
  static struct etimer periodic_timer;
  static char str[32];
  uip_ipaddr_t dest_ipaddr;
  PROCESS_BEGIN();
  simple_udp_register(&udp_conn, UDP_CLIENT_PORT, NULL,
                      UDP_SERVER_PORT, udp_rx_callback);
  etimer_set(&periodic_timer, random_rand() % SEND_INTERVAL);
  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&periodic_timer));
    /* ===== DIS Flooding Attack (type 3): blast DIS to all neighbors ===== */
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
        rpl_icmp6_dis_output(NULL); /* multicast DIS flood */
      }
    }
#endif
    /* ===== DAO Flooding Attack (type 8): blast DAO messages ===== */
#if defined(RPL_ATTACK_TYPE) && (RPL_ATTACK_TYPE == 8)
#ifndef RPL_ATTACKER_ID_MIN
#define RPL_ATTACKER_ID_MIN RPL_ATTACKER_ID
#endif
#ifndef RPL_ATTACKER_ID_MAX
#define RPL_ATTACKER_ID_MAX RPL_ATTACKER_ID
#endif
    if(node_id >= RPL_ATTACKER_ID_MIN && node_id <= RPL_ATTACKER_ID_MAX) {
      int df;
      for(df = 0; df < 10; df++) {
        rpl_icmp6_dao_output(RPL_DEFAULT_LIFETIME); /* DAO flood */
      }
    }
#endif
    /* ===== Heavy DIS Flooding Attack (type 9): aggressive DIS blast ===== */
#if defined(RPL_ATTACK_TYPE) && (RPL_ATTACK_TYPE == 9)
#ifndef RPL_ATTACKER_ID_MIN
#define RPL_ATTACKER_ID_MIN RPL_ATTACKER_ID
#endif
#ifndef RPL_ATTACKER_ID_MAX
#define RPL_ATTACKER_ID_MAX RPL_ATTACKER_ID
#endif
    if(node_id >= RPL_ATTACKER_ID_MIN && node_id <= RPL_ATTACKER_ID_MAX) {
      int hf;
      for(hf = 0; hf < 50; hf++) {
        rpl_icmp6_dis_output(NULL); /* heavy multicast DIS flood */
      }
    }
#endif
    if(NETSTACK_ROUTING.node_is_reachable() &&
        NETSTACK_ROUTING.get_root_ipaddr(&dest_ipaddr)) {
      print_features();
      snprintf(str, sizeof(str), "hello %" PRIu32 "", tx_count);
      simple_udp_sendto(&udp_conn, str, strlen(str), &dest_ipaddr);
      tx_count++;
    } else {
      LOG_INFO("Not reachable yet\n");
      if(tx_count > 0) {
        missed_tx_count++;
      }
    }
    etimer_set(&periodic_timer, SEND_INTERVAL
      - CLOCK_SECOND + (random_rand() % (2 * CLOCK_SECOND)));
  }
  PROCESS_END();
}
/*---------------------------------------------------------------------------*/
