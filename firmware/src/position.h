/*
 * Localisation du bijou.
 *
 * Toutes les 5 minutes, le bijou relève les bornes Wi-Fi qui l'entourent et
 * garde ce relevé en mémoire sans rien envoyer. Au moment d'une alerte, il
 * relève les bornes Wi-Fi et les antennes mobiles. Seuls les relevés utiles
 * sont envoyés à nRF Cloud, qui les convertit en coordonnées.
 */
#ifndef HESTIA_POSITION_H_
#define HESTIA_POSITION_H_

#include <stdbool.h>

#include "text.h"

/* Démarre la bibliothèque de localisation et les relevés en arrière-plan. */
int position_init(void);

/*
 * Cherche la position pour une alerte. Les relevés en arrière-plan sont
 * suspendus jusqu'à position_resume().
 *
 * Retourne true si une position est obtenue. Si elle vient d'un relevé ancien,
 * @p out->age_s indique depuis combien de secondes.
 */
bool position_get(struct text_position *out);

/* Reprend les relevés en arrière-plan. */
void position_resume(void);

#endif /* HESTIA_POSITION_H_ */
