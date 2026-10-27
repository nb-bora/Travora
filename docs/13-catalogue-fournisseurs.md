# 13 — Catalogue des fournisseurs, par type de voyage

Version 1, 27 octobre 2026. Ce catalogue recense les fournisseurs trouvés par les recherches de cette date, pour chaque type de voyage et chaque fonction (distribution, paiement, assurance…). Il ne prétend pas être exhaustif : le marché change, et les conditions d'accès ne sont pas publiques pour la plupart.

**Statuts d'accès** (valeurs du champ `statut` dans la plateforme) :

| Statut | Sens |
|---|---|
| `ACTIF` | Intégration existante et testée (aucun fournisseur n'est encore dans cet état pour Travora) |
| `CONTRAT` | Accès conditionné à un contrat, une certification ou une accréditation |
| `MANUEL` | Pas d'API : saisie ou import de relevé |
| `A_VERIFIER` | Existence signalée, conditions non établies |
| `EXCLU` | Interdit par les conditions d'usage ou technique non acceptable (scraping) |

**Niveaux de preuve** : **V** fournisseur ou organisme, page officielle lue ; **S** secondaire (presse, plateforme tierce, résumé de recherche) ; **H** hypothèse.

## 1. Aérien : distribution

### 1.1 Systèmes de distribution globaux (GDS)

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **Amadeus Enterprise** | GDS (PNR, billets, tarification) | Contrat ; identifiant de bureau par pays ; le programme Self-Service est fermé depuis le 17 juillet 2026 | S : presse et résumés concordants ; V : sandbox utilisée par l'équipe FairFare pour la recherche, la commande et l'annulation | `CONTRAT` |
| **Sabre** | GDS (PCC, Red Apps) | Accès production conditionné à un contrat, à une certification et à un avenant par API ou région ; documentation sous licence | S : revue tierce de juillet 2026 ; V : page développeur Sabre | `CONTRAT` |
| **Travelport** (uAPI ; Travelport+, ex-Galileo) | GDS | Programme développeur ; démonstration disponible ; retrait de schémas anciens | S : presse, historique 2012 ; V : documentation d'aide | `CONTRAT` |
| **Navitaire** (systèmes des compagnies low cost) | Système de réservation des compagnies low cost | Accès accordé par la compagnie, avec un compte agence fourni par elle | S : résumé de recherche ; propriété attribuée à Amadeus dans une source de 2019 | `CONTRAT` (via la compagnie) |

### 1.2 Agrégateurs de contenu aérien (NDC, low cost)

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **Duffel** | API de vols (NDC et connexions directes) | Inscription développeur ; conditions commerciales non relues | S : annuaires et intégrations tierces | `A_VERIFIER` |
| **Verteil** | API NDC | Partenariat ; onboarding indiqué par une compagnie aérienne | S : page partenaire d'une compagnie | `A_VERIFIER` |
| **Travelfusion** | Contenu LCC et NDC | Accord commercial ; chiffres de couverture déclaratifs et incohérents entre sources | S : déclaratif | `A_VERIFIER` |
| **HitchHiker** | API de vols, LCC et régionales | Client B2B ; 70 clients revendiqués dans 26 pays | S : déclaratif | `A_VERIFIER` |
| **Accelya** | Éditeur de logiciels aériens (NDC, revenue accounting), pas un agrégateur | Non concerné directement | S | — |

### 1.3 Compagnies directes

| Fournisseur | Canal | Preuve | Statut Travora |
|---|---|---|---|
| Compagnie aérienne nationale du Cameroun | Téléphone ou e-mail, paiement mobile (appel, puis code de validation) | S : presse | `MANUEL` |
| Compagnies africaines citées (Ethiopian Airlines, Kenya Airways) | API directe ou partenariat | S : article non daté ; non vérifié | `A_VERIFIER` |
| Autres compagnies desservant le Cameroun | À recenser avec les pilotes | H | `A_VERIFIER` |

### 1.4 Consolidateurs et BSP

| Élément | Preuve | Statut Travora |
|---|---|---|
| Consolidateurs accrédités au Cameroun | Non recensés | `A_VERIFIER` |
| Règle de remise hebdomadaire | V : document IATA | Règle, pas un fournisseur |

## 2. Autocar

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **Busbud** | Marketplace, API de distribution et marque blanche | Programme de partenariat avec partage de revenus | V : page du programme partenaire (déclaratif) ; couverture Afrique non précisée | `CONTRAT` |
| **12Go** | Plateforme de billetterie de transport en Asie et en Europe | Non établi | S : inventaire repris par Busbud | `A_VERIFIER` |
| **Omio** | Comparateur et vente de trains, cars, avions | Non établi | S : ferry rejoint par Omio via Direct Ferries (presse, décembre 2025) | `A_VERIFIER` |
| **Distribusion** | Réseau de transport terrestre | Non établi | S : profil | `A_VERIFIER` |
| **BuuPass** (ex-QuickBus) | Billetterie de cars au Kenya, Nigeria, Afrique du Sud ; entrée en Ouganda annoncée | Non établi (partenariat) | S : presse de 2024 | `A_VERIFIER` |
| **9jaBus** | Marketplace de billetterie de cars au Nigeria | Vente de capacité aux compagnies, avec API | S : présentation de l'éditeur | `A_VERIFIER` |
| **MastaBookit** | Application de car et d'hébergement (Zambie) | Pas d'API identifiée | S : fiche d'application | `A_VERIFIER` |
| Compagnies de cars camerounaises | Guichet, téléphone, paiement mobile dans certains cas | Presse : quelques compagnies VIP testent le mobile money (noms non donnés) | S | `MANUEL` (à recenser avec les pilotes) |

## 3. Train

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **Camrail** (Cameroun) | Exploitant de la ligne Douala–Yaoundé | Billetterie électronique et paiement par Orange Money et MTN annoncés ; état actuel à vérifier | S : presse non datée ; V : rien d'officiel lu | `A_VERIFIER` puis `MANUEL` |
| Trainline, Rail Europe, Omio | Trains européens | Hors zone Travora | H | `A_VERIFIER` (hors périmètre initial) |

## 4. Bateau

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **Ferryhopper** (FerryhAPI) | Billetterie de ferries, 130 opérateurs et plus de 30 pays revendiqués | Partenariat B2B ; API | V : page partenaire de Ferryhopper (déclaratif) | `CONTRAT` |
| **Direct Ferries Connect** | Billetterie de ferries, 230 opérateurs revendiqués | Accord et intégration technique ; commissions d'affiliation de 50 % revendiquées | V : page de Direct Ferries (déclaratif) ; S : communiqué de décembre 2025 | `CONTRAT` |
| Rome2Rio | Comparateur, sans vente directe selon une source | Pas de programme vérifié | S | `A_VERIFIER` |
| Liaison Douala–Malabo–Bata | Exploitant non identifié | Non établi | S : guide non daté | `A_VERIFIER` |
| Liaison Limbe–Calabar | Exploitant non identifié, fréquence hebdomadaire signalée | Non établi | S : agrégateur, source ancienne | `A_VERIFIER` |

## 5. Hôtel

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **Hotelbeds** | Bedbank B2B | Clé API et secret ; marchés et devises approuvés ; certification si le contrat l'exige | S : documentation d'intégrateur | `CONTRAT` |
| **WebBeds** | Bedbank B2B | Contrat | S : liste de connecteurs | `A_VERIFIER` |
| **TBO Holidays** | Bedbank | Contrat | S | `A_VERIFIER` |
| **RateHawk** | Bedbank | Contrat | S | `A_VERIFIER` |
| **Booking.com** (API de demande) | Hébergements | Programme partenaire | S : liste de connecteurs | `CONTRAT` |
| **Expedia Rapid** | Hébergements | Programme partenaire | S : une source | `A_VERIFIER` |
| **Amadeus Hotels** | Hébergements, via l'OID | Même contrat que le GDS ; l'équipe FairFare a reçu une erreur 401 sur les API d'hôtel | V : test de l'équipe FairFare (interne) | `CONTRAT` |
| Jumia Travel | Réservation en Afrique | Non confirmé comme disponible | S : pages tierces contradictoires | `A_VERIFIER` |
| Travelstart | Vols et hôtels en Afrique | Pas d'API officielle identifiée ; les données publiques sont récupérées par des outils de scraping | S | `EXCLU` (scraping) |

## 6. Location de véhicule

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **CarTrawler** | Agrégateur de loueurs | Contrat | S | `CONTRAT` |
| **Carnect** | Agrégateur, marque blanche, plus de 500 loueurs revendiqués | Contrat | S : déclaratif | `CONTRAT` |
| **Auto Europe** | Grossiste | Contrat | S | `A_VERIFIER` |
| **Avis Budget Group** (Avis, Budget, Payless) | API directe | Partenariat | S : déclaratif | `CONTRAT` |
| **Hertz** (Hertz, Dollar, Thrifty) | API directe | Partenariat | S : déclaratif | `CONTRAT` |
| **Europcar** | API directe annoncée | Non établi | S | `A_VERIFIER` |
| Localiza | Non vérifié | Non établi | — | `A_VERIFIER` |
| Priceline | Plateforme | Seuil de cinq réservations par jour pour les partenaires | S : une source | `CONTRAT` |

## 7. Assurance voyage

| Fournisseur | Rôle | Accès exigé | Preuve | Statut Travora |
|---|---|---|---|---|
| **Allianz Partners** | API pour agences (devis, achat, sinistres, annulations) | Partenaire contractuel ; compte professionnel | S : portail développeur | `CONTRAT` |
| **AXA Partners** (API Travel) | API avec environnement de test, authentification OAuth 2.0 | Partenariat | S | `CONTRAT` |
| **Cover Genius** | Assurance intégrée | Partenariat | S | `A_VERIFIER` |
| **IATI** | Assurance voyage | Non trouvé | — | `A_VERIFIER` |
| **AXA Mansard** (Nigeria) | Assurance, avec une API de distribution (Unyte Africa) | Partenariat | S | `A_VERIFIER` |
| **Imali.click** | Paiement et assurance pour le voyage en Afrique | Non établi | S : éditeur | `A_VERIFIER` |

## 8. Paiement (voir [05](05-integrations-et-canaux.md))

| Fournisseur | Ce qui est vérifié | Statut Travora |
|---|---|---|
| MTN MoMo Collections Cameroun | V : frais « between 1% » ; pas de coût par appel ; fonds sur un compte Collections | `CONTRAT` |
| Orange Money Web Payment | V : Cameroun disponible ; approbation par la banque centrale | `CONTRAT` |
| Campay | V (site) : 2 % à l'encaissement | `CONTRAT` |
| Notch Pay | V : frais non publiés | `CONTRAT` |
| MoPay (utilisé par FairFare) | V (interne) : sandbox vérifiée | `CONTRAT` |
| PawaPay, Fapshi, Flutterwave, CinetPay, Monetbil | S ou non vérifié | `A_VERIFIER` |
| Khenz (API de paiement mobile, Kenya) | S : étude de cas | `A_VERIFIER` |

## 9. Normes d'échange (vocabulaire, pas fournisseurs)

| Norme | Usage | Preuve |
|---|---|---|
| OpenTravel Alliance | Messages de transport terrestre, ferroviaire, types de transport (Air, Rail, Bus, Boat) | S : résumé de la documentation officielle |
| NeTEx (CEN) | Tarification et horaires du transport public | S : documentation CEN |
| GTFS | Horaires seulement | S |
| IATA (BSP, Résolutions 722 et 812) | Règles d'émission et de remise aériennes | V pour la remise ; S pour la numérotation |

## 10. Ce qui est exclu, et pourquoi

- **Les outils de scraping** (Travelstart, et tout site dont les données sont extraites par robot) : conditions d'utilisation interdisant l'extraction, risque juridique, données instables.
- **Les sources non datées ou purement déclaratives** pour les tarifs, la couverture et les volumes : ne servent pas de base à une décision commerciale.

## 11. Ce que cela implique

- Le catalogue est une **donnée** dans la plateforme, gérée par le fondateur (voir [ADR-0002](adr/ADR-0002-registre-fournisseurs.md)). Une agence ne voit que les fournisseurs `ACTIF` ou `MANUEL` qui la concernent. Montrer les fournisseurs « bientôt disponibles » aux agences serait une promesse non tenue : c'est proscrit par les constantes du cadrage.
- Chaque ligne `CONTRAT` a une étape concrète à franchir : contrat, certification, identifiants, accord de l'agence. Aucune ne se franchit sans que l'agence ait signé un pilote.
- Les lignes `A_VERIFIER` demandent une recherche ciblée, dans l'ordre des pilotes : ce que leurs agences vendent réellement décide de l'ordre.

## 12. Prochaines vérifications, par priorité

1. Ce que vendent réellement les pilotes (aérien, car, train, bateau, hôtel), et chez qui : c'est la seule liste qui compte.
2. Conditions d'accès de Sabre et Travelport pour un petit éditeur, auprès de leurs équipes partenaires.
3. Compagnies de cars et exploitant de la liaison Douala–Bioko : identité, canal de vente, règles d'annulation.
4. Accès à la documentation Amadeus Enterprise et Duffel (inscription développeur).
5. Statut de la billetterie électronique de Camrail.
