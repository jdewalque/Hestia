# Architecture et fonctionnalités

Vue d'ensemble du projet pour quelqu'un qui découvre le code : ce que fait le
bijou, ce qui se passe en arrière-plan, comment une alerte arrive jusqu'aux
contacts, et ce qui est envisagé pour la suite. Les détails se trouvent dans
les documents cités au fil du texte.

## Les éléments

```
                      Bluetooth                    réseau mobile (LTE-M / NB-IoT)
  Application  ◄──────────────────►  Bijou  ─────────────────────────────────────┐
  (réglages)                          │                                         │
                                      │ SMS direct (modem)                       ▼
                                      ▼                                     nRF Cloud
                                  Contacts  ◄── SMS / WhatsApp ── Twilio ◄── Serveur
                                      ▲                                  d'alertes
                                      └──────── notification ── ntfy ◄─────────┘
```

| Élément | Dossier | Rôle |
|---|---|---|
| **Bijou** | `firmware/` | Prototype sur Thingy:91 X. Un appui long sur le bouton localise le bijou et envoie l'alerte. |
| **Application mobile** | `app/` | Flutter, Android et iPhone. Sert seulement à régler le bijou (contacts, nom, message) et à lancer une alerte de test. |
| **nRF Cloud** | (service de Nordic) | Reçoit les alertes du bijou, convertit les relevés Wi-Fi et d'antennes en coordonnées, et pousse les alertes au serveur. |
| **Serveur d'alertes** | `server/` | Worker Cloudflare. Transforme chaque alerte reçue de nRF Cloud en SMS ou WhatsApp (par Twilio) et en notification (par ntfy). Il ne stocke rien. |

**Les alertes ne passent jamais par le téléphone ni par le Bluetooth** : elles
partent du bijou par le réseau mobile. L'application peut être fermée, ou le
téléphone loin.

## Le bijou

### Deux puces, une seule programmée par nous

Le Thingy:91 X contient :

- le **nRF9151**, qui fait tourner le firmware Hestia : modem LTE-M / NB-IoT
  avec SIM, bouton, voyant, mémoire des réglages ;
- le **nRF5340**, qui gère le Bluetooth avec le firmware d'origine de Nordic
  (« connectivity bridge »). Il relaie tel quel ce qui passe entre le
  téléphone et la liaison série du nRF9151 ;
- le **nRF7002**, puce Wi-Fi utilisée seulement pour lister les bornes
  visibles. Le bijou ne se connecte jamais à un réseau Wi-Fi.

Le GPS du Thingy n'est pas utilisé : il est trop lent et rarement utilisable
en intérieur.

### Ce qui tourne en permanence

| Quoi | Fréquence | Ce que ça fait | Code |
|---|---|---|---|
| **Relevé des bornes Wi-Fi** | 30 s après l'allumage, puis toutes les 5 min | Liste les bornes visibles et garde le relevé en mémoire avec son heure. **Rien n'est envoyé.** Un relevé sans borne ne remplace pas le précédent. | `src/position.c` |
| **Inscription au réseau mobile** | en continu | Le modem reste inscrit et dort entre deux échanges (veille longue demandée au réseau, réveil toutes les 8 h). | `src/net.c` |
| **Session nRF Cloud** | ouverte au démarrage | Gardée ouverte pour que la première alerte parte vite ; rouverte si elle semble rompue. | `src/net.c` |
| **Écoute de l'application** | en continu | Attend les commandes de l'application sur la liaison série (lignes JSON). | `src/link.c` |
| **Bouton et voyant** | sur événement | Détecte l'appui long, affiche l'état. | `src/ui.c` |

La mémoire des relevés est perdue si le bijou s'éteint.

### Déroulement d'une alerte

1. **Appui maintenu 1,5 s** sur le bouton. Le voyant passe au bleu fixe dès
   l'appui, puis au rouge clignotant quand l'alerte part.
2. **Attente du réseau mobile**, 2 minutes au plus.
3. **Localisation** (`src/position.c`). Le relevé en arrière-plan est
   suspendu. Le bijou relève les bornes Wi-Fi et les antennes mobiles
   (15 s au plus), puis demande à nRF Cloud de convertir, dans cet ordre,
   jusqu'à obtenir une position (20 s au plus) :
   1. les bornes Wi-Fi actuelles ;
   2. les bornes Wi-Fi en mémoire, si elles ont moins de 30 minutes ;
   3. les antennes actuelles ;
   4. les bornes Wi-Fi en mémoire plus anciennes.

   Une position tirée de la mémoire est envoyée avec son âge.
