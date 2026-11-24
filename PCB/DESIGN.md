# Bouton d'alerte LTE-M — dossier de conception

Version : coque en résine, antenne LTE dans la coque, carte double face. Deux formes de carte partagent le même schéma : un rectangle de 25 × 35 mm (§ 3 et 7) et un ovale de 28 × 38 mm (§ 12).

## 1. État du dossier

| Élément | État |
|---|---|
| Architecture, choix des composants, nomenclature | Fait |
| Schéma KiCad ([kicad/alert_button.kicad_sch](kicad/alert_button.kicad_sch)) | Fait ; contrôle électrique KiCad (ERC) : 0 erreur, 0 avertissement |
| Carte KiCad ([kicad/alert_button.kicad_pcb](kicad/alert_button.kicad_pcb)) | Contour, 4 couches, 58 empreintes placées, **routée** (§ 13) ; contrôle KiCad (DRC) : 0 connexion manquante, 0 violation d'isolement, cohérence schéma/carte : 0 écart |
| Carte ovale ([kicad_oval/alert_button_oval.kicad_pcb](kicad_oval/alert_button_oval.kicad_pcb)) | Ellipse 28 × 38 mm, mêmes 58 empreintes placées, **routée** (§ 13) ; contrôle KiCad (DRC) : 0 violation, 0 connexion manquante, cohérence schéma/carte : 0 écart |
| Routage des pistes | Les deux cartes : fait par routeur automatique puis complété par script, **à relire avant fabrication** (§ 13) |
| Fichiers de fabrication (Gerber, placement) | Non générés : à faire après relecture du routage |
| Antenne LTE dans la coque | Géométrie de départ proposée, ni simulée ni mesurée |
| Prototype, mesures de consommation et de portée | Non faits |

Les points marqués **[à vérifier]** doivent être confirmés avant fabrication (liste au § 10).

## 2. Architecture

```
 Contacts 5 V ─► TVS + Schottky ─► MCP73832 (chargeur) ─► VBAT (LiPo ~200 mAh avec protection)
                                                            │
                  ┌─────────────────────────────────────────┼───────────────┐
                  │ VDD direct batterie                     ▼               │
                  ▼                                  TPS63900 buck-boost    │
            ┌───────────┐                            3,3 V, Iq 75 nA        │
 Antenne ◄──┤ nRF9151   │◄── VDD_GPIO ◄──────────────── rail 3V3 ───────────┤
 dans la    │ LTE-M     │                                                   ▼
 coque (π)  │ + MCU M33 ├─ UART + EN ───────────────────────────► ESP32-C6-MINI-1
 eSIM MFF2 ─┤           ├─ PDM + alim par GPIO ─► micro MEMS        (scan Wi-Fi + BLE,
            │           ├─ GPIO ◄─ bouton                           antenne intégrée,
            │           └─ 3 GPIO ─► LED RGB (anode sur VBAT)       éteint hors alerte)
            └───────────┘
```

### Choix et raisons

| Fonction | Choix | Raison |
|---|---|---|
| Cellulaire + MCU | **nRF9151** | LTE-M disponible en Belgique, débit suffisant pour un fichier audio, veille de quelques µA en PSM, interface PDM intégrée. |
| Wi-Fi + BLE | **ESP32-C6-MINI-1-N4**, firmware ESP-AT | Un seul module précertifié avec antenne. Remplace l'ESP32-C3-MINI-1 prévu au départ : même taille et même rôle, mais KiCad fournit son symbole et son empreinte vérifiés, ce qui évite une erreur de brochage. |
| Rail 3,3 V | **TPS63900** | Iq 75 nA, 3,3 V sur toute la plage de la batterie, 400 mA. Configuration reprise du schéma d'application TI : SEL à l'état haut, 36,5 kΩ sur CFG1, CFG2 et CFG3 à la masse. |
| Charge | **MCP73832** + 2 contacts | Sortie d'état à drain ouvert (le MCP73831 prévu au départ sort du 5 V sur cette broche, incompatible avec une entrée 3,3 V). Courant de charge 100 mA (10 kΩ sur PROG). |
| SIM | **eSIM MFF2** soudée | 6 × 5 mm ; brochage standard : 1 = masse, 3 = données, 6 = horloge, 7 = reset, 8 = alimentation. |
| LED | **Würth 150080M153000** (RGB 0805) | Anode commune reliée à VBAT et non au 3,3 V : la verte et la bleue demandent environ 3,3 V à 20 mA, elles seraient trop faibles sur le rail 3,3 V. |
| Bouton | **C&K KSC621J** (série KSC6, 6,2 × 6,2 mm) | Empreinte disponible dans KiCad. |
| Mesure batterie | Modem nRF9151 (`AT%XVBAT`) | Aucun composant. |

