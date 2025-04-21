# game.py

import random
import time
import logging
from enum import Enum
from typing import List, Dict, Optional, Tuple # Typage plus précis

# --- Gestion Colorama ---
# Tente d'importer colorama pour améliorer l'affichage console.
# Si absent, définit des classes vides pour éviter les erreurs.
try:
    from colorama import Fore, Style, init
    init(autoreset=True) # Initialise colorama pour fonctionner sur Windows et reset auto
    USE_COLORAMA = True
except ImportError:
    # Définition de classes factices si colorama n'est pas installé
    class Fore: RED = YELLOW = CYAN = GREEN = MAGENTA = "" # type: ignore
    class Style: RESET_ALL = BRIGHT = "" # type: ignore
    USE_COLORAMA = False
    # print("Bibliothèque 'colorama' non trouvée. L'affichage sera sans couleurs.") # Éviter print pendant l'import

# --- Gestion nlp_utils (Import différé de l'objet modèle) ---
# Indicateurs pour gérer l'import et la disponibilité du modèle NLP.
_nlp_utils_present = False             # True si nlp_utils.py a pu être importé
_nlp_model_loaded_check_done = False   # True si on a déjà vérifié si le modèle est chargé
_nlp_model_available_flag = False      # True si le modèle spaCy est effectivement chargé et utilisable

try:
    # Importer SEULEMENT la fonction d'analyse au niveau supérieur.
    # L'import de l'objet 'nlp' lui-même est retardé.
    from nlp_utils import analyse_phrase_pour_joueurs
    _nlp_utils_present = True
except ImportError:
    # Log l'erreur si possible, sinon l'imprime (le logger n'est peut-être pas encore prêt)
    print(f"{Fore.RED}ERREUR CRITIQUE: Le fichier nlp_utils.py est introuvable.{Style.RESET_ALL}")
except Exception as e:
    print(f"{Fore.RED}ERREUR CRITIQUE: Une erreur est survenue lors de l'import de nlp_utils: {e}{Style.RESET_ALL}")

# --- Configuration Logging ---
# Configurer le système de logging pour afficher les informations de déroulement.
# Niveau INFO par défaut, peut être mis à DEBUG pour plus de détails.
LOG_LEVEL = logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S' # Format de date optionnel
)

# --- Définition des Rôles ---
class Role(Enum):
    """Énumération des rôles possibles dans le jeu."""
    VILLAGEOIS = "Villageois"
    LOUP_GAROU = "Loup-Garou"
    VOYANTE = "Voyante"
    SORCIERE = "Sorcière"
    # TODO: Ajouter d'autres rôles (Chasseur, Cupidon, etc.)

# --- Classe Joueur ---
class Player:
    """
    Représente un joueur dans la partie avec son état et ses capacités.

    Attributes:
        nom (str): Le nom unique du joueur.
        role (Role | None): Le rôle assigné au joueur.
        est_vivant (bool): Statut du joueur (True si vivant, False sinon).
        vote_pour (Player | None): Joueur pour lequel ce joueur a voté.
        potions_vie_restantes (int): Nombre de potions de vie (pour Sorcière).
        potions_mort_restantes (int): Nombre de potions de mort (pour Sorcière).
        est_protege_cette_nuit (bool): Flag si protégé par la Sorcière cette nuit.
        vient_de_mourir_par_poison (bool): Flag si empoisonné par la Sorcière cette nuit.
    """
    def __init__(self, nom: str):
        """Initialise un joueur avec son nom."""
        if not nom or not isinstance(nom, str):
            raise ValueError("Le nom du joueur ne peut pas être vide.")
        self.nom: str = nom.strip() # Enlever les espaces superflus
        self.role: Optional[Role] = None
        self.est_vivant: bool = True
        self.vote_pour: Optional[Player] = None
        # Attributs spécifiques initialisés
        self.potions_vie_restantes: int = 0
        self.potions_mort_restantes: int = 0
        self.est_protege_cette_nuit: bool = False
        self.vient_de_mourir_par_poison: bool = False

    def __str__(self) -> str:
        """Représentation textuelle pour l'affichage utilisateur."""
        status = f"{Fore.GREEN}Vivant{Style.RESET_ALL}" if self.est_vivant else f"{Fore.RED}Mort{Style.RESET_ALL}"
        role_str = self.role.value if self.role else "Rôle Inconnu"
        return f"{Style.BRIGHT}{self.nom}{Style.RESET_ALL} ({role_str} - {status})"

    def __repr__(self) -> str:
        """Représentation détaillée pour le débogage."""
        return f"Player(nom='{self.nom}', role={self.role}, est_vivant={self.est_vivant})"

    def recevoir_degats(self, type_mort: str = "inconnue") -> bool:
        """
        Marque le joueur comme mort s'il est vivant et loggue la cause.

        Args:
            type_mort (str): Description de la cause de la mort pour les logs.

        Returns:
            bool: True si le joueur vient de mourir, False s'il était déjà mort.
        """
        if self.est_vivant:
            self.est_vivant = False
            logging.info(f"{self.nom} est mort (raison: {type_mort}).")
            print(f"💀 {Style.BRIGHT}{self.nom}{Style.RESET_ALL} a été éliminé(e).")
            # TODO: Ajouter ici la logique pour d'autres effets déclenchés par la mort (ex: Chasseur)
            return True
        else:
            logging.debug(f"Tentative de tuer {self.nom} qui est déjà mort (cause: {type_mort}).")
            return False

    def reset_statuts_nuit(self):
        """Réinitialise les indicateurs de statut utilisés pendant la nuit."""
        self.est_protege_cette_nuit = False
        self.vient_de_mourir_par_poison = False


