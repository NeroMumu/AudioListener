# Plan UX grand écran 2560×1440

## Direction retenue

Interface dense et productive pour grand écran, avec :

- colonne principale très large pour [Transcription en direct](static/index.html:55)
- colonne secondaire visible pour [IA locale](static/index.html:66)
- hiérarchie d'actions plus nette dans [controls](static/index.html:25)
- [Logs techniques](static/index.html:94) relégués en zone secondaire repliable

## Principe de layout

### Desktop large

- conteneur plus large que l'actuel dans [static/styles.css](static/styles.css)
- grille centrale en `65/35`
- hauteur utile maximisée pour limiter le scroll vertical
- transcription et IA visibles simultanément sans empilement

### Tablette et résolutions plus petites

- bascule progressive vers une pile verticale
- priorité à la transcription, puis panneau IA

## Hiérarchie d'information proposée

### 1. Bandeau de contexte

Conserver l'en-tête de [static/index.html](static/index.html), mais le rendre plus opérationnel :

- statut courant
- dernier enregistrement
- modèle actif
- état audio

### 2. Barre de pilotage

Réorganiser [controls](static/index.html:25) en deux groupes :

- groupe principal : Démarrer, Arrêter
- groupe secondaire : Sauvegarder, Effacer, Enregistrer le son

Objectif : rendre l'action principale immédiatement identifiable.

### 3. Zone de travail maître-détail

Créer une grille centrale :

- gauche, grand panneau : transcription éditable
- droite, panneau IA : actions rapides, consigne libre, résultat

#### Colonne transcription

- titre
- compteurs
- zone éditable haute
- éventuelle micro-aide discrète

#### Colonne IA

- titre clair, par exemple IA locale
- ligne de contexte expliquant que l'IA travaille sur la transcription courante
- actions rapides sous forme de boutons compacts
- champ libre pour la consigne
- bouton d'envoi principal
- zone de résultat unique

### 4. Logs secondaires

Transformer [Logs techniques](static/index.html:94) en bloc repliable :

- fermé par défaut en usage normal
- accessible via un en-tête cliquable ou bouton Afficher les logs

## Changements concrets par fichier

### [static/index.html](static/index.html)

- introduire une grille de workspace centrale
- séparer nettement colonne transcription et colonne IA
- regrouper les contrôles par importance
- rendre les logs repliables

### [static/styles.css](static/styles.css)

- augmenter la largeur utile pour grand écran
- définir une grille desktop `65/35`
- donner à la transcription une hauteur plus généreuse
- compacter les actions IA pour usage dense
- ajouter le style du bloc logs repliable

### [static/app.js](static/app.js)

- gérer l'ouverture/fermeture des logs
- éventuellement enrichir le feedback visuel sur l'action IA en cours
- préserver la logique actuelle de remplacement du résultat IA

## Recommandations UX à faible coût et fort impact

### Priorité 1

- passer en vraie disposition deux colonnes
- rendre la transcription plus haute et plus large
- rendre les logs repliables

### Priorité 2

- améliorer la microcopie des actions IA
- mieux distinguer actions principales et secondaires

### Priorité 3

- ajouter une ligne de contexte dans le panneau IA, par exemple modèle utilisé et type de traitement en cours

## Checklist d'implémentation

- restructurer [static/index.html](static/index.html) autour d'un workspace central
- ajuster [static/styles.css](static/styles.css) pour un mode desktop dense en `65/35`
- rendre [Logs techniques](static/index.html:94) repliables
- raffiner les libellés UX de [IA locale](static/index.html:66)
- vérifier la lisibilité sur grand écran puis sur largeur réduite

## Résultat attendu

Une interface pensée comme un poste de travail :

- la transcription domine visuellement
- l'IA reste immédiatement exploitable
- les logs n'encombrent plus le flux principal
- l'écran 2560×1440 est réellement utilisé au service de la productivité
