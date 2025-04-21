# nlp_utils.py

import spacy
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Nom du modèle spaCy à utiliser
NOM_MODELE_SPACY = "fr_core_news_sm"
nlp = None  # Initialisation du modèle

try:
    # Chargement du modèle spaCy
    nlp = spacy.load(NOM_MODELE_SPACY)
    logging.info(f"Modèle spaCy '{NOM_MODELE_SPACY}' chargé avec succès.")
except OSError:
    logging.error(f"ERREUR CRITIQUE : Le modèle spaCy '{NOM_MODELE_SPACY}' n'a pas été trouvé.")
    logging.error(f"Veuillez le télécharger avec la commande : python -m spacy download {NOM_MODELE_SPACY}")
except Exception as e:
    logging.error(f"Une erreur inattendue est survenue lors du chargement du modèle spaCy : {e}")

def analyse_phrase_pour_joueurs(phrase: str) -> list[str]:
    """
    Analyse une phrase pour extraire les noms propres (entités PER)
    qui pourraient correspondre à des noms de joueurs.

    Args:
        phrase: La chaîne de caractères (message du joueur) à analyser.

    Returns:
        Une liste contenant les noms de personnes détectés.
        Retourne une liste vide si le modèle n'est pas chargé ou si aucune personne n'est trouvée.
    """
    if nlp is None:
        logging.warning("Avertissement : Le modèle spaCy n'est pas chargé. L'analyse NLP ne peut pas être effectuée.")
        return []

    if not phrase or not isinstance(phrase, str):
        logging.debug("Phrase vide ou invalide reçue pour l'analyse.")
        return []

    try:
        doc = nlp(phrase)
        joueurs_mentionnes = [ent.text for ent in doc.ents if ent.label_ == "PER"]

        if joueurs_mentionnes:
            logging.debug(f"Analyse NLP de '{phrase}' -> Joueurs mentionnés trouvés : {joueurs_mentionnes}")
        else:
            logging.debug(f"Analyse NLP de '{phrase}' -> Aucun joueur mentionné trouvé.")

        return joueurs_mentionnes

    except Exception as e:
        logging.error(f"Erreur pendant l'analyse NLP de la phrase '{phrase}' : {e}")
        return []

if __name__ == "__main__":
    if nlp:
        print("\n--- Test de la fonction analyse_phrase_pour_joueurs ---")
        phrases_test = [
            "Je pense que Paul est un loup-garou.",
            "Marie et Antoine semblent suspects, non ?",
            "Le village doit voter contre quelqu'un, peut-être Chloé ?",
            "Je suis certain que c'est Nicolas ou Sophie.",
            "Personne ne parle.",
            "J'accuse Pierre de mentir !",
            12345,
            ""
        ]

        for p in phrases_test:
            resultat = analyse_phrase_pour_joueurs(p)
            print(f"Phrase : '{p}' -> Joueurs détectés : {resultat}")
    else:
        print("\nImpossible d'exécuter les tests car le modèle spaCy n'est pas chargé.")
        print(f"Assurez-vous d'avoir téléchargé '{NOM_MODELE_SPACY}' avec : python -m spacy download {NOM_MODELE_SPACY}")