4. **Envoi à nRF Cloud** (`src/alert.c`, `src/alert_json.c`). Message JSON
   `HESTIA_ALERT` avec le nom, le message, la batterie, les numéros des
   contacts et la position. Dès que nRF Cloud en accuse réception, l'alerte
   est réussie et le voyant passe au vert.
5. **SMS direct** à chaque contact, envoyés par le modem du bijou
   (`src/text.c` rédige le texte). Si le réseau n'achemine pas les SMS, le
   bijou n'essaie pas les contacts suivants.
6. **Reprise** des relevés en arrière-plan.

L'alerte réussit dès qu'une des deux voies (nRF Cloud ou SMS direct)
fonctionne. Le voyant passe au rouge fixe si aucune n'a marché.

Exemple de SMS :

```
Marie a besoin d'aide.
Dernière position connue, il y a 7 min (à environ 20 m près) : https://maps.google.com/?q=50.84673,4.35247
```

Sans le « Dernière position connue », la position est actuelle. Sans position
du tout : « Position inconnue pour le moment. »

### Pourquoi deux voies d'envoi

- **Par nRF Cloud et le serveur** : fonctionne même sur les réseaux qui
  n'acheminent pas les SMS (NB-IoT chez Proximus, par exemple), et permet
  d'ajouter d'autres canaux (WhatsApp, notifications).
- **SMS direct par le modem** : fonctionne même si nRF Cloud ou le serveur
  sont injoignables, à condition que la SIM et le réseau acheminent les SMS.

Quand les deux marchent, les contacts reçoivent le message deux fois.

## Le chemin côté serveur

```
Bijou ─CoAP─► nRF Cloud ─HTTP (Message Routing)─► Serveur ─► Twilio ─► SMS ou WhatsApp
                                                     └─────► ntfy ───► notification
```

1. nRF Cloud pousse chaque message du bijou au serveur, avec un jeton et une
   signature que le serveur vérifie.
2. Le serveur ne garde que les messages `HESTIA_ALERT`, nettoie les numéros
   (`src/alert.js`), puis rédige le même texte que le bijou.
3. Il envoie :
   - un SMS par contact via Twilio, ou un message WhatsApp si l'expéditeur
     Twilio est un numéro WhatsApp (`src/twilio.js`) ;
   - une notification ntfy si un sujet est configuré (`src/ntfy.js`). Toucher
     la notification ouvre la carte.

Le serveur ne stocke rien : les numéros des contacts arrivent dans chaque
alerte. Mise en service, réglages et essais : `server/README.md`.

## L'application

- **Réglages** : contacts d'urgence (5 au plus), nom du porteur, message.
  Enregistrés dans le téléphone, puis envoyés au bijou dès qu'il est à
  portée. Si l'envoi échoue, il est refait à la connexion suivante.
- **État du bijou** : batterie et réseau mobile, redemandés toutes les
  30 secondes quand l'application est ouverte.
- **Alerte de test** : le bijou envoie une vraie alerte marquée « TEST - pas
  d'urgence ».
- **Reconnexion automatique** : l'application se reconnecte dès que le bijou
  revient à portée.
- **Mode démonstration** (`app/lib/jewel/demo_jewel.dart`) : un bijou simulé
  qui répond comme le vrai, pour essayer l'application sans Thingy.

Les commandes échangées (`get_status`, `get_config`, `set_config`,
`test_alert`) et leurs erreurs sont décrites dans `docs/protocole-ble.md`.

## Organisation du code

### `firmware/src/`

| Fichier | Rôle |
|---|---|
| `main.c` | Démarrage des modules. |
| `ui.c` | Bouton et voyant. |
| `alert.c` | Déroulement d'une alerte : localisation, nRF Cloud, SMS. |
| `position.c` | Relevés Wi-Fi en arrière-plan, relevé de l'alerte, conversion en position par nRF Cloud. |
| `alert_json.c` | Message d'alerte envoyé à nRF Cloud. |
| `text.c` | Rédaction des SMS, conversion des caractères. |
| `net.c` | Réseau mobile et session nRF Cloud. |
| `link.c` | Dialogue avec l'application (lignes JSON sur la liaison série). |
| `config.c`, `config_json.c` | Réglages : stockage en mémoire flash et JSON. |
| `battery.c` | Niveau de batterie, estimé d'après la tension. |

