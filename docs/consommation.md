# Consommation et autonomie du bijou

Estimation théorique, faite le 20 novembre 2026 sur le firmware qui relève les
bornes Wi-Fi toutes les 5 minutes (voir « Localisation » dans
`firmware/README.md`). **Rien n'a encore été mesuré** : les chiffres viennent
de la documentation de Nordic et d'estimations, indiquées comme telles.

## En bref

Avec une batterie de **250 mAh**, le bijou tiendrait **environ 5 jours**,
entre 3 et 7 jours selon les conditions.

Trois postes font 93 % de la consommation, et aucun n'est lié aux alertes :

1. les relevés Wi-Fi toutes les 5 minutes (la moitié) ;
2. les liaisons série du nRF9151, actives en permanence (un quart) ;
3. la connexion Bluetooth avec le téléphone (un cinquième).

Les alertes elles-mêmes coûtent peu : 3 par jour, c'est moins de 3 % du total.
En corrigeant les trois postes ci-dessus, sans perdre de fonction, on peut
viser **environ 3,5 à 7 semaines**, selon la réduction choisie pour le relevé
Wi-Fi (voir « Pistes »).

Les deux derniers postes viennent en fait tous les deux du Bluetooth : au
total, il pèse environ 45 % de la consommation (voir « Le Bluetooth en
détail »).

## Hypothèses

- **3 alertes par jour**, chacune envoyée à nRF Cloud et par SMS à quelques
  contacts. C'est volontairement beaucoup.
- **Un relevé Wi-Fi toutes les 5 minutes**, soit 288 par jour.
- **Veille longue du modem accordée par le réseau** (PSM). Le firmware la
  demande : réveil toutes les 8 heures pour rester inscrit, 8 secondes
  d'écoute après chaque échange (`prj.conf`).
- **Téléphone connecté une partie de la journée.** L'application se
  reconnecte toute seule dès que le bijou est à portée (`autoConnect` dans
  `app/lib/jewel/ble_jewel.dart`). On compte 2 h, 12 h ou 20 h de connexion
  par jour selon le cas.
- **Environ 212 mAh réellement utilisables** sur 250 mAh (85 %). Le firmware
  compte 0 % à 3,3 V, et le froid et l'usure réduisent la capacité.

## Consommation par poste

En mAh par jour.

| Poste | Optimiste | Typique | Pessimiste | D'où vient le chiffre |
|---|---|---|---|---|
| Relevés Wi-Fi toutes les 5 min | 20 | 21,5 | 24 | Nordic : un relevé complet (2,4 et 5 GHz) dure 4,65 s à 55 mA, soit 0,07 mAh par relevé, plus le processeur réveillé pendant ce temps |
| Liaisons série du nRF9151, toujours actives | 9,6 | 11 | 14,4 | Nordic : 470 µA avec une liaison série active, contre 6 µA sans. Soit 0,40 à 0,60 mA en continu. UART0 relie le nRF9151 à la puce Bluetooth : ce poste fait donc partie du coût du Bluetooth. UART1 porte les journaux |
| Bluetooth connecté au téléphone | 1 | 7,8 | 20 | 2, 12 ou 20 h par jour, à 0,5–1 mA. Estimation : la puce Bluetooth (nRF5340) ouvre sa propre liaison série vers le nRF9151 pendant toute la connexion |
| Veille du reste de la carte | 0,7 | 1,2 | 2,4 | 30 à 100 µA en tout : nRF9151 et modem en veille (environ 6 µA), puce Wi-Fi endormie (environ 15 µA), annonces Bluetooth, gestion d'alimentation, capteurs inutilisés |
| Réseau mobile hors alertes | 0,1 | 0,3 | 1 | Réveils du modem pour rester inscrit (3 par jour), mise à l'heure |
| 3 alertes | 0,45 | 1,2 | 4,5 | 0,15, 0,4 ou 1,5 mAh par alerte (voir ci-dessous) |
| Auto-décharge de la batterie | 0,17 | 0,25 | 0,4 | 2 à 5 % par mois |
| **Total** | **32** | **43** | **67** | |

Répartition dans le cas typique :

```
Relevés Wi-Fi             ██████████████████████████  21,5 mAh  50 %
Liaisons série nRF9151    █████████████               11   mAh  25 %
Bluetooth connecté        █████████                    7,8 mAh  18 %
3 alertes                 █                            1,2 mAh   3 %
Veille du reste           █                            1,2 mAh   3 %
Réseau hors alertes                                    0,3 mAh   1 %
Auto-décharge                                          0,25 mAh  1 %
```

## Autonomie

