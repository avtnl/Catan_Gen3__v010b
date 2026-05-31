"""
v010
Manages the Catan game logic.

This module defines the Game class, handling game state, player management, board interactions,
turn details, and resource card tracking. It initializes all attributes for the initial empty
board state and includes methods for game progression, such as advancing turns and distributing
resources.

Key components:
    - Game: Manages game state, players, board, and GUI.
    - StrategyDashboard: Tracks player statistics for the scoreboard.
    - TurnDetails: Tracks per-turn details.
    - ResourceCardDashboard: Tracks resource card distribution.
    - Settings: Manages game settings.

Dependencies:
    - typing: For type hints.
    - gui.gui_constants: For player colors.
    - core.board: For board interactions.
    - core.player: For player management.
    - gui.gui: For GUI updates (forward reference).
    - core.constants: For game configuration constants.
"""
import pygame
from typing import List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
from random import random
from core.board import Board
from core.player import Player
from core.constants import HUMAN_PLAYER, HP_ID, FNFREQ, FILENAME_FREQ, MG, FILENAME_MG, FILENAME_MGLOG, MEM_TWP, SAVE_PATH, PlayerColor, ResourceCard
from core.markov_evaluator import MarkovEvaluator

if TYPE_CHECKING:
    from gui.gui import GUI

class StrategyDashboard:
    """Tracks player statistics for the scoreboard."""
   
    def __init__(
        self,
        player_id: int,
        victory_points: int = 0,
        number_of_settlements: int = 0,
        number_of_cities: int = 0,
        victory_points_dcard: int = 0,
        longest_road: int = 0,
        largest_army: int = 0,
        number_of_rcards: int = 0,
        number_of_dcards: int = 0,
        distribution_of_tile_values: str = "00000X00000",
        distribution_of_tile_types: str = "000000"
    ) -> None:
        """Initialize a StrategyDashboard.

        Args:
            player_id: The player ID (1-4).
            victory_points: Total victory points.
            number_of_settlements: Number of settlements.
            number_of_cities: Number of cities.
            victory_points_dcard: Victory points from development cards.
            longest_road: Length of the longest road.
            largest_army: Number of knights played.
            number_of_rcards: Number of resource cards.
            number_of_dcards: Number of development cards.
            distribution_of_tile_values: Distribution of tile values as a string.
            distribution_of_tile_types: Distribution of tile types as a string.
        """
        self.player_id = player_id
        self.victory_points = victory_points
        self.number_of_settlements = number_of_settlements
        self.number_of_cities = number_of_cities
        self.victory_points_dcard = victory_points_dcard
        self.longest_road = longest_road
        self.largest_army = largest_army
        self.number_of_rcards = number_of_rcards
        self.number_of_dcards = number_of_dcards
        self.distribution_of_tile_values = distribution_of_tile_values
        self.distribution_of_tile_types = distribution_of_tile_types

