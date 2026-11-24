# Bouton d'alerte LTE-M — état avant commande JLCPCB

État au 13 novembre 2026. Carte concernée : version rectangulaire 25 × 35 mm, 4 couches, composants sur les deux faces.

## En bref

- La carte est dessinée, routée et les fichiers de fabrication sont prêts (Gerber, nomenclature, placement).
- Devis JLCPCB pour 5 cartes montées : **287,24 $**, soit environ 57 $ par carte, hors port, TVA et douane.
- La carte livrée ne sera **pas** prête à l'emploi : il restera l'eSIM, la batterie et l'antenne à souder, et tout le logiciel à écrire et à charger.
- C'est un premier prototype jamais fabriqué. Plusieurs points de conception ne sont pas vérifiés (liste plus bas) ; une erreur sur l'un d'eux peut rendre les 5 cartes inutilisables.

## Où j'en suis

| Élément | État |
|---|---|
| Schéma KiCad | Fait, contrôle électrique sans erreur |
| Placement des composants | Fait |
| Routage | Fait par routeur automatique puis complété par script ; contrôle KiCad sans erreur ; **pas relu à la main** |
| Gerber et perçage | Générés (`kicad/gerbers/`) |
| Nomenclature JLCPCB | Faite, 23 références, toutes avec numéro LCSC (`jlcpcb/bom_jlcpcb.csv`) |
| Fichier de placement JLCPCB | Fait, 36 composants ; rotations de U1, U3 et MK1 corrigées (`jlcpcb/cpl_jlcpcb.csv`) |
| Aperçu de placement JLCPCB | Vérifié pour le nRF9151, le module ESP32, le chargeur et le bouton ; **reste à confirmer pour D1, D2, D3** et à revoir après rechargement du fichier corrigé |
| Version ovale 28 × 38 mm | Placée, non routée, pas concernée par cette commande |
| Boîtier « Galet » | Fichiers d'impression 3D prêts pour la carte ovale, pas encore imprimés |
| Logiciel | Rien d'écrit |

## Devis JLCPCB (5 cartes)

| Poste | Montant |
|---|---|
| **Circuits imprimés** | **7,37 $** |
| dont offre de base | 4,00 $ |
| dont traitement des vias | 3,37 $ |
| **Assemblage standard, deux faces** | **279,87 $** |
| Composants (23 références) | 160,26 $ |
| Mise en route | 51,50 $ |
| Chargement des bobines | 35,65 $ |
| Pochoir | 16,54 $ |
| Contrôle aux rayons X | 12,45 $ |
| Pose des composants | 2,97 $ |
| Emballage | 0,50 $ |
| **Total** | **287,24 $** |

Délai annoncé : 2 jours pour les circuits, 3 à 4 jours pour l'assemblage (2 à 3 jours pour 49,63 $ de plus).

Non compris dans ce total : le port, la TVA et les frais de douane, ainsi qu'un éventuel supplément pour le micro (voir plus bas).

### Détail des composants

Les 160,26 $ couvrent 5 cartes, soit environ 32 $ par carte. Prix à l'unité relevés dans le catalogue JLCPCB :

| Pièce | Référence | N° LCSC | Prix unitaire |
|---|---|---|---|
| Modem LTE-M + processeur | nRF9151-LACA-R7 | C22397843 | 21,20 $ |
| Module Wi-Fi + Bluetooth | ESP32-C6-MINI-1-N4 | C5736265 | 4,09 $ |
| Micro | SPH0641LU4H-1 | C2879853 | 2,09 $ |
| Alimentation 3,3 V | TPS63900DSKR | C1518762 | 1,00 $ |
| Chargeur | MCP73832T-2ACI/OT | C38066 | 0,96 $ |
| LED RGB | 150080M153000 | C6785001 | 0,62 $ |
| Bouton | KSC641JLFS | C226344 | 0,62 $ |
| Passifs, diodes, inductance | 16 références | — | 0,85 $ au total |

Le nRF9151 représente à lui seul environ deux tiers du coût des composants.

### Coûts hors devis

| Poste | Estimation | Remarque |
|---|---|---|
| eSIM à souder | 12 à 14,50 € par appareil | 1NCE : 12 € pour 10 ans et 500 Mo, puce à 2,50 € ; il n'est pas clair si les 2,50 € s'ajoutent. Couverture LTE-M en Belgique non vérifiée |
| Batterie LiPo ~200 mAh | non chiffré | type LP502025 |
| Antenne LTE | non chiffré | ruban sur mesure, ou antenne du commerce sur connecteur U.FL pour les essais |
| Sonde de programmation | non chiffré | J-Link ou carte de développement Nordic |
| Adaptateur USB-série | non chiffré | pour le module ESP32 |
| Port, TVA, douane | non chiffré | |

## Ce que JLCPCB fait