La logique indépendante du matériel (SMS, JSON, réglages) est testée sur PC :
`firmware/tests/`.

### `server/src/`

| Fichier | Rôle |
|---|---|
| `index.js` | Réception des messages de nRF Cloud, vérification du jeton et de la signature, envoi. |
| `alert.js` | Lecture des alertes et rédaction des SMS. |
| `twilio.js` | Envoi par SMS ou WhatsApp via Twilio. |
| `ntfy.js` | Envoi en notification ntfy. |

Tests : `server/test/`, lancés avec `npm test`.

### `app/lib/`

| Fichier | Rôle |
|---|---|
| `main.dart`, `theme.dart` | Démarrage et apparence. |
| `app_state.dart` | État de l'application : réglages, synchronisation, état du bijou. |
| `models.dart` | Réglages et contacts. |
| `jewel/` | Liaison avec le bijou : Bluetooth (`ble_jewel.dart`), bijou simulé (`demo_jewel.dart`), format des messages (`protocol.dart`). |
| `screens/` | Écrans : bienvenue, accueil, contacts, message, test. |

## Fonctionnalités

### En place

- Alerte par appui long, envoyée à nRF Cloud et par SMS direct.
- Localisation par Wi-Fi puis antennes mobiles, convertie par nRF Cloud.
- Relevé Wi-Fi toutes les 5 minutes, gardé en mémoire sans rien envoyer, et
  utilisé comme dernière position connue si l'alerte ne trouve pas de borne.
- Âge de la position indiqué dans le SMS, le message nRF Cloud et les envois
  du serveur.
- Serveur d'alertes : SMS ou WhatsApp par Twilio, notifications ntfy.
- Application de réglage par Bluetooth, avec alerte de test et mode
  démonstration.
- Niveau de batterie et état du réseau visibles dans l'application.

### Envisagé

Surtout pour la consommation. Le détail et les chiffres sont dans
`docs/consommation.md` : environ 5 jours sur 250 mAh aujourd'hui, 3,5 à
7 semaines avec les trois premières pistes.

| Piste | Intérêt | Contrepartie |
|---|---|---|
| Relevé Wi-Fi en arrière-plan sur le 2,4 GHz seulement (1 s au lieu de 4,65 s) | Environ −16 mAh par jour, la moitié de la consommation actuelle | Les bornes 5 GHz ne sont plus mémorisées ; le relevé de l'alerte reste complet |
| Liaison série du nRF9151 réveillée à la demande | Environ −11 mAh par jour | L'application doit envoyer un message de réveil ou réessayer une fois |
| Application connectée seulement quand on l'ouvre | Jusqu'à −20 mAh par jour | L'état du bijou n'est plus suivi en continu |
| Relevé Wi-Fi seulement quand le bijou bouge (accéléromètre du Thingy) | Encore moins de relevés | Plus de code |
| Firmware du nRF5340 modifié (liaison série fermée au repos, échanges espacés) | Garde une connexion permanente à moindre coût | Un second firmware à compiler et installer |
| Noter le canal de chaque borne relevée pendant quelques jours | Vérifier ce qu'on perdrait en réduisant le relevé | — |
| Garder le dernier relevé en mémoire flash | Dernière position connue même après un redémarrage | Écritures en flash |
| Mesurer la consommation réelle (Power Profiler Kit II) | Remplacer les estimations par des mesures | Matériel de mesure |

Écarté : la localisation par Bluetooth. Le nRF5340 garde le firmware de
Nordic, et nRF Cloud ne sait convertir que les bornes Wi-Fi et les antennes
mobiles.

## Limites connues du prototype

- **Bluetooth non sécurisé** : toute personne à portée peut lire et modifier
  les réglages.
- **Les numéros des contacts transitent par nRF Cloud**, dans chaque alerte.
- **SMS directs** : ils demandent une SIM et un réseau qui acheminent les
  SMS. Avec la SIM Proximus essayée, le bijou n'est accepté qu'en NB-IoT, où
  les SMS ne passent pas.
- **Batterie estimée** d'après la tension : approximative.
- **Consommation non optimisée** : voir `docs/consommation.md`.

## Pour aller plus loin

- `firmware/README.md` : compiler, flasher, voyant, format du message
  nRF Cloud, localisation en détail.
- `server/README.md` : déployer le serveur, Twilio, WhatsApp, ntfy.
- `docs/protocole-ble.md` : dialogue entre l'application et le bijou.
- `docs/consommation.md` : consommation estimée, autonomie et pistes.