| | Optimiste | Typique | Pessimiste |
|---|---|---|---|
| Consommation par jour | 32 mAh | 43 mAh | 67 mAh |
| **Batterie de 250 mAh** | **~6,5 jours** | **~5 jours** | **~3 jours** |
| Batterie du Thingy:91 X (1 300 mAh) | ~34 jours | ~25 jours | ~16 jours |

La dernière ligne sert de contrôle : si le prototype tient 3 à 4 semaines par
charge, l'estimation est cohérente.

## Coût d'une alerte

| Étape | Typique |
|---|---|
| Relevé Wi-Fi et antennes mobiles | 0,09 mAh |
| Session sur le réseau mobile : envoi à nRF Cloud, conversion de la position, SMS, puis 10 à 60 s où le modem reste connecté | 0,25 mAh |
| Voyant et processeur | 0,05 mAh |
| **Total** | **0,4 mAh** |

Les cas extrêmes vont de 0,15 mAh (bonne couverture, réseau rapide) à 1,5 mAh
(couverture faible, session nRF Cloud à rouvrir, SMS qui attendent 30 s une
réponse du réseau).

Point de comparaison : Nordic a mesuré 0,032 mAh pour l'envoi de 40 octets sur
un vrai réseau, modem resté connecté compris. Même avec 10 alertes par jour,
on n'ajouterait qu'environ 4 mAh par jour.

## Pistes

Ces changements gardent toutes les fonctions actuelles.

| Changement | Gain par jour | Contrepartie |
|---|---|---|
| Réduire le relevé Wi-Fi en arrière-plan : tout le 2,4 GHz (1 s) ou seulement les canaux 1, 6 et 11 (0,2 s), au lieu de 4,65 s. Le relevé de l'alerte reste complet | −16 à −20 mAh | Moins de bornes vues entre les alertes (voir « Relever moins de canaux Wi-Fi ») |
| Ou ne relever que quand le bijou bouge, grâce à l'accéléromètre basse consommation du Thingy | encore plus | Plus de code |
| Réveiller la liaison série seulement quand l'application parle | environ −11 mAh | Le premier message après un silence peut se perdre. L'application devra envoyer un message de réveil, ou réessayer une fois : aujourd'hui, elle ne redemande que l'état (toutes les 30 s) et renvoie les réglages à la connexion suivante |
| L'application se connecte quand on l'ouvre, au lieu de rester connectée | −1 à −20 mAh | L'application ne suit plus l'état du bijou en continu (voir « Le Bluetooth en détail ») |

Gain de chaque étape, dans le cas typique, selon la réduction du relevé Wi-Fi :

| Après… | Tout le 2,4 GHz (recommandé) | Canaux 1, 6 et 11 seulement |
|---|---|---|
| Aujourd'hui | 43 mAh par jour · ~5 jours | 43 mAh par jour · ~5 jours |
| Relevé Wi-Fi réduit | 27 mAh par jour · ~8 jours | 23 mAh par jour · ~9 jours |
| … et liaison série à la demande | 16 mAh par jour · ~13 jours | 12 mAh par jour · ~18 jours |
| … et application connectée seulement à l'ouverture | ~8 mAh par jour · **~3,5 semaines** | ~4 mAh par jour · **~7 semaines** |

Dans la dernière ligne, ce sont le relevé Wi-Fi, les alertes et la veille de
la carte qui deviennent les postes principaux.

Réduire le relevé Wi-Fi est le plus gros gain et le plus simple : il suffit
de passer des paramètres de relevé (bande et canaux) au module Wi-Fi.

## Relever moins de canaux Wi-Fi : ce qu'on perd

Relever moins de canaux ne donne **pas exactement les mêmes chances** : on
voit moins de bornes. La perte est en général faible, et elle ne touche que le
relevé de secours, fait en arrière-plan. Le relevé de l'alerte reste complet.

### Comment se passe un relevé

La puce Wi-Fi écoute les canaux un par un et note les bornes qu'elle entend.

- **2,4 GHz** : 13 canaux en Europe, qui se chevauchent. Les bornes se
  mettent presque toutes sur 1, 6 ou 11, les seuls qui ne se chevauchent pas.
  C'est rapide : environ 1 s pour les 13 canaux.
- **5 GHz** : environ 25 canaux. Sur beaucoup d'entre eux, la réglementation
  interdit d'interroger les bornes : il faut attendre qu'elles se signalent,
  130 ms par canal. C'est pour ça que le 5 GHz prend 3,6 s des 4,65 s d'un
  relevé complet.

### Ce qu'on perd

En ne gardant que les canaux 1, 6 et 11 :

