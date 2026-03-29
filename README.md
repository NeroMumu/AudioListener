# Audio Journal Local

Application web locale de journal audio avec transcription française hors ligne via `faster-whisper`, choix du modèle de transcription dans une liste déroulante, enregistrement audio optionnel, et génération de résumé/actions via Ollama local, avec sauvegarde dans [History/](History/).

## Démarrage

1. Installer Python 3.11 ou plus récent.
2. Installer les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

3. Lancer le serveur local :

   ```bash
   python run_server.py
   ```

4. Ouvrir `http://127.0.0.1:8000`.

## Notes

- le premier chargement du modèle `small` peut télécharger les poids dans `.models/`
- le modèle de transcription peut être changé depuis l'interface parmi la liste configurée par `FASTER_WHISPER_AVAILABLE_MODELS`
- la transcription cible le français et tourne en CPU avec `int8`
- les fichiers texte sont enregistrés dans [History/](History/)
- les enregistrements audio sont convertis en MP3 via `ffmpeg` et enregistrés dans [History/](History/) avec le même nom de base que le fichier texte correspondant
- la génération de résumé utilise Ollama sur `http://127.0.0.1:11434` par défaut, configurable via `OLLAMA_BASE_URL`
- le lanceur [run_server.py](run_server.py) démarre `uvicorn` avec des délais WebSocket plus élevés pour éviter les coupures `keepalive ping timeout` sur les sessions longues
