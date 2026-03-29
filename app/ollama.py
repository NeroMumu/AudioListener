from __future__ import annotations

import json
from urllib import error, request

from app.config import settings


SUMMARY_MODEL_PREFERENCES = (
    "qwen2.5:7b",
    "llama3.1:latest",
    "llama3.2:latest",
    "llama3.3:latest",
    "qwen2.5:14b",
    "qwen2.5:32b",
)


class OllamaError(RuntimeError):
    pass


def _request_json(url: str, *, payload: dict[str, object] | None = None, timeout: int = 10) -> dict[str, object]:
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    http_request = request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")

    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OllamaError(f"Ollama a retourné une erreur HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise OllamaError(
            f"Impossible de joindre Ollama sur {settings.ollama_base_url}. Vérifiez qu'il écoute bien en local."
        ) from exc
    except json.JSONDecodeError as exc:
        raise OllamaError("Réponse Ollama invalide.") from exc


def list_local_models() -> list[str]:
    payload = _request_json(f"{settings.ollama_base_url}/api/tags", timeout=10)
    models = payload.get("models", [])
    if not isinstance(models, list):
        return []

    names = [item.get("name", "") for item in models if isinstance(item, dict)]
    return sorted(name for name in names if isinstance(name, str) and name.strip())


def _ordered_summary_models(local_models: list[str]) -> list[str]:
    ordered: list[str] = []

    for candidate in [settings.ollama_model, *SUMMARY_MODEL_PREFERENCES, *local_models]:
        normalized = str(candidate).strip()
        if normalized and normalized in local_models and normalized not in ordered:
            ordered.append(normalized)

    return ordered


def get_default_summary_model(local_models: list[str] | None = None) -> str:
    models = local_models or list_local_models()
    if not models:
        raise OllamaError("Aucun modèle Ollama local n'est disponible.")

    ordered_models = _ordered_summary_models(models)
    if ordered_models:
        return ordered_models[0]

    return models[0]


def _build_model_candidates(requested_model: str | None) -> list[str]:
    local_models = list_local_models()
    if not local_models:
        raise OllamaError("Aucun modèle Ollama local n'est disponible.")

    candidates: list[str] = []
    explicit_model = (requested_model or "").strip()
    if explicit_model:
        if explicit_model not in local_models:
            raise OllamaError(f"Le modèle Ollama demandé est introuvable en local : {explicit_model}")
        candidates.append(explicit_model)

    for model_name in _ordered_summary_models(local_models):
        if model_name not in candidates:
            candidates.append(model_name)

    return candidates