- les bornes réglées sur un autre canal 2,4 GHz (par exemple 13 ou 3). Celles
  qui sont très proches sont parfois captées quand même ;
- toutes les bornes 5 GHz.

En gardant tout le 2,4 GHz, on ne perd que les bornes 5 GHz.

### Pourquoi la perte est souvent faible

- Les box des opérateurs émettent en 2,4 et en 5 GHz, chaque bande sous son
  propre identifiant. On la retrouve donc par son identifiant 2,4 GHz.
- Le 2,4 GHz porte plus loin à travers les murs : c'est la bande où l'on voit
  le plus de bornes.
- nRF Cloud a besoin d'au moins 2 bornes. Au-delà de 5 environ, la précision
  gagne peu.

### Où ça peut coûter

- **Endroit avec très peu de bornes** (campagne, maison isolée) : on risque
  de passer sous 2 bornes. Il n'y a alors plus de position Wi-Fi en mémoire,
  et l'alerte se rabat sur les antennes mobiles, moins précises.
- **Précision un peu moins bonne** : une borne 5 GHz captée est en général
  plus proche.

Comme le relevé de l'alerte reste complet, ce choix ne change le résultat que
si l'alerte part d'un endroit où aucune borne n'est visible.

### Réglages possibles

Chiffres de Nordic, pour 288 relevés par jour :

