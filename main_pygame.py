import pygame
import sys
import os
import random
import time
import math

# Importer la logique du jeu depuis les autres fichiers
from game import Game
from player import Player
from roles import get_available_roles, ROLES_LIST # Importer ROLES_LIST si get_roles... l'utilise
from ai import create_ai_logic

# --- Constantes ---
LARGEUR_ECRAN, HAUTEUR_ECRAN = 1000, 750
FPS = 60
MIN_PLAYERS = 3 # Minimum de joueurs pour démarrer une partie
MAX_PLAYERS = 18 # Maximum arbitraire

# Couleurs (RVB)
BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
ROUGE = (180, 0, 0)
ROUGE_ERREUR = (255, 50, 50)
GRIS_FONCE = (30, 30, 30)
GRIS_MOYEN = (60, 60, 60)
GRIS_CLAIR = (100, 100, 100)
GRIS_TRES_CLAIR = (150, 150, 150)
JAUNE_LUNE = (240, 230, 140) # Prompt
BLEU_NUIT = (25, 25, 112)
VERT_POTION = (0, 150, 0)
VERT_POTION_SURVOL = (0, 200, 0)
ROUGE_POTION = (180, 0, 0)
ROUGE_POTION_SURVOL = (220, 0, 0)
ORANGE_ACTION = (255, 165, 0) # Action log
CYAN_IMPORTANT = (0, 200, 200) # Important log
JAUNE_PASSER = (150, 150, 0)
JAUNE_PASSER_SURVOL = (180, 180, 0)
VERT_CONFIRMER = (0, 120, 0)
VERT_CONFIRMER_SURVOL = (0, 160, 0)
COULEUR_BORDURE_BOUTON = (200, 200, 200)

# Log Message Types & Colors
LOG_COLORS = {
    "info": BLANC,
    "prompt": JAUNE_LUNE,
    "action": ORANGE_ACTION,
    "important": CYAN_IMPORTANT,
    "error": ROUGE_ERREUR,
}
DEFAULT_LOG_COLOR = BLANC

# États du jeu (pour gérer le flux)
ETAT_CONFIG = "CONFIGURATION"
ETAT_NUIT_SEQUENCE = "NUIT_SEQUENCE"
ETAT_NUIT_ATTENTE_HUMAIN = "NUIT_ATTENTE_HUMAIN"
ETAT_NUIT_RESOLUTION = "NUIT_RESOLUTION"
ETAT_CHASSEUR_SEQUENCE = "CHASSEUR_SEQUENCE"
ETAT_CHASSEUR_ATTENTE_HUMAIN = "CHASSEUR_ATTENTE_HUMAIN"
ETAT_JOUR_DEBAT = "JOUR_DEBAT"
ETAT_JOUR_VOTE_SEQUENCE = "JOUR_VOTE_SEQUENCE"
ETAT_JOUR_VOTE_ATTENTE_HUMAIN = "JOUR_VOTE_ATTENTE_HUMAIN"
ETAT_JOUR_VOTE_RESOLUTION = "JOUR_VOTE_RESOLUTION"
ETAT_FIN_PARTIE = "FIN_PARTIE"


# --- Fonctions Utilitaires ---

def charger_image(nom_fichier, utiliser_alpha=False):
    """Charge une image depuis le dossier 'images'."""
    chemin_complet = os.path.join("images", nom_fichier)
    try:
        image = pygame.image.load(chemin_complet)
        if utiliser_alpha:
            image = image.convert_alpha() # Pour la transparence
        else:
            image = image.convert()
        return image
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image '{chemin_complet}': {e}")
        # Retourner une surface vide ou placeholder si l'image manque
        surface_vide = pygame.Surface((50, 50), pygame.SRCALPHA) # SRCALPHA pour transparence placeholder
        pygame.draw.rect(surface_vide, ROUGE_ERREUR, surface_vide.get_rect(), 2) # Dessine un carré rouge
        # Utiliser une police par défaut chargée après l'init de pygame.font
        if pygame.font.get_init():
            police_erreur = pygame.font.Font(None, 30)
            dessiner_texte(surface_vide, "?", police_erreur, ROUGE_ERREUR, surface_vide.get_rect())
        return surface_vide

def charger_police(nom_fichier, taille):
    """Charge une police depuis le dossier 'fonts' ou une police système."""
    if nom_fichier:
        chemin_complet = os.path.join("fonts", nom_fichier)
        try:
            return pygame.font.Font(chemin_complet, taille)
        except pygame.error as e:
            print(f"Erreur lors du chargement de la police '{chemin_complet}', utilisation de la police par défaut: {e}")
    # Si fichier non spécifié ou erreur, utiliser police par défaut
    # S'assurer que pygame.font est initialisé avant d'appeler Font(None,...)
    if not pygame.font.get_init():
        pygame.font.init() # Initialiser si ce n'est pas déjà fait
    return pygame.font.Font(None, taille) # Police système par défaut

# Fonction Helper pour dessiner du texte avec retour à la ligne
def render_text_wrapped(surface, texte, police, couleur, rect_zone, alignement_h="center", alignement_v="top", anti_alias=True, couleur_fond=None):
    """
    Dessine du texte multiligne dans un rectangle donné avec retour à la ligne automatique.
    Args:
        surface: La surface Pygame sur laquelle dessiner.
        texte: La chaîne de caractères à afficher.
        police: L'objet pygame.font.Font à utiliser.
        couleur: La couleur du texte (tuple RVB).
        rect_zone: Le pygame.Rect délimitant la zone de texte.
        alignement_h: 'left', 'center', 'right' (horizontal).
        alignement_v: 'top', 'center', 'bottom' (vertical).
        anti_alias: Booléen pour l'anti-aliasing.
        couleur_fond: Couleur de fond optionnelle pour le texte.
    Returns:
        La liste des rectangles occupés par chaque ligne de texte.
    """
    lignes_finales = []
    mots = texte.split(' ')
    ligne_actuelle = ""
    largeur_max = rect_zone.width

    # Découper le texte en lignes qui tiennent dans la largeur max
    for mot in mots:
        # Teste si l'ajout du mot dépasse la largeur
        largeur_test, _ = police.size(ligne_actuelle + mot + " ")
        if ligne_actuelle == "" or largeur_test <= largeur_max:
            ligne_actuelle += mot + " "
        else:
            lignes_finales.append(ligne_actuelle.strip())
            ligne_actuelle = mot + " "
    lignes_finales.append(ligne_actuelle.strip()) # Ajouter la dernière ligne

    # Rendre et positionner chaque ligne
    surfaces_lignes = [police.render(ligne, anti_alias, couleur, couleur_fond) for ligne in lignes_finales]
    rects_lignes = [s.get_rect() for s in surfaces_lignes]

    hauteur_totale = sum(r.height for r in rects_lignes)
    line_spacing = police.get_linesize() - police.get_height() # Espace standard entre lignes
    hauteur_totale += max(0, len(rects_lignes) - 1) * line_spacing

    # Calculer la position Y de départ basée sur l'alignement vertical
    start_y = rect_zone.top
    if alignement_v == "center":
        start_y = rect_zone.centery - hauteur_totale // 2
    elif alignement_v == "bottom":
        start_y = rect_zone.bottom - hauteur_totale

    current_y = start_y
    drawn_rects = []

    # Dessiner chaque ligne en l'alignant horizontalement
    for i, s_ligne in enumerate(surfaces_lignes):
        r_ligne = rects_lignes[i]
        if alignement_h == "center":
            r_ligne.centerx = rect_zone.centerx
        elif alignement_h == "right":
            r_ligne.right = rect_zone.right
        else: # left par défaut
            r_ligne.left = rect_zone.left

        r_ligne.top = current_y
        surface.blit(s_ligne, r_ligne)
        drawn_rects.append(r_ligne)
        current_y += r_ligne.height + line_spacing

    return drawn_rects


def dessiner_texte(surface, texte, police, couleur, rect_ou_pos, alignement="center", anti_alias=True, couleur_fond=None):
    """Dessine du texte SIMPLE (une seule ligne) sur une surface."""
    # Pour le texte multiligne, utiliser render_text_wrapped
    try:
        texte_surface = police.render(texte, anti_alias, couleur, couleur_fond)
        texte_rect = texte_surface.get_rect()
        if isinstance(rect_ou_pos, pygame.Rect):
            # Alignement dans un Rect
            if alignement == "center": texte_rect.center = rect_ou_pos.center
            elif alignement == "topleft": texte_rect.topleft = rect_ou_pos.topleft
            elif alignement == "midtop": texte_rect.midtop = rect_ou_pos.midtop
            elif alignement == "midleft": texte_rect.midleft = rect_ou_pos.midleft
            elif alignement == "midright": texte_rect.midright = rect_ou_pos.midright
            elif alignement == "midbottom": texte_rect.midbottom = rect_ou_pos.midbottom
            elif alignement == "bottomleft": texte_rect.bottomleft = rect_ou_pos.bottomleft
            elif alignement == "bottomright": texte_rect.bottomright = rect_ou_pos.bottomright
            else: texte_rect.center = rect_ou_pos.center # Par défaut center
        else: # Position absolue (tuple/list)
             if alignement == "center": texte_rect.center = rect_ou_pos
             elif alignement == "topleft": texte_rect.topleft = rect_ou_pos
             elif alignement == "midtop": texte_rect.midtop = rect_ou_pos
             elif alignement == "midleft": texte_rect.midleft = rect_ou_pos
             elif alignement == "midright": texte_rect.midright = rect_ou_pos
             elif alignement == "midbottom": texte_rect.midbottom = rect_ou_pos
             elif alignement == "bottomleft": texte_rect.bottomleft = rect_ou_pos
             elif alignement == "bottomright": texte_rect.bottomright = rect_ou_pos
             else: texte_rect.center = rect_ou_pos # Par défaut center

        surface.blit(texte_surface, texte_rect)
        return texte_rect
    except Exception as e:
        print(f"Erreur lors du dessin du texte '{texte}': {e}")
        return pygame.Rect(0,0,0,0)

# --- Classes UI ---

