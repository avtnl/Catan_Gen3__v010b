"""
v010
Handles mouse click events for the Catan game.

This module defines the EventHandler class, responsible for processing mouse clicks,
including human placement of settlements/roads and confirmation (OKY/OKN) during
InitialPlacement phase.

Dependencies:
    - pygame: For event handling and sound.
    - gui.gui_constants: For button positions and sounds.
    - gui.gui_guidance: For human guidance and confirmation.
    - gui.gui_human_player: For rendering / activating / deactivating human buttons.
    - core.game: For game state.
    - core.constants: For logging and configuration.
"""

import pygame
from typing import Tuple

from gui.gui_constants import SOUNDS
from gui.gui_guidance import PlacementState
from gui.gui_human_player import GUIHumanPlayer
from core.game import Game
from core.constants import FNFREQ, FILENAME_FREQ


class EventHandler:
    """Manages mouse click events for the Catan game."""

    def __init__(self) -> None:
        """Initialize the EventHandler."""
        pass

    def handle_click(self, pos: Tuple[int, int], game: Game) -> bool:
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(
                    f"{game.id} | {game.state} | event_handler.py | "
                    f"handle_click | pos={pos}\n"
                )

        guidance = game.gui.human_guidance

        # ────────────────────────────────────────────────
        # 1. Confirmation clicks first: OKY / OKN
        # ────────────────────────────────────────────────
        if guidance.state in (
            PlacementState.SETTLEMENT_SELECTED,
            PlacementState.ROAD_SELECTED,
        ):
            conf = game.gui.handle_confirmation_click(pos)

            if conf:
                print(f"Confirmation clicked: {conf}")
                guidance.on_confirmation(conf)
                return True

            # Clicked during confirmation but not on OKY / OKN.
            pygame.mixer.Sound.play(SOUNDS["ERROR"])
            return True

        # ────────────────────────────────────────────────
        # 2. PLAY / next_turn2 button during InitialPlacement
        # ────────────────────────────────────────────────
        PLAY_RECT = pygame.Rect(20, 470, 130, 40)

        if game.phase == "InitialPlacement" and PLAY_RECT.collidepoint(pos):
            is_placing = guidance.state != PlacementState.IDLE
            button_active = game.gui.check_button("next_turn2")

            if is_placing:
                print("PLAY clicked while still placing → rejected")
                pygame.mixer.Sound.play(SOUNDS["ERROR"])
                return True

            if button_active:
                print("PLAY clicked → advancing turn")
                pygame.mixer.Sound.play(SOUNDS["BUTTON"])

                # Immediately deactivate the PLAY button before AI / Markov output starts.
                GUIHumanPlayer.button_next_turn2(game.gui, game, active=False)
                pygame.display.update()

                print("event_handler calling InitialPlacement.advance_turn")
                game.ip.advance_turn()
                return True

            # PLAY area was clicked, but the button is inactive.
            pygame.mixer.Sound.play(SOUNDS["ERROR"])
            return True

        # ────────────────────────────────────────────────
        # 3. Board clicks during InitialPlacement
        # ────────────────────────────────────────────────
        if game.phase == "InitialPlacement":
            if game.ip.handle_click(pos):
                return True

            if guidance.state != PlacementState.IDLE:
                if guidance.on_board_click(pos):
                    return True

        return False