# Maquette UX proposée

## Objectif

Transformer [static/index.html](static/index.html) en poste de travail plus fluide :

- pilotage clair en haut
- transcription comme source principale
- panneau IA comme zone d'exploitation
- logs relégués en zone secondaire

## Wireframe texte

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Journal audio                                                [Statut] [Save]│
│ Capture locale, transcription FR, assistance IA locale                      │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ [Démarrer] [Arrêter]    [Sauvegarder] [Effacer]    [x] Enregistrer le son  │
│ Modèle transcription [large-v3-turbo ▼]   Langue [français]                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┬───────────────────────────────────────┐
│ TRANSCRIPTION EN DIRECT              │ IA LOCALE                             │
│ 1024 caractères · 180 mots           │ Travaille sur la transcription active │
│                                      │                                       │
│ [zone de transcription éditable]     │ Actions rapides                       │
│                                      │ [Résumé clair] [Tâches] [Expliquer]   │
│                                      │ [Reformulation]                       │
│                                      │                                       │
│                                      │ Consigne personnalisée                │
│                                      │ [textarea ...                      ] │
│                                      │ [Envoyer à l'IA]                      │
│                                      │                                       │
│                                      │ Résultat IA                           │
│                                      │ [zone de sortie unique             ] │
└──────────────────────────────────────┴───────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Logs techniques [Afficher ▼]                                                │
│ visibles seulement si nécessaire                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Lecture UX

### 1. Barre haute simplifiée

- les actions critiques sont groupées : démarrer, arrêter
- les actions d'entretien sont séparées : sauvegarder, effacer
- les paramètres de session restent visibles sans prendre le dessus

### 2. Disposition maître-détail

- à gauche, la matière brute : [Transcription en direct](static/index.html:55)
- à droite, l'exploitation : [IA locale](static/index.html:66)
- bénéfice principal : comparaison immédiate entre source et résultat

### 3. Zone IA centrée usage

- les actions rapides deviennent des verbes métier
- la consigne libre sert de passerelle vers des besoins non prévus
- la sortie reste unique pour éviter l'effet fouillis

### 4. Logs moins envahissants

- visibles sur demande
- utiles pour debug, sans polluer l'usage quotidien

## Variante plus légère si vous voulez moins de changement

Conserver le flux vertical, mais :

- rendre la barre de contrôle plus hiérarchique
- compacter les cartes d'information
- mettre [IA locale](static/index.html:66) immédiatement sous [Transcription en direct](static/index.html:55)
- replier [Logs techniques](static/index.html:94) par défaut

Cette variante change moins la structure mais améliore moins fortement l'expérience.