Le GNSS du nRF9151 n'est pas câblé : la localisation se fait par Wi-Fi.

## 3. Mécanique et antenne LTE

- **Coque** : résine ou acrylique poli, parois de 1,5 mm, sans inclusion métallique. Cavité d'environ 27 × 37 mm, soit un objet d'environ 30 × 40 × 12 mm.
- **Empilement** : face A de la carte (bouton, LED, contacts de charge, module ESP32) côté utilisateur ; face B (nRF9151, alimentation, eSIM, micro) côté batterie ; batterie collée sur la face B avec un isolant.
- **Batterie** : type LP502025 (5 × 20 × 25 mm, ~200 mAh **[à vérifier]**), posée avec son côté de 20 mm dans la largeur, décalée vers la droite pour laisser libres les pastilles BAT+ / BAT− du bord gauche. Elle ne doit pas dépasser sur la zone d'antenne Wi-Fi (les 5,4 derniers millimètres de la carte).
- **Ouvertures de la coque** : un trou pour le micro (il débouche sur la face A, près du bouton), deux contacts de charge, une zone translucide pour la LED.

### Antenne LTE dans la coque : point de départ

Cette géométrie est un point de départ raisonné, pas un résultat de simulation.

- **Élément rayonnant** : ruban de cuivre ou circuit flexible de 3 mm de large, collé sur la paroi intérieure de la coque.
- **Alimentation** : pastille TP5 (`ANT_FEED`), en haut de la face B. La pastille TP6 (`ANT_GND`), 2,8 mm à côté, permet d'ajouter un retour à la masse pour une antenne en F inversé.
- **Tracé** : le long du petit côté supérieur, puis le long d'un grand côté, en s'éloignant le plus possible de la batterie.
- **Longueur** : partir d'environ 90 mm (un quart d'onde à 826 MHz dans l'air) et raccourcir par essais au VNA ; la résine abaisse la fréquence de résonance, donc la longueur finale sera plus courte.
- **Adaptation** : cinq emplacements 0402 (Z1 à Z5) entre le nRF9151 et la pastille. Z2 et Z4 sont des 0 Ω en série, Z1, Z3 et Z5 sont des emplacements vers la masse, non montés au départ.
- **Mesure** : le connecteur U.FL (J1, non monté) sert à brancher le VNA ou une antenne externe.
- **Bande haute de la carte** : pas de plan de cuivre sur les 5 premiers millimètres, sur toutes les couches. Seules la piste d'antenne et les liaisons de masse du connecteur U.FL y passent.

## 4. Budget énergétique (estimation à mesurer sur prototype)