# --- Classe Principale du Jeu ---
class Game:
    """
    Orchestre le déroulement complet d'une partie de Loup-Garou.
    Intègre la gestion des rôles (Voyante, Sorcière), l'analyse NLP des messages,
    et une structure pour les phases de jeu.
    """
    # --- Constantes et Configuration ---
    MIN_PLAYERS: int = 3 # Nombre minimum de joueurs requis
    PROFILE_NLP: bool = False # Mettre à True pour logguer le temps d'analyse NLP

    def __init__(self, noms_joueurs: List[str]):
        """
        Initialise une nouvelle partie avec la liste des noms de joueurs.

        Args:
            noms_joueurs (List[str]): Liste des noms des participants. Les noms doivent être uniques (insensible à la casse).

        Raises:
            ValueError: Si le nombre de joueurs est insuffisant ou si les noms ne sont pas uniques.
            TypeError: Si noms_joueurs n'est pas une liste de strings.
            RuntimeError: Si l'assignation des rôles échoue.
        """
        if not isinstance(noms_joueurs, list) or not all(isinstance(n, str) for n in noms_joueurs):
             raise TypeError("noms_joueurs doit être une liste de chaînes de caractères.")

        if len(noms_joueurs) < self.MIN_PLAYERS:
             raise ValueError(f"Nombre insuffisant de joueurs ({len(noms_joueurs)}). Minimum requis : {self.MIN_PLAYERS}.")

        # Vérifier l'unicité des noms (insensible à la casse et aux espaces)
        noms_normalises = [n.strip().lower() for n in noms_joueurs]
        if len(set(noms_normalises)) != len(noms_joueurs):
            from collections import Counter # Import localisé car peu utilisé ailleurs
            counts = Counter(noms_normalises)
            doublons = [nom for nom, count in counts.items() if count > 1]
            raise ValueError(f"Les noms des joueurs doivent être uniques (insensible à la casse). Doublon(s) trouvé(s): {', '.join(doublons)}")

        logging.info(f"Initialisation d'une nouvelle partie avec {len(noms_joueurs)} joueurs : {', '.join(noms_joueurs)}")
        self.joueurs: List[Player] = [Player(nom) for nom in noms_joueurs]
        self.phase: str = "Initialisation" # État actuel du jeu
        self.historique_chat: List[str] = [] # Log des messages sans formatage couleur
        self.votes_du_tour: Dict[Player, int] = {} # Stockage des votes du tour en cours
        self.morts_de_la_nuit: List[Tuple[Player, str]] = [] # Stockage des morts de la nuit pour annonce au matin
        self.jours: int = 0 # Compteur de jours/tours

        # Attribuer les rôles dès l'initialisation
        self._assigner_roles()

    # --- Méthodes Privées (Logique Interne) ---

    def _assigner_roles(self):
        """Attribue aléatoirement les rôles aux joueurs selon des règles définies."""
        nb_joueurs = len(self.joueurs)
        roles_disponibles = list(Role) # Copie de tous les rôles définis
        roles_a_assigner = []

        # --- Règles d'attribution (Exemple à adapter/améliorer) ---
        # Règle 1: Nombre de Loups-Garous
        nb_loups = max(1, nb_joueurs // 4) # Environ 1 loup pour 4 joueurs, minimum 1
        if Role.LOUP_GAROU in roles_disponibles:
            roles_a_assigner.extend([Role.LOUP_GAROU] * nb_loups)
            roles_disponibles.remove(Role.LOUP_GAROU)
        else:
            logging.error("Le rôle Loup-Garou n'est pas défini dans l'Enum Role ! Impossible d'assigner.")
            raise RuntimeError("Configuration des rôles invalide: Loup-Garou manquant.")

        # Règle 2: Attribution des rôles spéciaux (si assez de joueurs)
        roles_speciaux_prioritaires = [Role.VOYANTE, Role.SORCIERE]
        # TODO: Ajouter d'autres rôles spéciaux ici

        for special_role in roles_speciaux_prioritaires:
            if special_role in roles_disponibles and len(roles_a_assigner) < nb_joueurs:
                # Condition supplémentaire possible: ex: assigner Sorcière seulement si >= 4 joueurs
                assigner_special = False
                if special_role == Role.SORCIERE and nb_joueurs >= 4: assigner_special = True
                elif special_role == Role.VOYANTE and nb_joueurs >= 3: assigner_special = True
                # Ajouter des conditions pour d'autres rôles ici
                # elif special_role == Role.CHASSEUR and nb_joueurs >= 5: assigner_special = True
                elif special_role not in [Role.SORCIERE, Role.VOYANTE]: # Rôles sans condition de nb joueurs
                    assigner_special = True

                if assigner_special:
                    roles_a_assigner.append(special_role)
                    roles_disponibles.remove(special_role)

        # Règle 3: Compléter avec des Villageois
        nb_restant = nb_joueurs - len(roles_a_assigner)
        if nb_restant > 0:
            if Role.VILLAGEOIS in roles_disponibles:
                 roles_a_assigner.extend([Role.VILLAGEOIS] * nb_restant)
                 # roles_disponibles.remove(Role.VILLAGEOIS) # Pas nécessaire si on ne l'utilise plus
            else:
                 logging.critical("Le rôle Villageois n'est pas défini ou déjà épuisé. Impossible de compléter.")
                 raise RuntimeError("Configuration des rôles invalide: Villageois manquant ou insuffisant.")

        # Vérification finale et mélange
        if len(roles_a_assigner) != nb_joueurs:
            logging.critical(f"Erreur d'assignation des rôles: {len(roles_a_assigner)} rôles pour {nb_joueurs} joueurs. Configuration ou logique invalide.")
            raise RuntimeError("Échec de l'assignation des rôles. Nombre incorrect de rôles assignés.")

        random.shuffle(roles_a_assigner)
        logging.debug(f"Rôles mélangés à assigner: {[r.value for r in roles_a_assigner]}")

        # Assigner aux objets Player et initialiser les attributs spécifiques
        for joueur, role in zip(self.joueurs, roles_a_assigner):
            joueur.role = role
            if role == Role.SORCIERE:
                joueur.potions_vie_restantes = 1
                joueur.potions_mort_restantes = 1
            # TODO: Initialiser d'autres rôles ici (ex: munitions du chasseur)
            logging.debug(f"Rôle assigné : {joueur.nom} est {joueur.role.value}")

        logging.info("Rôles assignés secrètement aux joueurs.")

    def _get_joueur_par_input(self, invite: str, liste_cibles: List[Player], peut_passer: bool = True) -> Optional[Player]:
        """
        Demande à l'utilisateur (via input) de choisir un joueur dans une liste.

        Args:
            invite (str): Le message à afficher à l'utilisateur.
            liste_cibles (List[Player]): La liste des joueurs parmi lesquels choisir.
            peut_passer (bool): Si True, l'option 0 pour annuler/passer est proposée.

        Returns:
            Optional[Player]: Le joueur choisi, ou None si l'utilisateur passe/annule ou en cas d'erreur.
        """
        if not liste_cibles:
            print("Il n'y a personne à cibler.")
            return None

        print(invite)
        for i, p in enumerate(liste_cibles):
            print(f"  {i+1}. {p.nom}") # Affichage simple du nom ici

        prompt_fin = f"(1-{len(liste_cibles)})"
        if peut_passer:
            prompt_fin += ", ou 0 pour passer/annuler"

        while True:
            try:
                choix_str = input(f"Entrez le numéro {prompt_fin} > ")
                choix_num = int(choix_str)

                if peut_passer and choix_num == 0:
                    logging.debug("L'utilisateur a choisi de passer/annuler la sélection.")
                    return None # L'utilisateur choisit de passer
                elif 1 <= choix_num <= len(liste_cibles):
                    joueur_choisi = liste_cibles[choix_num - 1]
                    logging.debug(f"L'utilisateur a choisi {joueur_choisi.nom} (numéro {choix_num}).")
                    return joueur_choisi
                else:
                    # Message d'erreur plus précis
                    valid_range = f"entre 1 et {len(liste_cibles)}"
                    if peut_passer: valid_range += " (ou 0)"
                    print(f"{Fore.YELLOW}Numéro invalide. Veuillez choisir {valid_range}.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.YELLOW}Entrée invalide. Veuillez entrer un nombre.{Style.RESET_ALL}")
            except EOFError:
                logging.warning("Fin de l'input (EOF) détectée pendant la sélection.")
                return None # Considérer comme une annulation
            except Exception as e:
                 # Log l'erreur complète pour le débogage
                 logging.exception(f"Erreur imprévue pendant la sélection de joueur ({invite})", exc_info=True)
                 return None # Sécurité

    def _is_nlp_model_available(self) -> bool:
        """
        Vérifie (une seule fois par partie) si le modèle NLP est chargé et prêt.
        Utilise des flags globaux pour éviter les vérifications répétées.

        Returns:
            bool: True si le modèle NLP est considéré comme disponible, False sinon.
        """
        global _nlp_model_loaded_check_done, _nlp_model_available_flag
        if not _nlp_utils_present:
             return False # Le fichier nlp_utils lui-même n'est pas là

        # Si on n'a pas encore vérifié, on le fait maintenant
        if not _nlp_model_loaded_check_done:
            try:
                # Tenter d'importer l'objet modèle 'nlp' depuis nlp_utils
                from nlp_utils import nlp as nlp_model_object
                _nlp_model_available_flag = nlp_model_object is not None
                logging.info(f"Vérification du modèle NLP: {'Disponible' if _nlp_model_available_flag else 'Non chargé/Indisponible'}")
            except ImportError:
                 logging.warning("Impossible d'importer 'nlp' depuis nlp_utils lors de la vérification.")
                 _nlp_model_available_flag = False
            except Exception as e:
                 logging.exception(f"Erreur lors de la tentative d'import du modèle NLP depuis nlp_utils: {e}", exc_info=True)
                 _nlp_model_available_flag = False
            finally:
                 _nlp_model_loaded_check_done = True # Marquer comme vérifié, même en cas d'erreur

        return _nlp_model_available_flag

    def _resoudre_vote(self):
        """Analyse les votes enregistrés dans self.votes_du_tour et élimine le joueur désigné (si unique)."""
        if not self.votes_du_tour:
            logging.info("Dépouillement: Aucun vote enregistré.")
            print("\nAucun vote n'a été enregistré ce tour-ci.")
            return

        # Filtrer les votes pour ne compter que les joueurs encore valides (au cas où)
        votes_valides = {p: c for p, c in self.votes_du_tour.items() if p and p.est_vivant}
        logging.info(f"Résultats du vote (valides): { {j.nom: c for j, c in votes_valides.items() if c > 0} }")

        # Trouver le(s) joueur(s) ayant reçu le plus de votes
        max_votes = 0
        joueurs_avec_max_votes = []
        if votes_valides: # S'assurer qu'il y a des votes valides à analyser
            max_votes = max(votes_valides.values()) if votes_valides else 0
            if max_votes > 0: # Si au moins un vote a été émis
                joueurs_avec_max_votes = [joueur for joueur, compteur in votes_valides.items() if compteur == max_votes]

        # Appliquer le résultat du vote
        if len(joueurs_avec_max_votes) == 1:
            # Un seul joueur est éliminé
            elimine = joueurs_avec_max_votes[0]
            print(f"\n{Fore.RED}Le village a décidé d'éliminer {Style.BRIGHT}{elimine.nom}{Style.RESET_ALL} avec {max_votes} vote(s).")
            # Appeler recevoir_degats qui gère le statut et log/print
            if elimine.recevoir_degats(type_mort="Vote du village"):
                 print(f"Son rôle était : {Fore.MAGENTA}{elimine.role.value}{Style.RESET_ALL}") # Révéler le rôle
        elif len(joueurs_avec_max_votes) > 1:
            # Égalité
            noms_egalite = ', '.join([f"{Style.BRIGHT}{j.nom}{Style.RESET_ALL}" for j in joueurs_avec_max_votes])
            print(f"\n{Fore.YELLOW}Égalité ! {noms_egalite} ont reçu {max_votes} votes chacun.{Style.RESET_ALL}")
            print("Personne n'est éliminé par le village ce tour-ci.")
            logging.info(f"Vote terminé sur une égalité entre {len(joueurs_avec_max_votes)} joueurs avec {max_votes} votes.")
        else: # max_votes == 0 ou aucun joueur avec votes > 0
            print("\nPersonne n'a reçu de vote majoritaire. Le village n'élimine personne.")
            logging.info("Vote terminé sans élimination (aucun vote significatif).")

    def _action_voyante(self, voyante: Player):
        """Gère l'action nocturne de la Voyante."""
        # Assurer que la voyante est bien vivante avant de la faire agir
        if not voyante.est_vivant:
            logging.warning(f"Tentative d'action pour la voyante {voyante.nom} qui est morte.")
            return

        print(f"\n[{Style.BRIGHT}{voyante.nom}{Style.RESET_ALL} ({Fore.MAGENTA}{voyante.role.value}{Style.RESET_ALL})], c'est votre tour.")
        # Cibles: tous les autres joueurs vivants
        cibles_possibles = [j for j in self.get_joueurs_vivants() if j != voyante]

        # --- Intégration UI: Remplacer _get_joueur_par_input par l'interface spécifique ---
        cible = self._get_joueur_par_input("Qui souhaitez-vous sonder ?", cibles_possibles, peut_passer=True)

        if cible:
            role_cible = cible.role.value if cible.role else "Inconnu"
            # Afficher l'information de manière "secrète" (ici, en console)
            print(f"   -> {Fore.YELLOW}Vision:{Style.RESET_ALL} {Style.BRIGHT}{cible.nom}{Style.RESET_ALL} est {Fore.MAGENTA}{role_cible}{Style.RESET_ALL}. Gardez cette information !")
            logging.info(f"Nuit : Voyante ({voyante.nom}) a sondé {cible.nom} (Rôle: {role_cible}).")
        else:
            print("Vous n'avez sondé personne cette nuit.")
            logging.info(f"Nuit : Voyante ({voyante.nom}) a choisi de ne sonder personne.")

    def _action_loups_garous(self) -> Optional[Player]:
        """Gère l'action nocturne des Loups-Garous (choix de la victime)."""
        print(f"{Fore.RED}Les Loups-Garous se concertent...{Style.RESET_ALL}")
        time.sleep(0.5) # Pause pour l'ambiance

        loups_garous_actifs = self.get_joueurs_vivants(role_filtre=Role.LOUP_GAROU)
        if not loups_garous_actifs:
            print("Les Loups-Garous ne sont plus une menace...")
            logging.info("Nuit : Aucun loup-garou actif pour attaquer.")
            return None

        # Cibles potentielles : tous les joueurs vivants qui ne sont pas des loups
        cibles_potentielles = [j for j in self.get_joueurs_vivants() if j.role != Role.LOUP_GAROU]

        if not cibles_potentielles:
             print("Il n'y a plus de proies pour les Loups !")
             logging.info("Nuit : Aucune cible valide (non-loup) pour les loups.")
             return None

        # --- Logique de Choix des Loups ---
        # TODO: Implémenter une meilleure logique si plusieurs loups (vote interne, IA, etc.)
        # Pour l'instant, le premier loup actif choisit.
        loup_acteur = loups_garous_actifs[0]

        # --- Intégration UI/IA : Remplacer choix par concertation/IA ---
        invite = f"[{Style.BRIGHT}{loup_acteur.nom}{Style.RESET_ALL} ({Fore.RED}{loup_acteur.role.value}{Style.RESET_ALL})], qui attaquez-vous ?"
        # Les loups devraient être obligés de choisir quelqu'un s'il y a des cibles
        victime_choisie = self._get_joueur_par_input(invite, cibles_potentielles, peut_passer=False)

        if victime_choisie:
            print(f"{Fore.RED}Les Loups-Garous ont choisi leur cible...{Style.RESET_ALL}")
            noms_loups = [l.nom for l in loups_garous_actifs]
            logging.info(f"Nuit : Loups ({', '.join(noms_loups)}) ont ciblé {victime_choisie.nom}")
            return victime_choisie
        else:
            # S'il n'y a pas eu de choix (erreur ou cas imprévu)
            print(f"{Fore.YELLOW}Les Loups-Garous n'ont pas pu désigner de cible (erreur?).{Style.RESET_ALL}")
            logging.error(f"Nuit : Échec du choix de cible pour les Loups ({[l.nom for l in loups_garous_actifs]}).")
            return None

    def _action_sorciere(self, sorciere: Player, victime_loups: Optional[Player]):
        """Gère les actions nocturnes de la Sorcière (sauver et/ou empoisonner)."""
        # Assurer que la sorcière est vivante
        if not sorciere.est_vivant:
             logging.warning(f"Tentative d'action pour la sorcière {sorciere.nom} qui est morte.")
             return

        print(f"\n[{Style.BRIGHT}{sorciere.nom}{Style.RESET_ALL} ({Fore.MAGENTA}{sorciere.role.value}{Style.RESET_ALL})], c'est votre tour.")
        # Déterminer les actions possibles
        peut_sauver = sorciere.potions_vie_restantes > 0 and victime_loups is not None and victime_loups.est_vivant
        peut_tuer = sorciere.potions_mort_restantes > 0

        if not peut_sauver and not peut_tuer:
            print("Vous n'avez plus de potions.")
            logging.info(f"Nuit : Sorcière ({sorciere.nom}) n'a plus de potions.")
            return

        # --- 1. Action de Sauvetage (si possible) ---
        action_sauvetage_faite = False
        if peut_sauver:
            # Assurer que victime_loups est bien défini (contournement pour mypy/linting)
            nom_victime_loups = victime_loups.nom if victime_loups else "Inconnu"
            print(f"Les loups ont attaqué {Style.BRIGHT}{nom_victime_loups}{Style.RESET_ALL}.")
            # --- Intégration UI: Remplacer input ---
            reponse = input(f"Voulez-vous utiliser votre {Fore.GREEN}potion de vie{Style.RESET_ALL} ({sorciere.potions_vie_restantes} restante) pour sauver {nom_victime_loups} ? (o/n) > ").lower()
            if reponse.startswith('o'):
                if victime_loups: # Vérification supplémentaire pour mypy
                    victime_loups.est_protege_cette_nuit = True # Marquer comme protégé pour la résolution
                    sorciere.potions_vie_restantes -= 1
                    action_sauvetage_faite = True # Confirmer que l'action a eu lieu
                    print(f"Vous avez utilisé la potion de vie pour sauver {Style.BRIGHT}{nom_victime_loups}{Style.RESET_ALL}.")
                    logging.info(f"Nuit : Sorcière ({sorciere.nom}) a sauvé {nom_victime_loups}.")
            # Si la réponse n'est pas 'o', on ne fait rien (pas de else nécessaire pour la logique)
            if not action_sauvetage_faite:
                 print("Vous n'avez pas utilisé la potion de vie.")
                 logging.info(f"Nuit : Sorcière ({sorciere.nom}) n'a PAS sauvé {nom_victime_loups}.")

        # --- 2. Action d'Empoisonnement (si possible) ---
        if peut_tuer:
            # --- Intégration UI: Remplacer input ---
            reponse = input(f"Voulez-vous utiliser votre {Fore.RED}potion de mort{Style.RESET_ALL} ({sorciere.potions_mort_restantes} restante) sur quelqu'un ? (o/n) > ").lower()
            if reponse.startswith('o'):
                # Cibles : tous les joueurs vivants, sauf la sorcière elle-même.
                # On peut tuer qqn qui a été sauvé, ou la victime des loups si non sauvée.
                cibles_poison = [j for j in self.get_joueurs_vivants() if j != sorciere]

                if not cibles_poison:
                     print("Il n'y a personne d'autre à empoisonner.")
                else:
                    # --- Intégration UI: Remplacer _get_joueur_par_input ---
                    cible_poison = self._get_joueur_par_input("Qui souhaitez-vous empoisonner ?", cibles_poison, peut_passer=True)

                    if cible_poison:
                        cible_poison.vient_de_mourir_par_poison = True # Marquer pour la résolution
                        sorciere.potions_mort_restantes -= 1
                        print(f"Vous avez utilisé la potion de mort sur {Style.BRIGHT}{cible_poison.nom}{Style.RESET_ALL}.")
                        logging.info(f"Nuit : Sorcière ({sorciere.nom}) a empoisonné {cible_poison.nom}.")
                    else:
                        print("Vous n'avez empoisonné personne.")
                        logging.info(f"Nuit : Sorcière ({sorciere.nom}) a choisi de ne pas empoisonner.")

    def _resoudre_morts_nuit(self, victime_choisie_par_loups: Optional[Player]):
        """Applique les morts décidées pendant la nuit en tenant compte des protections."""
        self.morts_de_la_nuit = [] # Réinitialiser la liste des morts pour l'annonce

        # 1. Résoudre la mort par les Loups
        victime_loup_effective: Optional[Player] = None
        raison_mort_loup = "attaqué(e) par les Loups-Garous"
        if victime_choisie_par_loups and victime_choisie_par_loups.est_vivant:
            if victime_choisie_par_loups.est_protege_cette_nuit:
                logging.info(f"Nuit : {victime_choisie_par_loups.nom} était ciblé(e) par les loups mais a été protégé(e).")
            else:
                victime_loup_effective = victime_choisie_par_loups

        # 2. Résoudre la mort par la Potion de la Sorcière
        victime_poison_effective: Optional[Player] = None
        raison_mort_poison = "empoisonné(e) par la Sorcière"
        # Itérer sur une copie de la liste des joueurs au cas où la liste change pendant l'itération (peu probable ici)
        for joueur in list(self.joueurs):
            if joueur.vient_de_mourir_par_poison and joueur.est_vivant:
                 victime_poison_effective = joueur
                 break # On suppose qu'une seule potion de mort est utilisée par nuit

        # 3. Appliquer les morts et remplir la liste pour l'annonce
        # Gérer le cas où la même personne est tuée par les deux (priorité à la mort)
        if victime_loup_effective and victime_loup_effective == victime_poison_effective:
             if victime_loup_effective.recevoir_degats(type_mort="Attaque Loup-Garou et Potion Sorcière"):
                 self.morts_de_la_nuit.append((victime_loup_effective, f"{raison_mort_loup} ET {raison_mort_poison}"))
        else:
            # Mort par Loup seulement (si différent du poison ou si pas de poison)
            if victime_loup_effective and victime_loup_effective.recevoir_degats(type_mort="Attaque Loup-Garou"):
                self.morts_de_la_nuit.append((victime_loup_effective, raison_mort_loup))
            # Mort par Poison seulement (si différent du loup ou si pas de victime loup)
            if victime_poison_effective and victime_poison_effective.recevoir_degats(type_mort="Potion Sorcière"):
                 self.morts_de_la_nuit.append((victime_poison_effective, raison_mort_poison))

        # 4. Annoncer les morts au début du jour
        print("-" * 20) # Séparateur visuel
        if not self.morts_de_la_nuit:
            print("Personne n'est mort cette nuit. Le village semble calme...")
            logging.info("Nuit: Aucune mort effective.")
        else:
            print("Ce matin, le village découvre le(s) corps de :")
            for victime, cause in self.morts_de_la_nuit:
                 # recevoir_degats a déjà affiché la mort individuelle
                 print(f" - {Style.BRIGHT}{victime.nom}{Style.RESET_ALL}, {cause}.")
                 print(f"   Son rôle était : {Fore.MAGENTA}{victime.role.value}{Style.RESET_ALL}")
                 logging.info(f"Nuit: {victime.nom} est mort(e) ({cause}). Rôle: {victime.role.value}")
                 # TODO: Ajouter ici la logique pour d'autres effets (ex: Chasseur peut tirer)
                 # if victime.role == Role.CHASSEUR: self._action_chasseur_post_mortem(victime)


    # --- Méthodes Publiques (Contrôle du Jeu et Phases) ---

    def get_joueurs_vivants(self, role_filtre: Optional[Role] = None) -> List[Player]:
        """Retourne la liste des objets Player vivants, optionnellement filtrée par rôle."""
        vivants = [j for j in self.joueurs if j.est_vivant]
        if role_filtre:
            # Filtrer par rôle si demandé
            return [j for j in vivants if j.role == role_filtre]
        return vivants

    def get_player_by_name(self, nom: str, vivants_seulement: bool = True) -> Optional[Player]:
        """
        Trouve un objet Player par son nom (insensible à la casse et aux espaces).

        Args:
            nom (str): Le nom à rechercher.
            vivants_seulement (bool): Si True, ne cherche que parmi les joueurs vivants.

        Returns:
            Optional[Player]: Le joueur trouvé ou None.
        """
        if not nom or not isinstance(nom, str): return None # Entrée invalide
        nom_cherche = nom.strip().lower()
        joueurs_a_chercher = self.get_joueurs_vivants() if vivants_seulement else self.joueurs
        for joueur in joueurs_a_chercher:
            if joueur.nom.strip().lower() == nom_cherche:
                return joueur
        return None

    def traiter_message_joueur(self, nom_joueur_auteur: str, message: str):
        """
        Traite un message reçu, l'affiche, et utilise NLP (si disponible) pour détecter les mentions.
        Valide les mentions contre les joueurs vivants.
        """
        if not message or not isinstance(message, str):
            logging.debug("Message vide ou invalide reçu, ignoré.")
            return

        auteur = self.get_player_by_name(nom_joueur_auteur, vivants_seulement=True) # L'auteur doit être vivant
        if not auteur:
            logging.warning(f"Message reçu d'un joueur inconnu ou mort : {nom_joueur_auteur}")
            return

        # 1. Afficher le message (avec couleur si possible)
        log_message = f"[{Style.BRIGHT}{auteur.nom}{Style.RESET_ALL}]: {message}"
        self.historique_chat.append(f"[{auteur.nom}]: {message}") # Historique sans couleurs
        print(log_message)

        # 2. Analyser avec NLP (si disponible)
        joueurs_valides_mentionnes: List[Player] = []
        if self._is_nlp_model_available():
            try:
                 # La fonction a été importée au niveau supérieur si _nlp_utils_present est True
                 noms_detectes_nlp = analyse_phrase_pour_joueurs(message, perform_timing=self.PROFILE_NLP)

                 if noms_detectes_nlp:
                     logging.debug(f"NLP a détecté les mentions potentielles: {noms_detectes_nlp} dans le message de {auteur.nom}")
                     # 3. Valider les noms détectés contre les joueurs vivants (excluant l'auteur)
                     for nom_detecte in noms_detectes_nlp:
                         joueur_valide = self.get_player_by_name(nom_detecte, vivants_seulement=True)
                         # Vérifier existence, statut vivant, et que ce n'est pas l'auteur lui-même
                         if joueur_valide and joueur_valide != auteur:
                             # Éviter les doublons si un nom est mentionné plusieurs fois
                             if joueur_valide not in joueurs_valides_mentionnes:
                                 joueurs_valides_mentionnes.append(joueur_valide)

                     if joueurs_valides_mentionnes:
                         noms_str = ', '.join([f"{Style.BRIGHT}{jv.nom}{Style.RESET_ALL}" for jv in joueurs_valides_mentionnes])
                         info_msg = f"   ({Fore.CYAN}INFO:{Style.RESET_ALL} {auteur.nom} mentionne {noms_str})"
                         print(info_msg)
                         logging.info(f"INFO JEU (NLP): {auteur.nom} parle de joueur(s) valide(s) : {[jv.nom for jv in joueurs_valides_mentionnes]}")
                         # TODO: Que faire avec cette information ? (IA, historique, etc.)

            except NameError: # Sécurité si analyse_phrase_pour_joueurs n'a pas été importée
                 logging.error("Fonction NLP 'analyse_phrase_pour_joueurs' non trouvée, analyse annulée.")
            except Exception as e:
                 # Capturer les erreurs spécifiques à l'analyse NLP
                 logging.exception(f"Erreur pendant l'analyse NLP dans traiter_message_joueur pour '{message[:50]}...'", exc_info=True)
        # else: # Pas besoin de logguer ici si le modèle n'est pas dispo, c'est déjà signalé

    def lancer_phase_discussion(self):
        """Simule une phase de discussion où les joueurs parlent à tour de rôle."""
        # Incrémenter le jour ici, car la discussion marque le début du jour
        self.jours += 1
        self.phase = "Discussion"
        print(f"\n{Fore.YELLOW}--- JOUR {self.jours} : Phase de Discussion ---{Style.RESET_ALL}")
        print("Les villageois se réveillent (sauf les morts). Discutez pour trouver les Loups-Garous !")

        joueurs_a_parler = self.get_joueurs_vivants()
        if not joueurs_a_parler:
            logging.warning("Phase Discussion: Aucun joueur vivant pour parler.")
            return # Devrait être géré par check_game_over avant d'arriver ici

        # Ordre de parole aléatoire pour plus de dynamisme
        random.shuffle(joueurs_a_parler)
        logging.debug(f"Ordre de parole pour la discussion Jour {self.jours}: {[p.nom for p in joueurs_a_parler]}")

        for joueur_actuel in joueurs_a_parler:
            try:
                # --- Point d'intégration UI : Remplacer input() par la méthode de l'interface ---
                message = input(f"[{Style.BRIGHT}{joueur_actuel.nom}{Style.RESET_ALL}] > ")
                self.traiter_message_joueur(joueur_actuel.nom, message)
            except EOFError:
                logging.warning("Fin de l'input (EOF) détectée pendant la discussion.")
                break # Sortir de la boucle de discussion
            except Exception as e:
                 logging.exception(f"Erreur pendant le tour de parole de {joueur_actuel.nom}", exc_info=True)

            time.sleep(0.1) # Petite pause artificielle entre les tours de parole

        logging.info("Fin de la phase de discussion du jour %d.", self.jours)

    def lancer_phase_vote(self):
        """Gère la phase de vote du village pour éliminer un joueur."""
        self.phase = "Vote"
        print(f"\n{Fore.YELLOW}--- Phase de Vote ---{Style.RESET_ALL}")
        print("Le moment est venu de voter pour éliminer un suspect.")

        joueurs_votants = self.get_joueurs_vivants()
        # Dans la version simple, on peut voter pour n'importe qui de vivant
        joueurs_eligibles = self.get_joueurs_vivants()

        if not joueurs_votants:
            logging.info("Phase Vote: Aucun joueur vivant pour voter.")
            print("Il n'y a plus personne pour voter.")
            return

        # Réinitialiser les votes du tour précédent
        self.votes_du_tour = {j: 0 for j in joueurs_eligibles} # Initialiser avec 0 vote pour chaque éligible
        for j in joueurs_votants: j.vote_pour = None # Réinitialiser le choix de vote du joueur

        print(f"Joueurs éligibles au vote : {Fore.MAGENTA}{', '.join([j.nom for j in joueurs_eligibles])}{Style.RESET_ALL}")

        # Collecter les votes de chaque joueur vivant
        for votant in joueurs_votants:
            # --- Point d'intégration UI : Remplacer input() par la méthode de l'interface ---
            invite = f"[{Style.BRIGHT}{votant.nom}{Style.RESET_ALL}], pour qui votez-vous ?"
            # Utiliser la méthode helper pour obtenir le choix du joueur
            cible_votee = self._get_joueur_par_input(invite, joueurs_eligibles, peut_passer=True) # Permettre de passer/annuler

            if cible_votee:
                # Enregistrer le vote si une cible valide est choisie
                votant.vote_pour = cible_votee
                # Incrémenter le compteur pour le joueur ciblé
                self.votes_du_tour[cible_votee] = self.votes_du_tour.get(cible_votee, 0) + 1
                print(f"   {votant.nom} a voté pour {Style.BRIGHT}{cible_votee.nom}{Style.RESET_ALL}")
                logging.debug(f"Vote enregistré : {votant.nom} -> {cible_votee.nom}")
            else:
                # L'utilisateur a choisi 0 ou une erreur s'est produite dans _get_joueur_par_input
                print(f"   {votant.nom} n'a pas voté ou a annulé.")
                logging.debug(f"Vote non enregistré ou annulé pour : {votant.nom}")

        # Une fois tous les votes collectés, analyser le résultat
        self._resoudre_vote()

    def lancer_phase_nuit(self):
        """Simule les actions des rôles nocturnes (Voyante, Loups, Sorcière)."""
        self.phase = "Nuit"
        print(f"\n{Fore.CYAN}--- NUIT {self.jours} ---{Style.RESET_ALL}")
        print("Le village s'endort...")
        time.sleep(1) # Pause dramatique

        # Réinitialiser les statuts de nuit et la liste des morts prévues
        self.morts_de_la_nuit = []
        for p in self.joueurs: p.reset_statuts_nuit()

        # --- Déroulement des Actions Nocturnes (Ordre Important!) ---

        # 1. Action Voyante (si elle existe et est vivante)
        voyantes = self.get_joueurs_vivants(role_filtre=Role.VOYANTE)
        if voyantes:
            self._action_voyante(voyantes[0]) # On suppose une seule voyante
            time.sleep(0.5)

        # 2. Action Loups-Garous (choix de la victime)
        victime_choisie_par_loups: Optional[Player] = self._action_loups_garous()
        time.sleep(1)

        # 3. Action Sorcière (si elle existe et est vivante)
        sorcieres = self.get_joueurs_vivants(role_filtre=Role.SORCIERE)
        if sorcieres:
             self._action_sorciere(sorcieres[0], victime_choisie_par_loups) # On suppose une seule sorcière
             time.sleep(0.5)

        # TODO: Ajouter les actions d'autres rôles nocturnes ici

        # 4. Résolution des morts de la nuit
        self._resoudre_morts_nuit(victime_choisie_par_loups)

        print(f"{Fore.YELLOW}Le jour se lève...{Style.RESET_ALL}")


    def verifier_fin_partie(self) -> bool:
        """
        Vérifie si une condition de victoire/fin de partie est atteinte.

        Returns:
            bool: True si la partie est terminée, False sinon.
        """
        loups_vivants = self.get_joueurs_vivants(role_filtre=Role.LOUP_GAROU)
        # Considérer tous les non-loups comme "camp adverse" pour la condition simple
        non_loups_vivants = [j for j in self.get_joueurs_vivants() if j.role != Role.LOUP_GAROU]

        # --- Conditions de fin de partie ---
        # TODO: Ajouter des conditions pour rôles spéciaux (Amoureux, Flutiste, etc.)
        victoire_village = False
        victoire_loups = False
        raison_fin = ""

        if not loups_vivants:
            # Plus de loups : les villageois (et rôles alliés) gagnent
            victoire_village = True
            raison_fin = "Tous les Loups-Garous ont été éliminés."
        elif not non_loups_vivants:
            # Plus de non-loups : les loups gagnent
            victoire_loups = True
            raison_fin = "Les Loups-Garous ont dévoré tous les innocents."
        elif len(loups_vivants) >= len(non_loups_vivants):
            # Les loups sont aussi nombreux ou plus nombreux que les autres : ils gagnent
            victoire_loups = True
            raison_fin = "Les Loups-Garous sont majoritaires et contrôlent le village."

        # Si une condition de fin est remplie
        if victoire_village or victoire_loups:
            self.phase = "Terminee" # Mettre à jour l'état du jeu
            print("-" * 30)
            if victoire_village:
                print(f"\n{Fore.GREEN}🏆 VICTOIRE DES VILLAGEOIS !{Style.RESET_ALL}")
            elif victoire_loups:
                print(f"\n{Fore.RED}🐺 VICTOIRE DES LOUPS-GAROUS !{Style.RESET_ALL}")
            print(raison_fin)
            logging.info(f"Fin de partie : Victoire {'Villageois' if victoire_village else 'Loups-Garous'}. Raison: {raison_fin}")
            return True # Indiquer que la partie est finie

        # La partie continue
        return False

    def lancer_partie(self):
        """Boucle principale qui orchestre les tours de jeu jusqu'à la fin."""
        logging.info("Lancement de la boucle principale du jeu.")
        print(f"\n{Fore.MAGENTA}=== Bienvenue à Thiercelieux (Version Console) ==={Style.RESET_ALL}")
        print(f"Joueurs ({len(self.joueurs)}): {', '.join([p.nom for p in self.joueurs])}")

        # Révélation "secrète" des rôles (pour le mode console)
        print(f"\n{Fore.YELLOW}--- Révélation secrète des rôles ---{Style.RESET_ALL}")
        for joueur in self.joueurs:
            # --- Intégration UI: Envoyer via canal privé ---
            print(f"[{Style.BRIGHT}{joueur.nom}{Style.RESET_ALL}] Votre rôle est : {Fore.MAGENTA}{joueur.role.value if joueur.role else 'ERREUR'}{Style.RESET_ALL}")
        print("-" * 30)
        time.sleep(1) # Laisser le temps de lire

        # Boucle principale des tours
        try:
            while self.phase != "Terminee":
                logging.debug(f"Début du tour {self.jours + 1}. Phase actuelle: {self.phase}")

                # --- Début du Tour (Jour) ---
                if self.jours == 0:
                     # Premier tour: pas de morts la nuit précédente, on passe direct au vote
                     print("\nPremier jour. Personne n'est mort cette nuit (la partie commence).")
                     self.jours = 1 # Initialiser le compteur de jours pour la suite
                else:
                     # Tours suivants: commencer par la discussion
                     self.lancer_phase_discussion()
                     if self.verifier_fin_partie(): break # Vérifier après la discussion

                # --- Phase de Vote ---
                # Vérifier s'il reste assez de joueurs pour voter
                if len(self.get_joueurs_vivants()) >= 2:
                    self.lancer_phase_vote()
                    if self.verifier_fin_partie(): break # Vérifier après le vote/élimination
                else:
                     logging.info("Moins de 2 joueurs vivants, saut de la phase de vote.")


                # --- Phase de Nuit ---
                # Vérifier s'il y a des actions de nuit à faire (au moins un loup ou un rôle spécial nocturne)
                if any(p.role in [Role.LOUP_GAROU, Role.VOYANTE, Role.SORCIERE] for p in self.get_joueurs_vivants()):
                    self.lancer_phase_nuit()
                    if self.verifier_fin_partie(): break # Vérifier après les actions de nuit
                else:
                     logging.info("Aucun rôle nocturne actif, saut de la phase de nuit.")
                     print("\nLa nuit est étrangement calme... Aucun rôle spécial nocturne ou loup n'est actif.")
                     # Il faut quand même passer au jour suivant si la partie n'est pas finie
                     # Si on saute la nuit, on doit incrémenter le jour manuellement ici ?
                     # Normalement, lancer_phase_discussion l'incrémente. Vérifions.

        except Exception as e:
             # Capturer une erreur inattendue pendant la boucle de jeu
             logging.exception("Erreur inattendue pendant la boucle de jeu principale.", exc_info=True)
             print(f"\n{Fore.RED}Une erreur est survenue pendant le jeu: {e}{Style.RESET_ALL}")
             self.phase = "Terminee" # Forcer la fin en cas d'erreur grave


        # --- Fin de la Partie ---
        print(f"\n{Fore.MAGENTA}=== Partie Terminée ==={Style.RESET_ALL}")
        print("État final des joueurs :")
        # Utiliser la représentation __str__ de Player qui inclut les couleurs
        # Trier par nom pour un affichage cohérent
        for joueur in sorted(self.joueurs, key=lambda p: p.nom):
            print(f"- {joueur}") # __str__ gère l'affichage rôle/statut
        logging.info("Affichage de l'état final des joueurs.")


# --- Point d'Entrée Principal du Script ---
if __name__ == "__main__":
    # --- Vérification Explicite du Modèle NLP au Lancement ---
    nlp_ready_message_shown = False
    if not _nlp_utils_present:
        print(f"\n{Fore.YELLOW}INFO:{Style.RESET_ALL} Fichier nlp_utils.py introuvable. Analyse NLP désactivée.")
        nlp_ready_message_shown = True
    else:
        try:
            # Tenter d'importer l'objet 'nlp' juste pour vérifier son état pour l'utilisateur
            from nlp_utils import nlp as nlp_check_main, NOM_MODELE_SPACY
            if nlp_check_main is not None:
                 print(f"{Fore.GREEN}INFO:{Style.RESET_ALL} Modèle spaCy '{NOM_MODELE_SPACY}' chargé. Analyse NLP activée.")
                 nlp_ready_message_shown = True
            else:
                 # Le fichier existe mais le modèle n'a pas chargé (erreur logguée dans nlp_utils)
                 print(f"\n{Fore.YELLOW}INFO:{Style.RESET_ALL} Modèle spaCy ('{NOM_MODELE_SPACY}') non chargé (voir logs). Analyse NLP désactivée.")
                 print(f"   Pour l'activer, vérifiez l'installation et exécutez: python -m spacy download {NOM_MODELE_SPACY}")
                 nlp_ready_message_shown = True
        except ImportError:
             print(f"\n{Fore.YELLOW}INFO:{Style.RESET_ALL} Impossible d'importer depuis nlp_utils. Analyse NLP désactivée.")
             nlp_ready_message_shown = True
        except Exception as e:
             print(f"\n{Fore.YELLOW}INFO:{Style.RESET_ALL} Erreur lors de la vérification du modèle NLP: {e}. Analyse NLP désactivée.")
             nlp_ready_message_shown = True

    # --- Configuration et Lancement ---
    # TODO: Remplacer par une méthode pour obtenir les noms (arguments, interface, etc.)
    noms_des_joueurs_partie = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"] # Exemple

    try:
        # Créer l'instance du jeu
        jeu_en_cours = Game(noms_des_joueurs_partie)
        # Lancer la boucle principale du jeu
        jeu_en_cours.lancer_partie()

    except ValueError as ve:
        # Erreurs attendues lors de l'initialisation (pas assez de joueurs, doublons)
        print(f"\n{Fore.RED}Erreur de Configuration: {ve}{Style.RESET_ALL}")
        logging.error(f"Erreur de configuration de la partie: {ve}")
    except KeyboardInterrupt:
         # Permettre à l'utilisateur d'arrêter proprement avec Ctrl+C
         print("\nPartie interrompue par l'utilisateur (Ctrl+C).")
         logging.info("Partie interrompue par KeyboardInterrupt.")
    except Exception as e:
        # Capturer toutes les autres erreurs inattendues
        logging.exception("Une erreur CRITIQUE et non gérée est survenue pendant l'exécution du jeu!", exc_info=True)
        print(f"\n{Fore.RED}ERREUR CRITIQUE INATTENDUE: {e}{Style.RESET_ALL}")
        print("Veuillez consulter les logs pour un rapport d'erreur détaillé.")