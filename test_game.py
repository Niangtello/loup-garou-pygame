# test_game.py
import unittest
import io # Pour capturer stdout
import sys
from unittest.mock import patch # Pour simuler l'input utilisateur

# Assure-toi que game.py et nlp_utils.py sont accessibles
try:
    from game import Game, Player, Role, Fore, Style # Importer aussi Fore/Style si on teste l'output coloré
    from nlp_utils import analyse_phrase_pour_joueurs, nlp as nlp_model
except ImportError as e:
     print(f"Erreur d'import dans les tests: {e}. Assurez-vous que game.py/nlp_utils.py sont accessibles.")
     # Quitter si les imports de base échouent
     sys.exit(1)

# --- Tests NLP (Skipped si le modèle n'est pas là) ---
@unittest.skipIf(nlp_model is None, "Modèle spaCy non chargé, tests NLP sautés.")
class TestNLPFunctions(unittest.TestCase):
    # ... (Les tests NLP restent les mêmes que dans l'exemple précédent) ...
    def test_analyse_phrase_detection_simple(self):
        self.assertIn("Paul", analyse_phrase_pour_joueurs("Paul est très suspect."))
    def test_analyse_phrase_detection_multiple(self):
        res = analyse_phrase_pour_joueurs("Je pense que Marie ou Antoine mentent.")
        self.assertIn("Marie", res)
        self.assertIn("Antoine", res)
    def test_analyse_phrase_aucune_detection(self):
        self.assertEqual([], analyse_phrase_pour_joueurs("Il fait beau."))


