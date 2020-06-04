# Automate PyDrone : locuste.drone.automata
LOCUSTE : Automate Pyrhon connectée aux drones ANAFI / PARROT par le biais de la SDK OLYMPE Python (Raspberry PI)
Requiert une version installée de PARROT OLYMPE avec les commandes suivantes : 
source PATH/parrot-groundsdk/products/olympe/linux/env/shell
export LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1 (Si ARM)


[![Codacy Badge](https://app.codacy.com/project/badge/Grade/28b77886b9ad485d8c3b261a48dc2af3)](https://www.codacy.com/manual/axel.maciejewski/locuste.drone.automata?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=DaemonToolz/locuste.drone.automata&amp;utm_campaign=Badge_Grade)


[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=DaemonToolz_locuste.drone.automata&metric=alert_status)](https://sonarcloud.io/dashboard?id=DaemonToolz_locuste.drone.automata)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=DaemonToolz_locuste.drone.automata&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=DaemonToolz_locuste.drone.automata)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=DaemonToolz_locuste.drone.automata&metric=reliability_rating)](https://sonarcloud.io/dashboard?id=DaemonToolz_locuste.drone.automata)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=DaemonToolz_locuste.drone.automata&metric=security_rating)](https://sonarcloud.io/dashboard?id=DaemonToolz_locuste.drone.automata)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=DaemonToolz_locuste.drone.automata&metric=bugs)](https://sonarcloud.io/dashboard?id=DaemonToolz_locuste.drone.automata)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=DaemonToolz_locuste.drone.automata&metric=vulnerabilities)](https://sonarcloud.io/dashboard?id=DaemonToolz_locuste.drone.automata)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=DaemonToolz_locuste.drone.automata&metric=coverage)](https://sonarcloud.io/dashboard?id=DaemonToolz_locuste.drone.automata)



Le project Locuste se divise en 4 grandes sections : 
* Automate (Drone Automata) PYTHON (https://github.com/DaemonToolz/locuste.drone.automata)
* Unité de contrôle (Brain) GOLANG (https://github.com/DaemonToolz/locuste.service.brain)
* Unité de planification de vol / Ordonanceur (Scheduler) GOLANG (https://github.com/DaemonToolz/locuste.service.osm)
* Interface graphique (UI) ANGULAR (https://github.com/DaemonToolz/locuste.dashboard.ui)

![Composants](https://user-images.githubusercontent.com/6602774/83644711-dcc65000-a5b1-11ea-8661-977931bb6a9c.png)

Tout le système est embarqué sur une carte Raspberry PI 4B+, Raspbian BUSTER.
* Golang 1.11.2
* Angular 9
* Python 3.7
* Dépendance forte avec la SDK OLYMPE PARROT : (https://developer.parrot.com/docs/olympe/, https://github.com/Parrot-Developers/olympe)

![Vue globale](https://user-images.githubusercontent.com/6602774/83644783-f10a4d00-a5b1-11ea-8fed-80c3b76f1b00.png)

Détail des choix techniques pour la partie Automate :

* [Python] - Imposé par la SDK OLYMPE PARROT
* [SocketIO] - Elément facile intégré avec Angular, Node et Python

Evolutions à venir : 
* Refactoring global
* Correctifs de sécurité
* Scission totale de la section COMMON
* Ajout de nouveaux événements pour la gestion GPS / WIFI (étude plus poussée d'AR.SDK)
* Changement dans la gestion du DRONE (et chemins d'accès vers les logs) - implémenter des procédures et processus en cas d'interférences ou perte de signal