| Poste | Hypothèse | Par mois |
|---|---|---|
| Veille | ~20 µA moyens (théorique ~8 µA) | ~15 mAh |
| Message de vie quotidien | ~0,1 mAh | ~3 mAh |
| 10 alertes | ~2 mAh chacune (scan Wi-Fi, 10 s d'audio, envoi) | ~20 mAh |
| 2 sessions BLE de 5 min | ~5 mAh chacune | ~10 mAh |
| Autodécharge | ~3 %/mois | ~6 mAh |
| **Total** | | **~55 mAh** |

Avec ~200 mAh, cela donne environ trois mois théoriques. Deux hypothèses pèsent sur ce chiffre : l'opérateur doit accorder le mode PSM, et le module ESP32-C6 doit consommer de l'ordre du µA quand sa broche EN est à 0 **[à vérifier]**. Si ce n'est pas le cas, il faudra ajouter un interrupteur d'alimentation sur le module.

## 5. Nomenclature

La liste complète est dans [bom.csv](bom.csv), générée depuis le même fichier que le schéma.

| Réf. | Composant | Référence | Boîtier |
|---|---|---|---|
| U1 | SiP LTE-M + MCU | Nordic nRF9151-LACA-R7 | LGA 12,1 × 11,1 mm |
| U2 | Module Wi-Fi 2,4 GHz + BLE | Espressif ESP32-C6-MINI-1-N4 | 13,2 × 16,6 mm |
| U3 | Buck-boost 3,3 V | TI TPS63900DSKR | WSON-10 2,5 × 2,5 mm |
| U4 | Chargeur Li-ion | Microchip MCP73832T-2ACI/OT | SOT-23-5 |
| U5 | eSIM | puce MFF2 de l'opérateur IoT choisi | 6 × 5 mm |
| MK1 | Micro MEMS PDM, port inférieur | Knowles SPH0641LU4H-1 | 3,5 × 2,65 mm |
| SW1 | Bouton | C&K KSC621J LFS | 6,2 × 6,2 mm |
| D1 | LED RGB | Würth 150080M153000 | 0805 |
| D2 | Schottky série | Nexperia PMEG2005EJ | SOD-323F |
| D3 | TVS 5 V | Nexperia PESD5V0S1UL | SOD-882 |
| L1 | Inductance 2,2 µH | Murata DFE201612E-2R2M | 2,0 × 1,6 mm |
| J1 | U.FL (non monté) | Hirose U.FL-R-SMT-1(10) | — |
| C1–C15, R1–R10, Z1–Z5 | Passifs | voir bom.csv | 0402 à 0805 |
| TP1–TP16 | Pastilles : charge, batterie, antenne, test | — | — |
| BT1 | LiPo ~200 mAh avec protection | type LP502025 | 5 × 20 × 25 mm |

## 6. Affectation des broches du nRF9151

Les numéros de broches viennent de la documentation Nordic ; ils sont à recouper une fois avec la fiche officielle **[à vérifier]**.

| Signal | GPIO | Broche | Relié à |
|---|---|---|---|
| ESP_RXD (émission nRF) | P0.00 | 56 | ESP32 IO6 (réception AT) |
| ESP_TXD (réception nRF) | P0.01 | 57 | ESP32 IO7 (émission AT) |
| ESP_CTS (RTS nRF) | P0.02 | 58 | ESP32 IO5 (CTS) |
| ESP_RTS (CTS nRF) | P0.03 | 59 | ESP32 IO4 (RTS) |
| ESP_EN | P0.04 | 61 | ESP32 EN, 10 kΩ vers la masse |
| MIC_PWR | P0.05 | 62 | alimentation du micro via 100 Ω |
| PDM_CLK / PDM_DATA | P0.06 / P0.07 | 63 / 64 | micro |
| BTN | P0.08 | 67 | bouton vers la masse (tirage interne) |
| LED_R / LED_G / LED_B | P0.10 / P0.11 / P0.12 | 69 / 70 / 72 | cathodes via 470 / 220 / 220 Ω, actif bas |
| CHG_STAT | P0.13 | 73 | état du chargeur, 100 kΩ vers 3V3 |
| DBG_TX / DBG_RX | P0.27 / P0.28 | 45 / 47 | pastilles de test |
| VDD, ENABLE | — | 14, 10 | VBAT |
| VDD_GPIO | — | 65 | 3V3 |
| SIM_1V8 / RST / CLK / IO | — | 19 / 16 / 18 / 17 | eSIM |
| ANT | — | 35 | réseau d'adaptation puis TP5 |
| SWDIO / SWDCLK / nRESET | — | 4 / 3 / 9 | pastilles de test |

Les broches GPS, AUX, MAGPIO, COEX, RFFE et SIM_DET restent non connectées. Le condensateur C15 sur DEC0 est prévu mais non monté **[à vérifier]**.

Côté ESP32-C6 : IO8 et IO9 ont un tirage de 10 kΩ vers 3V3 ; IO9 (`ESP_BOOT`), RXD0 et TXD0 sortent sur pastilles pour le flash initial du firmware ESP-AT.

## 7. Placement sur la carte

Coordonnées et faces dans [kicad/tools/design.py](kicad/tools/design.py) (table `PLACEMENT`).

| Zone (du haut vers le bas) | Face A, côté utilisateur | Face B, côté batterie |
|---|---|---|
| 0–5 mm | vide | pastilles d'antenne TP5/TP6, U.FL |
| 5–18 mm | contacts de charge et protections, bouton, LED et résistances | réseau d'adaptation, micro, nRF9151, condensateurs réservoir, pastilles batterie et de test |
| 18–29,6 mm | module ESP32-C6 et ses passifs, pastilles de flash | fin du nRF9151, chargeur, eSIM, buck-boost |
| 29,6–35 mm | antenne du module ESP32 | rien (zone sans cuivre) |

## 8. Fonctionnement prévu (firmware, pour information)

1. Veille : nRF9151 en PSM, ESP32 à l'arrêt, micro non alimenté.
2. Appui : LED bleue, alimentation du micro, enregistrement PDM 16 kHz compressé en mémoire (~80 ko pour 10 s).
3. En parallèle : mise en marche de l'ESP32, commande `AT+CWLAP` pour la liste des points d'accès, puis arrêt.
4. Envoi par LTE-M : alerte et liste Wi-Fi d'abord, audio ensuite. Le serveur convertit la liste en position.
5. Accusé de réception : LED verte ; échec : LED rouge et nouvelles tentatives.
6. Appui long : mode configuration, ESP32 en serveur BLE pendant 2 min.

## 9. Projet KiCad

Ouvrir [kicad/alert_button.kicad_pro](kicad/alert_button.kicad_pro) avec KiCad 10.

- **Schéma** : une feuille A3 ; les liaisons se font par étiquettes de nets plutôt que par fils.
- **Symboles du projet** : nRF9151 et eSIM dans `alert_button.kicad_sym` ; tous les autres symboles et toutes les empreintes viennent des bibliothèques standard de KiCad.
- **Carte** : références masquées sur la sérigraphie (carte trop dense) ; plan de masse sur la couche interne 2, celle qui touche la face B (nRF9151 et ligne d'antenne).
- **Rapports** : `erc.rpt` et `drc.rpt`. Pour la carte rectangulaire routée, il ne reste que deux avertissements de sérigraphie (contour du module ESP32 coupé par le bord).
- **Régénération** : `kicad/build.sh` (ou `kicad/build.sh oval` pour la variante ovale) reconstruit schéma, netlist, carte et nomenclature depuis `kicad/tools/design.py`. **Il écrase le schéma et la carte**, routage compris. `kicad/route.sh` refait ensuite tout le routage de la carte rectangulaire (§ 13). Ne plus lancer ni l'un ni l'autre après une retouche manuelle de la carte.

## 10. À vérifier avant fabrication

1. Brochage du nRF9151 (table du § 6) et traitement de DEC0, à recouper avec la fiche Nordic et son schéma de référence.
2. Empreinte et brochage de l'eSIM retenue, et son itinérance LTE-M avec PSM en Belgique.
3. Consommation du module ESP32-C6 avec EN à 0.
4. Empreinte de L1 : celle de KiCad est prévue pour la DFE201610P, de mêmes dimensions au sol que la DFE201612E.
5. Capacité réelle et dimensions de la batterie.
6. Polarité du connecteur de charge : la TVS protège des décharges, la Schottky d'une inversion, mais une inversion prolongée fait conduire la TVS.
7. Adaptation de l'antenne au VNA, coque fermée et batterie en place.

## 11. Ce qui reste à faire

1. Relire le routage des deux cartes dans KiCad (points du § 13).
2. Ajuster le contour de la carte à la forme de la coque.
3. Générer les fichiers de fabrication et commander (4 couches, 0,8 mm).
4. Assembler, mesurer la consommation en veille, régler l'antenne.

## 12. Variante ovale 28 × 38 mm

Projet : [kicad_oval/alert_button_oval.kicad_pro](kicad_oval/alert_button_oval.kicad_pro). Le schéma, la nomenclature et l'affectation des broches sont identiques à la version rectangulaire ; seuls le contour et le placement changent (table `PLACEMENT_OVAL` de [kicad/tools/design.py](kicad/tools/design.py)).

- **Contour** : ellipse de 28 mm de large et 38 mm de haut (836 mm², contre 875 mm² pour le rectangle). Le contour est tracé en 180 segments.
- **Coque** : cavité ovale d'environ 30 × 40 mm, soit un objet d'environ 33 × 43 × 12 mm. La carte rectangulaire, elle, demanderait une cavité ovale d'environ 35 × 50 mm.
- **Contrôles** : ERC 0 erreur ; carte routée, DRC 0 violation, 0 connexion manquante, 0 écart schéma/carte. Toutes les pastilles sont à plus de 0,3 mm du bord.

| Zone (du haut vers le bas) | Face A, côté utilisateur | Face B, côté batterie |
|---|---|---|
| 0–5 mm | vide | U.FL, pastilles d'antenne TP5/TP6 (zone sans plan de cuivre) |
| 5–11 mm | LED et ses résistances | réseau d'adaptation, micro |
| 11–21 mm | bouton au milieu, un contact de charge de chaque côté | nRF9151, condensateurs réservoir, pastilles de test, pastilles batterie sur les deux flancs |
| 21–30 mm | module ESP32-C6 et ses passifs, pastilles de flash | chargeur, eSIM, buck-boost |
| 30–38 mm | antenne du module ESP32, au ras du bord | rien |

- **Bouton** : à 4 mm au-dessus du centre de l'ovale.
- **Batterie** : la LP502025 (20 × 25 mm) tient au centre, entre 5 et 30 mm depuis le haut ; ses coins dépassent légèrement de la carte mais restent dans la cavité **[à vérifier]**. Les pastilles BAT+ (flanc gauche) et BAT− (flanc droit) restent dégagées.
- **Antenne LTE** : même principe qu'au § 3. Le ruban part de TP5 en haut et suit la paroi courbe d'un seul côté ; il doit s'arrêter avant les 8 derniers millimètres du bas, réservés à l'antenne Wi-Fi. Un côté offre environ 50 mm : si la résonance est trop haute, prolonger par un second bras de l'autre côté ou par un méandre, à régler au VNA. Ni simulé ni mesuré.
- **Taille** : 28 × 38 mm est la plus petite ellipse que j'ai placée avec ces composants. Les zones qui semblent libres (haut de la face A, bas de la face B) sont les zones d'antenne et doivent rester vides. Ce qui fixe la taille : la hauteur du module ESP32 plus le bouton sur la face A, et la rangée chargeur + eSIM + buck-boost sur la face B. Une ellipse de 26 × 36 mm demanderait de déplacer le chargeur près de l'antenne LTE ; non tenté.

## 13. Routage des deux cartes

Le routage est produit par `kicad/route.sh` (carte rectangulaire) ou `kicad/route.sh oval` (carte ovale), en quatre temps :

1. **Ligne d'antenne tracée à la main** (script) : du nRF9151 à la pastille TP5 en passant par Z2 et Z4, entièrement sur la face B, 0,3 mm de large, 12 mm au total, sans via.
2. **Routeur automatique Freerouting 2.5.0** pour tout le reste. Selon les essais, il laisse entre 5 et 15 connexions ouvertes sur 171.
3. **Complément par script** ([kicad/tools/route_finish.py](kicad/tools/route_finish.py)) : un petit routeur sur grille de 0,05 mm termine les connexions ouvertes, retire les pistes que le DRC signale trop proches d'une pastille et les retrace.
4. **Masse** : plan plein sur la couche interne 2, remplissages de masse sur les deux faces, une trentaine de vias de couture.

Résultat, pistes sur les faces A et B et sur la couche interne 1 :

| | Rectangle 25 × 35 | Ovale 28 × 38 |
|---|---|---|
| Segments | 697 | 703 |
| Vias | 95 | 105 |
| Ligne d'antenne (sans via) | 12 mm | 11 mm |
| Alimentation batterie | 60 mm, 6 vias | 69 mm, 5 vias |
| Nœud de commutation LX1 | 6,6 mm, 2 vias | 5,2 mm, 2 vias |
| DRC | 2 avertissements de sérigraphie | 0 violation |

Dans les deux cas, le DRC de KiCad ne signale ni connexion manquante ni défaut d'isolement.

Pour la carte ovale, l'isolement est contrôlé à 0,11 mm et non à 0,127 mm : le routeur automatique arrondit certains écarts à environ 0,115 mm, ce qui reste au-dessus de la limite de fabrication de 0,1 mm. La carte rectangulaire avait été contrôlée à 0,127 mm.

Règles utilisées (à confirmer avec le fabricant **[à vérifier]**) :

| Règle | Valeur |
|---|---|
| Piste et isolement des signaux | 0,127 mm (quelques rétrécissements à 0,1 mm près des pastilles du nRF9151) |
| Pistes d'alimentation (VBAT, 3V3, VBUS, LX, masse) | 0,25 mm |
| Ligne d'antenne | 0,3 mm |
| Vias | diamètre 0,4 mm, perçage 0,2 mm |
| Distance cuivre – bord | 0,3 mm |

Ces valeurs sont plus fines que le standard le moins cher : il faut une fabrication 4 couches acceptant 0,1 mm et des perçages de 0,2 mm.

Points à relire avant fabrication, que le DRC ne juge pas :

- **Ligne d'antenne** : la largeur de 0,3 mm correspond à 50 Ω pour un isolant d'environ 0,2 mm entre la face B et le plan ; à recalculer avec l'empilement réel. La ligne étant très courte devant la longueur d'onde, l'écart reste rattrapable par le réseau d'adaptation.
- **Buck-boost** : le nœud de commutation LX1 passe par deux vias sur les deux cartes. Mieux vaudrait le retracer à la main, court et sur une seule face.
- **VBAT** : 60 à 69 mm de piste de 0,25 mm et 5 ou 6 vias au total. C'est suffisant pour le courant, mais un tracé plus large entre la batterie, C1/C2 et le nRF9151 réduirait la chute de tension pendant les émissions.
- **Esthétique** : les tracés automatiques font des détours et quelques raccords décalés de quelques centièmes de millimètre ; électriquement corrects, mais à nettoyer si la carte doit figurer dans le mémoire.

Chaque exécution de `route.sh` donne un routage différent, car le routeur automatique n'est pas reproductible.

## 14. Boîtier « Galet » : maquette à imprimer en 3D

Fichiers dans [boitier_3d/](boitier_3d/), générés par [boitier_3d/galet.py](boitier_3d/galet.py) (toutes les cotes sont des paramètres en tête de script) :

| Fichier | Pièce | Sens d'impression |
|---|---|---|
| `galet_coque_arriere.stl` | dos, paroi, bélière, plots d'appui de la carte | dos contre le plateau |
| `galet_face_avant.stl` | face avant avec les ouvertures | face extérieure contre le plateau (déjà retournée dans le fichier) |
| `gabarit_carte.stl` | fausse carte 28 × 38 × 0,8 mm avec le module ESP32 et le bouton | carte à plat |
| `gabarit_batterie.stl` | fausse batterie 20 × 25 × 5 mm | à plat |

- **Extérieur** : ovale 35 × 45 × 12 mm, plus une bélière de 8 mm ; bords chanfreinés puis arrondis pour s'imprimer sans support.
- **Cavité** : 31 × 41 mm, soit 1,5 mm de jeu autour de la carte ; paroi latérale 2 mm, dos et face avant 1 mm.
- **Empilement** (du dos vers l'avant) : dos 1 mm, batterie 5 mm, composants de la face B 1,3 mm, carte 0,8 mm, 2,7 mm pour le module ESP32, face avant 1 mm. Il ne reste aucune marge : si la batterie réelle dépasse 5 mm, augmenter `T` **[à vérifier]**.
- **Sens de montage** : antenne Wi-Fi du module ESP32 vers la bélière, départ d'antenne LTE en bas. La carte est donc tournée de 180° par rapport au dessin KiCad.
- **Antenne LTE** : logement de 4 mm de haut et 0,4 mm de profondeur dans la paroi intérieure, sur environ 85 mm, avec 32 mm sans antenne en haut. Les plots d'appui ne touchent pas la paroi, le ruban passe partout dans le jeu de 1,5 mm.
- **Appui de la carte** : 4 plots sur le fond, hors batterie et hors composants ; 3 butées dans la face avant la maintiennent.
- **Ouvertures de la face avant** : bouton (7 mm), LED (2 mm), deux contacts de charge (2,4 mm), micro (1,2 mm ; position approximative).
- **Fermeture** : emboîtement à feuillure avec 0,15 mm de jeu, tenu par frottement ; à ajuster selon l'imprimante (`FIT`).
- **Réglages conseillés** : PLA ou PETG, couches de 0,12 à 0,2 mm, sans support.

Hauteurs de composants supposées et non vérifiées sur fiche technique : module ESP32 2,4 mm, bouton 3,4 mm, nRF9151 1,1 mm.

## Sources

- [Brochage du nRF9151 (Nordic)](https://docs.nordicsemi.com/bundle/ps_nrf9151/page/pin.html)
- [Fiche technique TPS63900 (TI)](https://www.ti.com/lit/ds/symlink/tps63900.pdf)
- [Fiche technique LED 150080M153000 (Würth)](https://www.we-online.com/components/products/datasheet/150080M153000.pdf)
- [Connexions matérielles ESP-AT pour ESP32-C6 (Espressif)](https://docs.espressif.com/projects/esp-at/en/latest/esp32c6/Get_Started/Hardware_connection.html)
- [Résumé eSIM industrielle u-blox (brochage MFF2)](https://content.u-blox.com/sites/default/files/IndustrialM2M-SIM_ProductSummary_UBX-20046208.pdf)