def _build_ai_prompt(action: str, content: str, instruction: str | None = None) -> str:
    cleaned_content = content.strip()
    if not cleaned_content:
        raise ValueError("Impossible de générer une réponse IA à partir d'une transcription vide.")

    cleaned_instruction = (instruction or "").strip()
    normalized_action = action.strip().lower()

    prompts = {
        "summary_actions": (
            "Tu es un assistant de synthèse en français. "
            "À partir de la transcription ci-dessous, produis uniquement du texte final prêt à afficher.\n\n"
            "Contraintes de sortie :\n"
            "1. Commence par le titre exact : Résumé\n"
            "2. Rédige un résumé en 3 à 5 phrases maximum.\n"
            "3. Ajoute ensuite une ligne vide puis le titre exact : Actions\n"
            "4. Sous le titre Actions, donne une liste à puces avec des actions concrètes.\n"
            "5. S'il n'y a aucune action claire, écris une seule puce : - Aucune action identifiée.\n"
            "6. Ne rajoute aucune introduction ni conclusion hors de cette structure.\n\n"
            f"Transcription :\n{cleaned_content}"
        ),
        "summarize": (
            "Tu es un assistant francophone. Résume la transcription suivante de manière claire, concise et structurée. "
            "Donne un résumé utile en quelques paragraphes courts, sans invention ni digression. "
            "Ne mets aucune phrase d'introduction ni de commentaire du type 'Voici un résumé' ou 'Voici une version reformulée'.\n\n"
            f"Transcription :\n{cleaned_content}"
        ),
        "actions": (
            "Tu es un assistant francophone. Analyse la transcription suivante et extrais uniquement les actions concrètes, "
            "décisions, suivis ou prochaines étapes. Réponds avec une liste à puces. S'il n'y a rien, écris '- Aucune action identifiée.'\n\n"
            f"Transcription :\n{cleaned_content}"
        ),
        "explain": (
            "Tu es un assistant pédagogue en français. Explique le contenu de la transcription suivante simplement et clairement, "
            "comme à quelqu'un qui découvre le sujet.\n\n"
            f"Transcription :\n{cleaned_content}"
        ),
        "rewrite": (
            "Tu es un assistant de rédaction en français. Reformule proprement la transcription suivante dans un style clair, fluide, "
            "corrigé et lisible, sans changer le sens. "
            "Rends directement le texte final, sans aucune phrase d'introduction, sans titre, sans commentaire méta.\n\n"
            f"Transcription :\n{cleaned_content}"
        ),
        "format": (
            "Tu es un assistant de mise en forme en français. Réorganise uniquement la transcription suivante pour la rendre plus lisible. "
            "Contraintes strictes :\n"
            "1. Conserve le sens et les informations.\n"
            "2. N'invente rien.\n"
            "3. N'ajoute ni résumé ni commentaire.\n"
            "4. Ajoute ponctuation, casse et paragraphes lisibles.\n"
            "5. Garde un registre proche de l'oral d'origine quand c'est utile.\n"
            "6. Ne commence jamais par une phrase comme 'Voici la transcription reformulée' ou 'Voici une version améliorée'.\n\n"
            f"Transcription :\n{cleaned_content}"
        ),
    }

    if normalized_action == "custom":
        if not cleaned_instruction:
            raise ValueError("La consigne IA personnalisée est vide.")
        return (
            "Tu es un assistant francophone qui travaille uniquement à partir de la transcription fournie. "
            "Respecte précisément la consigne de l'utilisateur sans inventer d'informations. "
            "Rends uniquement le contenu final demandé, sans phrase d'introduction ni commentaire méta.\n\n"
            f"Consigne :\n{cleaned_instruction}\n\n"
            f"Transcription :\n{cleaned_content}"
        )

    if normalized_action not in prompts:
        raise ValueError(f"Action IA inconnue : {action}")

    return prompts[normalized_action]


def _build_summary_prompt(content: str) -> str:
    return _build_ai_prompt("summary_actions", content)


def generate_ai_output(
    action: str,
    content: str,
    instruction: str | None = None,
    requested_model: str | None = None,
) -> tuple[str, str]:
    prompt = _build_ai_prompt(action, content, instruction)
    attempted_models: list[str] = []
    last_error: OllamaError | None = None

    for model_name in _build_model_candidates(requested_model):
        attempted_models.append(model_name)
        try:
            payload = _request_json(
                f"{settings.ollama_base_url}/api/generate",
                payload={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=120,
            )
            response_text = str(payload.get("response", "")).strip()
            if not response_text:
                raise OllamaError(f"Le modèle Ollama {model_name} n'a renvoyé aucun contenu exploitable.")

            return model_name, response_text
        except OllamaError as error:
            last_error = error
            continue

    attempted = ", ".join(attempted_models)
    detail = str(last_error) if last_error is not None else "Erreur Ollama inconnue."
    raise OllamaError(
        f"Aucun modèle Ollama n'a pu générer la réponse IA. Modèles testés : {attempted}. Dernière erreur : {detail}"
    )


def generate_summary_actions(content: str, requested_model: str | None = None) -> tuple[str, str]:
    return generate_ai_output("summary_actions", content, None, requested_model)
