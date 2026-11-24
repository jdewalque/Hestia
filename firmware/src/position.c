#include <errno.h>
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include <modem/location.h>
#include <modem/lte_lc.h>
#include <net/nrf_cloud_coap.h>
#include <net/nrf_cloud_location.h>
#include <net/wifi_location_common.h>

#include "net.h"
#include "position.h"

LOG_MODULE_REGISTER(position, LOG_LEVEL_INF);

/* Relevés Wi-Fi en arrière-plan : le premier peu après le démarrage, puis
 * toutes les 5 minutes. Chacun allume le Wi-Fi quelques secondes, sans rien
 * émettre. Les antennes mobiles ne sont relevées qu'au moment de l'alerte :
 * elle attend de toute façon le réseau mobile pour partir.
 */
#define BACKGROUND_FIRST           K_SECONDS(30)
#define BACKGROUND_PERIOD          K_MINUTES(5)
#define BACKGROUND_SCAN_TIMEOUT_MS (10 * MSEC_PER_SEC)

/* Relevé au moment de l'alerte : il ne doit pas la retarder. */
#define ALERT_SCAN_TIMEOUT_MS (15 * MSEC_PER_SEC)
/* Temps laissé à nRF Cloud pour convertir les relevés, tous essais confondus. */
#define ALERT_RESOLVE_BUDGET_MS (20 * MSEC_PER_SEC)

/* Au-delà de cet âge, des bornes Wi-Fi mémorisées sont moins utiles que les
 * antennes actuelles : la personne a pu se déplacer.
 */
#define STORED_WIFI_MAX_AGE_S (30 * 60)

#define MAX_APS   CONFIG_LOCATION_METHOD_WIFI_SCANNING_RESULTS_MAX_CNT
#define MAX_CELLS CONFIG_LTE_NEIGHBOR_CELLS_MAX

/* Bornes Wi-Fi vues lors d'un relevé. */
struct wifi_record {
	bool valid;
	int64_t time_ms;
	struct wifi_scan_result aps[MAX_APS];
	struct wifi_scan_info info;
};

/* Antennes mobiles vues lors d'un relevé. */
struct cell_record {
	bool valid;
	int64_t time_ms;
	struct lte_lc_ncell neighbors[MAX_CELLS];
	struct lte_lc_cell gci[MAX_CELLS];
	struct lte_lc_cells_info info;
};

/* Dernier relevé Wi-Fi utile. Un relevé sans borne ne remplace pas le précédent. */
static struct wifi_record stored_wifi;
/* Relevés faits au moment de l'alerte. */
static struct wifi_record fresh_wifi;
static struct cell_record fresh_cells;
/* Où ranger le relevé en cours (NULL : pas demandé). */
static struct wifi_record *volatile wifi_target;
static struct cell_record *volatile cells_target;

/* Une seule demande à la bibliothèque de localisation à la fois. */
static K_MUTEX_DEFINE(lock);
static K_SEM_DEFINE(scan_done, 0, 1);
static atomic_t paused;

static void wifi_copy(struct wifi_record *dst, const struct wifi_scan_info *src, int64_t time_ms)
{
	uint16_t cnt = MIN(src->cnt, MAX_APS);

	memcpy(dst->aps, src->ap_info, cnt * sizeof(dst->aps[0]));
	dst->info.ap_info = dst->aps;
	dst->info.cnt = cnt;
	dst->time_ms = time_ms;
	dst->valid = true;
}

static void cells_copy(struct cell_record *dst, const struct lte_lc_cells_info *src,
		       int64_t time_ms)
{
	uint8_t ncells = src->neighbor_cells ? MIN(src->ncells_count, MAX_CELLS) : 0;
	uint8_t gci = src->gci_cells ? MIN(src->gci_cells_count, MAX_CELLS) : 0;

	dst->info.current_cell = src->current_cell;
	memcpy(dst->neighbors, src->neighbor_cells, ncells * sizeof(dst->neighbors[0]));
	dst->info.neighbor_cells = dst->neighbors;
	dst->info.ncells_count = ncells;
	memcpy(dst->gci, src->gci_cells, gci * sizeof(dst->gci[0]));
	dst->info.gci_cells = dst->gci;
	dst->info.gci_cells_count = gci;
	dst->time_ms = time_ms;
	dst->valid = true;
}

static uint32_t age_s(int64_t time_ms)
{
	return (uint32_t)((k_uptime_get() - time_ms) / MSEC_PER_SEC);
}

/*
 * La bibliothèque est en mode « service externe » : elle fait les relevés et
 * nous les confie au lieu de les envoyer elle-même à nRF Cloud. On les range,
 * et c'est position_get() qui décidera de les faire convertir.
 */