# --- Tests de la Logique du Jeu ---
class TestGameLogic(unittest.TestCase):

    def setUp(self):
        """Met en place une partie simple avant chaque test."""
        self.noms = ["P1", "P2", "P3", "P4"] # 4 joueurs pour avoir des rôles spéciaux
        # Supprimer les couleurs pour faciliter la comparaison des outputs capturés
        Fore.RED = Fore.YELLOW = Fore.CYAN = Fore.GREEN = Fore.MAGENTA = ""
        Style.RESET_ALL = Style.BRIGHT = ""
        # On crée la partie ici
        self.game = Game(self.noms)
        # Pour des tests prédictibles, on peut forcer les rôles APRES l'init
        # Note: Cela teste l'état après _assigner_roles, mais permet de contrôler les scénarios
        players = self.game.joueurs
        if len(players) == 4: # Adapter si MIN_PLAYERS ou la logique change
             players[0].role = Role.VILLAGEOIS
             players[1].role = Role.LOUP_GAROU
             players[2].role = Role.VOYANTE
             players[3].role = Role.SORCIERE
             # Réinitialiser les potions de la sorcière si on force le rôle après init
             players[3].potions_vie_restantes = 1
             players[3].potions_mort_restantes = 1
        self.p_villageois = players[0]
        self.p_loup = players[1]
        self.p_voyante = players[2]
        self.p_sorciere = players[3]

    def test_initialisation_partie_et_roles(self):
        self.assertEqual(len(self.game.joueurs), 4)
        self.assertTrue(all(p.est_vivant for p in self.game.joueurs))
        # Vérifier les rôles forcés dans setUp (ou vérifier qu'ils sont assignés si aléatoires)
        self.assertEqual(self.p_loup.role, Role.LOUP_GAROU)
        self.assertEqual(self.p_sorciere.role, Role.SORCIERE)
        self.assertEqual(self.p_sorciere.potions_vie_restantes, 1)

    def test_get_player_by_name_case_insensitive(self):
        self.assertEqual(self.game.get_player_by_name("p1"), self.p_villageois)
        self.assertEqual(self.game.get_player_by_name("P2"), self.p_loup)
        self.assertIsNone(self.game.get_player_by_name("p5"))

    @patch('builtins.input', side_effect=['2']) # Simule l'utilisateur entrant '2'
    def test_action_voyante_voit_role(self, mock_input):
        """Teste si la voyante 'voit' le rôle correctement."""
        # Capturer la sortie standard pour vérifier ce qui est affiché
        captured_output = io.StringIO()
        sys.stdout = captured_output

        self.game._action_voyante(self.p_voyante)

        sys.stdout = sys.__stdout__ # Restaurer stdout
        output = captured_output.getvalue()
        # P2 est le Loup-Garou
        self.assertIn(f"Vision: P2 est Loup-Garou", output)
        # Vérifier que l'input a été appelé une fois
        mock_input.assert_called_once()

    @patch('builtins.input', side_effect=['1']) # Le loup choisit P1 (Villageois)
    def test_action_loups_garous_ciblage(self, mock_input):
        victime = self.game._action_loups_garous()
        self.assertIsNotNone(victime)
        self.assertEqual(victime.nom, "P1") # P1 est à l'index 0, donc choix '1' le cible
        mock_input.assert_called_once() # Vérifie que l'input a été demandé

    @patch('builtins.input', side_effect=['o', 'n']) # Répond 'o' pour sauver, 'n' pour tuer
    def test_action_sorciere_sauvetage(self, mock_input):
        """Teste si la sorcière utilise la potion de vie."""
        victime_potentielle = self.p_villageois # P1
        self.assertEqual(self.p_sorciere.potions_vie_restantes, 1)
        self.assertFalse(victime_potentielle.est_protege_cette_nuit)

        self.game._action_sorciere(self.p_sorciere, victime_potentielle)

        self.assertEqual(self.p_sorciere.potions_vie_restantes, 0) # Potion utilisée
        self.assertTrue(victime_potentielle.est_protege_cette_nuit) # Marqué comme protégé
        # Vérifier que input a été appelé 2 fois (pour sauver, puis pour tuer)
        self.assertEqual(mock_input.call_count, 2)

    @patch('builtins.input', side_effect=['n', 'o', '1']) # Répond 'n' pour sauver, 'o' pour tuer, choisit la cible 1 (P1)
    def test_action_sorciere_empoisonnement(self, mock_input):
        """Teste si la sorcière utilise la potion de mort."""
        victime_potentielle_loups = self.p_loup # Disons que les loups ont ciblé P2 (le loup !) - pour le test
        self.assertEqual(self.p_sorciere.potions_mort_restantes, 1)
        self.assertFalse(self.p_villageois.vient_de_mourir_par_poison) # P1 est la cible potentielle du poison

        self.game._action_sorciere(self.p_sorciere, victime_potentielle_loups)

        self.assertEqual(self.p_sorciere.potions_mort_restantes, 0) # Potion utilisée
        # P1 devrait être la première cible valide proposée (car P2=victime_loups, P3=voyante, P4=sorciere)
        self.assertTrue(self.p_villageois.vient_de_mourir_par_poison)
        self.assertEqual(mock_input.call_count, 3) # n, o, 1

    def test_resolution_morts_nuit_loup_seul(self):
        """Teste si la victime des loups meurt s'il n'y a pas d'intervention."""
        victime = self.p_villageois
        self.assertTrue(victime.est_vivant)
        self.game._resoudre_morts_nuit(victime) # Passe P1 comme victime des loups
        self.assertFalse(victime.est_vivant)
        self.assertEqual(len(self.game.morts_de_la_nuit), 1)
        self.assertEqual(self.game.morts_de_la_nuit[0][0], victime)
        self.assertEqual(self.game.morts_de_la_nuit[0][1], "attaqué(e) par les Loups-Garous") # <--- MODIFIÉ

    def test_resolution_morts_nuit_sorciere_sauve(self):
        """Teste si la victime des loups survit si sauvée."""
        victime = self.p_villageois
        victime.est_protege_cette_nuit = True # La sorcière a (prétendument) sauvé
        self.assertTrue(victime.est_vivant)
        self.game._resoudre_morts_nuit(victime)
        self.assertTrue(victime.est_vivant) # Doit être toujours vivant
        self.assertEqual(len(self.game.morts_de_la_nuit), 0) # Aucune mort effective

    def test_resolution_morts_nuit_sorciere_tue(self):
        """Teste si la victime de la sorcière meurt."""
        victime_poison = self.p_voyante # La sorcière empoisonne la voyante P3
        victime_poison.vient_de_mourir_par_poison = True
        self.assertTrue(victime_poison.est_vivant)
        # Pas de victime des loups dans ce scénario simple
        self.game._resoudre_morts_nuit(None)
        self.assertFalse(victime_poison.est_vivant)
        self.assertEqual(len(self.game.morts_de_la_nuit), 1)
        self.assertEqual(self.game.morts_de_la_nuit[0][0], victime_poison)
        self.assertEqual(self.game.morts_de_la_nuit[0][1], "empoisonné(e) par la Sorcière") 

    def test_verifier_fin_partie_victoire_villageois(self):
        """Teste la condition de victoire des villageois."""
        self.p_loup.est_vivant = False # Tue le seul loup
        self.assertTrue(self.game.verifier_fin_partie())
        self.assertEqual(self.game.phase, "Terminee")

    def test_verifier_fin_partie_victoire_loups_elimination(self):
        """Teste la victoire des loups quand il n'y a plus d'autres joueurs."""
        self.p_villageois.est_vivant = False
        self.p_voyante.est_vivant = False
        self.p_sorciere.est_vivant = False
        # Seul le loup P2 reste
        self.assertTrue(self.game.verifier_fin_partie())
        self.assertEqual(self.game.phase, "Terminee")

    def test_verifier_fin_partie_victoire_loups_majorite(self):
        """Teste la victoire des loups quand ils sont majoritaires."""
        self.p_villageois.est_vivant = False # Tue un villageois
        # Reste : Loup, Voyante, Sorcière (1 loup vs 2 non-loups) -> Partie continue
        self.assertFalse(self.game.verifier_fin_partie())
        self.p_voyante.est_vivant = False # Tue la voyante
        # Reste : Loup, Sorcière (1 loup vs 1 non-loup) -> Victoire Loup
        self.assertTrue(self.game.verifier_fin_partie())
        self.assertEqual(self.game.phase, "Terminee")


    # --- Point d'intégration : Ajouter plus de tests ---
    # - Test _resoudre_vote (cas simple, égalité, aucun vote)
    # - Test traitement message NLP + validation (plus avancé avec mock NLP ou capture log)
    # - Tests pour les cas limites (nombre min de joueurs)
    # - Tests pour d'éventuels nouveaux rôles (Chasseur...)


if __name__ == '__main__':
    unittest.main(verbosity=2) # verbosity=2 pour plus de détails sur les tests exécutés