- Fabrique les 5 circuits imprimés 4 couches.
- Fournit et soude les 36 composants de la nomenclature, sur les deux faces.
- Contrôle aux rayons X les soudures cachées (nRF9151, module ESP32).
- Relit la commande avant fabrication et signale par e-mail les problèmes de placement ou un supplément.

## Ce que JLCPCB ne fait pas

- **eSIM (U5)** : retirée de la commande, à souder soi-même à l'air chaud.
- **Connecteur U.FL (J1)**, condensateur C15 et emplacements d'adaptation Z1, Z3, Z5 : prévus non montés.
- **Batterie et antenne** : à souder sur les pastilles.
- **Logiciel** : les puces arrivent vides.
- **Test de fonctionnement** : aucun, JLCPCB ne vérifie pas que la carte marche.

## À vérifier avant de commander

### Sur le site JLCPCB

- [ ] Recharger `cpl_jlcpcb.csv` corrigé. Avec l'ancienne version, le nRF9151, l'alimentation et le micro seraient soudés tournés de 180°.
- [ ] Dans l'aperçu, face du dessous : le point rose de U1, U3 et MK1 doit être à côté du triangle blanc de la sérigraphie.
- [ ] Dans l'aperçu, face du dessus : contrôler le sens de la LED D1 et de la diode D2.
- [ ] Diode de protection D3 : pas de modèle 3D, sens invisible. Écrire dans la remarque de commande : cathode côté pastille de charge, anode à la masse. À l'envers, elle court-circuite l'entrée de charge.
- [ ] Micro MK1 : coché, quantité égale au nombre de cartes. JLCPCB le classe « difficile » et peut demander un supplément après revue.
- [ ] Options du circuit : 4 couches, pistes de 0,1 mm et perçages de 0,2 mm acceptés sans surcoût imprévu.
- [ ] Voir si une commande de 2 cartes est possible pour limiter le risque.

### Sur la conception

Ces points viennent du dossier de conception et n'ont pas été levés. Ils décident si la carte fonctionnera.

- [ ] **Brochage du nRF9151** : recouper la table des broches avec la fiche officielle Nordic. Le symbole a été créé à la main.
- [ ] **Condensateur DEC0 (C15)** : non monté ; vérifier dans le schéma de référence Nordic s'il est obligatoire.
- [ ] **Routage** : relire dans KiCad l'alimentation batterie, la boucle de l'alimentation 3,3 V (son nœud de commutation passe par deux vias) et la ligne d'antenne.
- [ ] **Ligne d'antenne** : largeur de 0,3 mm à recalculer avec l'empilement réel de JLCPCB.
- [ ] **Trois composants de remplacement** : bouton KSC641J (appui deux fois plus ferme que prévu), diode PMEG3005EJ, protection TPESD5V0S1UL (fiche technique non comparée à l'original).
- [ ] **Inductance L1** : l'empreinte est celle d'un modèle voisin de mêmes dimensions ; à confirmer.
- [ ] **Empreinte de l'eSIM** : à comparer avec la puce réellement achetée.
- [ ] **Consommation du module ESP32 à l'arrêt** : l'autonomie d'un mois en dépend.

## À faire après réception

### Matériel

- [ ] Contrôle visuel, puis mesure : pas de court-circuit entre batterie et masse, ni entre 3,3 V et masse.
- [ ] Première mise sous tension sur alimentation de laboratoire limitée en courant ; vérifier le 3,3 V.
- [ ] Souder le connecteur U.FL et une antenne LTE du commerce pour les premiers essais.
- [ ] Souder l'eSIM.
- [ ] Souder la batterie et tester la charge avec deux contacts à ressort.
- [ ] Mesurer la consommation en veille.
- [ ] Plus tard : monter l'antenne en ruban dans le boîtier et la régler à l'analyseur de réseau.

### Logiciel

- [ ] Charger le firmware ESP-AT dans le module ESP32 par les trois pastilles prévues.
- [ ] Écrire le firmware du nRF9151 : bouton, LED, enregistrement du micro, scan Wi-Fi via le module ESP32, envoi par LTE-M, mise en veille.
- [ ] Le charger avec la sonde de programmation par les pastilles de test.
- [ ] Côté serveur : réception de l'alerte et de l'audio, conversion de la liste Wi-Fi en position.
- [ ] Application de configuration par Bluetooth.

## Fichiers

| Fichier | Contenu |
|---|---|
| `DESIGN.md` | Dossier de conception complet |
| `kicad/alert_button.kicad_pro` | Projet KiCad de la carte rectangulaire |
| `kicad/gerbers/gerbers.zip` | Fichiers de fabrication |
| `jlcpcb/bom_jlcpcb.csv` | Nomenclature au format JLCPCB |
| `jlcpcb/cpl_jlcpcb.csv` | Placement au format JLCPCB |
| `jlcpcb/original/` | Versions de départ de ces deux fichiers |