static void location_handler(const struct location_event_data *event)
{
	switch (event->id) {
	case LOCATION_EVT_CLOUD_LOCATION_EXT_REQUEST: {
		const struct location_data_cloud *data = &event->cloud_location_request;
		struct wifi_record *wifi = wifi_target;
		struct cell_record *cells = cells_target;
		int64_t now = k_uptime_get();

		if (wifi != NULL && data->wifi_data != NULL) {
			wifi_copy(wifi, data->wifi_data, now);
		}
		if (cells != NULL && data->cell_data != NULL) {
			cells_copy(cells, data->cell_data, now);
		}
		/* Rien n'est envoyé ici : la bibliothèque clôt la demande. */
		location_cloud_location_ext_result_set(LOCATION_EXT_RESULT_UNKNOWN, NULL);
		return;
	}
	case LOCATION_EVT_RESULT_UNKNOWN:
	case LOCATION_EVT_LOCATION:
		break;
	case LOCATION_EVT_TIMEOUT:
		LOG_WRN("Relevé : délai dépassé");
		break;
	case LOCATION_EVT_ERROR:
		/* Aussi quand aucune borne ni antenne n'est visible. */
		LOG_WRN("Relevé : rien trouvé");
		break;
	default:
		/* Événements intermédiaires (démarrage, changement de méthode…). */
		return;
	}
	k_sem_give(&scan_done);
}

/*
 * Relève les bornes Wi-Fi dans @p wifi et, si @p cells n'est pas NULL, les
 * antennes mobiles dans @p cells. Le verrou doit être pris.
 */
static void scan(struct wifi_record *wifi, struct cell_record *cells, int32_t timeout_ms)
{
	struct location_config config;
	/* Wi-Fi et antennes côte à côte : la bibliothèque fait les deux relevés
	 * en même temps et les rend ensemble.
	 */
	enum location_method methods[] = {LOCATION_METHOD_WIFI, LOCATION_METHOD_CELLULAR};
	int err;

	location_config_defaults_set(&config, cells ? ARRAY_SIZE(methods) : 1, methods);
	config.methods[0].wifi.timeout = timeout_ms;
	if (cells != NULL) {
		config.methods[1].cellular.timeout = timeout_ms;
	}
	config.timeout = timeout_ms + 5 * MSEC_PER_SEC;

	wifi_target = wifi;
	cells_target = cells;
	k_sem_reset(&scan_done);

	err = location_request(&config);
	if (err) {
		LOG_ERR("location_request: %d", err);
	} else if (k_sem_take(&scan_done, K_MSEC(config.timeout + 5 * MSEC_PER_SEC)) != 0) {
		LOG_WRN("Relevé sans réponse, annulation");
		(void)location_request_cancel();
	}
	wifi_target = NULL;
	cells_target = NULL;
}

static void background_thread(void *p1, void *p2, void *p3)
{
	k_sleep(BACKGROUND_FIRST);

	while (true) {
		k_mutex_lock(&lock, K_FOREVER);
		if (!atomic_get(&paused)) {
			scan(&stored_wifi, NULL, BACKGROUND_SCAN_TIMEOUT_MS);
			LOG_INF("Relevé en mémoire : %d borne(s) Wi-Fi (il y a %u s)",
				stored_wifi.valid ? stored_wifi.info.cnt : 0,
				stored_wifi.valid ? age_s(stored_wifi.time_ms) : 0);
		}
		k_mutex_unlock(&lock);
		k_sleep(BACKGROUND_PERIOD);
	}
}

K_THREAD_DEFINE(background_tid, 2048, background_thread, NULL, NULL, NULL,
		K_LOWEST_APPLICATION_THREAD_PRIO, 0, SYS_FOREVER_MS);

enum resolve_result {
	RESOLVED,
	/* nRF Cloud ne connaît pas ces bornes ou ces antennes. */
	NOT_FOUND,
	/* nRF Cloud est injoignable : inutile d'essayer d'autres relevés. */
	CLOUD_DOWN,
};

/* Une piste pour trouver la position : un relevé Wi-Fi, ou d'antennes. */
struct attempt {
	struct wifi_record *wifi;
	struct cell_record *cells;
	/* Relevé fait pendant l'alerte : la position est actuelle. */
	bool current;
	const char *what;
};

/* Fait convertir un relevé en coordonnées par nRF Cloud. */
static enum resolve_result resolve(const struct attempt *attempt, struct text_position *out)
{
	struct nrf_cloud_coap_location_request request = {
		.wifi_info = attempt->wifi ? &attempt->wifi->info : NULL,
		.cell_info = attempt->cells ? &attempt->cells->info : NULL,
	};
	struct nrf_cloud_location_result result = {.type = LOCATION_TYPE__INVALID};
	int64_t time_ms = attempt->wifi ? attempt->wifi->time_ms : attempt->cells->time_ms;
	int err = nrf_cloud_coap_location_get(&request, &result);

