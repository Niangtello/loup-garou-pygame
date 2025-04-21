# nlp_utils.py

import spacy
import logging
import time # Pour le profiling potentiel

# Configuration du logging (optionnel mais recommandé)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Chargement du modèle spaCy ---
NOM_MODELE_SPACY = "fr_core_news_sm"
nlp = None # Initialise à None

try:
    logging.info(f"Tentative de chargement du modèle spaCy '{NOM_MODELE_SPACY}'...")
    nlp = spacy.load(NOM_MODELE_SPACY)
    logging.info(f"Modèle spaCy '{NOM_MODELE_SPACY}' chargé avec succès.")
except OSError:
    logging.error(f"ERREUR CRITIQUE : Le modèle spaCy '{NOM_MODELE_SPACY}' n'a pas été trouvé.")
    logging.error(f"Veuillez le télécharger avec la commande : python -m spacy download {NOM_MODELE_SPACY}")
except Exception as e:
    logging.error(f"Une erreur inattendue est survenue lors du chargement du modèle spaCy : {e}")

# --- Fonctions d'analyse NLP ---

def analyse_phrase_pour_joueurs(phrase: str, perform_timing: bool = False) -> list[str]:
    """
    Analyse une phrase pour extraire les noms propres (entités PER)
    qui pourraient correspondre à des noms de joueurs.

    Args:
        phrase: La chaîne de caractères (message du joueur) à analyser.
        perform_timing (bool): Si True, loggue le temps pris pour l'analyse.

    Returns:
        Une liste contenant les noms de personnes détectés.
        Retourne une liste vide si le modèle n'est pas chargé, si aucune personne n'est trouvée,
        ou en cas d'erreur.
    """
    start_time = time.perf_counter() if perform_timing else 0

    if nlp is None:
        # Le warning est déjà émis lors du chargement échoué, on évite de spammer ici.
        # logging.warning("Avertissement : Modèle spaCy non chargé, analyse impossible.")
        return []

    if not phrase or not isinstance(phrase, str):
        logging.debug("Phrase vide ou invalide reçue pour l'analyse.")
        return []

    joueurs_mentionnes = []
    try:
        doc = nlp(phrase)
        joueurs_mentionnes = [ent.text for ent in doc.ents if ent.label_ == "PER"]

        if joueurs_mentionnes:
            logging.debug(f"Analyse NLP de '{phrase[:50]}...' -> Joueurs mentionnés trouvés : {joueurs_mentionnes}")
        # else: # Log moins verbeux
            # logging.debug(f"Analyse NLP de '{phrase[:50]}...' -> Aucun joueur mentionné trouvé.")

    except Exception as e:
        logging.error(f"Erreur pendant l'analyse NLP de la phrase '{phrase[:50]}...' : {e}")
        # Retourne une liste vide en cas d'erreur

    if perform_timing:
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        logging.debug(f"Analyse NLP traitée en {duration_ms:.2f} ms.")

    return joueurs_mentionnes

# --- Exemple d'utilisation (si le fichier est exécuté directement) ---
# (Le bloc if __name__ == "__main__" reste le même que précédemment)