"""
Defines the Player class for the Catan game.

This module manages player state, including resource cards, structures (settlements, roads, cities),
development cards, and game statistics. It supports both human and AI players, with attributes
initialized for the initial empty board state and methods for game interactions like building
and trading.

Key components:
    - Player: Represents a player with ID, color, resources, and game statistics.
    - Methods: Handle resource management, building, trade rate updates, and debugging.

Dependencies:
    - typing: For type hints.
    - math: For trade ratio calculations.
    - gui.gui_constants: For player colors.
    - core.constants: For resource and cost constants.
    - core.board: For board interactions (forward reference).
"""
from typing import Dict, List, Tuple, Any
import math
from core.constants import PlayerColor
from core.constants import ResourceCard, COSTS, FNFREQ, FILENAME_FREQ, MG, FILENAME_MG
from core.board import Board

class Player:
    """Represents a player in the Catan game."""

    def __init__(self, id_: int, color: str, sequence: int, 
                 is_human: bool = False, 
                 initial_placement_algorithm: int = 1,
                 human_like_placement: bool = True) -> None:
        """Initialize a Player.
        Args:
            id_: Unique player ID (e.g., 1, 2, 3, or 4).
            color: Player color (e.g., 'Blue', 'Red', 'White', 'Orange').
            sequence: Turn order (1-4).
            is_human: Whether the player is human (True) or AI (False, default).
        Raises:
            ValueError: If the provided color is not a valid PlayerColor.
        """
        valid_colors = [pc.color_name for pc in PlayerColor]
        if color not in valid_colors:
            raise ValueError(f"Invalid color: {color}. Must be one of {valid_colors}")
        self.game = None
        self.color = color
        self.color2 = color
        self.id = id_
        self.is_human = is_human  # Added
        self.gameover_tf = False
        self.sequence = sequence
        self.initial_placement_algorithm = initial_placement_algorithm
        self.human_like_placement = human_like_placement
        self.points = 0
        self.longest_route_tf = False
        self.size_longest_route = 0
        self.structure_longest_route: List[Tuple[int, int]] = []
        self.number_of_clusters = 0
        self.structure_of_clusters: List = []
        self.largest_army_tf = False
        self.size_largest_army = 0
        self.number_of_rcards = 0
        self.number_of_dcards = 0
        self.rcards: Dict[ResourceCard, int] = {rc: 0 for rc in ResourceCard}
        self.dcard_summary = [
            ["victory_point", 0, 0, 0],
            ["knight", 0, 0, 0],
            ["two_free_roads", 0, 0, 0],
            ["year_of_plenty", 0, 0, 0],
            ["monopoly", 0, 0, 0]
        ]
        self.development_cards: List[str] = []
        self.victory_points: int = 0
        self.settlements: List[int] = []
        self.cities: List[int] = []
        self.roads: List[Tuple[int, int]] = []
        self.turn_details_resource_production = [0, 0, 0, 0, 0, 0]
        self.turn_details_resource_production_robber = [0, 0, 0, 0, 0, 0]
        self.turn_details_buy = [0, 0, 0, 0, 0, 0]
        self.turn_details_steal = [0, 0, 0, 0, 0, 0]
        self.turn_details_discard = [0, 0, 0, 0, 0, 0]
        self.turn_details_TwP = [0, 0, 0, 0, 0, 0]
        self.turn_details_last_TwPdeal = [0, 0, 0, 0, 0, 0]
        self.turn_details_TwB = [0, 0, 0, 0, 0, 0]
        self.turn_details_dcard = [0, 0, 0, 0, 0, 0]
        self.trade_rates: Dict[ResourceCard, int] = {rc: 4 for rc in ResourceCard}
        self.port_access: Dict[str, bool] = {
            "3:1": False,
            "2:1 Wheat": False,
            "2:1 Ore": False,
            "2:1 Wood": False,
            "2:1 Brick": False,
            "2:1 Wool": False
        }
        self.last_action: str = "None"

    def add_rcard(self, resource: ResourceCard, amount: int) -> None:
        """Add resource cards to the player's hand.

        Args:
            resource: The resource card type to add (e.g., ResourceCard.WHEAT).
            amount: The number of resource cards to add.

        Examples:
            >>> player.add_rcard(ResourceCard.WOOD, 2)
        """
        self.rcards[resource] = self.rcards.get(resource, 0) + amount
        self.number_of_rcards = sum(self.rcards.get(rc, 0) for rc in ResourceCard)

    def can_afford(self, structure: str) -> bool:
        """Check if the player has enough resource cards to build a structure.

        Args:
            structure: The structure type ('settlement', 'city', 'road', 'development_card').

        Returns:
            bool: True if the player has enough resource cards, False otherwise.
        """
        costs = COSTS.get(structure, {})
        return all(self.rcards.get(res, 0) >= amt for res, amt in costs.items())

    def build_structure(self, structure: str, location: int | Tuple[int, int], board: 'Board') -> bool:
        """Build a structure on the board and update player state.

        Now correctly updates self.settlements and self.cities (including settlement → city upgrade).
        """
        if not self.can_afford(structure):
            return False

        if structure in ["settlement", "city"]:
            if not board.can_build_intersection(location):
                return False

            # Let the board handle the visual / tile state
            board.occupy_intersection(location, structure.capitalize(), self.color)

            if structure == "settlement":
                # First settlement
                if location not in self.settlements:
                    self.settlements.append(location)
                self.victory_points += 1

            elif structure == "city":
                # Upgrade: remove from settlements, add to cities
                if location in self.settlements:
                    self.settlements.remove(location)
                if location not in self.cities:
                    self.cities.append(location)
                self.victory_points += 2   # city gives +2 total (replaces the +1 from settlement)

            self.points = self.victory_points

        elif structure == "road":
            if not board.can_build_road_for_color_tf(list(location), self.color):
                return False
            board.occupy_road(list(location), "Road", self.color)
            self.roads.append(location)

        # Deduct resources
        for rc, amt in COSTS[structure].items():
            self.rcards[rc] -= amt

        self.number_of_rcards = sum(self.rcards.get(rc, 0) for rc in ResourceCard)
        self.last_action = f"Built {structure} at {location}"

        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"player.py | build_structure | {structure} at {location} by player {self.id} "
                        f"(settlements: {len(self.settlements)}, cities: {len(self.cities)})\n")

        return True

    def update_trade_rates(self, board: 'Board') -> None:
        """Update trade rates based on harbor access.

        Args:
            board: The game board instance.
        """
        for intersection_id in self.settlements + self.cities:
            for intersection in board.intersections:
                if intersection.id == intersection_id and intersection.port_tf == True:
                    self.port_access[intersection.port_type] = True
        for port, has_access in self.port_access.items():
            if has_access:
                if port == "3:1":
                    for rc in ResourceCard:
                        self.trade_rates[rc] = min(self.trade_rates[rc], 3)
                elif port.startswith("2:1"):
                    resource_name = port.split(" ")[1]
                    resource = next((r for r in ResourceCard if r.value == resource_name), None)
                    if resource:
                        self.trade_rates[resource] = min(self.trade_rates[resource], 2)

    def get_resource_production_probability(self, board: 'Board') -> Dict[ResourceCard, int]:
        """Calculate the total resource production probability for each resource.

        Args:
            board: The game board instance.

        Returns:
            Dict[ResourceCard, int]: Dictionary mapping resource types to total probability (dots).
        """
        probabilities = {rc: 0 for rc in ResourceCard}
        for intersection_id in self.settlements + self.cities:
            for intersection in board.intersections:
                if intersection.id == intersection_id:
                    for tile_id, prob in zip(intersection.three_tile_ids, intersection.three_tile_probabilities_v2):
                        for tile in board.tiles:
                            if tile and tile.id == tile_id:
                                resource = next((r for r in ResourceCard if r.value == tile.type), None)
                                if resource:
                                    multiplier = 2 if intersection_id in self.cities else 1
                                    probabilities[resource] += prob * multiplier
        return probabilities

    def rcards_in_hand(self) -> Tuple[List[int], List[int], List[int]]:
        """Retrieve resource cards in the player's hand and their trade ratios.

        Args:
            None

        Returns:
            Tuple[List[int], List[int], List[int]]: A tuple containing:
                - Resource counts [Wheat, Ore, Wood, Brick, Wool].
                - Trade ratios for each resource.
                - Trade ratios in terms of resource counts.

        Examples:
            >>> player.rcards_in_hand()
            ([0, 0, 0, 0, 0], [4, 4, 4, 4, 4], [0, 0, 0, 0, 0])
        """
        if FNFREQ == "Y":
            with open(FILENAME_FREQ, "a") as f:
                f.write(f"{self.game.sequence_number} | {self.game.state} | player.py | rcards_in_hand\n")
        rcards5 = [
            self.rcards.get(ResourceCard.WHEAT, 0),
            self.rcards.get(ResourceCard.ORE, 0),
            self.rcards.get(ResourceCard.WOOD, 0),
            self.rcards.get(ResourceCard.BRICK, 0),
            self.rcards.get(ResourceCard.WOOL, 0)
        ]
        trade_ratio = [self.trade_rates.get(res, 4) for res in [
            ResourceCard.WHEAT, ResourceCard.ORE, ResourceCard.WOOD,
            ResourceCard.BRICK, ResourceCard.WOOL
        ]]
        trade_ratio_in_rcards5 = [int(math.floor(rcards5[i] / trade_ratio[i])) for i in range(5)]
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"player.py | rcards_in_hand for Player: {self.id} | rcards5: {rcards5} | TR: {trade_ratio} | TRinR5: {trade_ratio_in_rcards5}\n")
        return rcards5, trade_ratio, trade_ratio_in_rcards5
   
    def write_debug_info(self) -> None:
        """Write player attributes to FILENAME_MG for debugging.

        Args:
            None
        """
        if MG:
            with open(FILENAME_MG, "a") as f:
                f.write(f"player.py | write_debug_info | Player ID: {self.id}\n")
                f.write(f" Color: {self.color}, Sequence: {self.sequence}\n")
                f.write(f" Victory Points: {self.victory_points}, Points: {self.points}\n")
                f.write(f" Longest Route: {self.longest_route_tf}, Size: {self.size_longest_route}, "
                        f"Structure: {self.structure_longest_route}\n")
                f.write(f" Largest Army: {self.largest_army_tf}, Size: {self.size_largest_army}\n")
                f.write(f" Number of Resource Cards: {self.number_of_rcards}, Number of Dev Cards: {self.number_of_dcards}\n")
                f.write(f" Resource Cards: {self.rcards}\n")
                f.write(f" Development Cards: {self.development_cards}, DCard Summary: {self.dcard_summary}\n")
                f.write(f" Settlements: {self.settlements}, Cities: {self.cities}, Roads: {self.roads}\n")
                f.write(f" Port Access: {self.port_access}\n")
                f.write(f" Last Action: {self.last_action}\n")
                rcards, trade_ratio, trade_ratio_in_rcards = self.rcards_in_hand()
                f.write(f" Resouce Cards in Hand: {rcards}, Trade Ratio: {trade_ratio}, "
                        f"Trade Ratio in RCards: {trade_ratio_in_rcards}\n")

    @staticmethod
    def _safe_float(val: Any) -> float:
        """Safe conversion to float, returns 0.0 on failure."""
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def has_harbor(self) -> bool:
        """Return True if the player owns at least one settlement or city on a harbor/port intersection."""
        for inter_id in self.settlements + self.cities:
            inter = self.game.board.intersections[inter_id]
            if inter and (getattr(inter, "port_tf", False) or getattr(inter, "harborYN", "N") == "Y"):
                return True
        return False

    def get_current_production_pips(self, board: 'Board') -> List[float]:
        pips = [0.0] * 5
        for inter_id in self.settlements + self.cities:
            inter = board.intersections[inter_id]
            if not inter:
                continue
            probs = getattr(inter, "all_tile_probabilities",
                            getattr(inter, "three_tile_probabilities_v2",
                                    getattr(inter, "three_tile_probabilities", [0.0]*5)))
            types = getattr(inter, "all_tile_types", [0]*5)
            multiplier = 2 if inter_id in self.cities else 1
            for idx in range(5):
                if types[idx] > 0:
                    pips[idx] += Player._safe_float(probs[idx]) * multiplier
        return pips
    
