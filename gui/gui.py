"""
Handles general GUI functionality for the Catan game.
Now includes HumanGuidance for settlement/road placement and confirmation.
"""
import pygame
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
from core import board
from gui.gui_constants import WIN, COLORS, Font, IMAGES, POSITIONS, BOARD_OFFSET
from gui.gui_guidance import HumanGuidance
from core.board import Board
from core.game import Game, Player
from core.constants import FNFREQ, FILENAME_FREQ, MG, FILENAME_MG, SAVE_PATH, ResourceCard

def convert_tile(tile_id: int) -> Optional[Tuple[int, int]]:
    """Convert a tile ID to its GUI midpoint coordinates."""
    coords = POSITIONS["tiles"].get(tile_id)
    if coords is None and MG:
        with open(FILENAME_MG, "a") as f:
            f.write(f"gui.py | convert_tile | Missing coordinates for tile ID: {tile_id}\n")
    return tuple(coords) if coords else None

class Button:
    """Represents a button with name, display state, and switch status."""
    def __init__(self, name: str, display_tf: bool):
        self.name = name
        self.display_tf = display_tf
        self.switched_tf = False

class GUI:
    """Manages button states, modes, board rendering, and human guidance."""
    def __init__(self, round_number: int, turn: int, game: 'Game'):  # Add game parameter with forward reference
        """Initialize the GUI with game round and turn."""
        if not pygame.font.get_init():
            pygame.font.init()
        Font.initialize_fonts()
        self.game = game  # Set the attribute here
        self.round = round_number
        self.turn = turn
        self.buttons: List[Button] = []
        self.modes: List[any] = []
        # Persistent queue for continuous subtle highlight of last placement
        self.animate_queue_elements: List[Tuple[Tuple[int,int], Tuple[int,int,int], int, str]] = []

        # Human guidance system
        self.human_guidance = HumanGuidance(self)

        # Pre-register all buttons so they exist from the start
        for name in ["next_turn2", "roll_dices", "end_turn", "buy_city", "buy_settlement",
                     "buy_road", "buy_dcard", "twp", "twb", "text_buy", "text_trade", "cancel"]:
            self.set_button(name, False)

    def print_queues(self) -> None:
        """Log the contents of animation queues for debugging."""
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui.py | print_queues | Elements: {self.animate_queue_elements}\n")

    def _animate_elements(self, board: Board) -> None:
        """Unified animation for settlements, cities, roads and tiles using quarter-circle reveal."""
        if not self.animate_queue_elements:
            return

        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"gui.py | _animate_elements | Queue size: {len(self.animate_queue_elements)}\n")

        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui.py | _animate_elements | Animating {len(self.animate_queue_elements)} elements\n")

        for step in range(4):
            quadrants = [
                (True,  True,  True,  False),   # 0: top-right
                (True,  False, True,  True),    # 1: top-left
                (False, True,  True,  True),    # 2: bottom-right
                (True,  True,  False, True),    # 3: bottom-left
            ]

            draw_tr, draw_tl, draw_br, draw_bl = quadrants[step]

            for center, color, diameter, kind in self.animate_queue_elements:
                # For tiles we usually use width=3, others width=2 → you can parameterize later if needed
                width = 3 if kind == "tile" else 2

                # Clear previous animation frame (use background-appropriate color)
                clear_color = COLORS["WHITE"] if color == COLORS["BLUE"] else COLORS["BLUE"]
                pygame.draw.circle(WIN, clear_color, center, diameter, width,
                                draw_top_right=True, draw_top_left=True,
                                draw_bottom_right=True, draw_bottom_left=True)

                # Draw current quadrant
                pygame.draw.circle(WIN, color, center, diameter, width,
                                draw_top_right=draw_tr, draw_top_left=draw_tl,
                                draw_bottom_right=draw_br, draw_bottom_left=draw_bl)

    def animate_continuous(self):
        """Very conservative continuous animation.
        - Disabled completely during InitialPlacement
        - Only animates newest-looking items
        - Auto-clears queue when suspicious
        """
        if not self.animate_queue_elements:
            return

        # Disable pulsing entirely during setup phase (cleanest look)
        # if self.game.phase == "InitialPlacement":
        #     return

        # Quick check: does queue look like it contains current game objects?
        has_valid = any(
            len(item) >= 4 and item[3] in ("settlement", "city", "road", "tile")
            for item in self.animate_queue_elements
        )

        if not has_valid:
            self.animate_queue_elements.clear()
            print("Cleared animate_queue_elements due to invalid contents")
            return

        quadrants = [
            (True,  True,  True,  False),
            (True,  False, True,  True),
            (False, True,  True,  True),
            (True,  True,  False, True),
        ]

        # Normal smooth quadrant animation
        # step = (pygame.time.get_ticks() // 80) % 4
        for step in range(4):

            draw_tr, draw_tl, draw_br, draw_bl = quadrants[step]

            for center, color, diameter, kind in self.animate_queue_elements:
                # For tiles we usually use width=3, others width=2 → you can parameterize later if needed
                width = 3 if kind == "tile" else 2

                # Clear previous animation frame (use background-appropriate color)
                clear_color = COLORS["WHITE"] if color == COLORS["BLUE"] else COLORS["BLUE"]
                pygame.draw.circle(WIN, clear_color, center, diameter, width,
                                draw_top_right=True, draw_top_left=True,
                                draw_bottom_right=True, draw_bottom_left=True)

                # Draw current quadrant
                pygame.draw.circle(WIN, color, center, diameter, width,
                                draw_top_right=draw_tr, draw_top_left=draw_tl,
                                draw_bottom_right=draw_br, draw_bottom_left=draw_bl)

            pygame.display.flip() 
            pygame.time.delay(100)

    def set_button(self, name: str, display_tf: bool) -> None:
        """Set button state. Creates the button if it does not exist yet."""

        if FNFREQ=="Y":
            f= open(FILENAME_Freq,"a")
            f.write("gui.py | set_button"+"\n")
            f.close()

        found=False
        for button in self.buttons:
            if button.name == name:
                if button.display_tf==display_tf:
                    button.switched_tf=False
                else:
                    button.switched_tf=True
                button.display_tf=display_tf
                found=True
        if found == False:
            self.buttons.append(Button(name, display_tf))

    def check_button(self, name: str) -> bool:
        """Check if a button is set to display."""
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write("gui.py | check_button\n")
        for button in self.buttons:
            if button.name == name:
                return button.display_tf
        return False

    def check_mode(self, name: str) -> bool:
        """Check if a mode is active (stub implementation)."""
        return False

    def set_mode_duo(self, mode1: str, mode2: str, source: str) -> None:
        """Set two modes simultaneously (stub implementation)."""
        pass

    def display_fresh_board(self, board: Board, scoreboard_tf: bool = False) -> None:
        """Render the initial empty board and optionally the scoreboard."""
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write("gui.py | display_fresh_board\n")
        WIN.fill(COLORS["LGRAY"], (180 + BOARD_OFFSET[0], 25, 480, 475))
        self._draw_hexagon_lines(board)
        self._draw_tiles(board)
        self._draw_tile_values(board)
        self._draw_ports(board)
        self._draw_intersections(board)
        if scoreboard_tf:
            self.display_scoreboard()
        pygame.display.update()
        self.draw_guidance()

    def _draw_hexagon_lines(self, board: Board) -> None:
        """Draw lines connecting intersections to form hexagons."""
        if not pygame.display.get_init():
            return
        for road in board.roads:
            if road and road.id:
                start_id, end_id = road.id
                start_pos = POSITIONS["intersections"].get(start_id, None)
                end_pos = POSITIONS["intersections"].get(end_id, None)
                if start_pos is None or end_pos is None:
                    if MG:
                        with open(FILENAME_MG, "a") as f:
                            if start_pos is None:
                                f.write(f"gui.py | _draw_hexagon_lines | No coordinates for intersection ID: {start_id}\n")
                            if end_pos is None:
                                f.write(f"gui.py | _draw_hexagon_lines | No coordinates for intersection ID: {end_id}\n")
                    continue
                pygame.draw.line(WIN, COLORS["BLACK"], start_pos, end_pos, 2)

    def _draw_tiles(self, board: Board) -> None:
        """Draw hexagonal tiles on the board."""
        rendered_tiles = []
        for tile in board.tiles:
            if tile and tile.id in POSITIONS["tiles"]:
                pos = convert_tile(tile.id)
                if pos is None:
                    if MG:
                        with open(FILENAME_MG, "a") as f:
                            f.write(f"gui.py | _draw_tiles | No coordinates for tile ID: {tile.id}\n")
                    continue
                image_key = {
                    "Field": "FIELD",
                    "Mountain": "MOUNTAIN",
                    "Forest": "FOREST",
                    "Hill": "HILL",
                    "Pasture": "PASTURE",
                    "Desert": "DESERT",
                    "Sea": "SEA"
                }.get(tile.type, "SEA")
                image = IMAGES[image_key]["40x40"] if image_key in ["FIELD", "MOUNTAIN", "FOREST", "HILL", "PASTURE"] else IMAGES[image_key]["default"]
                if image is not None:
                    WIN.blit(image, (pos[0] - 20, pos[1] - 20))
                    rendered_tiles.append(tile.id)
                else:
                    if MG:
                        with open(FILENAME_MG, "a") as f:
                            f.write(f"gui.py | _draw_tiles | Failed to render tile ID: {tile.id}, Type: {tile.type}, Pos: {pos}\n")
            else:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui.py | _draw_tiles | Skipped tile ID: {tile.id if tile else None}, Pos: {convert_tile(tile.id) if tile else None}\n")
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui.py | _draw_tiles | Rendered tile IDs: {rendered_tiles}\n")

    def _draw_tile_values(self, board: Board) -> None:
        """Draw number chits on tiles."""
        font = Font.LARGE.value["regular"]
        for tile in board.tiles:
            if tile and tile.id in POSITIONS["tiles"] and tile.value != 0:
                pos = convert_tile(tile.id)
                if pos is None:
                    continue
                color = COLORS["RED"] if tile.value in [6, 8] else COLORS["BLACK"]
                text = font.render(str(tile.value), True, color)
                WIN.blit(text, (pos[0] - 8, pos[1] + 15))

    def _draw_ports(self, board: Board) -> None:
        """Draw port icons, circles, and lines on the board."""
        font = Font.SMALL.value["regular"]
        port_intersection_ids = set()
        for port_pair in board.INTERSECTIONS_ARE_PORT:
            port_intersection_ids.update(port_pair)
        for intersection_id in port_intersection_ids:
            if intersection_id in board.INTERSECTION_IN_WATER or board.intersections[intersection_id] is None:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui.py | _draw_ports | Skipping None or water intersection ID: {intersection_id}\n")
                continue
            pos = POSITIONS["intersections"].get(intersection_id, None)
            if pos is None:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui.py | _draw_ports | No coordinates for intersection ID: {intersection_id}\n")
                continue
            pygame.draw.circle(WIN, COLORS["BLACK"], pos, 5, 0)
        for port_pair in board.INTERSECTIONS_ARE_PORT:
            first_intersection_id = port_pair[0]
            second_intersection_id = port_pair[1]
            if (first_intersection_id in board.INTERSECTION_IN_WATER or 
                second_intersection_id in board.INTERSECTION_IN_WATER or
                board.intersections[first_intersection_id] is None or
                board.intersections[second_intersection_id] is None):
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui.py | _draw_ports | Skipping port pair {port_pair} due to None or water intersections\n")
                continue
            first_intersection = next((i for i in board.intersections if i is not None and i.id == first_intersection_id), None)
            if not first_intersection:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui.py | _draw_ports | No valid intersection found for ID: {first_intersection_id}\n")
                continue
            sea_tile_id = None
            for tile in board.tiles:
                if tile and tile.type == "Sea":
                    corner_intersections = [corner.intersection for corner in tile.corners]
                    if first_intersection_id in corner_intersections and second_intersection_id in corner_intersections:
                        sea_tile_id = tile.id
                        break
            if sea_tile_id is None:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui.py | _draw_ports | No sea tile found for port pair: {port_pair}\n")
                continue
            pos = convert_tile(sea_tile_id)
            if pos is None:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui.py | _draw_ports | No coordinates for sea tile id: {sea_tile_id}\n")
                continue
            first_intersection_pos = POSITIONS["intersections"].get(first_intersection_id, None)
            second_intersection_pos = POSITIONS["intersections"].get(second_intersection_id, None)
            if first_intersection_pos:
                pygame.draw.line(WIN, COLORS["BLACK"], first_intersection_pos, pos, 2)
            if second_intersection_pos:
                pygame.draw.line(WIN, COLORS["BLACK"], second_intersection_pos, pos, 2)
            if first_intersection.port_type == "Blank":
                pygame.draw.rect(WIN, COLORS["WHITE"], [pos[0] - 10, pos[1] - 10, 20, 20])
                text = font.render(" ?", True, COLORS["BLACK"])
                WIN.blit(text, (pos[0] - 7, pos[1] - 8))
            elif first_intersection.port_type == "3:1":
                pygame.draw.rect(WIN, COLORS["WHITE"], [pos[0] - 10, pos[1] - 10, 20, 20])
                text = font.render("3:1", True, COLORS["BLACK"])
                WIN.blit(text, (pos[0] - 7, pos[1] - 8))
            else:
                image_key = {
                    "2:1 Wheat": "FIELD",
                    "2:1 Ore": "MOUNTAIN",
                    "2:1 Wood": "FOREST",
                    "2:1 Brick": "HILL",
                    "2:1 Wool": "PASTURE"
                }.get(first_intersection.port_type)
                if image_key:
                    image = IMAGES[image_key]["20x20"]
                    if image is not None:
                        WIN.blit(image, (pos[0] - 10, pos[1] - 10))
                    else:
                        if MG:
                            with open(FILENAME_MG, "a") as f:
                                f.write(f"gui.py | _draw_ports | Missing image for port type: {first_intersection.port_type}, Tile ID: {sea_tile_id}\n")

    def _draw_intersections(self, board: Board) -> None:
        """Draw intersections (vertices) on the board with bold IDs."""
        font = Font.SMALL.value["bold"]
        offset_minus_3 = {4, 6, 8}
        offset_minus_6 = {59, 61, 63}
        for intersection in board.intersections:
            if intersection is None or intersection.id in board.INTERSECTION_IN_WATER:
                continue
            if intersection.id in POSITIONS["intersections"]:
                pos = POSITIONS["intersections"][intersection.id]
                text = font.render(str(intersection.id), True, COLORS["DGRAY"])
                y_offset = -16 if intersection.id in {14, 16, 18, 20, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 58, 60, 62, 64} else 2
                x_offset = -3 if intersection.id in offset_minus_3 else -6 if intersection.id in offset_minus_6 else 4
                WIN.blit(text, (pos[0] + x_offset, pos[1] + y_offset))

    def display_scoreboard(self) -> None:
        """Display the empty scoreboard (placeholder)."""
        pass

    def _occupy_settlement_in_gui(self, board: Board, intersection_id: int, color: str) -> None:
        pos = POSITIONS["intersections"].get(intersection_id)
        if not pos: return
        image = IMAGES.get(f"SETTLEMENT_{color.upper()}", {}).get("30x30")
        if image:
            WIN.blit(image, (pos[0] - 15, pos[1] - 15))

    def _occupy_road_in_gui(self, board: Board, road_id: Tuple[int, int], color: str) -> None:
        pos1 = POSITIONS["intersections"].get(road_id[0])
        pos2 = POSITIONS["intersections"].get(road_id[1])
        if pos1 and pos2:
            pygame.draw.line(WIN, COLORS[color.upper()], pos1, pos2, 5)

    def _occupy_city_in_gui(self, board: Board, intersection_id: int, color: str) -> None:
        pos = POSITIONS["intersections"].get(intersection_id)
        if not pos: return
        image = IMAGES.get(f"CITY_{color.upper()}", {}).get("30x30")
        if image:
            WIN.blit(image, (pos[0] - 15, pos[1] - 15))

    def draw_board_base(self, board: Board) -> None:
        """Static empty board only (tiles, lines, numbers, ports, intersection IDs)."""
        WIN.fill(COLORS["LGRAY"], (180 + BOARD_OFFSET[0], 25, 480, 475))
        self._draw_hexagon_lines(board)
        self._draw_tiles(board)
        self._draw_tile_values(board)
        self._draw_ports(board)
        self._draw_intersections(board)

    def draw_all_permanent_buildings(self, board: Board, block_visual: bool = False):
        """Draw EVERY currently placed road/settlement/city + blocked dots."""
        # Roads
        for road in board.roads:
            if road and road.occupied_tf:
                self._occupy_road_in_gui(board, road.id, road.color)  # simplified version below

        # Settlements & Cities
        for inter in board.intersections:
            if inter and inter.occupied_tf:
                if inter.face == "Settlement":
                    self._occupy_settlement_in_gui(board, inter.id, inter.color)
                elif inter.face == "City":
                    self._occupy_city_in_gui(board, inter.id, inter.color)

        # Blocked dots (adjacent to any settlement)
        for inter in board.intersections:
                if inter and inter.occupied_tf:
                    self._block_adjacent_in_gui(board, inter.id, block_visual=block_visual)

    def save_screenshot(self) -> None:
        """Save a screenshot of the game window to SAVE_PATH with a timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(SAVE_PATH, f"Catan_Screenshot_{timestamp}.png")
        Path(SAVE_PATH).mkdir(parents=True, exist_ok=True)
        try:
            pygame.image.save(WIN, filename)
            if MG:
                with open(FILENAME_MG, "a") as f:
                    f.write(f"gui.py | save_screenshot | Saved to {filename}\n")
        except pygame.error as e:
            if MG:
                with open(FILENAME_MG, "a") as f:
                    f.write(f"gui.py | save_screenshot | Error saving screenshot to {filename}: {e}\n")

    def update_round_turn(self, game: Game, special: bool) -> None:
        """
        Update the round and turn display in the GUI.
        Also syncs internal round/turn values used for animation filtering.
        """
        # Critical: sync GUI's round & turn with game state
        # This makes sure update_board's "this turn only" filter works correctly
        self.round = game.round
        self.turn  = game.turn

        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"gui.py | update_round_turn\n")

        # Clear the round/turn display area
        pygame.draw.rect(WIN, COLORS["LGRAY"], [2, 2, 400, 40])

        # Use local variables for display (your original pattern)
        help_round = game.round
        help_turn = game.turn

        color = {1: "BLUE", 2: "RED", 3: "WHITE", 4: "ORANGE"}.get(help_turn, "BLACK")
        font = Font.LARGE.value["regular"]
        turn_text = font.render(f"Turn: {help_turn}", True, COLORS[color])
        round_text = font.render(f"Round: {help_round}", True, COLORS[color])
        WIN.blit(turn_text, (165, 5))
        WIN.blit(round_text, (15, 5))
        # pygame.display.update()

        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui.py | update_round_turn | Actual: {self.round}, {self.turn} | "
                        f"Display: {help_round}, {help_turn}, Color: {color}, Special: {special}\n")

    def _block_adjacent_in_gui(self, board: Board, intersection_id: int, block_visual: bool = False) -> None:
        """
            Optionally render visual indication of blocked (forbidden) adjacent intersections.

            This method does nothing unless `block_visual=True` is explicitly passed.
            It is meant to highlight intersections that cannot be built on due to adjacency rules.

            Args:
                board: The current game board instance.
                intersection_id: ID of the occupied intersection whose neighbors should be checked.
                block_visual: If True, draw blocking indicators on adjacent valid intersections.
                            Defaults to False (no visual change).
            """
        if not block_visual:
            return  # do nothing by default
        
        # existing blocking/highlighting logic
        intersection = board.intersections[intersection_id]
        if intersection:
            for neighbor_id in intersection.three_intersection_ids:
                if (neighbor_id not in board.INTERSECTION_IN_WATER and
                    board.intersections[neighbor_id] is not None and
                    board.intersections[neighbor_id].can_build_tf):
                    pos = POSITIONS["intersections"].get(neighbor_id)
                    if pos:
                        pygame.draw.circle(WIN, COLORS["BLACK"], pos, 10)

    def queue_latest_placement(self) -> None:
        """
        Populate self.animate_queue_elements with the most recent placement
        using placement_step (works for both AI and human, no more round/turn bugs).
        """
        temp_queue = []
        max_step = -1

        # Find the highest placement_step that was used
        for inter in self.game.board.intersections:
            if inter and inter.occupied_tf and inter.face in ("Settlement", "City"):
                max_step = max(max_step, inter.placement_step)
        for road in self.game.board.roads:
            if road and road.occupied_tf:
                max_step = max(max_step, road.placement_step)

        if max_step == -1:
            print("No placement found to add to animation queue")
            self.animate_queue_elements = []
            return

        # ── Latest settlement/city with this step ─────────────────────────────
        latest_inter = None
        for inter in self.game.board.intersections:
            if (inter and inter.occupied_tf and inter.face in ("Settlement", "City") and
                inter.placement_step == max_step):
                latest_inter = inter
                break

        if latest_inter:
            pos = POSITIONS["intersections"].get(latest_inter.id)
            if pos:
                kind = "settlement" if latest_inter.face == "Settlement" else "city"
                color = COLORS[latest_inter.color.upper()]
                temp_queue.append((pos, color, 20, kind))

                # Second settlement -> highlight resource tiles (setup phase)
                if self.game.round == -1:
                    for tile_id in latest_inter.three_tile_ids:
                        tile = self.game.board.tiles[tile_id]
                        if tile and tile.type not in ("Sea", "Desert"):
                            tile_pos = convert_tile(tile_id)
                            if tile_pos:
                                temp_queue.append((tile_pos, (255, 255, 0), 26, "tile"))

        # ── Latest road with this step ───────────────────────────────────────
        latest_road = None
        for road in self.game.board.roads:
            if road and road.occupied_tf and road.placement_step == max_step:
                latest_road = road
                break

        if latest_road:
            pos1 = POSITIONS["intersections"].get(latest_road.id[0])
            pos2 = POSITIONS["intersections"].get(latest_road.id[1])
            if pos1 and pos2:
                mid = ((pos1[0] + pos2[0]) // 2, (pos1[1] + pos2[1]) // 2)
                color = COLORS[latest_road.color.upper()]
                temp_queue.append((mid, color, 20, "road"))

        print(f"Queueing {len(temp_queue)} items for animation queue (step {max_step})")
        for item in temp_queue:
            print(f"  -> {item}")

        self.animate_queue_elements = temp_queue

    def update_board(self, board: Board, update_type: str) -> None:
        """Update the board display based on an action."""
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"gui.py | update_board | type={update_type}\n")

        if update_type == "All":
            # Full board redraw
            self.display_fresh_board(board, scoreboard_tf=True)
        
            # Block adjacent intersections for all existing settlements
            for intersection in board.intersections:
                if intersection and intersection.occupied_tf:
                    self._block_adjacent_in_gui(board, intersection.id)
        
            # Draw all existing roads (permanent)
            for road in board.roads:
                if road.occupied_tf:
                    self._occupy_road_in_gui(board, road.id, road.color)
        
            # Draw all existing settlements and cities (permanent)
            for intersection in board.intersections:
                if intersection and intersection.occupied_tf:
                    if intersection.face == "Settlement":
                        self._occupy_settlement_in_gui(board, intersection.id, intersection.color)
                    elif intersection.face == "City":
                        self._occupy_city_in_gui(board, intersection.id, intersection.color)

        else:  # "Last" — animate and draw only the most recent placement
            self.draw_board_base(board)
            self.draw_all_permanent_buildings(board)

            # ── Find highest placement_step used so far ───────────────────────────
            max_step = -1
            for inter in board.intersections:
                if inter and inter.occupied_tf and inter.face in ("Settlement", "City"):
                    max_step = max(max_step, inter.placement_step)
            for road in board.roads:
                if road and road.occupied_tf:
                    max_step = max(max_step, road.placement_step)

            temp_queue = []

            if max_step == -1:
                print("No placement found to animate this turn (update_board 'Last')")
            else:
                print(f"Animating items for latest placement (step {max_step})")

                # ── Latest settlement/city with this step ─────────────────────────
                latest_inter = None
                for inter in board.intersections:
                    if (inter is not None and
                        inter.occupied_tf and
                        inter.face in ("Settlement", "City") and
                        inter.placement_step == max_step):
                        latest_inter = inter
                        break  # usually only one per step

                if latest_inter:
                    pos = POSITIONS["intersections"].get(latest_inter.id)
                    if pos:
                        kind = "settlement" if latest_inter.face == "Settlement" else "city"
                        color = COLORS[latest_inter.color.upper()]
                        temp_queue.append((pos, color, 20, kind))
                        print(f"  -> {pos} {color} 20 '{kind}'")

                        # Draw it permanently right away
                        if latest_inter.face == "Settlement":
                            self._occupy_settlement_in_gui(board, latest_inter.id, latest_inter.color)
                        else:
                            self._occupy_city_in_gui(board, latest_inter.id, latest_inter.color)

                        # ── Resource tiles highlight on second settlement (round -1) ──
                        if self.round == -1:
                            for tile_id in latest_inter.three_tile_ids:
                                tile = board.tiles[tile_id]
                                if tile and tile.type not in ("Sea", "Desert"):
                                    tile_pos = convert_tile(tile_id)
                                    if tile_pos:
                                        temp_queue.append((tile_pos, (255, 255, 0), 26, "tile"))
                                        print(f"  -> {tile_pos} (255,255,0) 26 'tile'")

                # ── Latest road with this step ────────────────────────────────────
                latest_road = None
                for road in board.roads:
                    if (road is not None and
                        road.occupied_tf and
                        road.placement_step == max_step):
                        latest_road = road
                        break

                if latest_road:
                    pos1 = POSITIONS["intersections"].get(latest_road.id[0])
                    pos2 = POSITIONS["intersections"].get(latest_road.id[1])
                    if pos1 and pos2:
                        mid = ((pos1[0] + pos2[0]) // 2, (pos1[1] + pos2[1]) // 2)
                        color = COLORS[latest_road.color.upper()]
                        temp_queue.append((mid, color, 20, "road"))
                        print(f"  -> {mid} {color} 20 'road'")

                        # Draw permanently
                        self._occupy_road_in_gui(board, latest_road.id, latest_road.color)

            # Set animation queue (will be used by _animate_elements and animate_continuous)
            self.animate_queue_elements = temp_queue

            # Run the reveal animation immediately (quarter circles)
            if temp_queue:
                self._animate_elements(board)

    def update_scoreboard(self, game: Game) -> None:
        """Render the entire scoreboard with headers and player statistics.

        Args:
            game: The game instance containing player data.
        """
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"{game.sequence_number} | {game.state} | gui_game.py | update_scoreboard\n")

        # Resource_exploration (=pips summary
        self.update_resource_exploration(game.board)

        # Scoreboard area
        pygame.draw.rect(WIN, COLORS["LGRAY"], [110, 595, 525, 155])
       
        # Header: Small "VP" above C, S, R (Longest Route), A, E
        font_small = Font.SMALL.value["regular"]
        vp_columns = [1, 2, 4, 5, 6] # Indices for C, S, R (Longest Route), A, E
        header_x_positions = [115, 145, 165, 185, 205, 225, 245, 270, 300, 330, 360, 390, 435, 480, 525, 570, 635, 670, 705, 740, 775]
        for i in vp_columns:
            vp_header = font_small.render("VP", True, COLORS["BLACK"])
            vp_rect = vp_header.get_rect(center=(header_x_positions[i] + 10, 550)) # Center for 20-pixel column
            WIN.blit(vp_header, vp_rect)
       
        # Header: Main text and images
        font = Font.NORMAL.value["regular"]
        header_parts = ["VP", "C", "S", "R", "R", "A", "E", "LR", "LA", "RC", "DC"]
        for i, part in enumerate(header_parts):
            text = font.render(part, True, COLORS["BLACK"])
            text_rect = text.get_rect(center=(header_x_positions[i] + 10, 560)) # Center for 20-pixel column
            WIN.blit(text, text_rect)
       
        # RC images (Wheat, Ore, Wood, Brick, Wool) at 40x40, 5 pixels apart
        rc_images = ["FIELD", "MOUNTAIN", "FOREST", "HILL", "PASTURE"]
        rc_x_positions = [390, 435, 480, 525, 570] # 40x40 images + 5-pixel gaps
        for i, img_key in enumerate(rc_images):
            try:
                image = IMAGES[img_key]["40x40"]
                if image is not None:
                    img_rect = image.get_rect(center=(rc_x_positions[i] + 20, 560)) # Center for 40x40
                    WIN.blit(image, img_rect)
                else:
                    if MG:
                        with open(FILENAME_MG, "a") as f:
                            f.write(f"gui_game.py | update_scoreboard | Missing RC image: {img_key}\n")
            except KeyError:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui_game.py | update_scoreboard | KeyError: No '40x40' for RC image: {img_key}\n")
       
        # Vertical lines before/after RC, before DC
        pygame.draw.line(WIN, COLORS["BLACK"], (385, 540), (385, 780), 2) # Before RC
        pygame.draw.line(WIN, COLORS["BLACK"], (615, 540), (615, 780), 2) # After RC
        pygame.draw.line(WIN, COLORS["BLACK"], (630, 540), (630, 780), 2) # Before DC
       
        # DC images (VP, Knight, Road, Plenty, Monopoly) at 30x30, 5 pixels apart
        dc_images = ["DC_VPOINT", "DC_KNIGHT", "DC_ROAD", "DC_PLENTY", "DC_MONOPOLY"]
        dc_x_positions = [635, 670, 705, 740, 775] # 30x30 images + 5-pixel gaps
        for i, img_key in enumerate(dc_images):
            try:
                image = IMAGES[img_key]["30x30"]
                if image is not None:
                    img_rect = image.get_rect(center=(dc_x_positions[i] + 15, 560)) # Center for 30x30
                    WIN.blit(image, img_rect)
                else:
                    if MG:
                        with open(FILENAME_MG, "a") as f:
                            f.write(f"gui_game.py | update_scoreboard | Missing DC image: {img_key}\n")
            except KeyError:
                if MG:
                    with open(FILENAME_MG, "a") as f:
                        f.write(f"gui_game.py | update_scoreboard | KeyError: No '30x30' for DC image: {img_key}\n")
       
        # Player rows
        for i, player in enumerate(game.players):
            self._render_scoreboard_row(player, game, 15, 560 + (i + 1) * 40 - 10, 560 + (i + 1) * 40)
       
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_game.py | update_scoreboard | Rendered scoreboard for {len(game.players)} players\n")

    def _render_scoreboard_row(self, player: Player, game: Game, x: int, name_y: int, stats_y: int) -> None:
        """Render a single player's scoreboard row with statistics and resource counts.

        Args:
            player: The player whose statistics to render.
            game: The game instance containing player data.
            x: X-coordinate for the player name.
            name_y: Y-coordinate for the player name.
            stats_y: Y-coordinate for the player's statistics and resource counts.
        """
        font = Font.NORMAL.value["regular"]
        font_large = Font.LARGE.value["regular"]
        x_positions = [115, 145, 165, 185, 205, 225, 245, 270, 300, 330, 360, 390, 435, 480, 525, 570]
       
        # Player name in color, large font, at x=15
        player_colors = {
            1: COLORS["BLUE"],
            2: COLORS["RED"],
            3: COLORS["WHITE"],
            4: COLORS["ORANGE"]
        }
        player_name = f"Player {player.id}"
        name_text = font_large.render(player_name, True, player_colors.get(player.id, COLORS["BLACK"]))
        WIN.blit(name_text, (x, name_y))
       
        # Player stats
        extra_vp = sum([dcard[3] for dcard in player.dcard_summary]) # Victory points from DC
        stats = [
            str(player.victory_points), # VP
            str(len(player.cities)), # C
            str(len(player.settlements)), # S
            str(len(player.roads)), # R (roads)
            str(2 if player.longest_route_tf == True else 0), # R (longest route points)
            str(2 if player.largest_army_tf == True else 0), # A
            str(extra_vp), # E
            str(player.size_longest_route), # LR
            str(player.size_largest_army), # LA
            str(player.number_of_rcards), # RC
            str(player.number_of_dcards), # DC
        ]
        for i, stat in enumerate(stats):
            text = font.render(stat, True, COLORS["BLACK"])
            text_rect = text.get_rect(center=(x_positions[i] + 10, stats_y))
            WIN.blit(text, text_rect)
       
        # Resource cards (Wheat, Ore, Wood, Brick, Wool) for all players
        rc_stats = [
            player.rcards.get(ResourceCard.WHEAT, 0),
            player.rcards.get(ResourceCard.ORE, 0),
            player.rcards.get(ResourceCard.WOOD, 0),
            player.rcards.get(ResourceCard.BRICK, 0),
            player.rcards.get(ResourceCard.WOOL, 0)
        ]
        for i, stat in enumerate(rc_stats):
            text = font.render(str(stat), True, COLORS["BLACK"])
            text_rect = text.get_rect(center=(x_positions[i + 11] + 20, stats_y))
            WIN.blit(text, text_rect)
       
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"gui_game.py | _render_scoreboard_row | Player {player.id}: {player_name} {stats} RC: {rc_stats}\n")

    def draw_guidance(self):
        self.human_guidance.draw()

    def draw_guidance_text(self, lines: list[str] | str, y_offset: int = 0, font_size: str = "normal"):
        font = Font.NORMAL.value["regular"] if font_size == "normal" else Font.LARGE.value["regular"]
        """
        Draw one or more lines of guidance text.
        - lines: can be a single string or a list of strings
        - y_offset: extra pixels to shift the whole block downward (default 0)
        """
        if isinstance(lines, str):
            lines = [lines]  # convert single string to list

        # Clear previous text area — make it taller to fit 2 lines safely
        rect_height = 40 + (len(lines) - 1) * 20  # ~30px per extra line
        pygame.draw.rect(WIN, COLORS["LGRAY"], [20, 20 + y_offset, 400, rect_height])

        font = Font.NORMAL.value["regular"]
        y = 28 + y_offset  # base y-position + offset

        for line in lines:
            if line:  # skip empty lines
                surf = font.render(line, True, COLORS["BLACK"])
                WIN.blit(surf, (15, y))
                y += 20  # line spacing (adjust if your font is taller/shorter)

        pygame.display.update()  # optional — can be removed if called from elsewhere

    def handle_confirmation_click(self, pos: Tuple[int, int]) -> str | None:
        """Check if click was on the dynamic OKY / OKN icons."""
        if not self.human_guidance.confirm_center:
            return None

        x, y = self.human_guidance.confirm_center
        
        # OKY is drawn at (x + 35, y - 45), size 40×40
        oky_rect = pygame.Rect(x + 35, y - 45, 40, 40)
        
        # OKN is drawn at (x + 35, y + 10), size 40×40
        okn_rect = pygame.Rect(x + 35, y + 10, 40, 40)

        if oky_rect.collidepoint(pos):
            return "OKY"
        if okn_rect.collidepoint(pos):
            return "OKN"
        
        return None               

    def update_resource_exploration(self, board: Board):
        """Display resource exploration (= pip summary above the scoreboard)."""
        
        # ─── Display Constants ───────────────────────────────────────────────
        AREA_X            = 10
        AREA_Y_START      = 100
        HEADER_Y          = AREA_Y_START          # "Resource Potential:" title
        LABEL_Y           = AREA_Y_START + 25     # Resource names (Wheat, Ore...)
        CURRENT_Y         = AREA_Y_START + 40     # "Current:" row numbers
        APPROX_Y          = AREA_Y_START + 65     # "Remaining:" row numbers
        
        BG_RECT_X         = 5
        BG_RECT_Y         = AREA_Y_START - 10
        BG_RECT_WIDTH     = 400                   # wider to fit longer header
        BG_RECT_HEIGHT    = 135                   # taller for three rows + spacing
        BG_COLOR          = COLORS["LGRAY"]
        
        COL_WIDTH         = 50
        COL_WHEAT         = 150
        COL_ORE           = COL_WHEAT + COL_WIDTH
        COL_WOOD          = COL_ORE   + COL_WIDTH
        COL_BRICK         = COL_WOOD  + COL_WIDTH
        COL_SHEEP         = COL_BRICK + COL_WIDTH
        
        RESOURCE_COLUMNS = {
            "wheat": COL_WHEAT,
            "ore":   COL_ORE,
            "wood":  COL_WOOD,
            "brick": COL_BRICK,
            "sheep": COL_SHEEP,
        }
        
        FONT_HEADER = Font.NORMAL.value["bold"]
        FONT_NORMAL = Font.NORMAL.value["regular"]
        FONT_SMALL  = Font.SMALL.value["regular"]
        # ─────────────────────────────────────────────────────────────────────

        # Clear background rectangle
        pygame.draw.rect(WIN, BG_COLOR, 
                        (BG_RECT_X, BG_RECT_Y, BG_RECT_WIDTH, BG_RECT_HEIGHT))

        # Header
        header_surf = FONT_HEADER.render("Resource Potential:", 
                                        True, COLORS["BLACK"])
        WIN.blit(header_surf, (AREA_X, HEADER_Y))

        # Resource labels (Wheat, Ore, etc. — now on their own row above numbers)
        for res, cx in RESOURCE_COLUMNS.items():
            label_surf = FONT_SMALL.render(res.capitalize(), True, COLORS["DGRAY"])
            WIN.blit(label_surf, (cx - label_surf.get_width() // 2, LABEL_Y))

        # ── Current factual row ──────────────────────────────────────────────
        current = board.get_current_settlement_pips()
        
        current_text = FONT_NORMAL.render("Current:", True, COLORS["BLACK"])
        WIN.blit(current_text, (AREA_X, CURRENT_Y))

        for res, cx in RESOURCE_COLUMNS.items():
            val = current.get(res, 0.0)
            txt = FONT_NORMAL.render(f"{val:.1f}", True, COLORS["BLACK"])
            WIN.blit(txt, (cx - txt.get_width() // 2, CURRENT_Y))

        # ── Approximation row ────────────────────────────────────────────────
        approx = board.resource_exploration()
        
        approx_text = FONT_NORMAL.render("Remaining:", True, COLORS["BLACK"])
        WIN.blit(approx_text, (AREA_X, APPROX_Y))

        for res, cx in RESOURCE_COLUMNS.items():
            if res not in approx:
                continue
            mi = approx[res]["min"]
            ma = approx[res]["max"]
            if abs(mi - ma) < 0.5:
                display_str = f"{mi:.1f}"
            else:
                display_str = f"{mi:.0f}–{ma:.0f}"
            txt = FONT_NORMAL.render(display_str, True, COLORS["BLACK"])
            WIN.blit(txt, (cx - txt.get_width() // 2, APPROX_Y))