| Relevé en arrière-plan | Durée | mAh par jour | Ce qu'on rate |
|---|---|---|---|
| Complet (aujourd'hui) | 4,65 s | ~21 | rien |
| **Tout le 2,4 GHz** | 1 s | **~4,6** | les bornes 5 GHz seulement |
| 2,4 GHz canaux 1, 6 et 11, et 5 GHz sans attente | 1,36 s | ~6 | une partie des deux bandes |
| 2,4 GHz canaux 1, 6 et 11 | 0,2 s | ~1 | le 5 GHz et les canaux 2,4 GHz peu utilisés |

**Recommandation : tout le 2,4 GHz.** On ne rate que les bornes 5 GHz,
rarement seules dans un logement, et on économise déjà environ 16 mAh par
jour sur 21.

Pour le vérifier : faire noter au bijou le canal de chaque borne vue pendant
les relevés complets. Quelques jours dans les lieux habituels de la personne
montreraient la part de bornes qu'on perdrait réellement.

## Le Bluetooth en détail

### Le chemin des messages

Sur le Thingy:91 X, le Bluetooth passe par deux puces :

```
Téléphone ⇄ Bluetooth ⇄ nRF5340 (firmware de Nordic) ⇄ liaison série ⇄ nRF9151 (firmware Hestia)
```

Le nRF9151 fait tourner le firmware Hestia et gère le réseau mobile, mais il
ne sait pas faire de Bluetooth. Le nRF5340 s'en charge et relaie les messages
par une liaison série (voir `docs/protocole-ble.md`).

### À quoi il sert

Le Bluetooth ne sert qu'à l'application : régler les contacts, le nom et le
message, afficher la batterie et le réseau, lancer une alerte de test. **Les
vraies alertes ne passent pas du tout par le Bluetooth**, elles partent par le
réseau mobile. Réduire le Bluetooth ne touche donc pas à la sécurité.

### Ce qu'il coûte

Le coût vient à la fois du Bluetooth « activé tout le temps » et de la
connexion au téléphone, mais surtout pas de la radio elle-même :

| Coût | Quand | Courant | mAh par jour (typique) |
|---|---|---|---|
| **Annonces** : le nRF5340 signale sa présence environ chaque seconde, pour que le téléphone le retrouve | toujours | 10–40 µA | ~0,5 |
| **Connexion entretenue** : échanges radio toutes les 15 à 50 ms, même vides, et le nRF5340 ouvre sa liaison série vers le nRF9151 | quand le téléphone est connecté | 0,5–1 mA (estimation) | ~7,8 (12 h) |
| **Écoute de la liaison série par le nRF9151**, au cas où un message arrive | toujours | 0,4–0,6 mA (Nordic) | ~11 |

En tout, environ 19 mAh par jour, soit **45 % de la consommation**. La ligne
« Liaisons série du nRF9151 » du bilan fait donc partie du coût du Bluetooth.

**Pourquoi une liaison série coûte autant :** pour recevoir un message à
n'importe quel moment, la puce doit garder son horloge rapide allumée en
permanence. Elle ne peut donc jamais passer en sommeil profond. C'est la
différence entre 470 µA et 6 µA mesurée par Nordic.

### Ce qu'on peut couper, et ce que ça change

**A. Le nRF9151 n'écoute plus en permanence (environ −11 mAh par jour).**

- On éteint la réception de la liaison série. Une simple surveillance de la
  ligne, qui ne coûte presque rien, la rallume au premier signal et la garde
  ouverte une trentaine de secondes.
- On coupe aussi les journaux (UART1) en usage normal, et on les garde pour
  le développement.
- Effet : le premier message après un silence peut se perdre. Il faut donc
  adapter l'application : envoyer d'abord un court message de réveil, ou
  réessayer une fois. Aujourd'hui elle ne le fait pas : une alerte de test
  échouerait au bout de 10 secondes.
- Tout est dans notre code (firmware et application).

**B. Le téléphone ne reste plus connecté en permanence (−1 à −20 mAh par
jour, environ −8 en typique).**

- L'application se connecte quand on l'ouvre ou quand elle a quelque chose à
  envoyer, puis se déconnecte après environ 30 secondes sans échange.
- Effets :
  - l'application n'affiche plus en continu « connecté » ou « hors de
    portée » quand elle est fermée ;
  - à l'ouverture, l'état apparaît après 1 à 3 secondes ;
  - les réglages modifiés loin du bijou partent à la connexion suivante.
    L'application sait déjà le faire.
- Seule l'application change.
- Autre solution, sans changer l'usage : modifier le firmware du nRF5340
  (Nordic fournit son code) pour qu'il ferme sa liaison série quand rien ne
  passe et espace les échanges. C'est plus de travail : un second firmware à
  compiler et à installer.

**C. Les annonces (environ 0,5 mAh par jour).** On pourrait les espacer,
toutes les 2 à 5 secondes. On gagnerait environ 0,3 mAh par jour, et le
téléphone retrouverait le bijou plus lentement. Ça ne vaut pas la peine pour
l'instant.

**A et B vont ensemble.** Avec A seul, un téléphone connecté qui redemande
l'état toutes les 30 secondes rallumerait sans cesse la liaison série. Avec
les deux, le Bluetooth passe d'environ 19 à environ 1 mAh par jour.

**Pour le vrai bijou**, c'est un point à prévoir au choix du matériel : un fil
de réveil entre les deux puces, ou une seule puce, permet aux deux côtés de
dormir.

## Ce qui peut fausser l'estimation

- **Réseau qui refuse la veille longue du modem.** Le modem reste alors à
  l'écoute, ce qui ajouterait 5 à 20 mAh par jour (estimation). Les journaux
  du modem indiquent si la veille est accordée.
- **Zone sans réseau** (cave, campagne). Le modem cherche le réseau en
  continu. En ordre de grandeur, ça viderait 250 mAh en 1 à 3 jours.
- **Pointes de courant.** L'émission mobile peut tirer plusieurs centaines de
  mA d'un coup. Une petite batterie peut alors chuter en tension et faire
  redémarrer le bijou en pleine alerte quand elle est presque vide. Il faut
  une batterie qui supporte au moins 2C (500 mA pour 250 mAh), et sans doute
  un condensateur pour amortir les pointes.
- **Bluetooth connecté.** C'est le chiffre le plus incertain : il repose sur
  une estimation, pas sur une mesure ni sur une donnée de Nordic.

## Pour mesurer

Une heure de mesure suffit pour fixer les trois gros postes. Il faut un Power
Profiler Kit II (PPK2) en source d'alimentation, branché à la place de la
batterie du Thingy:91 X, et trois mesures :

1. le bijou au repos, téléphone éloigné : veille, liaisons série et
   annonces Bluetooth ;
2. le passage d'un relevé Wi-Fi, au moins une fois toutes les 5 minutes ;
3. le téléphone connecté avec l'application ouverte.

L'Online Power Profiler de Nordic donne aussi une estimation de la partie
réseau mobile pour un opérateur et des réglages donnés.

## Sources

Documentation du nRF Connect SDK v3.4.2 (dossier `nrf/doc/nrf/`) :

- `protocols/wifi/scan_mode/scan_operation.rst` : durée et courant des
  relevés Wi-Fi selon les bandes et les canaux ;
- `protocols/wifi/station_mode/powersave.rst` : puce Wi-Fi endormie
  (environ 15 µA) ou éteinte (environ 2 µA) ;
- `test_and_optimize/optimizing/power_general.rst` : 470 µA avec une liaison
  série active, contre 6 µA sans ;
- `protocols/lte/power_nrf91.rst` : veille du modem (3,44 µA mesurés) et coût
  d'un envoi sur un vrai réseau (115 mC, soit 0,032 mAh).

Code du nRF5340 (`nrf/applications/connectivity_bridge`) : annonces Bluetooth
toutes les secondes environ, liaison série vers le nRF9151 ouverte seulement
quand un téléphone est connecté.