class TurnDetails:
    """Keeps track of specific details to be renewed every turn."""
   
    def __init__(
        self,
        round_num: int,
        turn: int,
        dice_roll: int,
        validate_function_enough: bool,
        validate_function_TwP_Match: bool,
        validate_function_discard_rcards_by_HP: bool,
        validate_function_set_robber_by_HP: bool,
        validate_function_outlook_opponents_for_HP: bool,
        validate_function_built_two_roads: int,
        question_mark_button: List[int]
    ) -> None:
        """Initialize TurnDetails.

        Args:
            round_num: Current game round number.
            turn: Current player's turn number.
            dice_roll: Sum of the dice roll.
            validate_function_enough: Whether enough resources are available.
            validate_function_TwP_Match: Whether trade with player matches.
            validate_function_discard_rcards_by_HP: Whether human player must discard resource cards.
            validate_function_set_robber_by_HP: Whether human player must set the robber.
            validate_function_outlook_opponents_for_HP: Whether to outlook opponents for human player.
            validate_function_built_two_roads: Number of roads built this turn.
            question_mark_button: Status of question mark buttons per player.
        """
        self.round = round_num
        self.turn = turn
        self.dice_roll = dice_roll
        self.validate_function_enough = validate_function_enough
        self.validate_function_TwP_Match = validate_function_TwP_Match
        self.validate_function_discard_rcards_by_HP = validate_function_discard_rcards_by_HP
        self.validate_function_set_robber_by_HP = validate_function_set_robber_by_HP
        self.validate_function_outlook_opponents_for_HP = validate_function_outlook_opponents_for_HP
        self.validate_function_built_two_roads = validate_function_built_two_roads
        self.road_built_in_turn_TF = False
        self.roads_built_in_turn: List[Tuple[int, int]] = []
        self.settlement_built_in_turn_TF = False
        self.settlements_built_in_turn: List[int] = []
        self.city_built_in_turn_TF = False
        self.cities_built_in_turn: List[int] = []
        self.question_mark_button = question_mark_button
        self.dcard_played_in_turn = [0, 0, 0, 0, 0]
        self.dcard_played_in_turn_TF = False
        self.tile_type_selected_1 = [0, 0, 0, 0, 0]
        self.tile_type_selected_2 = [0, 0, 0, 0, 0]
        self.players_having_too_many_rcards = [0, 0, 0, 0, 0]
        self.rcard_give = [0, 0, 0, 0, 0]
        self.rcard_get = [0, 0, 0, 0, 0]
        self.list_of_TwP: List = []
        self.number_of_deals_offered = 0
        self.list_of_TwP_rejected_by_HP: List = []
        self.list_of_TwHP = [0, 0, 0, 0, 0]
        self.dcard_selected = [0, 0, 0, 0, 0]
        self.modes: List = []

    def clear_turn_details(self) -> None:
        """Clear all turn details to their initial values.

        Args:
            None
        """
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write("turn_details.py | clear_turn_details\n")
        self.dice_roll = 0
        self.validate_function_enough = False
        self.validate_function_TwP_Match = False
        self.validate_function_discard_rcards_by_HP = False
        self.validate_function_set_robber_by_HP = False
        self.validate_function_outlook_opponents_for_HP = False
        self.road_built_in_turn_TF = False
        self.roads_built_in_turn = []
        self.settlement_built_in_turn_TF = False
        self.settlements_built_in_turn = []
        self.city_built_in_turn_TF = False
        self.cities_built_in_turn = []
        self.dcard_played_in_turn = [0, 0, 0, 0, 0]
        self.dcard_played_in_turn_TF = False
        self.tile_type_selected_1 = [0, 0, 0, 0, 0]
        self.tile_type_selected_2 = [0, 0, 0, 0, 0]
        self.question_mark_button = [0, 0, 0, 0, 0, 0]
        self.players_having_too_many_rcards = [0, 0, 0, 0, 0]
        self.rcard_give = [0, 0, 0, 0, 0]
        self.rcard_get = [0, 0, 0, 0, 0]
        self.list_of_TwP = []
        self.number_of_deals_offered = 0
        if not MEM_TWP:
            self.list_of_TwP_rejected_by_HP = []
        self.list_of_TwHP = []
        self.dcard_selected = [0, 0, 0, 0, 0]
        self.modes = []

    def validate_list_of_TwP(self, game: 'Game') -> None:
        """Validate the list of Trade with Players (TwP).

        Args:
            game: The game instance containing player data.
        """
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"{game.sequence_number} | {game.state} | turn_details.py | validate_list_of_TwP\n")
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write("turn_details.py | validate_list_of_TwP | Before\n")
                for deal in self.list_of_TwP:
                    f.write(f"{deal}\n")
        idx = 0
        while idx < len(self.list_of_TwP):
            deal = self.list_of_TwP[idx]
            for player in game.players:
                if player.id == deal[2]:
                    rcards = player.rcards_in_hand()
                    if MG:
                        with open(FILENAME_MG, "a") as f:
                            f.write(f"turn_details.py | validate_list_of_TwP | rcards_in_hand: {rcards[0]}\n")
                    for card_idx in range(5):
                        if rcards[0][card_idx] == 0 and deal[5] > 0:
                            self.list_of_TwP.pop(idx)
                            idx -= 1
                            break
            idx += 1
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write("turn_details.py | validate_list_of_TwP | After\n")
                for deal in self.list_of_TwP:
                    f.write(f"{deal}\n")

