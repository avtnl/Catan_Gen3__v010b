"""
Handles button rendering for human player interactions in the Catan game.

This module defines the GUIHumanPlayer class, responsible for rendering buttons
for human player actions (e.g., buying settlements, rolling dice) within a panel.
Buttons are conditionally displayed based on game phase, human player status, and modes.

Classes:
    GUIHumanPlayer: Manages button rendering for human player interactions.

Dependencies:
    - pygame: For rendering graphics.
    - gui.gui_constants: For fonts, colors, images, and positions.
    - core.game: For game state.
    - core.player: For player attributes.
    - core.constants: For logging and configuration constants.
"""
import pygame
from core import game
from gui.gui_constants import WIN, COLORS, Font, IMAGES
from core.game import Game
from core.player import ResourceCard
from core.constants import FNFREQ, MG, FILENAME_FREQ, FILENAME_MG, HP_ID, HUMAN_PLAYER, FILENAME_SPEC2

class GUIHumanPlayer:
    """Manages button rendering for human player interactions."""
    
    def __init__(self) -> None:
        """Initialize the GUIHumanPlayer with an empty state.

        Args:
            None
        """
        pass

    def text_buy(self, game: Game, active: bool) -> None:
        """Render 'Buy -->' text with active or inactive styling.

        Args:
            game: The game instance.
            active: Whether the text is active (black) or inactive (gray).
        """
        font = Font.LARGE.value["regular"]
        color = COLORS["BLACK"] if active else COLORS["GRAY"]
        game.gui.set_button("text_buy", active)
        text = font.render("Buy -->", True, color)
        WIN.blit(text, (25, 262))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | text_buy | Active: {active}\n")

    def text_trade(self, game: Game, active: bool) -> None:
        """Render 'Trade -->' text with active or inactive styling.

        Args:
            game: The game instance.
            active: Whether the text is active (black) or inactive (gray).
        """
        font = Font.LARGE.value["regular"]
        color = COLORS["BLACK"] if active else COLORS["GRAY"]
        game.gui.set_button("text_trade", active)
        text = font.render("Trade -->", True, color)
        WIN.blit(text, (25, 322))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | text_trade | Active: {active}\n")

    def button_buy_city(self, game: Game, active: bool) -> None:
        """Render 'Buy City' button with image and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, CITY_GREEN) or inactive (gray border, CITY_DGRAY).
        """
        game.gui.set_button("buy_city", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        image_key = "CITY_GREEN" if active else "CITY_DGRAY"
        pygame.draw.rect(WIN, border_color, [140, 260, 40, 40], 2)
        image = IMAGES.get(image_key, {}).get("30x30")
        if image is not None:
            WIN.blit(image, (145, 265))
        else:
            if MG:
                with open(FILENAME_MG, "a") as f:
                    f.write(f"gui_human_player.py | button_buy_city | Missing image: {image_key}\n")
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_buy_city | Active: {active}\n")

    def button_buy_settlement(self, game: Game, active: bool) -> None:
        """Render 'Buy Settlement' button with image and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, SETTLEMENT_GREEN) or inactive (gray border, SETTLEMENT_DGRAY).
        """
        game.gui.set_button("buy_settlement", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        image_key = "SETTLEMENT_GREEN" if active else "SETTLEMENT_DGRAY"
        pygame.draw.rect(WIN, border_color, [190, 260, 40, 40], 2)
        image = IMAGES.get(image_key, {}).get("30x30")
        if image is not None:
            WIN.blit(image, (195, 265))
        else:
            if MG:
                with open(FILENAME_MG, "a") as f:
                    f.write(f"gui_human_player.py | button_buy_settlement | Missing image: {image_key}\n")
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_buy_settlement | Active: {active}\n")

    def button_buy_road(self, game: Game, active: bool) -> None:
        """Render 'Buy Road' button with image and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, ROAD_GREEN) or inactive (gray border, ROAD_DGRAY).
        """
        game.gui.set_button("buy_road", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        image_key = "ROAD_GREEN" if active else "ROAD_DGRAY"
        pygame.draw.rect(WIN, border_color, [240, 260, 40, 40], 2)
        image = IMAGES.get(image_key, {}).get("30x30")
        if image is not None:
            WIN.blit(image, (245, 265))
        else:
            if MG:
                with open(FILENAME_MG, "a") as f:
                    f.write(f"gui_human_player.py | button_buy_road | Missing image: {image_key}\n")
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_buy_road | Active: {active}\n")

    def button_buy_dcard(self, game: Game, active: bool) -> None:
        """Render 'Buy DCard' button with image and border, checking resource availability.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, DCARD_GREEN) or inactive (gray border, DCARD_DGRAY), modified by resource availability.
        """
        human_player = game.players[game.turn - 1]
        resources = [
            human_player.rcards.get(ResourceCard.WHEAT, 0),
            human_player.rcards.get(ResourceCard.ORE, 0),
            human_player.rcards.get(ResourceCard.WOOL, 0)
        ]
        can_buy = (resources[0] >= 1 and resources[1] >= 1 and resources[2] >= 1 and len(game.dcards_stack) > 0)
        game.gui.set_button("buy_dcard", active and can_buy)
        border_color = COLORS["GREEN"] if active and can_buy else COLORS["GRAY"]
        image_key = "DCARD_GREEN" if active and can_buy else "DCARD_DGRAY"
        pygame.draw.rect(WIN, border_color, [290, 260, 40, 40], 2)
        image = IMAGES.get(image_key, {}).get("30x30")
        if image is not None:
            WIN.blit(image, (295, 265))
        else:
            if MG:
                with open(FILENAME_MG, "a") as f:
                    f.write(f"gui_human_player.py | button_buy_dcard | Missing image: {image_key}\n")
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_buy_dcard | Active: {active and can_buy}\n")

    def button_twp(self, game: Game, active: bool) -> None:
        """Render 'Trade w/ Player' button with text and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, white text) or inactive (gray border, gray text).
        """
        game.gui.set_button("twp", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        text_color = COLORS["WHITE"] if active else COLORS["GRAY"]
        pygame.draw.rect(WIN, border_color, [200, 320, 60, 40], 2)
        text = Font.LARGE.value["regular"].render("TwP", True, text_color)
        WIN.blit(text, (205, 322))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_twp | Active: {active}\n")

    def button_twb(self, game: Game, active: bool) -> None:
        """Render 'Trade w/ Bank' button with text and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, white text) or inactive (gray border, gray text).
        """
        game.gui.set_button("twb", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        text_color = COLORS["WHITE"] if active else COLORS["GRAY"]
        pygame.draw.rect(WIN, border_color, [270, 320, 60, 40], 2)
        text = Font.LARGE.value["regular"].render("TwB", True, text_color)
        WIN.blit(text, (275, 322))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_twb | Active: {active}\n")

    def button_roll_dices(self, game: Game, active: bool) -> None:
        """Render 'Roll Dices' button with text and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, white text) or inactive (gray border, gray text).
        """
        game.gui.set_button("roll_dices", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        text_color = COLORS["WHITE"] if active else COLORS["GRAY"]
        pygame.draw.rect(WIN, border_color, [200, 400, 130, 40], 2)
        text = Font.LARGE.value["regular"].render("Roll Dices", True, text_color)
        WIN.blit(text, (205, 402))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_roll_dices | Active: {active}\n")

    def button_end_turn(self, game: Game, active: bool) -> None:
        """Render 'End Turn' button with text and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, white text) or inactive (gray border, gray text).
        """
        game.gui.set_button("end_turn", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        text_color = COLORS["WHITE"] if active else COLORS["GRAY"]
        pygame.draw.rect(WIN, border_color, [200, 470, 130, 40], 2)
        text = Font.LARGE.value["regular"].render("End Turn", True, text_color)
        WIN.blit(text, (205, 472))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_end_turn | Active: {active}\n")

    def button_cancel(self, game: Game, active: bool) -> None:
        """Render 'Cancel' button with text and border.

        Args:
            game: The game instance.
            active: Whether the button is active (green border, white text) or inactive (gray border, gray text).
        """
        game.gui.set_button("cancel", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        text_color = COLORS["WHITE"] if active else COLORS["GRAY"]
        pygame.draw.rect(WIN, border_color, [200, 470, 130, 40], 2)
        text = Font.LARGE.value["regular"].render("Cancel", True, text_color)
        WIN.blit(text, (205, 472))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_cancel | Active: {active}\n")

    def button_next_turn2(self, game: Game, active: bool) -> None:
        """Render 'Play' button with text and border

        Args:
            game: The game instance.
            active: Whether the button is active (green border, white text) or inactive (gray border, gray text).
        """        
        game.gui.set_button("next_turn2", active)
        border_color = COLORS["GREEN"] if active else COLORS["GRAY"]
        text_color = COLORS["WHITE"] if active else COLORS["GRAY"]
        pygame.draw.rect(WIN, border_color, [20, 470, 130, 40], 2)
        text = Font.LARGE.value["regular"].render("Play", True, text_color)
        WIN.blit(text, (25, 472))
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | button_next_turn2 | Active: {active}\n")

        # Optional debug (you can delete later)
        ### print(f"DEBUG: button_next_turn2 | active={active} | registered={game.gui.check_button('next_turn2')}")

    def show_buttons_HP(self, game: Game, analysis_tf: bool = False) -> None:
        """Render buttons for human player actions based on game phase and status.

        Args:
            game: The game instance containing phase and player data.
            analysis_tf: Whether analysis mode is active (True) or not (False, default).
        """
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"{game.sequence_number} | {game.state} | gui_human_player.py | show_buttons_HP\n")
       
        # Draw button panel with black border
        pygame.draw.rect(WIN, COLORS["BLACK"], [10, 250, 330, 270], 2)
 
        # Helper functions
        def log_spec2(nr: int, txt: str) -> None:
            """Log button modes and states to FILENAME_SPEC2.

            Args:
                nr: Log entry number for identification.
                txt: Descriptive text for the log entry.
            """
            with open(FILENAME_SPEC2, "a") as f:
                f.write(f"{nr} {txt}\n")
                for mode in game.gui.modes:
                    f.write(f"{mode.name} {mode.true_false}\n")
                game.gui.write_queues()
       
        def get_hp_sequence_hp(game: Game) -> list:
            """Return the sequence of turns for the human player.

            Args:
                game: The game instance.

            Returns:
                list: List of human player turn IDs (e.g., [HP_ID]).
            """
            return [HP_ID] # Assume HP_ID is the human player's turn
       
        def check_modes1() -> bool:
            """Check if any button is set to display.

            Args:
                None

            Returns:
                bool: True if any button is set to display, False otherwise.
            """
            for button in game.gui.buttons:
                if button.display_yn:
                    return True
            return False
       
        def check_modes2() -> bool:
            """Check if specific modes are active.

            Args:
                None

            Returns:
                bool: True if modes like Show_availableintersectionss or Show_available_roads are active, False otherwise.
            """
            return (game.gui.check_mode("Show_availableintersectionss") or
                    game.gui.check_mode("Show_available_roads") or
                    game.gui.check_mode("TwP_OpponentFoundAndSelected"))

        # ────────────────────────────────────────────────
        # Main logic – tightened for initial placement
        # ────────────────────────────────────────────────
        if game.phase == "InitialPlacement" and not analysis_tf:
            self.text_buy(game, False)
            self.text_trade(game, False)
            self.button_buy_city(game, False)
            self.button_buy_settlement(game, False)
            self.button_buy_road(game, False)
            self.button_buy_dcard(game, False)
            self.button_twp(game, False)
            self.button_twb(game, False)
            self.button_end_turn(game, False)
            # self.button_cancel(game, False)  # deliberately not shown – Option B

            hp_sequence = get_hp_sequence_hp(game)

            is_placing = game.gui.human_guidance.is_placing() if hasattr(game.gui, 'human_guidance') else False

            if is_placing:
                # During active settlement/road placement → minimal UI, Play disabled
                self.button_roll_dices(game, False)
                self.button_next_turn2(game, False)          # <--- enforced disabled
            else:
                # Not placing → normal initial placement turn logic
                if not HUMAN_PLAYER:
                    self.button_roll_dices(game, False)
                    self.button_next_turn2(game, True)
                    self.button_end_turn(game, False)
                else:
                    if (game.round == -2 and game.turn not in hp_sequence) or \
                       (game.round == -1 and 5 - game.turn not in hp_sequence):
                        self.button_roll_dices(game, False)
                        self.button_next_turn2(game, True)
                        self.button_end_turn(game, False)
                    elif (game.round == -2 and game.turn in hp_sequence) or \
                         (game.round == -1 and 5 - game.turn in hp_sequence):
                        log_spec2(254, "show_buttons_HP")
                        if not analysis_tf and not (game.gui.check_mode("Show_last_turn") or game.gui.check_mode("Turn_completed")):
                            self.button_roll_dices(game, False)
                            self.button_next_turn2(game, False)
                            self.button_end_turn(game, False)
                        elif game.gui.check_mode("Show_last_turn"):
                            self.button_roll_dices(game, False)
                            self.button_next_turn2(game, True)
                            self.button_end_turn(game, False)
                        elif game.gui.check_mode("Turn_completed"):
                            self.button_roll_dices(game, False)
                            self.button_next_turn2(game, False)
                            self.button_end_turn(game, True)

        elif game.phase == "Planning" and analysis_tf:
            self.button_next_turn2(game, True) # Analysis button not fully implemented
            log_spec2(260, "show_buttons_HP | Analysis mode")
       
        elif game.phase == "Execution" and not analysis_tf:
            # Green borders for playable development cards
            dc_positions = [633, 668, 703, 738, 773] # Aligned with scoreboard DC images
            for i, x_pos in enumerate(dc_positions):
                if game.players[game.turn - 1].dcard_summary[i][2] > 0:
                    pygame.draw.rect(WIN, COLORS["GREEN"], [x_pos, 543, 34, 34], 2)
           
            if check_modes2():
                self.text_buy(game, False)
                self.text_trade(game, False)
                self.button_buy_city(game, False)
                self.button_buy_settlement(game, False)
                self.button_buy_road(game, False)
                self.button_buy_dcard(game, False)
                self.button_twp(game, False)
                self.button_twb(game, False)
                self.button_roll_dices(game, False)
                self.button_next_turn2(game, False)
                self.button_end_turn(game, False)
                self.button_cancel(game, False)
            else:
                log_spec2(270, "show_buttons_HP")
                pygame.draw.rect(WIN, COLORS["BLACK"], [10, 250, 330, 270], 2)
                self.text_buy(game, False)
                self.text_trade(game, False)
                self.button_buy_city(game, False)
                self.button_buy_settlement(game, False)
                self.button_buy_road(game, False)
                self.button_buy_dcard(game, False)
                self.button_twp(game, False)
                self.button_twb(game, False)
               
                if not HUMAN_PLAYER or (HUMAN_PLAYER and game.turn not in hp_sequence):
                    self.button_roll_dices(game, False)
                    self.button_next_turn2(game, True)
                    self.button_end_turn(game, False)
                elif HUMAN_PLAYER and game.turn in hp_sequence:
                    if game.gui.check_mode("Cancel"):
                        self.button_end_turn(game, False)
                        self.button_cancel(game, True)
                        game.gui.set_mode_duo("Cancel", "Show_last_turn", "Human_Player-336")
                    elif game.gui.check_mode("Buy_completed"):
                        self.button_end_turn(game, True)
                        self.button_cancel(game, False)
                    elif game.gui.check_mode("Turn_completed") or game.gui.check_mode("Turn_completed*"):
                        game.gui.set_mode_duo("Turn_completed", "Show_last_turn", "Human_Player-343")
                        game.gui.set_mode_duo("Turn_completed*", "Show_last_turn", "Human_Player-350")
                        self.button_roll_dices(game, False)
                        self.button_next_turn2(game, True)
                        self.button_end_turn(game, False)
                        self.button_cancel(game, False)
                    elif game.gui.check_mode("Show_last_turn") or game.gui.check_button("next_turn2"):
                        self.button_roll_dices(game, True)
                        self.button_next_turn2(game, False)
                        self.button_end_turn(game, False)
                        self.button_cancel(game, False)
       
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_human_player.py | show_buttons_HP | Rendered buttons for phase: {game.phase}, analysis_tf: {analysis_tf}\n")

        pygame.display.update()