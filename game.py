# game.py
import random
from player import Player
from roles import ROLES_LIST, get_role # Assurez-vous que roles.py existe et contient ROLES_LIST et get_role

class Game:
    """
    Gère l'état global et les règles de base d'une partie de Loup Garou.
    Cette classe ne gère PAS les interactions utilisateur (GUI/console)
    ni le séquencement détaillé des actions de nuit/jour, qui sont gérés par la couche UI/contrôleur.
    Elle stocke l'état et fournit des méthodes pour interroger/modifier cet état.
    """
    def __init__(self):
        self.players = [] # Liste de tous les objets Player dans la partie
        self.day_count = 0 # Compteur de jours/nuits
        self.is_day = False # True = Jour, False = Nuit (commence avant la Nuit 1)
        self.game_over = False # Indicateur si la partie est terminée
        self.winning_team = None # Stocke l'équipe gagnante ("Villageois" ou "Loups-Garous")

        # Variables pour stocker les résultats temporaires de la nuit/jour
        self.killed_this_night = [] # Liste des joueurs *potentiellement* tués par les loups (avant résolution sorcière)
        self.saved_this_night = None # Joueur sauvé par la sorcière
        self.potioned_to_death_this_night = None # Joueur tué par la sorcière
        self.lynched_this_day = None # Joueur lynché pendant le jour

        # D'autres états spécifiques aux rôles pourraient être ajoutés ici ou dans les Player objects

    def add_player(self, player):
        """Ajoute un joueur à la partie."""
        if isinstance(player, Player):
            self.players.append(player)
        else:
            print(f"Erreur: Tentative d'ajouter un objet qui n'est pas un joueur: {player}")


    def get_alive_players(self):
        """Retourne la liste des joueurs vivants."""
        return [p for p in self.players if p.is_alive]

    def get_player_by_name(self, name):
        """Recherche et retourne un joueur par son nom (insensible à la casse)."""
        for player in self.players:
            if player.name.lower() == name.strip().lower():
                return player
        return None # Retourne None si le joueur n'est pas trouvé

    def assign_roles(self, roles_config):
        """
        Attribue aléatoirement les rôles aux joueurs en fonction de la configuration.
        Retourne True si l'attribution réussit, False sinon.
        """
        roles_to_assign = []
        for role_name, count in roles_config.items():
            role_obj = get_role(role_name)
            if role_obj:
                 roles_to_assign.extend([role_obj] * count)
            else:
                print(f"Avertissement: Rôle '{role_name}' non reconnu dans ROLES_LIST.") # Debug si un rôle est mal nommé dans la config

        # Vérification que le nombre de rôles correspond au nombre de joueurs
        if len(roles_to_assign) != len(self.players):
            print(f"Erreur: Le nombre de rôles ({len(roles_to_assign)}) ne correspond pas au nombre de joueurs ({len(self.players)}).")
            # Logique de correction ou d'échec si les nombres ne correspondent pas après configuration
            # Pour l'instant, on renvoie False et la GUI doit gérer ça.
            return False

        random.shuffle(roles_to_assign) # Mélange les rôles

        # Assignation
        for i, player in enumerate(self.players):
            player.assign_role(roles_to_assign[i])
            # Note: L'assignation de l'IA logic (player.ai_logic) se fait dans la GUI après l'assignation des rôles

        # print("DEBUG: Rôles assignés.") # Peut laisser pour debug si nécessaire
        return True

    def check_victory_condition(self):
        """
        Vérifie si une condition de victoire est remplie et met à jour l'état du jeu.
        Retourne True si la partie est terminée, False sinon.
        """
        if self.game_over:
            return True # Si déjà terminé, ne revérifie pas

        alive_players = self.get_alive_players()
        wolves_alive = [p for p in alive_players if p.role.is_wolf]
        # Villageois inclut tous les non-loups avec team="Village"
        villagers_alive = [p for p in alive_players if p.role.team == "Village" and not p.role.is_wolf]

        # Condition de victoire des Villageois : tous les Loups-Garous sont morts
        if not wolves_alive:
            self.game_over = True
            self.winning_team = "Villageois"
            # L'annonce de la victoire est gérée par la GUI
            return True

        # Condition de victoire des Loups-Garous : les Loups-Garous sont majoritaires ou à égalité avec les Villageois restants
        if len(wolves_alive) >= len(villagers_alive):
             self.game_over = True
             self.winning_team = "Loups-Garous"
             # L'annonce de la victoire est gérée par la GUI
             return True

        # Ajouter d'autres conditions de victoire/défaite si plus de rôles (ex: couple, joueur solitaire)

        return False # Aucune condition de victoire n'est remplie

    def end_game(self):
        """
        Marque la partie comme terminée. L'affichage final est géré par la GUI.
        La méthode check_victory_condition met déjà game_over et winning_team,
        cette méthode peut être un appel explicite si nécessaire, mais
        check_victory_condition suffit souvent.
        """
        self.game_over = True
        # La GUI se chargera d'afficher les résultats lorsque game_over devient True
        # print("DEBUG: Game.end_game called") # Peut laisser pour debug
        pass # La GUI gère l'affichage de fin de jeu

    # Cette classe peut contenir d'autres méthodes utilitaires si nécessaire,
    # mais les méthodes principales de déroulement (play_night, play_day)
    # sont déplacées dans la logique de l'interface graphique pour gérer
    # le flux événementiel et les pauses pour les joueurs humains.