class ResourceCardDashboard:
    """Tracks resource card distribution across the game."""
   
    def __init__(
        self,
        resource_production_game_total: List[int],
        resource_production_game_player: List[List[int]],
        resource_production_game_player_view: List[List[int]]
    ) -> None:
        """Initialize a ResourceCardDashboard.

        Args:
            resource_production_game_total: Total resources distributed [Wheat, Ore, Wood, Brick, Wool, Gold].
            resource_production_game_player: Per-player resources [[player_id, Wheat, Ore, Wood, Brick, Wool, Gold], ...].
            resource_production_game_player_view: Each player's view of others' resources [[viewer_id, viewed_id, Wheat, Ore, Wood, Brick, Wool, Gold, QM_Added, QM_Discarded], ...].
        """
        self.resource_production_game_total = resource_production_game_total
        self.resource_production_game_player = resource_production_game_player
        self.resource_production_game_player_view = resource_production_game_player_view

class Settings:
    """Manages game settings."""
   
    def __init__(
        self,
        human_player_tf: str,
        human_player_sequence: int,
        topx_tf: str,
        topx: int,
        weight_balanced: float,
        weight_wood_brick: float,
        weight_wheat_ore: float,
        weight_wheat_ore_wool: float,
        weight_monopoly: float,
        weight_probability: float,
        weight_blocked: float,
        user_text1: str,
        user_text2: str,
        user_text3: str
    ) -> None:
        """Initialize Settings.

        Args:
            human_player_tf: Whether human player is enabled ('True' or 'False').
            human_player_sequence: Human player sequence (e.g., 3).
            topx_tf: Whether top-x is enabled ('True' or 'False').
            topx: Top-x value (e.g., 15).
            weight_balanced: Weight for balanced strategy.
            weight_wood_brick: Weight for wood/brick resource strategy.
            weight_wheat_ore: Weight for wheat/ore resource strategy.
            weight_wheat_ore_wool: Weight for wheat/ore/wool resource strategy.
            weight_monopoly: Weight for monopoly strategy.
            weight_probability: Weight for probability-based strategy.
            weight_blocked: Weight for blocked strategy.
            user_text1: Harbor user text 1 (e.g., '3').
            user_text2: Harbor user text 2 (e.g., '2').
            user_text3: Harbor user text 3 (e.g., '1').
        """
        self.human_player_tf = human_player_tf
        self.human_player_sequence = human_player_sequence
        self.topx_tf = topx_tf
        self.topx = topx
        self.weight_balanced = weight_balanced
        self.weight_wood_brick = weight_wood_brick
        self.weight_wheat_ore = weight_wheat_ore
        self.weight_wheat_ore_wool = weight_wheat_ore_wool
        self.weight_monopoly = weight_monopoly
        self.weight_probability = weight_probability
        self.weight_blocked = weight_blocked
        self.user_text1 = user_text1
        self.user_text2 = user_text2
        self.user_text3 = user_text3

