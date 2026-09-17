#ifndef PROJECT_CONF_H_
#define PROJECT_CONF_H_
#define ENERGEST_CONF_ON 1
#define IEEE802154_CONF_PANID 0x8921
#define TSCH_CONF_RX_WAIT 1000
#define TSCH_CONF_EB_PERIOD (2 * CLOCK_SECOND)
#define TSCH_CONF_MAX_EB_PERIOD (2 * CLOCK_SECOND)
#define TSCH_CONF_KEEPALIVE_TIMEOUT (10 * CLOCK_SECOND)
#define NETSTACK_MAX_ROUTE_ENTRIES 60
#define NBR_TABLE_CONF_MAX_NEIGHBORS 16
#define LOG_CONF_LEVEL_MAC LOG_LEVEL_NONE
#define LOG_CONF_LEVEL_TCPIP LOG_LEVEL_NONE

/* ===== Attack configuration =====
 * To run NORMAL: comment out RPL_ATTACK_TYPE below.
 * To run an ATTACK: set RPL_ATTACK_TYPE to 1/2/3 and choose attacker(s).
 *   1 = Decreased Rank, 2 = Version Number, 3 = DIS Flooding
 * Attacker: single RPL_ATTACKER_ID, or a range via _MIN/_MAX. */

#define RPL_ATTACK_TYPE 1
#define RPL_ATTACKER_ID 8

#endif /* PROJECT_CONF_H_ */