class Bouton:
    """Classe améliorée pour créer des boutons cliquables avec états visuels."""
    def __init__(self, x, y, largeur, hauteur, texte='',
                 couleur_fond=GRIS_CLAIR, couleur_survol=GRIS_TRES_CLAIR, couleur_presse=GRIS_MOYEN, couleur_desactive=GRIS_FONCE,
                 couleur_texte=BLANC, police=None, border_radius=5, border_width=1, border_color=COULEUR_BORDURE_BOUTON,
                 image=None, image_survol=None, image_desactive=None, callback=None):
        self.rect = pygame.Rect(x, y, largeur, hauteur)
        self.texte = texte
        self.couleur_fond = couleur_fond
        self.couleur_survol = couleur_survol
        self.couleur_presse = couleur_presse
        self.couleur_desactive = couleur_desactive
        self.couleur_texte = couleur_texte
        self.police = police if police else charger_police(None, 20)
        self.border_radius = border_radius
        self.border_width = border_width
        self.border_color = border_color
        self.image = image # Priorité sur couleur si fourni
        self.image_survol = image_survol if image_survol else image
        self.image_desactive = image_desactive if image_desactive else image
        self.callback = callback
        self.survol = False
        self.is_pressed = False # Nouvel état pour le clic
        self.actif = True

    def dessiner(self, surface):
        current_image = self.image
        current_color = self.couleur_fond
        text_color = self.couleur_texte
        text_offset = (0, 0)
        current_border_color = self.border_color

        if not self.actif:
            current_image = self.image_desactive
            current_color = self.couleur_desactive
            text_color = tuple(c // 2 for c in self.couleur_texte) # Texte grisé
            current_border_color = tuple(c // 2 for c in self.border_color) # Bordure grisée
        elif self.is_pressed:
            current_image = self.image_survol # Ou une image pressée dédiée si fournie
            current_color = self.couleur_presse
            text_offset = (1, 1) # Légèrement décalé pour effet enfoncé
        elif self.survol:
            current_image = self.image_survol
            current_color = self.couleur_survol
            current_border_color = BLANC # Bordure blanche au survol
        # else: Utilise les couleurs/images par défaut

        if current_image:
            try:
                image_resized = pygame.transform.scale(current_image, (self.rect.width, self.rect.height))
                surface.blit(image_resized, self.rect.topleft)
            except Exception as e:
                print(f"Erreur dessin image bouton '{self.texte}': {e}")
                pygame.draw.rect(surface, current_color, self.rect, border_radius=self.border_radius) # Fallback couleur
        else:
            # Dessiner rectangle avec couleur d'état
            pygame.draw.rect(surface, current_color, self.rect, border_radius=self.border_radius)
            # Dessiner la bordure
            if self.border_width > 0:
                 pygame.draw.rect(surface, current_border_color, self.rect, width=self.border_width, border_radius=self.border_radius)


        if self.texte:
            # Positionner le texte au centre du bouton, avec offset si pressé
            text_rect = pygame.Rect(self.rect)
            text_rect.centerx += text_offset[0]
            text_rect.centery += text_offset[1]
            dessiner_texte(surface, self.texte, self.police, text_color, text_rect)

    def gerer_evenement(self, event):
        """Gère les événements souris pour le bouton."""
        if not self.actif:
            self.survol = False
            self.is_pressed = False
            return None

        pos_souris = pygame.mouse.get_pos()
        self.survol = self.rect.collidepoint(pos_souris)
        callback_result = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.survol:
            self.is_pressed = True
            print(f"DEBUG: Bouton '{self.texte}' pressé.")
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                if self.survol: # S'assurer que la souris est toujours sur le bouton au relâchement
                    print(f"DEBUG: Bouton '{self.texte}' relâché (clic!).")
                    if self.callback:
                        callback_result = self.callback() # Appeler le callback au relâchement
                else:
                     print(f"DEBUG: Bouton '{self.texte}' relâché hors du bouton.")
                self.is_pressed = False # Réinitialiser l'état pressé dans tous les cas

        # Gérer le cas où le bouton est pressé et la souris sort
        if self.is_pressed and not self.survol:
             self.is_pressed = False # Annuler l'état pressé si la souris sort

        return callback_result # Retourne le résultat du callback (ou None)


class CarteJoueur:
    """Représente visuellement une carte de joueur."""
    TAILLE_CARTE = (100, 140); ESPACEMENT = 15 # Espacement non utilisé dans la disposition en arc

    def __init__(self, joueur, x, y, police_nom, police_statut, image_texture=None, icones_roles=None, icone_mort=None):
        self.joueur = joueur; self.rect = pygame.Rect(x, y, self.TAILLE_CARTE[0], self.TAILLE_CARTE[1])
        self.police_nom = police_nom; self.police_statut = police_statut
        self.image_texture = image_texture # Texture pour la carte (si fournie)
        self.icones_roles = icones_roles if icones_roles else {}; self.icone_mort = icone_mort
        self.survol = False; self.selectionne = False; self.peut_etre_cible = False; self.afficher_role = False

    def dessiner(self, surface):
        # --- Dessiner le fond/texture ---
        current_card_color = GRIS_FONCE # Couleur par défaut si pas de texture
        if self.image_texture:
            try:
                texture_scaled = pygame.transform.scale(self.image_texture, self.TAILLE_CARTE)
                surface.blit(texture_scaled, self.rect.topleft)
            except Exception as e:
                print(f"Erreur affichage texture carte: {e}")
                pygame.draw.rect(surface, current_card_color, self.rect, border_radius=8) # Fallback couleur
        else:
             if not self.joueur.is_alive: current_card_color = tuple(c // 2 for c in GRIS_FONCE)
             pygame.draw.rect(surface, current_card_color, self.rect, border_radius=8)

        # --- Superpositions (sélection, survol, mort) ---
        overlay_alpha = 0
        overlay_color = NOIR

        if not self.joueur.is_alive:
             overlay_alpha = 190 # Encore plus opaque pour les morts
             overlay_color = (10, 10, 10) # Presque noir
        elif self.selectionne:
             overlay_alpha = 70 # Plus visible
             overlay_color = JAUNE_LUNE
        elif self.survol and self.peut_etre_cible:
             overlay_alpha = 50
             overlay_color = GRIS_TRES_CLAIR
        elif self.survol:
             overlay_alpha = 30
             overlay_color = GRIS_CLAIR

        if overlay_alpha > 0:
            overlay = pygame.Surface(self.TAILLE_CARTE, pygame.SRCALPHA)
            overlay.fill((*overlay_color, overlay_alpha))
            surface.blit(overlay, self.rect.topleft)

        # --- Bordures (sélectionnable, sélectionné) ---
        if self.peut_etre_cible:
             pygame.draw.rect(surface, ORANGE_ACTION, self.rect, width=3, border_radius=8)
        elif self.selectionne:
             pygame.draw.rect(surface, BLANC, self.rect, width=3, border_radius=8)

        # --- Contenu (Nom, Icône Rôle, Icône Mort) ---
        nom_rect = self.rect.inflate(-10, -10) # Marge intérieure
        dessiner_texte(surface, self.joueur.name, self.police_nom, BLANC, nom_rect, alignement="midtop")

        role_a_afficher = self.joueur.role.name if self.joueur.role else None
        # Condition simplifiée : afficher le rôle si fin de partie ou si c'est le joueur humain (ET qu'il a un rôle)
        if self.joueur.role and (self.afficher_role or self.joueur.is_human):
             icone = self.icones_roles.get(role_a_afficher)
             if icone:
                 try:
                    icone_size = (40, 40)
                    icone_scaled = pygame.transform.smoothscale(icone, icone_size);
                    icone_rect = icone_scaled.get_rect(centerx=self.rect.centerx, centery=self.rect.centery + 10)
                    surface.blit(icone_scaled, icone_rect)
                 except Exception as e: print(f"Erreur affichage icone role {role_a_afficher}: {e}")

        if not self.joueur.is_alive:
            if self.icone_mort:
                try:
                    icone_mort_size = (50, 50)
                    icone_mort_scaled = pygame.transform.smoothscale(self.icone_mort, icone_mort_size);
                    mort_rect = icone_mort_scaled.get_rect(center=self.rect.center)
                    surface.blit(icone_mort_scaled, mort_rect)
                except Exception as e: print(f"Erreur affichage icone mort: {e}")
            else: # Fallback texte
                statut_rect = pygame.Rect(self.rect.left + 5, self.rect.centery - 10, self.rect.width - 10, 20)
                dessiner_texte(surface, "Mort", self.police_statut, ROUGE, statut_rect, alignement="center")

    def gerer_evenement(self, event):
        pos_souris = pygame.mouse.get_pos(); self.survol = self.rect.collidepoint(pos_souris)
        # Utiliser MOUSEBUTTONUP pour la confirmation du clic sur la carte
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.survol:
             # Retourne le joueur si le *relâchement* du clic est sur la carte
             return self.joueur
        return None

# --- Classe Principale de l'Application Pygame ---

class GameApp:
    def __init__(self):
        try:
            pygame.init(); pygame.mixer.init()
            self.ecran = pygame.display.set_mode((LARGEUR_ECRAN, HAUTEUR_ECRAN))
            pygame.display.set_caption("Loup Garou de Thiercelieux - Édition Pygame")
            self.horloge = pygame.time.Clock()
            self.jeu = None; self.etat_jeu = ETAT_CONFIG; self.en_cours = True

            # Variables pour la configuration de la partie
            self.config_total_joueurs = 5 # Défaut
            self.config_num_humains = 1 # Défaut
            self.config_message_erreur = "" # Pour afficher erreurs de config

            self.charger_assets()
            self.widgets_config = self.creer_widgets_config(); # Créer widgets config d'abord
            self.cartes_joueurs_visuels = []; self.boutons_jeu = {}; self.log_messages_jeu = []
            self.creer_widgets_jeu() # Puis les widgets de jeu

            self.acteur_humain_actuel = None; self.action_humaine_attendue = None; self.cibles_possibles_action = []; self.cible_humaine_selectionnee = None
            self.delai_prochaine_action = 0; self.sequence_nuit_restante = []; self.votants_restants = []; self.votes_en_cours = {}
            self.chasseurs_morts_sequence = []; self.callback_apres_chasseur = None

            # Variables pour gérer les actions humaines spécifiques
            self._human_vote_target = None
            self._human_vote_target_actor_name = None
            self._sorciere_action_type = None # "save" ou "kill" ou None pour la sorciere humaine


        except Exception as e:
             print("\n*** ERREUR INIT ***"); print(f"Erreur: {e}"); print("Vérifiez Pygame, dossiers 'images', 'fonts'."); print("******************\n")
             self.en_cours = False
             try: # Message erreur graphique
                 pygame.font.init(); police_erreur = pygame.font.Font(None, 30); msg1 = police_erreur.render("Erreur fatale initialisation.", True, ROUGE_ERREUR, NOIR); msg2 = police_erreur.render("Verifier console.", True, ROUGE_ERREUR, NOIR)
                 screen_error = pygame.display.set_mode((600, 100)); screen_error.blit(msg1, (10, 10)); screen_error.blit(msg2, (10, 50)); pygame.display.flip()
                 while True:
                      for event in pygame.event.get():
                          if event.type == pygame.QUIT or event.type == pygame.KEYDOWN: pygame.quit(); sys.exit()
             except: pygame.quit(); sys.exit()

    def charger_assets(self):
        """Charge toutes les images et polices nécessaires."""
        print("Chargement des assets...")
        # --- Polices ---
        self.polices = {
            "titre": charger_police("Cinzel-Regular.ttf", 48),
            "normal": charger_police("EBGaramond-Regular.ttf", 20), # Police du log augmentée
            "config_label": charger_police("EBGaramond-Regular.ttf", 24), # Police pour labels config
            "config_value": charger_police("EBGaramond-Bold.ttf", 28), # Police pour valeurs config
            "bouton": charger_police("EBGaramond-Bold.ttf", 20),
            "carte_nom": charger_police("EBGaramond-Regular.ttf", 16),
            "carte_statut": charger_police("EBGaramond-Regular.ttf", 14),
            "error": charger_police("EBGaramond-Bold.ttf", 20), # Police pour messages erreur config
        }
        # --- Images ---
        self.images = {
            "fond_config": charger_image("fond_village.jpg"), "fond_nuit": charger_image("fond_foret_nuit.jpg"), "fond_jour": charger_image("fond_village_jour.jpg"),
            "carte_texture": charger_image("carte_texture.png", utiliser_alpha=True), # Placeholder for card texture
            "icone_loup": charger_image("icone_loup.png", utiliser_alpha=True), "icone_villageois": charger_image("icone_villageois.png", utiliser_alpha=True),
            "icone_voyante": charger_image("icone_voyante.png", utiliser_alpha=True), "icone_sorciere": charger_image("icone_sorciere.png", utiliser_alpha=True),
            "icone_chasseur": charger_image("icone_chasseur.png", utiliser_alpha=True), "icone_mort": charger_image("icone_crane.png", utiliser_alpha=True),
            "soleil": charger_image("icone_soleil.png", utiliser_alpha=True), "lune": charger_image("icone_lune.png", utiliser_alpha=True),
        }
        # Utiliser None si carte_texture n'a pas été chargée (pour fallback couleur dans CarteJoueur)
        if not isinstance(self.images["carte_texture"], pygame.Surface) or self.images["carte_texture"].get_width() <= 50: # Vérifie si c'est le placeholder
             print("WARN: Image 'carte_texture.png' non trouvée ou invalide. Utilisation d'un fond uni pour les cartes.")
             self.images["carte_texture"] = None

        self.icones_roles_map = {
            "Loup-Garou": self.images.get("icone_loup"), "Villageois": self.images.get("icone_villageois"), "Voyante": self.images.get("icone_voyante"),
            "Sorcière": self.images.get("icone_sorciere"), "Chasseur": self.images.get("icone_chasseur"),
        }
        try: # Redimensionner fonds
            self.images["fond_config"] = pygame.transform.scale(self.images["fond_config"], (LARGEUR_ECRAN, HAUTEUR_ECRAN))
            self.images["fond_nuit"] = pygame.transform.scale(self.images["fond_nuit"], (LARGEUR_ECRAN, HAUTEUR_ECRAN))
            self.images["fond_jour"] = pygame.transform.scale(self.images["fond_jour"], (LARGEUR_ECRAN, HAUTEUR_ECRAN))
        except Exception as e: print(f"Erreur redimensionnement fonds: {e}")
        print("Assets chargés.")

    # --- Configuration UI ---
    def creer_widgets_config(self):
        """Crée les widgets de l'écran de configuration."""
        widgets = {}
        label_font = self.polices["config_label"]
        button_font = self.polices["bouton"]
        btn_small_size = 40 # Taille des boutons +/-
        value_width = 60 # Largeur pour afficher la valeur
        spacing = 10
        start_y = 200
        row_height = 60
        center_x = LARGEUR_ECRAN // 2

        # --- Total Joueurs ---
        y_pos = start_y
        # Label
        widgets["label_total"] = {"text": "Nombre Total de Joueurs:", "pos": (center_x - 150, y_pos), "align": "midright", "font": label_font}
        # Bouton Moins
        widgets["btn_total_moins"] = Bouton(center_x - value_width // 2 - spacing - btn_small_size, y_pos - btn_small_size // 2, btn_small_size, btn_small_size, "-", police=button_font, callback=self.decrement_total)
        # Affichage Valeur (Rect pour position)
        widgets["value_total_rect"] = pygame.Rect(center_x - value_width // 2, y_pos - btn_small_size // 2, value_width, btn_small_size)
        # Bouton Plus
        widgets["btn_total_plus"] = Bouton(center_x + value_width // 2 + spacing, y_pos - btn_small_size // 2, btn_small_size, btn_small_size, "+", police=button_font, callback=self.increment_total)

        # --- Joueurs Humains ---
        y_pos += row_height
        # Label
        widgets["label_humains"] = {"text": "Nombre de Joueurs Humains:", "pos": (center_x - 150, y_pos), "align": "midright", "font": label_font}
        # Bouton Moins
        widgets["btn_humains_moins"] = Bouton(center_x - value_width // 2 - spacing - btn_small_size, y_pos - btn_small_size // 2, btn_small_size, btn_small_size, "-", police=button_font, callback=self.decrement_humains)
        # Affichage Valeur (Rect pour position)
        widgets["value_humains_rect"] = pygame.Rect(center_x - value_width // 2, y_pos - btn_small_size // 2, value_width, btn_small_size)
        # Bouton Plus
        widgets["btn_humains_plus"] = Bouton(center_x + value_width // 2 + spacing, y_pos - btn_small_size // 2, btn_small_size, btn_small_size, "+", police=button_font, callback=self.increment_humains)

        # --- Bouton Démarrer ---
        y_pos += row_height + 20
        widgets["bouton_demarrer"] = Bouton(center_x - 150, y_pos, 300, 50, texte="Valider et Démarrer", couleur_fond=(50, 100, 50), couleur_survol=(70, 140, 70), couleur_presse=(40, 80, 40), police=button_font, callback=self.demarrer_partie)
        widgets["bouton_demarrer"].actif = False # Inactif par défaut, activé par validation

        # --- Zone Message Erreur ---
        widgets["error_rect"] = pygame.Rect(center_x - 250, y_pos + row_height, 500, 40)

        return widgets

    # --- Callbacks et Validation Configuration ---
    def increment_total(self):
        if self.config_total_joueurs < MAX_PLAYERS:
            self.config_total_joueurs += 1
        self.validate_config()

    def decrement_total(self):
        # Ne pas descendre en dessous du nombre d'humains actuels ou MIN_PLAYERS
        min_allowed = max(MIN_PLAYERS, self.config_num_humains)
        if self.config_total_joueurs > min_allowed:
            self.config_total_joueurs -= 1
        self.validate_config()

    def increment_humains(self):
        # Ne pas dépasser le nombre total de joueurs
        if self.config_num_humains < self.config_total_joueurs:
            self.config_num_humains += 1
        self.validate_config()

    def decrement_humains(self):
        if self.config_num_humains > 0:
            self.config_num_humains -= 1
            # S'assurer que total >= MIN_PLAYERS même si humains baisse
            if self.config_total_joueurs < MIN_PLAYERS:
                 # Option : remonter aussi le total si besoin ? Non, laissons l'utilisateur ajuster.
                 pass # On ne remonte pas le total automatiquement
        self.validate_config()


    def is_config_valid(self):
        """Vérifie si la configuration actuelle est valide."""
        total = self.config_total_joueurs
        humains = self.config_num_humains
        if total < MIN_PLAYERS:
            self.config_message_erreur = f"Il faut au moins {MIN_PLAYERS} joueurs."
            return False
        if total > MAX_PLAYERS:
            self.config_message_erreur = f"Maximum {MAX_PLAYERS} joueurs."
            return False
        if humains < 0: # Devrait pas arriver avec les boutons
            self.config_message_erreur = "Nombre d'humains invalide."
            return False
        if humains > total:
            self.config_message_erreur = "Trop de joueurs humains."
            return False
        # Vérifier si une config de rôles existe pour ce nombre
        if get_roles_for_player_count(total) is None:
             self.config_message_erreur = f"Configuration de rôles non définie pour {total} joueurs."
             return False

        self.config_message_erreur = "" # Pas d'erreur
        return True

    def validate_config(self):
        """Met à jour l'état du bouton démarrer basé sur la validation."""
        is_valid = self.is_config_valid()
        # Assurer que le widget existe avant de modifier son état
        if "bouton_demarrer" in self.widgets_config:
            self.widgets_config["bouton_demarrer"].actif = is_valid


    # --- Reste des méthodes GameApp ---
    def creer_widgets_jeu(self):
        # Zone de log (position inchangée pour l'instant)
        self.rect_zone_messages = pygame.Rect(50, HAUTEUR_ECRAN - 170, LARGEUR_ECRAN - 100, 150)

        # --- Boutons d'Action repositionnés au-dessus de la zone de log ---
        btn_w, btn_h = 160, 40 # Légèrement moins larges
        spacing = 10
        # Calculer la largeur nécessaire dynamiquement en fonction des boutons *potentiellement* visibles
        # Max 4 boutons: Confirmer, Passer, Potion Vie, Potion Mort
        total_width_max_buttons = 4 * btn_w + 3 * spacing
        start_x_buttons = (LARGEUR_ECRAN - total_width_max_buttons) // 2
        button_y = self.rect_zone_messages.top - btn_h - 15 # Y position above log area, with margin

        # Boutons communs
        self.boutons_jeu["confirmer"] = Bouton(start_x_buttons, button_y, btn_w, btn_h, texte="Confirmer Action", police=self.polices["bouton"], callback=self.confirmer_action_humaine, couleur_fond=VERT_CONFIRMER, couleur_survol=VERT_CONFIRMER_SURVOL, couleur_presse=(0, 80, 0))
        self.boutons_jeu["passer"] = Bouton(start_x_buttons + btn_w + spacing, button_y, btn_w, btn_h, texte="Passer l'Action", police=self.polices["bouton"], callback=self.passer_action_humaine, couleur_fond=JAUNE_PASSER, couleur_survol=JAUNE_PASSER_SURVOL, couleur_presse=(120, 120, 0))

        # Boutons Sorcière (mêmes positions relatives, activés/désactivés par la logique)
        self.boutons_jeu["sorciere_save"] = Bouton(start_x_buttons + 2 * (btn_w + spacing), button_y, btn_w, btn_h, texte="Potion de Vie", police=self.polices["bouton"], callback=lambda: self.preparer_action_sorciere("save"), couleur_fond=VERT_POTION, couleur_survol=VERT_POTION_SURVOL, couleur_presse=(0, 100, 0))
        self.boutons_jeu["sorciere_kill"] = Bouton(start_x_buttons + 3 * (btn_w + spacing), button_y, btn_w, btn_h, texte="Potion de Mort", police=self.polices["bouton"], callback=lambda: self.preparer_action_sorciere("kill"), couleur_fond=ROUGE_POTION, couleur_survol=ROUGE_POTION_SURVOL, couleur_presse=(120, 0, 0))

        # Autres boutons (position inchangée pour l'instant)
        self.boutons_jeu["passer_au_vote"] = Bouton(LARGEUR_ECRAN // 2 - 100, 20, 200, 40, texte="Passer au Vote", police=self.polices["bouton"], callback=self.lancer_phase_vote, couleur_fond=(0,0,100), couleur_survol=(0,0,150), couleur_presse=(0,0,70))
        # Boutons de fin de partie positionnés en bas au centre
        btn_fin_w = 200
        btn_fin_h = 50
        btn_fin_y = HAUTEUR_ECRAN - btn_fin_h - 20
        btn_fin_spacing = 20
        self.boutons_jeu["nouvelle_partie"] = Bouton(LARGEUR_ECRAN // 2 - btn_fin_w - btn_fin_spacing // 2, btn_fin_y, btn_fin_w, btn_fin_h, texte="Nouvelle Partie", police=self.polices["bouton"], callback=self.reinitialiser_jeu, couleur_fond=(50,50,100), couleur_survol=(70,70,140), couleur_presse=(30,30,70))
        self.boutons_jeu["quitter"] = Bouton(LARGEUR_ECRAN // 2 + btn_fin_spacing // 2, btn_fin_y, btn_fin_w, btn_fin_h, texte="Quitter", police=self.polices["bouton"], callback=self.quitter_jeu, couleur_fond=(100,50,50), couleur_survol=(140,70,70), couleur_presse=(70,30,30))

        # Désactiver tous les boutons de jeu par défaut
        for btn in self.boutons_jeu.values(): btn.actif = False

    # Fonction de démarrage modifiée
    def demarrer_partie(self):
        """Démarre la partie avec la configuration choisie."""
        if not self.is_config_valid():
            print("ERREUR: Tentative de démarrage avec config invalide.")
            return # Ne pas démarrer si la config n'est pas valide

        total_joueurs = self.config_total_joueurs
        num_humains = self.config_num_humains
        num_ia = total_joueurs - num_humains

        # Obtenir la configuration des rôles pour ce nombre de joueurs
        roles_config = get_roles_for_player_count(total_joueurs)
        if roles_config is None:
             self.log_message_jeu(f"Configuration de rôles non gérée pour {total_joueurs} joueurs.", msg_type="error")
             self.config_message_erreur = f"Configuration de rôles non gérée pour {total_joueurs} joueurs."
             self.etat_jeu = ETAT_CONFIG # Rester sur l'écran de config
             return

        try:
            self.log_message_jeu(f"Démarrage partie : {total_joueurs} Joueurs ({num_humains} Humains, {num_ia} IA)", msg_type="info")
            self.log_message_jeu(f"Configuration Rôles: {roles_config}", msg_type="info")
            print(f"DEBUG: Config Roles: {roles_config}")

            self.jeu = Game(); human_names = []

            # Créer les joueurs humains
            for i in range(num_humains):
                 name = f"Joueur {i+1}"; human_names.append(name);
                 self.jeu.add_player(Player(name, is_human=True))

            # Créer les joueurs IA
            ia_index = 1; num_ia_added = 0
            while num_ia_added < num_ia:
                 name = f"IA_{ia_index}";
                 if not self.jeu.get_player_by_name(name):
                      self.jeu.add_player(Player(name, is_human=False))
                      num_ia_added += 1
                 ia_index += 1
                 if ia_index > total_joueurs * 5: raise Exception("Boucle infinie nom IA");

            print(f"DEBUG: Ajouté {num_ia_added} IA.")
            if len(self.jeu.players) != total_joueurs: raise Exception(f"Incohérence joueurs créés {len(self.jeu.players)} != total {total_joueurs}")

            # Assigner les rôles
            if self.jeu.assign_roles(roles_config):
                # Initialiser les potions pour les Sorcières *APRES* l'assignation des rôles
                for player in self.jeu.players:
                     if player.role and player.role.name == "Sorcière":
                          player.has_saved_potion = True # Assumer 1 potion de vie
                          player.has_kill_potion = True  # Assumer 1 potion de mort
                    # Créer la logique IA pour les joueurs IA
                     if not player.is_human:
                          player.ai_logic = create_ai_logic(player, self.jeu)

                self.log_message_jeu("Partie commence !", msg_type="info");
                if human_names: self.log_message_jeu(f"Humains: {', '.join(human_names)}", msg_type="info");
                self.log_message_jeu("Distribution rôles...", msg_type="info")
                for player in self.jeu.players:
                     if player.is_human: self.log_message_jeu(f"IMPORTANT: Vous êtes {player.name}, votre rôle est : {player.role.name}", msg_type="important")

                self.organiser_cartes_joueurs();
                self.etat_jeu = ETAT_NUIT_SEQUENCE;
                self.lancer_phase_nuit()

            else:
                 self.log_message_jeu("Erreur assignation rôles.", msg_type="error");
                 self.etat_jeu = ETAT_CONFIG # Rester sur l'écran de config si erreur

        except Exception as e:
             self.log_message_jeu(f"Erreur démarrage partie: {e}", msg_type="error");
             print(f"ERREUR démarrage partie: {e}");
             self.etat_jeu = ETAT_CONFIG # Rester sur l'écran de config si erreur grave


    def organiser_cartes_joueurs(self):
        self.cartes_joueurs_visuels = [];
        if not self.jeu or not self.jeu.players: return; # S'assurer qu'il y a des joueurs

        all_players = self.jeu.players
        nb_joueurs_total = len(all_players)
        if nb_joueurs_total == 0: return

        # Paramètres de l'arc ajustés
        arc_center_x = LARGEUR_ECRAN // 2
        arc_center_y = HAUTEUR_ECRAN + 80 # Remonté légèrement (moins négatif)
        arc_radius = HAUTEUR_ECRAN * 0.75 # Rayon légèrement réduit pour un arc plus serré
        angle_start_deg = 195 # Angle de départ un peu plus large
        angle_end_deg = 345   # Angle de fin un peu plus large
        total_angle_deg = angle_end_deg - angle_start_deg

        # Calculer l'espacement angulaire
        if nb_joueurs_total == 1:
             angle_step_deg = 0
             current_angle_deg = angle_start_deg + total_angle_deg / 2
        else:
             # Répartir les joueurs sur l'angle total
             angle_step_deg = total_angle_deg / (nb_joueurs_total - 1)
             current_angle_deg = angle_start_deg

        for i, joueur in enumerate(all_players):
            # Calculer la position sur l'arc
            angle_rad = math.radians(current_angle_deg)
            x_pos = arc_center_x + arc_radius * math.cos(angle_rad)
            y_pos = arc_center_y + arc_radius * math.sin(angle_rad) # Utiliser + pour sin car Y augmente vers le bas

            # Centrer la carte sur le point (x_pos, y_pos)
            card_x = x_pos - CarteJoueur.TAILLE_CARTE[0] // 2
            card_y = y_pos - CarteJoueur.TAILLE_CARTE[1] // 2

            # Créer et ajouter la carte visuelle
            carte = CarteJoueur(joueur, card_x, card_y,
                                self.polices["carte_nom"], self.polices["carte_statut"],
                                self.images.get("carte_texture"), # Passer la texture (peut être None)
                                self.icones_roles_map, self.images.get("icone_mort"));
            self.cartes_joueurs_visuels.append(carte)

            # Passer à l'angle suivant
            current_angle_deg += angle_step_deg


    def log_message_jeu(self, message, msg_type="info"):
        """Ajoute un message au log avec un type pour la couleur."""
        print(f"LOG ({msg_type}): {message}");
        self.log_messages_jeu.append((message, msg_type)) # Stocker tuple (message, type)
        max_log_lines = 6; # Réduit car police plus grande
        if len(self.log_messages_jeu) > max_log_lines: self.log_messages_jeu = self.log_messages_jeu[-max_log_lines:]

    def quitter_jeu(self): self.en_cours = False

    def run(self):
        # Vérifier la configuration initiale au démarrage
        self.validate_config()
        while self.en_cours:
            temps_actuel = pygame.time.get_ticks()
            self.gerer_evenements()
            if self.jeu and self.etat_jeu != ETAT_CONFIG: # Mettre à jour logique seulement si jeu lancé
                self.mettre_a_jour_logique(temps_actuel)
            self.dessiner_ecran()
            self.horloge.tick(FPS)
        print("Arrêt Pygame."); pygame.quit(); sys.exit()

    def gerer_evenements(self):
        # Ne réinitialise pas la cible ici si on est en attente d'action humaine
        if self.etat_jeu not in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN]:
             self.cible_humaine_selectionnee = None # Réinitialise si on n'attend pas d'input
             for c in self.cartes_joueurs_visuels: c.selectionne = False # Désélectionne visuellement

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: self.en_cours = False

            # --- Gestion des événements pour les boutons ---
            boutons_a_verifier = [] # Liste des boutons qui doivent écouter les événements CETTE FRAME
            if self.etat_jeu == ETAT_CONFIG:
                 # Widgets de configuration
                 boutons_a_verifier = [widget for widget in self.widgets_config.values() if isinstance(widget, Bouton)]
            elif self.etat_jeu == ETAT_FIN_PARTIE:
                 # ***** CORRECTION ICI *****
                 # Ajouter les boutons de fin de partie à la liste des boutons à vérifier
                 boutons_a_verifier = [self.boutons_jeu["nouvelle_partie"], self.boutons_jeu["quitter"]]
                 # ***** FIN CORRECTION *****
            elif self.etat_jeu == ETAT_JOUR_DEBAT:
                 # Bouton pour passer au vote
                 boutons_a_verifier = [self.boutons_jeu["passer_au_vote"]]
            elif self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN]:
                  # Boutons d'action pendant l'attente humaine
                  boutons_a_verifier.extend([self.boutons_jeu["confirmer"], self.boutons_jeu["passer"]])
                  if self.action_humaine_attendue == "Sorcière":
                      boutons_a_verifier.extend([self.boutons_jeu["sorciere_save"], self.boutons_jeu["sorciere_kill"]])

            # Passer l'événement à chaque bouton DANS LA LISTE à vérifier
            # Cela assure que seuls les boutons pertinents pour l'état actuel reçoivent l'événement
            for btn in boutons_a_verifier:
                 # Le bouton gère lui-même s'il est actif et réagit à l'événement
                 callback_result = btn.gerer_evenement(event)
                 # ... (le reste du code pour potentiellement utiliser callback_result reste inchangé)


            # --- Gestion du clic sur les cartes joueurs ---
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1: # Utiliser MOUSEBUTTONUP pour sélection finale
                 # Seulement si on est dans un état où l'humain doit choisir une cible ET qu'il y a un acteur humain en attente
                 if self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN] and self.acteur_humain_actuel:
                    # Vérifier si le clic n'était pas sur un bouton (pour éviter de sélectionner une carte derrière un bouton)
                    # Check mouse position against ALL potentially active buttons at the moment of click release
                    pos_souris_up = event.pos
                    # Vérifier tous les boutons visibles/actifs, pas seulement ceux de 'boutons_a_verifier'
                    active_buttons_now = [b for b_name, b in self.boutons_jeu.items() if b.actif]
                    if not any(btn.rect.collidepoint(pos_souris_up) for btn in active_buttons_now): # Correction ici aussi pour vérifier tous les boutons actifs
                        clicked_on_card = False
                        for carte in self.cartes_joueurs_visuels:
                            # Vérifier si le relâchement est sur une carte
                            # carte.gerer_evenement retourne le joueur si le clic UP est dessus
                            joueur_clique = carte.gerer_evenement(event)
                            if joueur_clique:
                                clicked_on_card = True
                                # Vérifie si le joueur cliqué est une cible possible pour l'action en cours
                                if joueur_clique in self.cibles_possibles_action:
                                    # Si on clique à nouveau sur la même cible, on la désélectionne
                                    if self.cible_humaine_selectionnee == joueur_clique:
                                        self.cible_humaine_selectionnee = None # Désélectionne
                                        self.boutons_jeu["confirmer"].actif = False
                                        print(f"DEBUG: Cible {joueur_clique.name} désélectionnée.")
                                    else:
                                        self.cible_humaine_selectionnee = joueur_clique
                                        self.boutons_jeu["confirmer"].actif = True
                                        print(f"DEBUG: Cible {joueur_clique.name} sélectionnée.")
                                        # self.log_message_jeu(f"Cible sélectionnée : {joueur_clique.name}", "info") # Optionnel
                                else:
                                    self.log_message_jeu(f"{joueur_clique.name} n'est pas une cible valide.", "error")
                                    print(f"DEBUG: Clic sur {joueur_clique.name} non ciblable.")
                                    # Ne pas désélectionner une cible valide si on clique sur une invalide
                                # Met à jour la sélection visuelle pour toutes les cartes
                                for c in self.cartes_joueurs_visuels:
                                     c.selectionne = (c.joueur == self.cible_humaine_selectionnee)
                                break # Sortir après avoir traité le clic sur une carte


    def mettre_a_jour_logique(self, temps_actuel):
        if not self.jeu or self.etat_jeu == ETAT_FIN_PARTIE: return # Rien à faire si pas de jeu ou partie finie

        # Vérifier la victoire à chaque étape logique avant de continuer
        # Mettre la vérification APRES l'attente de l'humain pour ne pas couper une action humaine
        # if self.jeu.check_victory_condition():
        #     self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie(); return

        # Ne pas exécuter la logique si le délai n'est pas écoulé ou si on attend une action humaine
        if temps_actuel < self.delai_prochaine_action: return
        if self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN]: return # Attente input humain

        # Exécuter l'étape suivante de la séquence en fonction de l'état
        # Vérifier la victoire *avant* d'exécuter l'action suivante
        if self.jeu.check_victory_condition():
            self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie(); return

        if self.etat_jeu == ETAT_NUIT_SEQUENCE: self.executer_action_nuit_suivante()
        elif self.etat_jeu == ETAT_NUIT_RESOLUTION: self.resoudre_nuit()
        elif self.etat_jeu == ETAT_CHASSEUR_SEQUENCE: self.executer_action_chasseur_suivante()
        elif self.etat_jeu == ETAT_JOUR_VOTE_SEQUENCE: self.traiter_votant_suivant()
        elif self.etat_jeu == ETAT_JOUR_VOTE_RESOLUTION: self.resoudre_vote()
        # ETAT_JOUR_DEBAT n'a pas de logique de mise à jour automatique, il attend le clic sur "Passer au Vote"

    def dessiner_ecran(self):
        if self.etat_jeu == ETAT_CONFIG: self.dessiner_ecran_config()
        else: # Tous les états de jeu sauf config
             self.dessiner_ecran_jeu()
        pygame.display.flip()

    def dessiner_ecran_config(self):
        """Dessine l'écran de configuration."""
        self.ecran.blit(self.images["fond_config"], (0, 0))
        dessiner_texte(self.ecran, "Configuration de la Partie", self.polices["titre"], JAUNE_LUNE, (LARGEUR_ECRAN // 2, 80))

        # Dessiner les widgets de configuration
        for nom, widget in self.widgets_config.items():
            if isinstance(widget, Bouton):
                widget.dessiner(self.ecran)
            elif isinstance(widget, dict) and "text" in widget: # Pour les labels
                dessiner_texte(self.ecran, widget["text"], widget["font"], BLANC, widget["pos"], alignement=widget["align"])

        # Afficher les valeurs numériques
        font_valeur = self.polices["config_value"]
        rect_total = self.widgets_config["value_total_rect"]
        dessiner_texte(self.ecran, str(self.config_total_joueurs), font_valeur, BLANC, rect_total, alignement="center")
        rect_humains = self.widgets_config["value_humains_rect"]
        dessiner_texte(self.ecran, str(self.config_num_humains), font_valeur, BLANC, rect_humains, alignement="center")

        # Afficher le message d'erreur de configuration (si existe)
        if self.config_message_erreur:
            error_rect = self.widgets_config["error_rect"]
            dessiner_texte(self.ecran, self.config_message_erreur, self.polices["error"], ROUGE_ERREUR, error_rect, alignement="center")


    def dessiner_ecran_jeu(self):
        # --- Inchangé (version précédente avec log centré et wrapping) ---
        fond = self.images["fond_jour"] if self.jeu and self.jeu.is_day else self.images["fond_nuit"]
        self.ecran.blit(fond, (0,0))
        pos_souris = pygame.mouse.get_pos() # Obtenir une seule fois

        # --- Dessiner les cartes joueurs ---
        for carte in self.cartes_joueurs_visuels:
            carte.survol = carte.rect.collidepoint(pos_souris)
            carte.peut_etre_cible = (carte.joueur in self.cibles_possibles_action) and (self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN])
            carte.selectionne = (self.cible_humaine_selectionnee == carte.joueur)
            carte.afficher_role = (self.etat_jeu == ETAT_FIN_PARTIE) or (carte.joueur.is_human and carte.joueur.role is not None)
            carte.dessiner(self.ecran)

        # --- Dessiner la zone de log ---
        log_area_rect = self.rect_zone_messages
        log_surface = pygame.Surface((log_area_rect.width, log_area_rect.height), pygame.SRCALPHA);
        log_surface.fill((*GRIS_FONCE, 210)) # Légèrement plus opaque

        log_font = self.polices["normal"]
        padding = 10 # Marge intérieure pour le texte dans la zone de log
        max_total_lines = 7 # Limite arbitraire du nombre total de lignes affichables
        line_spacing = 4 # Plus d'espace

        # 1. Pré-calculer toutes les lignes nécessaires pour les messages récents
        all_lines_to_draw = []
        lines_count = 0
        for message, msg_type in reversed(self.log_messages_jeu):
             couleur = LOG_COLORS.get(msg_type, DEFAULT_LOG_COLOR)
             # Wrapper le message
             mots = message.split(' ')
             ligne_actuelle_wrap = ""
             wrapped_lines_for_msg = []
             zone_texte_log_locale_width = log_area_rect.width - padding * 2
             for mot in mots:
                 largeur_test, _ = log_font.size(ligne_actuelle_wrap + mot + " ")
                 if ligne_actuelle_wrap == "" or largeur_test <= zone_texte_log_locale_width:
                     ligne_actuelle_wrap += mot + " "
                 else:
                     wrapped_lines_for_msg.append(ligne_actuelle_wrap.strip())
                     ligne_actuelle_wrap = mot + " "
             wrapped_lines_for_msg.append(ligne_actuelle_wrap.strip())

             # Ajouter ces lignes (dans l'ordre inverse pour dessin bottom-up) à la liste globale
             # tout en respectant la limite max de lignes totales
             for line_text in reversed(wrapped_lines_for_msg):
                 if lines_count < max_total_lines:
                      all_lines_to_draw.append((line_text, couleur))
                      lines_count += 1
                 else:
                      break # Limite de lignes atteinte
             if lines_count >= max_total_lines:
                 break # Limite de lignes atteinte

        # 2. Dessiner les lignes pré-calculées de bas en haut
        y_pos_on_surface = log_area_rect.height - padding # Y pour le bas du dernier message
        center_x_on_surface = log_surface.get_rect().centerx
        text_height = log_font.get_height()

        # Itérer sur les lignes calculées (qui sont déjà dans l'ordre inverse d'affichage)
        for line_text, couleur in all_lines_to_draw:
             potential_top = y_pos_on_surface - text_height
             if potential_top < padding: break # Stop si on sort de la zone

             dessiner_texte(log_surface, line_text, log_font, couleur, (center_x_on_surface, y_pos_on_surface), alignement="midbottom");
             y_pos_on_surface -= (text_height + line_spacing)


        # Blit the log surface onto the main screen
        self.ecran.blit(log_surface, log_area_rect.topleft)
        # --- End Draw Log Messages ---

        # --- Dessiner l'indicateur de phase (plus grand, centré en haut) ---
        icone_phase = self.images.get("soleil") if self.jeu and self.jeu.is_day else self.images.get("lune")
        if icone_phase:
            try:
                icone_size = (70, 70) # Taille légèrement augmentée
                icone_phase_scaled = pygame.transform.smoothscale(icone_phase, icone_size);
                rect_phase = icone_phase_scaled.get_rect(centerx=LARGEUR_ECRAN // 2, top=10); # Centré en haut
                self.ecran.blit(icone_phase_scaled, rect_phase)
            except Exception as e: print(f"Erreur dessin icone phase: {e}")

        # --- Dessiner les boutons de jeu actifs ---
        boutons_a_dessiner_noms = []
        # Logique de visibilité des boutons (vérifie l'état ET si le bouton doit être actif)
        if self.etat_jeu == ETAT_FIN_PARTIE:
            boutons_a_dessiner_noms = ["nouvelle_partie", "quitter"]
        elif self.etat_jeu == ETAT_JOUR_DEBAT:
             if self.boutons_jeu["passer_au_vote"].actif: boutons_a_dessiner_noms = ["passer_au_vote"]
        elif self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN] and self.acteur_humain_actuel:
            # Seuls les boutons réellement activés par la logique sont ajoutés
            if self.boutons_jeu["confirmer"].actif: boutons_a_dessiner_noms.append("confirmer")
            if self.boutons_jeu["passer"].actif: boutons_a_dessiner_noms.append("passer")
            if self.action_humaine_attendue == "Sorcière":
                if self.boutons_jeu["sorciere_save"].actif: boutons_a_dessiner_noms.append("sorciere_save")
                if self.boutons_jeu["sorciere_kill"].actif: boutons_a_dessiner_noms.append("sorciere_kill")

        # Mettre à jour l'état survol et dessiner les boutons actifs
        for nom_btn in boutons_a_dessiner_noms:
             if nom_btn in self.boutons_jeu: # Vérifier si le bouton existe
                  btn = self.boutons_jeu[nom_btn]
                  # L'état survol est mis à jour dans gerer_evenement, mais recalculons ici pour le dessin
                  btn.survol = btn.rect.collidepoint(pos_souris)
                  # Dessiner le bouton (il gère son apparence actif/inactif/pressé)
                  btn.dessiner(self.ecran)


    # --- Logique de Jeu (Méthodes INCLUSES CI-DESSOUS) ---
    def lancer_phase_nuit(self):
        if not self.jeu or self.jeu.game_over: return
        self.jeu.is_day = False; self.jeu.day_count += 1 # Incrémente le jour au début de la nuit
        self.jeu.killed_this_night = []; self.jeu.saved_this_night = None; self.jeu.potioned_to_death_this_night = None # Réinitialise la nuit
        # Important : Réinitialiser le flag is_attacked_this_night pour tous les joueurs au début de la nuit
        for p in self.jeu.players:
            p.is_attacked_this_night = False

        self.log_message_jeu(f"\n--- Nuit {self.jeu.day_count} ---", msg_type="info")
        # Déterminer la séquence des rôles actifs la nuit (Loups, Voyante, Sorcière)
        # L'ordre est important : Loups -> Voyante -> Sorcière
        nuit_roles_sequence_possible = ["Loup-Garou", "Voyante", "Sorcière"]
        self.sequence_nuit_restante = [
            role for role in nuit_roles_sequence_possible
            if any(p.role and p.role.name == role and p.is_alive for p in self.jeu.players) # Vérifie si au moins un joueur vivant a ce rôle
        ]
        print(f"DEBUG: Séquence nuit: {self.sequence_nuit_restante}")
        self.delai_prochaine_action = pygame.time.get_ticks() + 1000 # Petit délai avant la 1ère action
        self.etat_jeu = ETAT_NUIT_SEQUENCE

    def executer_action_nuit_suivante(self):
        # This method is called repeatedly by mettre_a_jour_logique in ETAT_NUIT_SEQUENCE

        if not self.jeu or self.jeu.game_over:
             # Check if victory occurred
             if self.jeu and self.jeu.check_victory_condition():
                 self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie();
                 self.sequence_nuit_restante = []; # Vider la séquence
                 return
             # Otherwise, if jeu is None or other strange case, finish sequence
             self.etat_jeu = ETAT_NUIT_RESOLUTION; # Transition to resolution
             self.delai_prochaine_action = pygame.time.get_ticks() + 50;
             return

        if not self.sequence_nuit_restante:
            print("DEBUG: Fin séquence nuit.")
            self.etat_jeu = ETAT_NUIT_RESOLUTION; # Transition to resolution
            self.delai_prochaine_action = pygame.time.get_ticks() + 500; # Delay before resolution
            return

        role_actuel = self.sequence_nuit_restante.pop(0)
        # Get all living players with this role
        joueurs_actifs_vivants_pour_role = [p for p in self.jeu.get_alive_players() if p.role and p.role.name == role_actuel]

        if not joueurs_actifs_vivants_pour_role:
            print(f"DEBUG: Nuit - Pas de joueur vivant pour {role_actuel}. Skip.")
            self.delai_prochaine_action = pygame.time.get_ticks() + 50;
            self.etat_jeu = ETAT_NUIT_SEQUENCE; # Immediately move to the next role in sequence
            return

        acteur_humain = next((p for p in joueurs_actifs_vivants_pour_role if p.is_human), None)

        if acteur_humain:
            # --- Handle Human Player Action ---
            # Check for specific human roles with conditions or different flows
            if role_actuel == "Sorcière":
                # Human Sorciere only acts if she has at least one potion
                if not (acteur_humain.has_saved_potion or acteur_humain.has_kill_potion):
                    self.log_message_jeu(f"{acteur_humain.name} (Sorcière) sans potions. Passe sa nuit.", msg_type="action");
                    self.delai_prochaine_action = pygame.time.get_ticks() + 500;
                    self.etat_jeu = ETAT_NUIT_SEQUENCE; # Skip this role's turn, move to next in sequence
                    return
                # If she has potions, prepare her action - she needs to choose a potion first
                self.preparer_action_humaine(acteur_humain, role_actuel) # This prepares the UI to choose a potion
                self.etat_jeu = ETAT_NUIT_ATTENTE_HUMAIN; # STOP here, wait for human input (potion choice or pass)
                return
            elif role_actuel == "Chasseur":
                 # The Hunter has no standard night action while alive. Their power activates on death.
                 self.log_message_jeu(f"{acteur_humain.name} (Chasseur) n'agit pas la nuit.", msg_type="info");
                 self.delai_prochaine_action = pygame.time.get_ticks() + 500;
                 self.etat_jeu = ETAT_NUIT_SEQUENCE; # Skip this role's turn, move to next in sequence
                 return
            else:
                 # For other roles with simple night actions (like Voyante, Loup-Garou if multiple humans existed)
                 # Prepare the UI for the human to choose a target
                 self.preparer_action_humaine(acteur_humain, role_actuel)
                 self.etat_jeu = ETAT_NUIT_ATTENTE_HUMAIN; # STOP here, wait for human input (target choice)
                 return # STOP

        else:
            # --- Handle IA Player Action ---
            print(f"DEBUG: Nuit - IA {role_actuel} agit...");
            # IA players act immediately without waiting for input

            if role_actuel == "Loup-Garou":
                # IA Loup-Garou Logic: One wolf IA decides for the group
                loup_ia = joueurs_actifs_vivants_pour_role[0] # Take the first living wolf IA
                if hasattr(loup_ia, 'ai_logic') and loup_ia.ai_logic:
                    # The IA Loup must implement decide_night_action and return the target player or None
                    cible = loup_ia.ai_logic.decide_night_action();
                    if cible and cible.is_alive: # Ensure the chosen target is valid and still alive
                        # The wolves decide collectively, so we set the single target for the night attack
                        self.jeu.killed_this_night = [cible] # Overwrite if multiple wolf IAs acted (this is simple V1)
                        # Mark the target as attacked so Sorciere IA can potentially see it
                        cible.is_attacked_this_night = True
                        self.log_message_jeu(f"Les loups attaquent {cible.name}.", msg_type="action")
                        print(f"DEBUG: Loup IA -> {cible.name}")
                    else:
                        self.log_message_jeu("Les loups n'attaquent personne.", msg_type="info") # If IA couldn't find a target
                        print("DEBUG: Loup IA n'a pas trouvé de cible valide ou a passé son tour.")
            elif role_actuel == "Voyante":
                # Each Voyante IA acts independently
                for voyante_ia in joueurs_actifs_vivants_pour_role:
                     if hasattr(voyante_ia, 'ai_logic') and voyante_ia.ai_logic:
                          # The IA Voyante must implement decide_night_action.
                          # It returns the inspected player, but the main loop doesn't *need* this,
                          # the AI logic is responsible for "knowing" the result internally.
                          voyante_ia.ai_logic.decide_night_action() # Call the AI's decision method

            elif role_actuel == "Sorcière":
                 # Each Sorciere IA acts independently if she has potions
                 sorcieres_actives = [p for p in joueurs_actifs_vivants_pour_role if (p.has_saved_potion or p.has_kill_potion)]
                 for sorciere_ia in sorcieres_actives:
                      if hasattr(sorciere_ia, 'ai_logic') and sorciere_ia.ai_logic:
                           # The Sorciere IA needs to know who was attacked by the wolves to decide on using the save potion.
                           attaques_loups = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None # Get the wolf target if any
                           # The Sorciere IA must implement decide_night_action, accepting attaques_loups
                           # It returns a dictionary {"save": player_to_save, "kill": player_to_kill}
                           action_decided = sorciere_ia.ai_logic.decide_night_action(attaques_loups=attaques_loups) # Pass the info

                           # --- Execute Sorciere IA's Decided Actions ---
                           saved_target = action_decided.get("save")
                           killed_target = action_decided.get("kill")

                           # Execute Save Action
                           cible_loup = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None
                           if saved_target and sorciere_ia.has_saved_potion and saved_target == cible_loup and saved_target.is_alive:
                                self.jeu.saved_this_night = saved_target # Game records the save
                                sorciere_ia.has_saved_potion = False # Consume the potion
                                self.log_message_jeu(f"Sorcière {sorciere_ia.name} utilise sa potion de vie sur {saved_target.name}.", msg_type="action")
                                print(f"DEBUG: Sorc IA save {saved_target.name} executed.")
                           elif saved_target and sorciere_ia.has_saved_potion:
                                sorciere_ia.has_saved_potion = False # Consume the potion
                                print(f"DEBUG: Sorc IA save {saved_target.name} used on invalid target.")


                           # Execute Kill Action
                           if killed_target and sorciere_ia.has_kill_potion and killed_target.is_alive and killed_target != self.jeu.saved_this_night:
                                self.jeu.potioned_to_death_this_night = killed_target # Game records the poisoning
                                sorciere_ia.has_kill_potion = False # Consume the potion
                                self.log_message_jeu(f"Sorcière {sorciere_ia.name} utilise sa potion de mort sur {killed_target.name}.", msg_type="action")
                                print(f"DEBUG: Sorc IA kill {killed_target.name} executed.")
                           elif killed_target and sorciere_ia.has_kill_potion:
                                sorciere_ia.has_kill_potion = False # Consume the potion
                                print(f"DEBUG: Sorc IA kill {killed_target.name} used on invalid target.")


            # After the IA action(s), plan the next step in the sequence with a delay
            self.delai_prochaine_action = pygame.time.get_ticks() + 750;
            self.etat_jeu = ETAT_NUIT_SEQUENCE; # Continue to the next role in sequence or finish night if done


    def preparer_action_humaine(self, acteur, type_action):
        """
        Prepares the UI and state for a human player's action (choosing a target).
        Args:
            acteur: The human Player instance performing the action.
            type_action: String indicating the type of action ("Loup-Garou", "Voyante", "Vote", "Chasseur", "Sorcière").
        """
        self.acteur_humain_actuel = acteur;
        self.action_humaine_attendue = type_action;
        self.cible_humaine_selectionnee = None; # No target selected initially

        # Deactivate general action buttons by default
        self.boutons_jeu["confirmer"].actif = False; # Confirm requires a target selection (except for Sorciere's initial potion choice)
        self.boutons_jeu["passer"].actif = False; # Activate passer only if the action is skippable

        # Deactivate specific role buttons (like Sorciere potions) by default
        self.boutons_jeu["sorciere_save"].actif = False;
        self.boutons_jeu["sorciere_kill"].actif = False;
        self._sorciere_action_type = None # Reset for Sorciere

        cibles = []; prompt = ""; log_prefix = f"\n{acteur.name} ({acteur.role.name}), à vous."

        if type_action == "Loup-Garou":
             prompt = "Qui dévorer ?";
             # Loups-Garous cannot target other Loups-Garous
             cibles = [p for p in self.jeu.get_alive_players() if p.role and not p.role.is_wolf]
             # Loup-Garou action is mandatory (cannot pass in basic rules)
             # self.boutons_jeu["passer"].actif = False; # Already False

        elif type_action == "Voyante":
             prompt = "Qui espionner ?";
             # Voyante cannot inspect self
             cibles = [p for p in self.jeu.get_alive_players() if p != acteur];
             # Voyante can pass her turn
             self.boutons_jeu["passer"].actif = True;

        elif type_action == "Sorcière":
             # For the Sorciere, the human first chooses which potion to use (via buttons)
             # Targets become selectable *after* a potion is chosen (handled in prepare_action_sorciere)
             prompt = "Quelle potion utiliser ?";
             self.log_message_jeu(log_prefix, msg_type="prompt");
             self.log_message_jeu(prompt, msg_type="prompt");

             # Activate potion buttons only if the Sorciere player has the potion
             if acteur.has_saved_potion:
                  self.boutons_jeu["sorciere_save"].actif = True
             if acteur.has_kill_potion:
                  self.boutons_jeu["sorciere_kill"].actif = True

             # Sorciere can pass her turn without using any potion
             self.boutons_jeu["passer"].actif = True

             # Inform the Sorciere about the wolf attack target (if any)
             cible_loup = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None
             if cible_loup and cible_loup.is_alive:
                 self.log_message_jeu(f"Les loups ont attaqué {cible_loup.name}.", msg_type="info");
             else:
                  self.log_message_jeu("Personne n'a été attaqué par les loups cette nuit.", msg_type="info");

             self.cibles_possibles_action = []; # No target selectable yet, waiting for potion choice
             self.log_message_jeu("Choisissez une potion ou Passez l'Action.", msg_type="prompt")

             # The state remains ETAT_NUIT_ATTENTE_HUMAIN, waiting for a button click (potion or pass)
             # The list of possible targets (self.cibles_possibles_action) will be populated in prepare_action_sorciere
             # The Confirm button will only become active after a target is selected *in prepare_action_sorciere*
             return # Exit this function, waiting for human input (button click)


        elif type_action == "Vote":
             prompt = "Pour qui voter ?";
             # Players cannot vote for themselves
             cibles = [p for p in self.jeu.get_alive_players() if p != acteur]
             # Voting is generally mandatory (cannot pass in basic rules)
             # self.boutons_jeu["passer"].actif = False; # Already False

        elif type_action == "Chasseur": # Action of a dead Hunter
             prompt = "Qui éliminer ?";
             # A dead Hunter can target any living player
             cibles = self.jeu.get_alive_players()
             # The Hunter's shot upon death is mandatory (cannot pass)
             # self.boutons_jeu["passer"].actif = False; # Already False


        # --- For actions requiring target selection (all except initial Sorciere choice) ---
        # Set the list of possible targets for the UI
        self.cibles_possibles_action = cibles;

        # Display prompt messages (only if not Sorciere, whose prompt is handled above)
        if type_action != "Sorcière":
             self.log_message_jeu(log_prefix, msg_type="prompt");
             self.log_message_jeu(prompt, msg_type="prompt");
             self.log_message_jeu("Sélectionnez une carte et confirmez.", msg_type="prompt");


        # Update the visual cards to indicate which players can be targeted
        for carte in self.cartes_joueurs_visuels:
             carte.peut_etre_cible = (carte.joueur in self.cibles_possibles_action)
             carte.selectionne = False # Deselect all cards initially

        # If the list of possible targets is empty for a mandatory action, something is wrong or the game should end.
        # For now, print a warning and effectively make the human player 'pass' this action automatically.
        if not self.cibles_possibles_action and not self.boutons_jeu["passer"].actif:
             print(f"WARN: {acteur.name} ({acteur.role.name}) a une action obligatoire ({type_action}) mais 0 cibles possibles. Passer action automatiquement.");
             self.log_message_jeu(f"{acteur.name} ({acteur.role.name}) ne trouve pas de cible possible et passe son tour.", msg_type="info");
             # Simulate passing the action
             self.acteur_humain_actuel = None; self.action_humaine_attendue = None;
             self.cibles_possibles_action = []; # Clear possible targets
             # Determine next state based on current state
             if self.etat_jeu == ETAT_NUIT_ATTENTE_HUMAIN:
                 self.etat_jeu = ETAT_NUIT_SEQUENCE
             elif self.etat_jeu == ETAT_JOUR_VOTE_ATTENTE_HUMAIN:
                 # If a voter cannot vote, their vote is effectively skipped.
                 # traiter_votant_suivant handles processing the next voter.
                 # We need to ensure the state transitions properly.
                 # We set a delay and let mettre_a_jour_logique call traiter_votant_suivant again.
                 self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE # Move back to sequence state
             elif self.etat_jeu == ETAT_CHASSEUR_ATTENTE_HUMAIN:
                  # If a dead Hunter cannot shoot, their action is over.
                  self.etat_jeu = ETAT_CHASSEUR_SEQUENCE
             # Add a short delay before the next state logic runs
             self.delai_prochaine_action = pygame.time.get_ticks() + 50 # Short delay
             # No return needed here, the state transition will happen in mettre_a_jour_logique


    def preparer_action_sorciere(self, type_potion):
         """
         Prepares the state for the human Sorciere's action after she has chosen a potion.
         This is called by the potion button callbacks.
         Args:
             type_potion: String, either "save" or "kill".
         """
         # Ensure we are in the correct state and there's a human Sorciere actor
         if not self.acteur_humain_actuel or self.action_humaine_attendue != "Sorcière":
             print("WARN: prepare_action_sorciere called in wrong state or with no Sorciere actor."); return

         acteur = self.acteur_humain_actuel

         # Double-check if the player actually has the chosen potion
         if (type_potion == "save" and not acteur.has_saved_potion) or \
            (type_potion == "kill" and not acteur.has_kill_potion):
             print(f"WARN: Joueur {acteur.name} a essayé d'utiliser une potion ({type_potion}) qu'il n'a pas. Buttons should be inactive.");
             # Reset state to wait for another potion choice or pass, or just return
             self.log_message_jeu(f"Vous n'avez pas la potion de {type_potion}. Choisissez à nouveau ou passez.", msg_type="error")
             # Re-activate potion buttons based on actual remaining potions
             if acteur.has_saved_potion: self.boutons_jeu["sorciere_save"].actif = True
             if acteur.has_kill_potion: self.boutons_jeu["sorciere_kill"].actif = True
             self.boutons_jeu["confirmer"].actif = False # Confirm still needs a target
             self.cible_humaine_selectionnee = None
             self.cibles_possibles_action = [] # Clear potential targets display
             for carte in self.cartes_joueurs_visuels: carte.peut_etre_cible = False
             self._sorciere_action_type = None # Reset chosen potion type
             return # Stay in ETAT_NUIT_ATTENTE_HUMAIN, waiting for a valid choice


         self._sorciere_action_type = type_potion # Store the chosen potion type
         self.cible_humaine_selectionnee = None # Reset target selection
         self.boutons_jeu["confirmer"].actif = False # Confirm requires a target for this potion
         # Deactivate potion choice buttons once one is chosen
         self.boutons_jeu["sorciere_save"].actif = False
         self.boutons_jeu["sorciere_kill"].actif = False
         self.boutons_jeu["passer"].actif = True # Sorciere can still pass after choosing potion

         cibles = []
         if type_potion == "save":
             self.log_message_jeu("Qui sauver ?", msg_type="prompt");
             # The save potion can only target the player attacked by the wolves, if that player is alive
             cible_loup = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None
             if cible_loup and cible_loup.is_alive:
                  cibles = [cible_loup] # The only possible target for save potion
             else:
                  self.log_message_jeu("Personne n'a été attaqué par les loups cette nuit ou la cible est déjà morte. Cette potion n'a pas de cible valide.", msg_type="info");
                  cibles = [] # No valid target for save potion
                  # If no valid target, the player must pass the *targeting* phase for this potion
                  # Confirmer button stays False, Passer button remains Active
                  self.boutons_jeu["confirmer"].actif = False # Cannot confirm if no targets


         elif type_potion == "kill":
              self.log_message_jeu("Qui empoisonner ?", msg_type="prompt");
              # The kill potion can target any living player EXCEPT the Sorciere herself.
              cibles = [p for p in self.jeu.get_alive_players() if p != self.acteur_humain_actuel]
              # The passer button remains active


         # Update the list of possible targets for the UI and game logic
         self.cibles_possibles_action = cibles;
         self.log_message_jeu("Sélectionnez une carte et confirmez, ou Passez.", msg_type="prompt")

         # Update visual cards to indicate possible targets based on the chosen potion
         for carte in self.cartes_joueurs_visuels:
              carte.peut_etre_cible = (carte.joueur in self.cibles_possibles_action)
              carte.selectionne = False # Deselect all cards


         # If there are no possible targets for the chosen potion (e.g., save potion when no one attacked)
         # The Confirm button remains inactive, the Passer button remains active.


         # State remains ETAT_NUIT_ATTENTE_HUMAIN, now waiting for target selection or pass


    def confirmer_action_humaine(self):
        # This method is called when the "Confirmer Action" button is clicked.
        # This button is only active when a target has been selected.
        if not self.acteur_humain_actuel or not self.action_humaine_attendue or not self.cible_humaine_selectionnee:
            print("WARN: Confirmer cliqué without valid actor, action, or selected target."); return # Should not happen if button active state is correct

        acteur = self.acteur_humain_actuel;
        action_type = self.action_humaine_attendue;
        cible = self.cible_humaine_selectionnee;

        print(f"DEBUG: Humain {acteur.name} ({action_type}) confirme action on {cible.name}")

        # --- Deactivate UI Elements ---
        # Deactivate action buttons
        self.boutons_jeu["confirmer"].actif = False;
        self.boutons_jeu["passer"].actif = False;
        self.boutons_jeu["sorciere_save"].actif = False; # Deactivate Sorciere buttons
        self.boutons_jeu["sorciere_kill"].actif = False;
        # Clear selected target and possible targets visualization
        self.cible_humaine_selectionnee = None;
        self.cibles_possibles_action = [];
        for carte in self.cartes_joueurs_visuels:
             carte.selectionne = False;
             carte.peut_etre_cible = False;
        # --- End Deactivate UI ---

        # --- Execute the Confirmed Action ---
        # Check if the target is still valid (alive) before executing the action
        if not cible.is_alive and action_type != "Chasseur": # A dead Hunter can target a living player
             self.log_message_jeu(f"Cible {cible.name} est déjà morte, action annulée.", msg_type="info");
             print(f"DEBUG: Cible {cible.name} for action {action_type} was already dead.")
             # Action cannot be executed, simply end the human's turn for this role
             self.acteur_humain_actuel = None; self.action_humaine_attendue = None; self._sorciere_action_type = None;
             # Determine next state
             if action_type in ["Loup-Garou", "Voyante", "Sorcière"]:
                 self.etat_jeu = ETAT_NUIT_SEQUENCE;
                 self.delai_prochaine_action = pygame.time.get_ticks() + 200
             elif action_type == "Vote":
                  # If a voter's target is dead, their vote is wasted/cancelled
                  # We set the target to None to ensure it's not processed in traiter_votant_suivant
                  self._human_vote_target = None
                  self._human_vote_target_actor_name = None
                  self.acteur_humain_actuel = None; self.action_humaine_attendue = None;
                  self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE # Go back to sequence to process next voter
                  self.delai_prochaine_action = pygame.time.get_ticks() + 100 # Short delay
             elif action_type == "Chasseur":
                  # If a dead Hunter's target is dead, they don't shoot anyone
                  self.acteur_humain_actuel = None; self.action_humaine_attendue = None;
                  self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; # Continue sequence
                  self.delai_prochaine_action = pygame.time.get_ticks() + 500
             return # Action finished (cancelled), return


        # Execute action for living target
        if action_type == "Loup-Garou":
             # Human Loup-Garou decides the target for the wolves
             # In a multi-human setup, this would be more complex. Here assumes 1 human wolf decides.
             self.jeu.killed_this_night = [cible] # Game records the wolf target
             # Mark the target as attacked so Sorciere can see it
             cible.is_attacked_this_night = True
             self.log_message_jeu(f"Vous (Loup-Garou) décidez de dévorer {cible.name}.", msg_type="action");
             print(f"DEBUG: Loup-Garou humain {acteur.name} cible {cible.name}")

             # Action finished, proceed to next role in night sequence
             self.acteur_humain_actuel = None; self.action_humaine_attendue = None;
             self.etat_jeu = ETAT_NUIT_SEQUENCE;
             self.delai_prochaine_action = pygame.time.get_ticks() + 200 # Short delay


        elif action_type == "Voyante":
             # Human Voyante inspects a player
             self.log_message_jeu(f"Rôle de {cible.name} : {cible.role.name}", msg_type="important"); # Marqué comme important
             print(f"DEBUG: Voyante humaine {acteur.name} inspecte {cible.name}. Rôle: {cible.role.name}")

             # Action finished, proceed to next role in night sequence
             self.acteur_humain_actuel = None; self.action_humaine_attendue = None;
             self.etat_jeu = ETAT_NUIT_SEQUENCE;
             self.delai_prochaine_action = pygame.time.get_ticks() + 200

        elif action_type == "Sorcière":
             # Human Sorciere uses a potion on a target
             # _sorciere_action_type indicates which potion was chosen before this confirmation
             type_potion = self._sorciere_action_type

             if type_potion == "save" and acteur.has_saved_potion:
                 # Check if the target is the actual wolf target this night and is alive
                 cible_loup = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None
                 if cible == cible_loup and cible.is_alive:
                     self.jeu.saved_this_night = cible # Game records the save
                     acteur.has_saved_potion = False # Consume potion
                     self.log_message_jeu(f"Vous utilisez votre potion de vie sur {cible.name}.", msg_type="action");
                     print(f"DEBUG: Sorciere humaine {acteur.name} sauve {cible.name}")
                 else:
                      # Potion used on invalid target
                      acteur.has_saved_potion = False # Potion consumed
                      self.log_message_jeu(f"La potion de vie sur {cible.name} n'a pas eu d'effet (pas la cible des loups ou déjà mort).", msg_type="info");
                      print(f"DEBUG: Sorciere humaine {acteur.name} used save potion on {cible.name}, but it had no effect.")


             elif type_potion == "kill" and acteur.has_kill_potion:
                  # Check if target is valid for kill potion (alive, not self, not saved this turn)
                  if cible.is_alive and cible != self.jeu.saved_this_night:
                       self.jeu.potioned_to_death_this_night = cible # Game records the poisoning
                       acteur.has_kill_potion = False # Consume potion
                       self.log_message_jeu(f"Vous utilisez votre potion de mort sur {cible.name}.", msg_type="action");
                       print(f"DEBUG: Sorciere humaine {acteur.name} empoisonne {cible.name}")
                  else:
                       # Potion used on invalid target
                       acteur.has_kill_potion = False # Potion consumed
                       self.log_message_jeu(f"La potion de mort sur {cible.name} n'a pas eu d'effet (déjà mort ou sauvé).", msg_type="info");
                       print(f"DEBUG: Sorciere humaine {acteur.name} used kill potion on {cible.name}, but it had no effect.")

             # Action finished, proceed to next role in night sequence
             self.acteur_humain_actuel = None; self.action_humaine_attendue = None; self._sorciere_action_type = None;
             self.etat_jeu = ETAT_NUIT_SEQUENCE;
             self.delai_prochaine_action = pygame.time.get_ticks() + 200


        elif action_type == "Vote":
             # Human player confirms their vote target
             # Store the target and the voter's name to be processed later in traiter_votant_suivant
             self._human_vote_target = cible;
             self._human_vote_target_actor_name = acteur.name;
             self.log_message_jeu(f"Vous votez pour {cible.name}.", msg_type="action");
             print(f"DEBUG: Vote Humain {acteur.name} -> {cible.name} enregistré, prêt à être traité.")

             # Action finished, return to vote sequence processing
             self.acteur_humain_actuel = None; self.action_humaine_attendue = None;
             # State should transition back to ETAT_JOUR_VOTE_SEQUENCE to process next voter
             self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE
             self.delai_prochaine_action = pygame.time.get_ticks() + 100 # Short delay before next voter is processed

        elif action_type == "Chasseur": # Action of a dead Human Hunter
             # Human Hunter eliminates a target upon death
             # Check for cible.is_alive already done at the start of the method
             self.log_message_jeu(f"Chasseur {acteur.name} élimine {cible.name} !", msg_type="important");
             cible.die() # Game handles the death

             self.organiser_cartes_joueurs(); # Update display after death
             self.jeu.check_victory_condition() # Check victory after this death

             # Check if the eliminated player is also a Hunter who needs to shoot
             if cible.role and cible.role.name == "Chasseur":
                  # Add this new dead Hunter to the sequence of Hunter actions
                  # Insert at the beginning so they act immediately after the current one
                  if cible not in self.chasseurs_morts_sequence: # Avoid adding same Hunter multiple times
                       self.chasseurs_morts_sequence.insert(0, cible)
                       self.log_message_jeu(f"{cible.name} était aussi Chasseur et doit tirer!", msg_type="important")
                 # else: Target was not a Hunter, sequence continues with next dead Hunter (if any)

             # Action finished, proceed to next Hunter in sequence (if any) or callback
             self.acteur_humain_actuel = None; self.action_humaine_attendue = None;
             self.etat_jeu = ETAT_CHASSEUR_SEQUENCE;
             self.delai_prochaine_action = pygame.time.get_ticks() + 500


    def passer_action_humaine(self):
        """
        Handles the human player choosing to pass their action.
        This button should only be active for skippable actions (Voyante, Sorciere).
        """
        if not self.acteur_humain_actuel or not self.action_humaine_attendue:
             print("WARN: Passer cliqué without valid actor or action."); return

        acteur = self.acteur_humain_actuel; action_type = self.action_humaine_attendue

        # Only allow passing for specific roles/actions
        if action_type in ["Voyante", "Sorcière"]:
             self.log_message_jeu(f"{acteur.name} ({acteur.role.name}) passe son action.", msg_type="action");
             print(f"DEBUG: Humain {acteur.name} passe action '{action_type}'.")

             # --- Deactivate UI Elements ---
             self.boutons_jeu["confirmer"].actif = False;
             self.boutons_jeu["passer"].actif = False;
             self.boutons_jeu["sorciere_save"].actif = False; # Deactivate Sorciere buttons
             self.boutons_jeu["sorciere_kill"].actif = False;
             # Clear state variables
             self.cible_humaine_selectionnee = None;
             self.acteur_humain_actuel = None;
             self.action_humaine_attendue = None;
             self._sorciere_action_type = None;
             self.cibles_possibles_action = []; # Clear possible targets
             # Update card visuals
             for carte in self.cartes_joueurs_visuels:
                 carte.selectionne = False;
                 carte.peut_etre_cible = False;
             # --- End Deactivate UI ---

             # Action finished, proceed to the next role in night sequence
             self.etat_jeu = ETAT_NUIT_SEQUENCE;
             self.delai_prochaine_action = pygame.time.get_ticks() + 200
        else:
             print(f"WARN: Tentative de passer action non passible ({action_type}). Button should not be active.")


    def resoudre_nuit(self):
        # This method is called once after all night roles have had their turn (ETAT_NUIT_RESOLUTION)
        if not self.jeu or self.jeu.game_over: return # Security

        self.log_message_jeu("\nLe village se réveille...", msg_type="info");
        morts_cette_nuit_list = []; # List to collect players who die this night
        cible_loup = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None # Get the wolf target (if any)
        cible_poison = self.jeu.potioned_to_death_this_night # Get the poisoned target (if any)

        # --- Resolution of the Wolf Attack ---
        if cible_loup and cible_loup.is_alive: # Check if the wolf target exists and is alive
             if cible_loup == self.jeu.saved_this_night: # Check if the wolf target was saved by Sorciere
                  self.log_message_jeu(f"{cible_loup.name} a été attaqué mais sauvé(e) !", msg_type="important");
             else:
                  morts_cette_nuit_list.append(cible_loup); # Add to the list of players who will die
                  self.log_message_jeu(f"{cible_loup.name} dévoré(e) !", msg_type="important");
        # else: No wolf target, or wolf target was already dead before resolution

        # --- Resolution of the Poison Potion ---
        # Check if a player was poisoned AND is alive AND was NOT saved
        if cible_poison and cible_poison.is_alive and cible_poison != self.jeu.saved_this_night:
             # Ensure the poisoned target is not already on the death list (e.g., was both attacked and poisoned)
             if cible_poison not in morts_cette_nuit_list:
                 morts_cette_nuit_list.append(cible_poison); # Add to the list of players who will die
                 self.log_message_jeu(f"{cible_poison.name} empoisonné(e) !", msg_type="important");
             else:
                  # Case where the same player was both attacked and poisoned
                  self.log_message_jeu(f"{cible_poison.name} a aussi été empoisonné(e), mais était déjà dévoré(e).", msg_type="info");
        # else: No poisoned target, or target already dead/saved before resolution


        # --- Execute Deaths and Check for Hunter Effect ---
        chasseurs_morts_suite = []; # List to collect Hunters who die and need to shoot
        # Process each player in the list of those who are marked to die this night
        for joueur_a_tuer in morts_cette_nuit_list:
             if joueur_a_tuer.is_alive: # Double check they are still alive before dying
                  joueur_a_tuer.die(); # Call the player's die method
                  self.log_message_jeu(f"Son rôle était : {joueur_a_tuer.role.name}", msg_type="info");
                  # Check if the dying player is a Hunter (and has a role)
                  if joueur_a_tuer.role and joueur_a_tuer.role.name == "Chasseur":
                       chasseurs_morts_suite.append(joueur_a_tuer) # Add to the list of Hunters who need to act

             else:
                  # This player was already dead when processing the death list (shouldn't happen with current logic, but good check)
                  print(f"DEBUG: Résolution Nuit - Joueur {joueur_a_tuer.name} already dead in the list of deaths. Skipping death process for this player.");


        self.organiser_cartes_joueurs(); # Update the visual cards display after deaths
        self.jeu.check_victory_condition() # Check victory conditions after deaths

        # --- Transition to Next Phase ---
        # If any Hunters died this night, start the Hunter action sequence
        if chasseurs_morts_suite:
             self.chasseurs_morts_sequence = chasseurs_morts_suite; # Set the sequence of Hunters who must shoot
             self.callback_apres_chasseur = self.verifier_victoire_et_lancer_jour; # Define the callback after Hunter sequence finishes
             self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; # Transition to Hunter sequence state
             self.delai_prochaine_action = pygame.time.get_ticks() + 1000 # Delay before the first Hunter acts
        else:
             # If no Hunters died, proceed directly to checking victory and then to the day phase
             self.verifier_victoire_et_lancer_jour()


    def executer_action_chasseur_suivante(self):
        # This method is called repeatedly by mettre_a_jour_logique in ETAT_CHASSEUR_SEQUENCE
        # It handles one dead Hunter's action at a time.

        if not self.jeu or self.jeu.game_over:
            # Check if victory occurred during the Hunter sequence (e.g., a Hunter's shot kills the last necessary player)
            if self.jeu and self.jeu.check_victory_condition():
                self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie();
                self.chasseurs_morts_sequence = []; # Clear the sequence
                self.callback_apres_chasseur = None; # Cancel the callback
                return # Game is over

            # If game is not over but jeu is None or some other strange state, attempt to finish the sequence
            print("WARN: Game in strange state during Hunter sequence. Attempting to proceed.")
            if self.callback_apres_chasseur:
                 callback = self.callback_apres_chasseur; self.callback_apres_chasseur = None; callback(); # Call the stored callback
            return


        if not self.chasseurs_morts_sequence:
            print("DEBUG: Fin séquence Chasseurs.");
            # All Hunters in the sequence have acted (or been skipped). Call the stored callback.
            if self.callback_apres_chasseur:
                 callback = self.callback_apres_chasseur; # Get callback
                 self.callback_apres_chasseur = None; # Clear callback variable
                 callback(); # Execute callback (usually verifier_victoire_et_lancer_jour or verifier_victoire_et_lancer_nuit)
            return

        # Get the next dead Hunter from the sequence
        chasseur_mort_actuel = self.chasseurs_morts_sequence.pop(0)

        # Double-check that the player is actually dead (should be, but safety first)
        if chasseur_mort_actuel.is_alive:
            print(f"WARN: Chasseur {chasseur_mort_actuel.name} listed to act but is alive. Skipping their action.");
            self.delai_prochaine_action = pygame.time.get_ticks() + 50; # Short delay before checking next in sequence
            self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; # Stay in this state to process the rest of the sequence
            return # Skip this Hunter's turn

        self.log_message_jeu(f"\nChasseur {chasseur_mort_actuel.name} (mort) choisit sa cible !", msg_type="prompt");
        cibles_vivantes = self.jeu.get_alive_players() # Get current living players

        if not cibles_vivantes:
            self.log_message_jeu("... mais personne n'est vivant pour être ciblé !", msg_type="info");
            print("DEBUG: No living players for dead Hunter to target.")
            self.delai_prochaine_action = pygame.time.get_ticks() + 500; # Delay before processing next in sequence or callback
            self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; # Stay in this state
            return # Hunter couldn't shoot, move to next in sequence

        if chasseur_mort_actuel.is_human:
            # If the dead Hunter was human, wait for their input to choose a target
            self.preparer_action_humaine(chasseur_mort_actuel, "Chasseur") # type_action "Chasseur"
            self.etat_jeu = ETAT_CHASSEUR_ATTENTE_HUMAIN; # STOP here, wait for human input (target selection)
            # The "Passer" button for a dead Hunter is disabled in prepare_action_humaine as the shot is mandatory.
        else:
             # If the dead Hunter was an IA player
             print(f"DEBUG: Chasseur IA mort {chasseur_mort_actuel.name} agit...");
             if hasattr(chasseur_mort_actuel, 'ai_logic') and chasseur_mort_actuel.ai_logic:
                  # The Hunter IA must implement decide_chasseur_action and return the target player or None
                  cible_ia = chasseur_mort_actuel.ai_logic.decide_chasseur_action();
                  if cible_ia and cible_ia.is_alive: # Check if the chosen target is valid and still alive
                       self.log_message_jeu(f"Chasseur IA {chasseur_mort_actuel.name} tire sur {cible_ia.name} !", msg_type="important");
                       # Execute the elimination
                       cible_ia.die()
                       self.organiser_cartes_joueurs(); # Update display
                       self.jeu.check_victory_condition() # Check victory after this death

                       # Check if the player who just died is also a Hunter
                       if cible_ia.role and cible_ia.role.name == "Chasseur": # Check if role exists
                           # If so, add them to the front of the sequence
                           if cible_ia not in self.chasseurs_morts_sequence: # Avoid adding same Hunter multiple times
                               self.chasseurs_morts_sequence.insert(0, cible_ia)
                               self.log_message_jeu(f"{cible_ia.name} était aussi Chasseur et doit tirer!", msg_type="important")
                       # else: The target was not a Hunter, sequence continues with next dead Hunter (if any)

                  else:
                       self.log_message_jeu(f"Chasseur IA {chasseur_mort_actuel.name} n'a pas trouvé de cible valide ou cible morte.", msg_type="info");
                       print(f"DEBUG: Chasseur IA mort {chasseur_mort_actuel.name} could not target.")
             else:
                  print(f"ERREUR: IA Chasseur {chasseur_mort_actuel.name} sans ai_logic. Ne peut pas agir.")
                  self.log_message_jeu(f"Chasseur IA {chasseur_mort_actuel.name} ne peut pas agir (logique IA manquante).", msg_type="error")

             # After the IA Hunter action (or failed action), proceed to the next Hunter in sequence
             self.delai_prochaine_action = pygame.time.get_ticks() + 1000 # Delay before next action
             self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; # Stay in this state

        # Note: If it was a human Hunter, the state machine waits in ETAT_CHASSEUR_ATTENTE_HUMAIN.
        # Their action is processed when confirmer_action_humaine is called, and that method transitions the state back to ETAT_CHASSEUR_SEQUENCE.


    def verifier_victoire_et_lancer_jour(self):
        # Called after night resolution or after the last Hunter action resulting from night deaths.
        if self.jeu and self.jeu.check_victory_condition():
            self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie()
        else:
            # Only launch the day phase if the game is not over
            self.etat_jeu = ETAT_JOUR_DEBAT; # Transition to Day Debate state
            self.lancer_phase_jour()


    def lancer_phase_jour(self):
        if not self.jeu or self.jeu.game_over: return # Security
        self.jeu.is_day = True; # It is now Day
        # day_count is incremented at the beginning of the night

        self.log_message_jeu(f"\n--- Jour {self.jeu.day_count} ---", msg_type="info")
        joueurs_vivants = self.jeu.get_alive_players();
        self.log_message_jeu(f"Vivants : {', '.join([p.name for p in joueurs_vivants])}", msg_type="info")

        # Check victory conditions immediately at the start of the day
        # (e.g., if night deaths resulted in a win)
        if self.jeu.check_victory_condition():
            self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie(); return

        humains_vivants = [p for p in joueurs_vivants if p.is_human]

        # Activate the "Passer au Vote" button if there is at least one human player alive
        # This allows the human(s) to control when voting starts after debate (even if no complex debate system exists yet)
        if len(humains_vivants) > 0:
             self.log_message_jeu("\nPhase de débat. Cliquez sur 'Passer au Vote' pour voter.", msg_type="prompt")
             self.boutons_jeu["passer_au_vote"].actif = True; # Activate the button
             self.etat_jeu = ETAT_JOUR_DEBAT # Stay in debate state waiting for the button click
        else:
             # If no living humans, proceed directly to automatic vote by IAs
             self.log_message_jeu("\nAucun humain vivant. Passage direct au vote IA.", msg_type="info");
             self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE; # Transition to vote sequence state
             self.lancer_phase_vote() # Launch the vote sequence immediately

    def lancer_phase_vote(self):
        # This is called when the "Passer au Vote" button is clicked (if humans are alive)
        # or automatically if no humans are alive at the start of the day.
        if not self.jeu or self.jeu.game_over: return # Security

        self.boutons_jeu["passer_au_vote"].actif = False; # Deactivate the debate button once voting starts

        self.log_message_jeu("\n--- Phase de Vote ---", msg_type="info")
        # Get the list of players who can vote (all living players)
        self.votants_restants = self.jeu.get_alive_players()[:] # Make a copy of the list
        self.votes_en_cours = {} # Reset the vote count for this round

        # Transition to the vote sequence state and start processing voters
        self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE;
        self.delai_prochaine_action = pygame.time.get_ticks() + 500 # Delay before processing the first voter

    def traiter_votant_suivant(self):
        # This method is called repeatedly by mettre_a_jour_logique in ETAT_JOUR_VOTE_SEQUENCE
        # It handles one voter at a time (human or IA) or processes the result of a human vote just completed.

        if not self.jeu or self.jeu.game_over:
             # Check if victory occurred during voting sequence
             if self.jeu and self.jeu.check_victory_condition():
                 self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie();
                 self.votants_restants = []; # Empty voter list
                 return # Game is over

             # If game is not over but jeu is None or some other strange state, finish voting
             print("WARN: Game in strange state during Vote sequence. Attempting to proceed to resolution.")
             self.etat_jeu = ETAT_JOUR_VOTE_RESOLUTION; # Transition to resolution
             self.delai_prochaine_action = pygame.time.get_ticks() + 50;
             return # Go directly to resolution


        # --- Step 1: Process the previous human vote if one is pending ---
        # A human vote is recorded in _human_vote_target when the Confirm button is clicked
        # This block processes the result of the last human's vote selection
        if self._human_vote_target is not None:
             # Find the human player who just voted
             voter_prec = self.jeu.get_player_by_name(self._human_vote_target_actor_name) if self._human_vote_target_actor_name else None

             # Check if the voter is still alive and if the target is still alive at the moment of processing
             if voter_prec and voter_prec.is_alive and self._human_vote_target.is_alive:
                  target = self._human_vote_target;
                  self.votes_en_cours[target] = self.votes_en_cours.get(target, 0) + 1; # Register the vote for the target
                  print(f"DEBUG: Vote humain {voter_prec.name} -> {target.name} enregistré.")
                  # Log the vote only after confirming it's valid
                  self.log_message_jeu(f"Vote de {voter_prec.name} enregistré.", msg_type="action")
             elif voter_prec: # If voter existed but was not valid (dead or target dead)
                  self.log_message_jeu(f"Vote de {voter_prec.name} annulé (votant mort ou cible morte).", msg_type="info")
                  print(f"DEBUG: Vote humain de {voter_prec.name} annulé. Voter alive: {voter_prec.is_alive if voter_prec else 'N/A'}, Target alive: {self._human_vote_target.is_alive if self._human_vote_target else 'N/A'}")


             # Reset human vote variables after processing the pending vote
             self._human_vote_target = None;
             self._human_vote_target_actor_name = None;

             # Add a small delay after processing a human vote before moving to the next voter
             self.delai_prochaine_action = pygame.time.get_ticks() + 100
             # The state remains ETAT_JOUR_VOTE_SEQUENCE. mettre_a_jour_logique will call this function again after the delay,
             # and it will then proceed to Step 2 (process the next voter from the list).
             return # Exit this iteration to allow delay and next frame rendering


        # --- Step 2: Process the next voter in the remaining voters list ---
        if not self.votants_restants:
            print("DEBUG: Fin de la liste des votants pour ce tour.")
            self.etat_jeu = ETAT_JOUR_VOTE_RESOLUTION; # All votes processed, move to resolution
            self.delai_prochaine_action = pygame.time.get_ticks() + 500; # Delay before displaying results
            return # Exit, transition to resolution

        # Get the next voter from the remaining list
        votant_actuel = self.votants_restants.pop(0)

        # If the current voter is dead (could happen if a Hunter shot during voting, for example), skip them
        if not votant_actuel.is_alive:
            print(f"DEBUG: Vote - {votant_actuel.name} est mort, skip leur vote.")
            self.delai_prochaine_action = pygame.time.get_ticks() + 50; # Short delay before checking next in sequence
            self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE; # Stay in this state to process the rest of the sequence
            return # Skip this voter's turn

        if votant_actuel.is_human:
            # If the next voter is human, prepare the UI for their vote selection
            self.preparer_action_humaine(votant_actuel, "Vote") # type_action "Vote"
            self.etat_jeu = ETAT_JOUR_VOTE_ATTENTE_HUMAIN; # STOP here, wait for human input (target selection)
            # The human's confirmed vote will be processed at the beginning of the *next* call to traiter_votant_suivant
            # after they click the Confirm button.
        else:
             # If the current voter is an IA player
             print(f"DEBUG: Vote IA - {votant_actuel.name} vote...");
             if hasattr(votant_actuel, 'ai_logic') and votant_actuel.ai_logic:
                  # The IA must implement decide_vote and return the target player or None (for white vote)
                  cible_ia = votant_actuel.ai_logic.decide_vote();
                  if cible_ia and cible_ia.is_alive: # Check if the chosen target is valid and still alive
                       self.votes_en_cours[cible_ia] = self.votes_en_cours.get(cible_ia, 0) + 1; # Register the IA vote
                       self.log_message_jeu(f"Vote de {votant_actuel.name} enregistré.", msg_type="action") # Log the IA vote
                       print(f"DEBUG: Vote IA - {votant_actuel.name} -> {cible_ia.name} enregistré.")
                  else:
                       self.log_message_jeu(f"{votant_actuel.name} (IA) vote blanc ou pour cible invalide/morte.", msg_type="info")
                       print(f"DEBUG: Vote IA - {votant_actuel.name} vote blanc ou cible invalide/morte.")
             else:
                  print(f"ERREUR: IA {votant_actuel.name} sans ai_logic. Ne peut pas voter.")
                  self.log_message_jeu(f"{votant_actuel.name} (IA) ne peut pas voter (logique IA manquante).", msg_type="error")

             # After the IA vote (or failed vote), plan the transition to process the next voter in sequence
             self.delai_prochaine_action = pygame.time.get_ticks() + 300; # Small delay between IA votes
             self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE; # Stay in this state to process the next voter


    def resoudre_vote(self):
        # This method is called once after all voters have had their turn (ETAT_JOUR_VOTE_RESOLUTION)
        if not self.jeu or self.jeu.game_over: return # Security

        self.log_message_jeu("\n--- Résultat du Vote ---", msg_type="info");
        lynche_joueur = None # Player who will be lynched (if any)

        # Filter votes to only include those for living players
        votes_vivants = {p: count for p, count in self.votes_en_cours.items() if p and p.is_alive}

        if not votes_vivants:
             self.log_message_jeu("Aucun vote valide exprimé sur des joueurs vivants.", msg_type="info")
        else:
            # Display vote counts for each living player who received votes
            # Get all living players who received at least one vote
            vivants_cibles_vote = sorted(votes_vivants.keys(), key=lambda p: p.name)

            # Also list living players who received 0 votes for completeness
            all_living_players_names = {p.name for p in self.jeu.get_alive_players()}
            voted_for_names = {p.name for p in votes_vivants.keys()}
            zero_vote_players_names = all_living_players_names - voted_for_names

            all_players_to_list = sorted(vivants_cibles_vote + [p for p in self.jeu.get_alive_players() if p.name in zero_vote_players_names], key=lambda p: p.name)


            for p in all_players_to_list:
                 self.log_message_jeu(f"- {p.name}: {votes_vivants.get(p, 0)} voix", msg_type="info")


            # Find the maximum number of votes among living players
            max_votes = 0;
            if votes_vivants: # Ensure there are votes for living players
                max_votes = max(votes_vivants.values())

            # Find living players who received the maximum number of votes
            candidats = [p for p, count in votes_vivants.items() if count == max_votes]


            if max_votes == 0:
                 self.log_message_jeu("Aucun joueur vivant n'a reçu de vote.", msg_type="info")
                 # In case of 0 votes for everyone, no one is lynched. lynche_joueur remains None.
            elif len(candidats) > 1:
                 self.log_message_jeu(f"Égalité des votes entre: {', '.join([p.name for p in candidats])}", msg_type="info");
                 # In case of tie, randomly select one player from tied candidates to be lynched
                 lynche_joueur = random.choice(candidats);
                 self.log_message_jeu(f"Tirage au sort : {lynche_joueur.name} est lynché(e) !", msg_type="important");
            else:
                 # Only one player with the maximum votes
                 lynche_joueur = candidats[0];
                 self.log_message_jeu(f"{lynche_joueur.name} est lynché(e) avec {max_votes} voix !", msg_type="important");

        # --- Execute the Lynching ---
        # If a player was determined to be lynched AND they are still alive
        if lynche_joueur and lynche_joueur.is_alive:
             joueur_mort = lynche_joueur;
             joueur_mort.die(); # Call the player's die method
             self.log_message_jeu(f"Son rôle était : {joueur_mort.role.name}", msg_type="info");
             self.organiser_cartes_joueurs(); # Update the visual display after death

             self.jeu.check_victory_condition() # Check victory conditions after death by lynch

             # If the lynched player is a Hunter
             if joueur_mort.role and joueur_mort.role.name == "Chasseur": # Check if role exists
                  # Add this dead Hunter to the sequence of Hunter actions
                  # They act immediately after being lynched
                  self.chasseurs_morts_sequence = [joueur_mort]; # Start a new sequence with this Hunter
                  # The callback after this Hunter sequence will be to check victory and then potentially start the night
                  self.callback_apres_chasseur = self.verifier_victoire_et_lancer_nuit;
                  self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; # Transition to Hunter sequence state
                  self.delai_prochaine_action = pygame.time.get_ticks() + 1000 # Delay before the Hunter's action
             else:
                  # If the lynched player is not a Hunter, proceed directly to checking victory and then potentially starting the night
                  self.verifier_victoire_et_lancer_nuit()
        else:
             # If no player was lynched (equality, 0 votes, or target already dead)
             self.log_message_jeu("Personne n'est éliminé aujourd'hui.", msg_type="info");
             # Proceed directly to checking victory and then potentially starting the night
             self.verifier_victoire_et_lancer_nuit()


    def verifier_victoire_et_lancer_nuit(self):
        # Called after vote resolution or after the last hunter action resulting from a lynch.
        if self.jeu and self.jeu.check_victory_condition():
            self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie()
        else:
            # Only launch the night phase if the game is not over
            self.etat_jeu = ETAT_NUIT_SEQUENCE; # Transition to Night Sequence state
            self.lancer_phase_nuit()


    def preparer_fin_partie(self):
        if not self.jeu or self.jeu.game_over: return # Security
        self.log_message_jeu("\n--- PARTIE TERMINEE ---", msg_type="important");
        self.jeu.game_over = True # Ensure flag is True

        # Determine winning team(s)
        # check_victory_condition updates self.jeu.winning_team
        self.jeu.check_victory_condition();
        # Handle the case where winning_team might be a list of teams or a single team string/object
        # Assuming winning_team is set to the name of the winning team(s) (e.g., "Villageois", "Loups-Garous", "Match nul")
        gagnant = self.jeu.winning_team if self.jeu.winning_team else "Indéterminé";
        self.log_message_jeu(f"Équipe(s) gagnante(s) : {gagnant}", msg_type="important")

        self.log_message_jeu("\nRôles finaux de tous les joueurs :", msg_type="info");
        # Display all roles and statuses at the end
        for p in self.jeu.players:
            statut = "Vivant" if p.is_alive else "Mort";
            role_nom = p.role.name if p.role else "Inconnu"; # Handle case where role might be None
            self.log_message_jeu(f"- {p.name}: {role_nom} ({statut})", msg_type="info")

        # Activer les boutons de fin de partie et désactiver les autres
        self.boutons_jeu["nouvelle_partie"].actif = True;
        self.boutons_jeu["quitter"].actif = True;
        # Désactiver tous les boutons d'action de jeu
        self.boutons_jeu["confirmer"].actif = False;
        self.boutons_jeu["passer"].actif = False;
        self.boutons_jeu["sorciere_save"].actif = False;
        self.boutons_jeu["sorciere_kill"].actif = False;
        self.boutons_jeu["passer_au_vote"].actif = False;


        # Display all roles on visual cards
        for carte in self.cartes_joueurs_visuels: carte.afficher_role = True
        self.organiser_cartes_joueurs() # Refresh display to ensure roles are shown

    def reinitialiser_jeu(self):
        # Reset game state variables
        self.jeu = None; # Delete game instance
        self.etat_jeu = ETAT_CONFIG; # Return to config screen
        self.log_messages_jeu = []; # Clear logs
        self.cartes_joueurs_visuels = [] # Clear visual cards
        # Reset other state variables
        self.acteur_humain_actuel = None; self.action_humaine_attendue = None; self.cibles_possibles_action = []; self.cible_humaine_selectionnee = None
        self.delai_prochaine_action = 0; self.sequence_nuit_restante = []; self.votants_restants = []; self.votes_en_cours = {}
        self.chasseurs_morts_sequence = []; self.callback_apres_chasseur = None
        self._human_vote_target = None; self._human_vote_target_actor_name = None; self._sorciere_action_type = None;

        # Reset config values to default
        self.config_total_joueurs = 5
        self.config_num_humains = 1
        self.config_message_erreur = ""
        self.validate_config() # Re-validate to set button state

        # Activer uniquement les widgets de config (le bouton démarrer sera géré par validate_config)
        for widget in self.widgets_config.values():
             if isinstance(widget, Bouton): widget.actif = True # Réactiver tous les boutons de config
        # Désactiver les boutons de jeu
        for btn in self.boutons_jeu.values(): btn.actif = False

        self.log_message_jeu("Retour configuration. Choisissez le nombre de joueurs.", msg_type="info") # Log for console and config screen

# --- Fonction Helper pour déterminer les rôles ---
def get_roles_for_player_count(total_joueurs):
    """
    Retourne un dictionnaire de configuration des rôles basé sur le nombre total de joueurs.
    C'est ici qu'on définit l'équilibrage du jeu.
    Retourne None si le nombre de joueurs n'est pas géré.
    """
    if total_joueurs < MIN_PLAYERS: return None

    # Exemples de configurations (à adapter/compléter selon les règles souhaitées)
    if total_joueurs == 3: # 1 LG, 1 Voyante, 1 Villager
        return {'Loup-Garou': 1, 'Voyante': 1, 'Villageois': 1}
    elif total_joueurs == 4: # 1 LG, 1 Voyante, 1 Sorciere, 1 Villager
        return {'Loup-Garou': 1, 'Voyante': 1, 'Sorcière': 1, 'Villageois': 1}
    elif total_joueurs == 5: # 1 LG, 1 Voyante, 1 Sorciere, 2 Villagers
        return {'Loup-Garou': 1, 'Voyante': 1, 'Sorcière': 1, 'Villageois': 2}
    elif total_joueurs == 6: # 2 LG, 1 Voyante, 1 Sorciere, 2 Villagers
        return {'Loup-Garou': 2, 'Voyante': 1, 'Sorcière': 1, 'Villageois': 2}
    elif total_joueurs == 7: # 2 LG, 1 Voyante, 1 Sorciere, 1 Chasseur, 2 Villagers
        return {'Loup-Garou': 2, 'Voyante': 1, 'Sorcière': 1, 'Chasseur': 1, 'Villageois': 2}
    elif total_joueurs == 8: # 2 LG, 1 Voyante, 1 Sorciere, 1 Chasseur, 3 Villagers
        return {'Loup-Garou': 2, 'Voyante': 1, 'Sorcière': 1, 'Chasseur': 1, 'Villageois': 3}
    # Ajouter d'autres configurations pour plus de joueurs...
    elif total_joueurs <= MAX_PLAYERS:
         # Configuration générique simple pour plus de joueurs (ex: ~1/3 loups)
         num_loups = max(1, total_joueurs // 3)
         num_voyante = 1 if total_joueurs >= 3 else 0
         num_sorciere = 1 if total_joueurs >= 4 else 0
         num_chasseur = 1 if total_joueurs >= 7 else 0
         num_speciaux = num_loups + num_voyante + num_sorciere + num_chasseur
         num_villageois = total_joueurs - num_speciaux
         if num_villageois < 0: num_villageois = 0 # S'assurer qu'on n'a pas de négatif

         config = {'Loup-Garou': num_loups}
         if num_voyante > 0: config['Voyante'] = num_voyante
         if num_sorciere > 0: config['Sorcière'] = num_sorciere
         if num_chasseur > 0: config['Chasseur'] = num_chasseur
         if num_villageois > 0: config['Villageois'] = num_villageois

         # Ajuster si le compte n'est pas bon (devrait pas arriver avec ce calcul)
         current_total = sum(config.values())
         if current_total != total_joueurs:
              print(f"WARN: Ajustement auto config rôles pour {total_joueurs}J. Diff: {total_joueurs - current_total}")
              config['Villageois'] = max(0, config.get('Villageois', 0) + (total_joueurs - current_total))
              if sum(config.values()) != total_joueurs:
                   print(f"ERREUR: Impossible d'ajuster la config des rôles pour {total_joueurs} joueurs.")
                   return None # Échec de la configuration

         return config

    else:
        return None # Nombre de joueurs trop élevé ou non géré


# --- Lancement ---
if __name__ == '__main__':
    app = GameApp()
    if app.en_cours: # Check if initialization was successful
        app.run()