class Game:
    """Represents a Catan game instance."""
   
    def __init__(
        self,
        sequence_number: int,
        id_: str,
        phase: str,
        state: str,
        state_1: str,
        state_2: str,
        myplayers: List[Player],
        board_name: str
    ) -> None:
        """Initialize a Game.

        Args:
            sequence_number: Game sequence number (e.g., 1).
            id_: Unique game ID (e.g., timestamp-based string).
            phase: Game phase (e.g., 'Initial Placement', 'Execution').
            state: Game state (e.g., 'None').
            state_1: Additional state information (e.g., '0').
            state_2: Additional state information (e.g., '0').
            myplayers: List of players or None to initialize new players.
            board_name: Name of the board (e.g., 'Base_Random').
        """
        self.manager = None # Placeholder for game manager
        self.sequence_number = sequence_number
        self.id = id_
        self.time_ended: Optional[str] = None
        self.phase = phase
        self.state = state
        self.state_1 = state_1
        self.state_2 = state_2
        self.round: int = -2
        self.turn: int = 1
        self.players = myplayers or self._initialize_players()
        self.board = Board(board_name)

        # ──────────────────────────────────────────────────────────────
        # LOAD SAVED PLAYBOARD (controlled from constants.py)
        #    - When LOAD_PLAYBOARD=True → completely deterministic board
        #    - Skips all randomness in _get_board()
        #    - Then runs all post-load steps automatically
        # ──────────────────────────────────────────────────────────────
        # from core.constants import LOAD_PLAYBOARD, SAVED_PLAYBOARD
        # if LOAD_PLAYBOARD:
        #     print(f"📂 Loading saved playboard: {SAVED_PLAYBOARD}")
        #     self.board.load_board(SAVED_PLAYBOARD)
        # else:
        #     print("🎲 Generating random board (Base_Random)")

        # ──────────────────────────────────────────────────────────────
        # MARKOV EVALUATOR
        # ──────────────────────────────────────────────────────────────
        # Markov is algorithm_id == 4. Do not precompute it unless an AI
        # player actually uses algorithm 4; this keeps normal 5-Strategies
        # runs fast and quiet.
        self.vertex_to_rolls = None
        self.markov = None

        uses_markov = any(
            getattr(player, "initial_placement_algorithm", None) == 4
            and not getattr(player, "is_human", False)
            for player in self.players
        )

        if uses_markov:
            import contextlib
            import io

            self.vertex_to_rolls = self.board.get_vertex_to_rolls()
            with contextlib.redirect_stdout(io.StringIO()):
                self.markov = MarkovEvaluator()
                self.markov.precompute_game(self.vertex_to_rolls)
            self.markov.board = self.board
        
        self.gui: Optional['GUI'] = None
        self.ip = None # Placeholder for InitialPlacement
        self.dice_roll: Optional[Tuple[int, int]] = None
        self.dice_rolls: List[Tuple[int, int]] = []
        self.dice_roll_history = [0] * 13 # Indices 0-12
        self.dice_roll_matrix: List = [] # Placeholder for dice roll matrix
        self.dcards_stack: List = [] # Placeholder for shuffled development cards
        self.robber_tile_probabilities = [[tile, 0.0] for tile in self.board.LIST_OF_LAND_TILES]
        self.previous_tile_having_robber = [0, 0, 0]
        self.list_of_tiles_having_robber: List = []
        self.last_total_turn_with_dr7: int = 0
        self.settings_tf = False
        self.settings = Settings(
            human_player_tf=True,
            human_player_sequence=3,
            topx_tf=True,
            topx=15,
            weight_balanced=1,
            weight_wood_brick=0.1,
            weight_wheat_ore=1,
            weight_wheat_ore_wool=0.15,
            weight_monopoly=1,
            weight_probability=1,
            weight_blocked=0.2,
            user_text1="3",
            user_text2="2",
            user_text3="1"
        )
        self.initial_placement_balanced: List = []
        self.initial_placement_wood_brick: List = []
        self.initial_placement_wheat_ore: List = []
        self.initial_placement_wheat_ore_wool: List = []
        self.initial_placement_monopoly: List = []
        self.resource_production_probability = [[0, 0, 0, 0, 0, 0]] + [[i, 0, 0, 0, 0, 0] for i in range(1, 5)]
        self.tile_type: List = []
        self.resource_type_available: List = []
        self.resource_type_occupied: List = []
        self.resource_type_players: List = []
        self.players_impacted = [False] * 4
        self.common_next_settlements: List = []
        self.common_new_settlements: List = []
        self.common_next_roads: List = []
        self.last_known_strategies = [[[0] * 8, 0] for _ in range(4)]
        self.last_known_outlooks = [["BBBBBBBBB", [], [], [], 0, 0, 0, 0, 0, 0, 0, [], 0, [], []] for _ in range(4)]
        self.current_player: Optional[Player] = None
        self.winner: Optional[Player] = None
        self.game_over: bool = False
        self.longest_road_player: Optional[Player] = None
        self.largest_army_player: Optional[Player] = None
        self.strategy_dashboard = [
            StrategyDashboard(i, 0, 0, 0, 0, 0, 0, 0, 0, "00000X00000", "000000")
            for i in range(1, 5)
        ]
        self.resource_card_dashboard = [
            ResourceCardDashboard(
                resource_production_game_total=[0, 0, 0, 0, 0, 0],
                resource_production_game_player=[
                    [1, 0, 0, 0, 0, 0, 0],
                    [2, 0, 0, 0, 0, 0, 0],
                    [3, 0, 0, 0, 0, 0, 0],
                    [4, 0, 0, 0, 0, 0, 0]
                ],
                resource_production_game_player_view=[
                    [1, 2, 0, 0, 0, 0, 0, 0, 0, 0],
                    [1, 3, 0, 0, 0, 0, 0, 0, 0, 0],
                    [1, 4, 0, 0, 0, 0, 0, 0, 0, 0],
                    [2, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                    [2, 3, 0, 0, 0, 0, 0, 0, 0, 0],
                    [2, 4, 0, 0, 0, 0, 0, 0, 0, 0],
                    [3, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                    [3, 2, 0, 0, 0, 0, 0, 0, 0, 0],
                    [3, 4, 0, 0, 0, 0, 0, 0, 0, 0],
                    [4, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                    [4, 2, 0, 0, 0, 0, 0, 0, 0, 0],
                    [4, 3, 0, 0, 0, 0, 0, 0, 0, 0]
                ]
            )
        ]
        self.myturn = TurnDetails(
            round_num=self.round,
            turn=self.turn,
            dice_roll=0,
            validate_function_enough=False,
            validate_function_TwP_Match=False,
            validate_function_discard_rcards_by_HP=False,
            validate_function_set_robber_by_HP=False,
            validate_function_outlook_opponents_for_HP=False,
            validate_function_built_two_roads=0,
            question_mark_button=[0, 0, 0, 0, 0, 0]
        )

    def _initialize_players(self) -> List[Player]:
        """
        Initialize players for the game.

        Algorithms:
        1 = _max_of_pips; acutally using _max_of_pips_and_optonal_port with use_port=False
        2 = _max_of_pips_and_port; actually using _max_of_pips_and_optonal_port with use_port=True
        3 = 5 Strategies (balanced, wood/brick, wheat/ore, wheat/ore/wool, monopoly)
        4 = Markov AI (strong probabilistic AI based on precomputed transition matrices)

        New flag:
            human_like_placement=True  → random from top 8 best spots (more natural/human-like)
            human_like_placement=False → always pick the absolute best remaining spot (deterministic)
        """
        players = [
            Player(
                id_=1,
                color=PlayerColor.BLUE.color_name,
                sequence=1,
                is_human=(HUMAN_PLAYER and 1 in HP_ID),
                initial_placement_algorithm=4,
                human_like_placement=False           # human-like (recommended)
            ),
            Player(
                id_=2,
                color=PlayerColor.RED.color_name,
                sequence=2,
                is_human=(HUMAN_PLAYER and 2 in HP_ID),
                initial_placement_algorithm=4,
                human_like_placement=False           # human-like (recommended)
            ),
            Player(
                id_=3,
                color=PlayerColor.WHITE.color_name,
                sequence=3,
                is_human=(HUMAN_PLAYER and 3 in HP_ID),
                initial_placement_algorithm=1,
                human_like_placement=False          # doesn't matter for human
            ),
            Player(
                id_=4,
                color=PlayerColor.ORANGE.color_name,
                sequence=4,
                is_human=(HUMAN_PLAYER and 4 in HP_ID),
                initial_placement_algorithm=3,
                human_like_placement=False           # human-like (recommended)
            ),
        ]

        # Link each Player back to this Game instance
        for player in players:
            player.game = self

        return players

    def handle_oky_click(self, board: Board, player: Player) -> None:
        """Handle OKY button click for human player/operator.

        Args:
            board: The game board instance.
            player: The current player instance.
        """
        # Placeholder: Implement OKY logic
        pass

    def handle_okn_click(self, board: Board, player: Player) -> None:
        """Handle OKN button click for human player/operator.

        Args:
            board: The game board instance.
            player: The current player instance.
        """
        # Placeholder: Implement OKN logic
        pass
    
    def _is_connected_to_road(self, intersection_id: int, player: Player) -> bool:
        """Return True if intersection_id touches one of player's roads."""
        inter = self.board.intersections[intersection_id]
        if inter is None:
            return False

        for road_tuple in inter.three_roads:
            road_id = tuple(sorted(road_tuple))
            road = next((r for r in self.board.roads if r and r.id == road_id), None)
            if road and road.occupied_tf and road.color == player.color:
                return True

        return False

    def can_build_intersection_tf(self, intersection_id: int, player: Optional[Player] = None) -> bool:
        """Return True if a settlement/city can be built at the intersection.

        Distance rule is always enforced. Road connection is required only in
        normal game rounds >= 0. During initial placement, player may be None.
        """
        inter = self.board.intersections[intersection_id]

        if inter is None:
            return False
        if intersection_id in self.board.INTERSECTION_IN_WATER:
            return False
        if inter.occupied_tf:
            return False
        if self.round >= 0 and not inter.can_build_tf:
            return False

        # Distance rule: reject if adjacent to any occupied intersection.
        for other in self.board.intersections:
            if other and other.occupied_tf and other.id != intersection_id:
                dist = self.board._distance_between_intersections(intersection_id, other.id)
                if dist <= 1:
                    return False

        # Road connection is required only during the normal game.
        if self.round >= 0:
            if player is None:
                return False
            if not self._is_connected_to_road(intersection_id, player):
                return False

        return True

    def get_player_ports_dict(self, player: Player) -> dict:
        """Convert player's port_access into the dict format required by apply_trading_layer.
        Example output: {"wool": 2, "generic": 3}"""
        if not hasattr(player, 'port_access') or not player.port_access:
            return {}

        ports_dict = {}
        for port_name, has_port in player.port_access.items():
            if not has_port:
                continue
            if port_name == "3:1":
                ports_dict["generic"] = 3
            elif port_name.startswith("2:1-"):
                # e.g. "2:1-wool" → {"wool": 2}
                res = port_name.split("-")[1].lower()
                if res in self.markov.RES_NAMES:   # safety
                    ports_dict[res] = 2
            # 4:1 bank is always available by default in apply_trading_layer
        return ports_dict

    def roll_dice(self) -> Tuple[int, int]:
        """Simulate rolling two dice.

        Args:
            None

        Returns:
            Tuple[int, int]: Tuple of two dice values (1-6).
        """
        return (random.randint(1, 6), random.randint(1, 6))

    def distribute_rcards(self, roll: int) -> None:
        """Distribute resource cards to players based on the dice roll.

        Args:
            roll: The sum of the dice roll (2-12).
        """
        for player in self.players:
            for intersection_id in player.settlements + player.cities:
                for intersection in self.board.intersections:
                    if intersection.id == intersection_id:
                        for tile_id in intersection.three_tile_ids:
                            for tile in self.board.tiles:
                                if tile and tile.id == tile_id and tile.value == roll:
                                    resource = next((r for r in ResourceCard if r.value == tile.type), None)
                                    if resource:
                                        multiplier = 2 if intersection_id in player.cities else 1
                                        player.add_resource(resource, multiplier)

    def sync_round_turn(self) -> None:
        """Synchronize round and turn with Board.

        Args:
            None
        """
        self.board.round = self.round
        self.board.turn = self.turn

    def advance_turn(self) -> None:
        """Advance to the next player's turn and update game state.

        Handles the initial placement sequence (1,2,3,4,4,3,2,1) and transitions to Execution phase.
        """
        print("game.advance_turn executed")
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"{self.id} | {self.state} | game.py | advance_turn\n")

        if self.phase == "InitialPlacement":
            if self.round == -2:
                self.turn += 1
                if self.turn > 4:
                    self.round = -1
                    self.turn = 4
            elif self.round == -1:
                self.turn -= 1
                if self.turn < 1:
                    self.round = 1
                    self.turn = 1
                    self.phase = "Execution"
                    self.game_over = True
                    self.save_screenshot()
        else:
            self.turn = (self.turn % len(self.players)) + 1
            if self.turn == 1:
                self.round += 1

        self.sync_round_turn()

        if self.gui is not None:
            self.gui.update_round_turn(self, special=False)

        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"game.py | advance_turn | Round: {self.round}, Turn: {self.turn}, Phase: {self.phase}\n")

    def update_strategy_dashboard(self, player: Player) -> None:
        """Sync StrategyDashboard with the current real player state.

        Call this after every settlement/city/road build or resource change.
        """
        for sd in self.strategy_dashboard:
            if sd.player_id == player.id:
                sd.number_of_settlements = len(player.settlements)
                sd.number_of_cities      = len(player.cities)
                sd.number_of_rcards      = player.number_of_rcards
                sd.number_of_dcards      = player.number_of_dcards
                sd.victory_points        = player.points          # or player.victory_points if you use that
                # sd.victory_points_dcard  = sum(...)             # if you track DC VP separately
                # sd.longest_road = ...                           # update only when longest road changes
                # sd.largest_army = ...                           # update only when largest army changes
                break

    def log_event(self, event: List) -> None:
        """Log a game event to FILENAME_MGlog in CSV format.

        Args:
            event: List of [index, value] pairs for logging (indices 1-33).
        """
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"{self.id} | {self.state} | game.py | log_event\n")

        with open(FILENAME_MGLOG, "a") as f:
            x = 2
            for i in event:
                if i[0] == 1:
                    log = str(i[1])
                    f.write(f'"{log}",')
                elif i[0] == x:
                    x += 1
                    f.write(str(i[1]) + ",")
                elif i[0] > x:
                    for y in range(x, i[0]):
                        f.write(",")
                    x = i[0] + 1
                    f.write(str(i[1]))
                    if i[0] == 33:
                        continue
                    f.write(",")
            for y in range(x, 34):
                f.write(",")
            f.write("\n")

    def save_screenshot(self) -> None:
        """Save a screenshot of the game window via the GUI."""
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"{self.id} | {self.state} | game.py | save_screenshot\n")
        self.gui.save_screenshot()

    def write_debug_info(self) -> None:
        """Write game attributes to FILENAME_MG for debugging.

        Args:
            None
        """
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"game.py | write_debug_info | Game ID: {self.id}\n")
                f.write(f" Sequence Number: {self.sequence_number}, Phase: {self.phase}, State: {self.state}, "
                        f"State 1: {self.state_1}, State 2: {self.state_2}\n")
                f.write(f" Round: {self.round}, Turn: {self.turn}, Game Over: {self.game_over}\n")
                f.write(f" Current Player: {self.current_player.id if self.current_player else None}, "
                        f"Winner: {self.winner.id if self.winner else None}\n")
                f.write(f" Longest Road Player: {self.longest_road_player.id if self.longest_road_player else None}, "
                        f"Largest Army Player: {self.largest_army_player.id if self.largest_army_player else None}\n")
                f.write(f" Dice Roll: {self.dice_roll}, Dice Roll History: {self.dice_roll_history}\n")
                f.write(f" Development Cards Stack: {self.dcards_stack}, dice_roll Matrix: {self.dice_roll_matrix}\n")
                f.write(f" Robber Tile Probabilities: {self.robber_tile_probabilities}\n")
                f.write(f" Previous Tile Having Robber: {self.previous_tile_having_robber}, "
                        f"List of Tiles Having Robber: {self.list_of_tiles_having_robber}\n")
                f.write(f" Last Total Turn with dice roll 7: {self.last_total_turn_with_dr7}\n")
                f.write(f" Settings TF (True/ False): {self.settings_tf}, Settings: {vars(self.settings)}\n")
                f.write(f" IP Balanced: {self.initial_placement_balanced}, IP WB: {self.initial_placement_wood_brick}, IP WO: {self.initial_placement_wheat_ore}, "
                        f"IP WOW: {self.initial_placement_wheat_ore_wool}, IP Monopoly: {self.initial_placement_monopoly}\n")
                f.write(f" Tile Type: {self.tile_type}, Resource Type Available: {self.resource_type_available}, "
                        f"Resource Type Occupied: {self.resource_type_occupied}, Resource Type Players: {self.resource_type_players}\n")
                f.write(f" Players Impacted: {self.players_impacted}\n")
                f.write(f" Common Next Settlements: {self.common_next_settlements}, "
                        f"Common New Settlements: {self.common_new_settlements}, "
                        f"Common Next Roads: {self.common_next_roads}\n")
                f.write(f" Last Known Strategies: {self.last_known_strategies}, "
                        f"Last Known Outlooks: {self.last_known_outlooks}\n")
                f.write("game.py | write_debug_info | Strategy Dashboard\n")
                for sd in self.strategy_dashboard:
                    f.write(f" Player {sd.player_id}: Victory Points: {sd.victory_points}, "
                            f"Settlements: {sd.number_of_settlements}, Cities: {sd.number_of_cities}, "
                            f"Dev Card VP: {sd.victory_points_dcard}, Longest Road: {sd.longest_road}, "
                            f"Largest Army: {sd.largest_army}, RCards: {sd.number_of_rcards}, "
                            f"DCards: {sd.number_of_dcards}, Distribution of Tile Values: {sd.distribution_of_tile_values}, "
                            f"Distribution of Tile Types: {sd.distribution_of_tile_types}\n")
                f.write("game.py | write_debug_info | Resource Card Dashboard\n")
                rcd = self.resource_card_dashboard[0]
                f.write(f" Total Resources: {rcd.resource_production_game_total}\n")
                f.write(f" Player Resources: {rcd.resource_production_game_player}\n")
                f.write(f" Player Resource Views: {rcd.resource_production_game_player_view}\n")
                f.write("game.py | write_debug_info | Turn Details\n")
                f.write(f" Round: {self.myturn.round}, Turn: {self.myturn.turn}, Dice Roll: {self.myturn.dice_roll}, "
                        f"Validate Enough: {self.myturn.validate_function_enough}, "
                        f"Validate TwP Match: {self.myturn.validate_function_TwP_Match}, "
                        f"Validate Discard RCards: {self.myturn.validate_function_discard_rcards_by_HP}, "
                        f"Validate Set Robber: {self.myturn.validate_function_set_robber_by_HP}, "
                        f"Validate Outlook Opponents: {self.myturn.validate_function_outlook_opponents_for_HP}, "
                        f"Built Two Roads: {self.myturn.validate_function_built_two_roads}\n")
                f.write(f" Road Built TF: {self.myturn.road_built_in_turn_TF}, "
                        f"Roads Built: {self.myturn.roads_built_in_turn}\n")
                f.write(f" Settlement Built TF: {self.myturn.settlement_built_in_turn_TF}, "
                        f"Settlements Built: {self.myturn.settlements_built_in_turn}\n")
                f.write(f" City Built TF: {self.myturn.city_built_in_turn_TF}, "
                        f"Cities Built: {self.myturn.cities_built_in_turn}\n")
                f.write(f" DCard Played: {self.myturn.dcard_played_in_turn}, "
                        f"DCard Played TF: {self.myturn.dcard_played_in_turn_TF}\n")
                f.write(f" Tile Type Selected 1: {self.myturn.tile_type_selected_1}, "
                        f"Tile Type Selected 2: {self.myturn.tile_type_selected_2}\n")
                f.write(f" Players Too Many RCards: {self.myturn.players_having_too_many_rcards}\n")
                f.write(f" RCard Give: {self.myturn.rcard_give}, RCard Get: {self.myturn.rcard_get}\n")
                f.write(f" List of TwP: {self.myturn.list_of_TwP}, Deals Offered: {self.myturn.number_of_deals_offered}\n")
                f.write(f" TwP Rejected by HP: {self.myturn.list_of_TwP_rejected_by_HP}, "
                        f"TwHP: {self.myturn.list_of_TwHP}, DCard Selected: {self.myturn.dcard_selected}\n")
                f.write(f" Modes: {self.myturn.modes}\n")