	if (err < 0 && err != -EINVAL && err != -ENOMEM && err != -E2BIG && err != -ENOBUFS &&
	    err != -EBADMSG) {
		LOG_WRN("%s : nRF Cloud injoignable (%d)", attempt->what, err);
		/* La session est peut-être rompue : elle sera rouverte la prochaine fois. */
		net_cloud_invalidate();
		return CLOUD_DOWN;
	}
	if (err != 0 || result.err != NRF_CLOUD_ERROR_NONE ||
	    result.type == LOCATION_TYPE__INVALID) {
		LOG_WRN("%s : position introuvable (%d)", attempt->what, err);
		return NOT_FOUND;
	}

	out->latitude = result.lat;
	out->longitude = result.lon;
	out->accuracy = (float)result.unc;
	out->age_s = attempt->current ? 0 : age_s(time_ms);
	LOG_INF("Position obtenue par %s (marge %u m, âge %u s)", attempt->what,
		result.unc, out->age_s);
	return RESOLVED;
}

/*
 * Essaie les relevés du plus utile au moins utile, jusqu'à obtenir une
 * position :
 *   1. bornes Wi-Fi actuelles ;
 *   2. bornes Wi-Fi mémorisées, si elles ont moins de 30 minutes ;
 *   3. antennes actuelles ;
 *   4. bornes Wi-Fi mémorisées plus anciennes.
 */
static bool resolve_best(struct text_position *out)
{
	struct attempt attempts[4];
	int count = 0;
	bool stored_wifi_recent =
		stored_wifi.valid && age_s(stored_wifi.time_ms) <= STORED_WIFI_MAX_AGE_S;
	int64_t deadline;

	if (fresh_wifi.valid) {
		attempts[count++] = (struct attempt){
			.wifi = &fresh_wifi, .current = true, .what = "Wi-Fi actuel"};
	}
	if (stored_wifi_recent) {
		attempts[count++] = (struct attempt){
			.wifi = &stored_wifi, .what = "Wi-Fi mémorisé"};
	}
	if (fresh_cells.valid) {
		attempts[count++] = (struct attempt){
			.cells = &fresh_cells, .current = true, .what = "antennes actuelles"};
	}
	if (stored_wifi.valid && !stored_wifi_recent) {
		attempts[count++] = (struct attempt){
			.wifi = &stored_wifi, .what = "ancien Wi-Fi mémorisé"};
	}

	if (count == 0) {
		LOG_WRN("Aucune borne ni antenne relevée");
		return false;
	}
	if (net_cloud_ensure() != 0) {
		return false;
	}

	deadline = k_uptime_get() + ALERT_RESOLVE_BUDGET_MS;
	for (int i = 0; i < count; i++) {
		if (k_uptime_get() > deadline) {
			LOG_WRN("Localisation : délai dépassé");
			break;
		}
		switch (resolve(&attempts[i], out)) {
		case RESOLVED:
			return true;
		case CLOUD_DOWN:
			return false;
		case NOT_FOUND:
			break;
		}
	}
	return false;
}

bool position_get(struct text_position *out)
{
	bool found;

	atomic_set(&paused, 1);

	/* Un relevé en arrière-plan en cours ne doit pas retarder l'alerte. */
	if (k_mutex_lock(&lock, K_NO_WAIT) != 0) {
		LOG_INF("Relevé en arrière-plan interrompu");
		(void)location_request_cancel();
		k_sem_give(&scan_done);
		k_mutex_lock(&lock, K_FOREVER);
	}

	/* Ouvre la session nRF Cloud avant le relevé, pour qu'elle soit prête à
	 * convertir les relevés aussitôt.
	 */
	(void)net_cloud_ensure();

	fresh_wifi.valid = false;
	fresh_cells.valid = false;
	scan(&fresh_wifi, &fresh_cells, ALERT_SCAN_TIMEOUT_MS);

	found = resolve_best(out);

	/* Le relevé Wi-Fi de l'alerte devient le plus récent en mémoire. */
	if (fresh_wifi.valid) {
		wifi_copy(&stored_wifi, &fresh_wifi.info, fresh_wifi.time_ms);
	}

	k_mutex_unlock(&lock);
	return found;
}

void position_resume(void)
{
	atomic_clear(&paused);
}

int position_init(void)
{
	int err = location_init(location_handler);

	if (err) {
		LOG_ERR("location_init: %d", err);
		return err;
	}
	k_thread_start(background_tid);
	return 0;
}
