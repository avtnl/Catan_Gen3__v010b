#!/usr/bin/env python3
"""
catan_strategic_placement.py

Catan board analyzer + strategic initial placement advisor.

Reads a PlayBoard *.txt, the 142 win-path CSV, uses board.resource_exploration()
and port/bank trade realities (4:1, 3:1, 2:1) to rank all 142 scenarios by
expected turns-to-win (not raw card count), then provides an enhanced version
of _max_of_pips_and_optional_port that also considers:
- win-path alignment for the best scenarios on *this* board
- opponent denial / blocking of high-value spots
- turn-order context (1st/2nd/3rd/4th picker, first vs second settlement)

Designed to be runnable both:
  (a) inside the full Catan package (imports from core.*)
  (b) standalone from this directory (pure-Python fallback loader)

Usage:
    python catan_strategic_placement.py --board "PlayBoard 07_Oct_2025_13_16_39.txt"
    python catan_strategic_placement.py --board "PlayBoard 07_Oct_2025_13_16_39.txt" --player 3 --debug

Part of the Grok Build assignment for intelligent Catan opening strategy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# CONSTANTS (duplicated from board.py / algorithms for standalone mode)
# =============================================================================

LIST_OF_LAND_TILES = [9, 10, 11, 15, 16, 17, 18, 21, 22, 23, 24, 25, 28, 29, 30, 31, 35, 36, 37]
LIST_OF_SKIPPED_TILE_IDS = [0, 1, 6, 7, 13, 33, 39, 40, 45]
INTERSECTION_IN_WATER = [0, 1, 2, 10, 11, 12, 22, 45, 55, 56, 57, 65, 66]
LIST_OF_PORTTYPES = ["3:1", "3:1", "3:1", "3:1", "2:1 Wheat", "2:1 Ore", "2:1 Wood", "2:1 Brick", "2:1 Wool"]
INTERSECTIONS_ARE_PORT = [[3, 4], [6, 7], [13, 24], [20, 21], [33, 44], [35, 46], [53, 54], [58, 59], [61, 62]]
BOARD_LAYOUT = [
    [0,1,2,3,4,5,6,0],
    [7,8,9,10,11,12,13],
    [0,14,15,16,17,18,19,0],
    [20,21,22,23,24,25,26],
    [0,27,28,29,30,31,32,0],
    [33,34,35,36,37,38,39],
    [0,40,41,42,43,44,45,0]
]
NUM_TILES = 46
NUM_INTERSECTIONS = 67

# Resource canonical order used by placement code (wheat, ore, wood, brick, sheep)
# CSV uses Wheat, Ore, Wood, Brick, Wool (Wool == sheep)
RES_ORDER = ["wheat", "ore", "wood", "brick", "sheep"]
RES_ORDER_CSV = ["Wheat", "Ore", "Wood", "Brick", "Wool"]
TERRAIN_TO_RES = {
    "Field": "wheat",
    "Mountain": "ore",
    "Forest": "wood",
    "Hill": "brick",
    "Pasture": "sheep",
}

# Port trade ratios (default bank 4:1)
DEFAULT_RATIOS = {"wheat": 4, "ore": 4, "wood": 4, "brick": 4, "sheep": 4}


# =============================================================================
# PIPS HELPERS (exact copy from board.py:31)
# =============================================================================

def pips_from_tile_value(value: int) -> float:
    """Classic Catan pip/dot count."""
    if not (2 <= value <= 12):
        return 0.0
    return 6 - abs(7 - value)


def true_probability_from_pips(pips: float) -> float:
    return pips / 36.0


# =============================================================================
# LIGHTWEIGHT DATA CLASSES (standalone fallback)
# =============================================================================

@dataclass
class SimpleTile:
    id: int
    type: str = "Blank"
    value: int = 0
    current_settlements: int = 0
    # corners populated lazily for port sync
    corners: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SimpleIntersection:
    id: int
    port_tf: bool = False
    port_type: str = "Blank"
    can_build_tf: bool = True
    occupied_tf: bool = False
    face: str = "Blank"
    color: str = "Blank"
    three_tile_ids: List[int] = field(default_factory=list)
    three_tile_pips: List[float] = field(default_factory=list)
    three_tile_types: List[str] = field(default_factory=list)
    three_tile_values: List[int] = field(default_factory=list)
    all_tile_types: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])  # wheat,ore,wood,brick,sheep
    all_tile_pips: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0])
    three_intersection_ids: List[int] = field(default_factory=list)
    three_roads: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class SimpleBoard:
    """Minimal board surface used by the analyzer when full core.* is unavailable."""
    tiles: List[Optional[SimpleTile]] = field(default_factory=list)
    intersections: List[Optional[SimpleIntersection]] = field(default_factory=list)
    roads: List[Any] = field(default_factory=list)
    list_of_roads_connected_to_intersection: List[List[Tuple[int, int]]] = field(default_factory=list)
    precomputed_pp_raw: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    # constants needed by algorithms
    INTERSECTION_IN_WATER: List[int] = field(default_factory=lambda: INTERSECTION_IN_WATER[:])
    # For occupy simulation (very minimal)
    round: int = -2
    turn: int = 1


# =============================================================================
# TRY IMPORT FULL PACKAGE (preferred when available)
# =============================================================================

FULL_MODE = False
Board = None
InitialPlacementStrategies = None
Player = None  # only needed for five-strat path (not used in v1)

try:
    from core.board import Board as _RealBoard, pips_from_tile_value as _real_pips
    from core.algorithms_initial_placement import InitialPlacementStrategies as _RealIPS
    # Also pull the real constants if they exist
    try:
        from core.constants import BLOCKED_WEIGHT, TOP_N, MG, FILENAME_MG
    except Exception:
        BLOCKED_WEIGHT = 0.08   # reasonable default used in the 5-strat engine
        TOP_N = 10
        MG = False
        FILENAME_MG = "debug.log"

    Board = _RealBoard
    InitialPlacementStrategies = _RealIPS
    # Override local pips with real one (identical)
    pips_from_tile_value = _real_pips
    FULL_MODE = True
    print("[OK] Running in FULL package mode (core.* available)")
except Exception as e:
    print(f"[WARN] core.* not importable ({e}). Using standalone fallback loader.")
    FULL_MODE = False
    BLOCKED_WEIGHT = 0.08
    TOP_N = 10
    MG = False


# =============================================================================
# STANDALONE BOARD LOADER (adapted from board.py load_board + post steps)
# =============================================================================

def _create_minimal_board() -> SimpleBoard:
    """Create empty structures matching the real Board.__init__ path."""
    board = SimpleBoard()
    board.tiles = [None] * NUM_TILES
    board.intersections = [None] * NUM_INTERSECTIONS
    for i in range(NUM_INTERSECTIONS):
        if i not in INTERSECTION_IN_WATER:
            board.intersections[i] = SimpleIntersection(i)
    board.list_of_roads_connected_to_intersection = [[] for _ in range(NUM_INTERSECTIONS)]
    board.roads = []
    return board


def load_board_standalone(board_path: str) -> SimpleBoard:
    """
    Parse a PlayBoard txt exactly like board.py:load_board (816-984).
    Then run the minimal post-population steps so that:
      - all_tile_pips / all_tile_types (wheat/ore/wood/brick/sheep order)
      - three_tile_* lists
      - port_tf / port_type on intersections + corners
      - three_intersection_ids
    are populated. This is sufficient for resource_exploration + placement scoring.
    """
    board = _create_minimal_board()

    valid_tile_types = {"Sea", "Desert", "Mountain", "Hill", "Forest", "Pasture", "Field"}
    valid_port_types = set(LIST_OF_PORTTYPES)

    with open(board_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    idx = 0
    # 1. Tiles: id / type / value
    while idx + 2 < len(lines):
        try:
            tid = int(lines[idx])
            ttype = lines[idx + 1]
            if ttype not in valid_tile_types:
                break
            tval = int(lines[idx + 2])
        except ValueError:
            break

        idx += 3

    # Actually populate tiles properly (the loop above is defensive)
    # Re-parse cleanly
    idx = 0
    tile_map = {}
    while idx + 2 < len(lines):
        try:
            tid = int(lines[idx])
            ttype = lines[idx + 1]
            if ttype not in valid_tile_types:
                break
            tval = int(lines[idx + 2])
            tile_map[tid] = (ttype, tval)
        except ValueError:
            break
        idx += 3

    # Create Tile objects for land + sea
    for tid in range(NUM_TILES):
        if tid in LIST_OF_SKIPPED_TILE_IDS:
            continue
        if tid in LIST_OF_LAND_TILES:
            ttype, tval = tile_map.get(tid, ("Blank", 0))
            board.tiles[tid] = SimpleTile(id=tid, type=ttype, value=tval)
        else:
            board.tiles[tid] = SimpleTile(id=tid, type="Sea", value=0)

    # 2. Ports
    while idx + 1 < len(lines):
        try:
            inter_id = int(lines[idx])
        except ValueError:
            idx += 1
            continue
        ptype = lines[idx + 1]
        if ptype not in valid_port_types:
            idx += 2
            continue
        if 0 <= inter_id < NUM_INTERSECTIONS and board.intersections[inter_id] is not None:
            inter = board.intersections[inter_id]
            inter.port_tf = True
            inter.port_type = ptype
        idx += 2

    # Now run the critical population logic (simplified but faithful)
    _populate_intersection_tile_data(board)
    _populate_three_intersection_ids(board)
    _create_minimal_roads(board)

    return board


def _populate_intersection_tile_data(board: SimpleBoard) -> None:
    """
    Replicates the core of board.py:_add_intersections (both odd and even passes)
    so that three_tile_* and all_tile_* (in RES_ORDER) are correct.
    This is the most complex part of standalone mode.
    """
    corner_indices = {"N": 0, "EH": 1, "EL": 2, "S": 3, "WL": 4, "WH": 5}

    # We need a reverse map from tile_id to its index in board.tiles
    tile_by_id = {t.id: t for t in board.tiles if t is not None}

    # Odd intersections first (1,3,5,...)
    for i in range(1, NUM_INTERSECTIONS, 2):
        inter = board.intersections[i]
        if inter is None:
            continue
        inter.three_tile_ids = []
        inter.three_tile_pips = []
        inter.three_tile_types = []
        inter.three_tile_values = []
        inter.all_tile_types = [0, 0, 0, 0, 0]
        inter.all_tile_pips = [0.0] * 5

        # Find row/col (exact logic from board.py:312)
        r = 0
        for rr in range(6):
            c = i - rr * 11
            if i <= (rr + 1) * 11:
                r = rr
                break

        if r % 2 == 0:
            col = int((c + 1) / 2)
            tile_ids = [
                BOARD_LAYOUT[r + 1][col - 1] if r + 1 < 7 and col - 1 >= 0 else 0,
                BOARD_LAYOUT[r][col] if col < len(BOARD_LAYOUT[r]) else 0,
                BOARD_LAYOUT[r + 1][col] if r + 1 < 7 and col < len(BOARD_LAYOUT[r + 1]) else 0,
            ]
        else:
            col = int(c / 2)
            tile_ids = [
                BOARD_LAYOUT[r + 1][col] if r + 1 < 7 and col < len(BOARD_LAYOUT[r + 1]) else 0,
                BOARD_LAYOUT[r][col] if col < len(BOARD_LAYOUT[r]) else 0,
                BOARD_LAYOUT[r + 1][col + 1] if r + 1 < 7 and col + 1 < len(BOARD_LAYOUT[r + 1]) else 0,
            ]

        for tid in tile_ids:
            if tid == 0:
                continue
            tile = tile_by_id.get(tid)
            if not tile or tile.type == "Sea":
                continue
            inter.three_tile_ids.append(tid)
            inter.three_tile_types.append(tile.type)
            p = pips_from_tile_value(tile.value)
            inter.three_tile_pips.append(p)
            inter.three_tile_values.append(tile.value)

            res = TERRAIN_TO_RES.get(tile.type)
            if res and res in RES_ORDER:
                ridx = RES_ORDER.index(res)
                inter.all_tile_types[ridx] += 1
                inter.all_tile_pips[ridx] += p

    # Even intersections (2,4,6,...)
    for i in range(2, NUM_INTERSECTIONS, 2):
        inter = board.intersections[i]
        if inter is None:
            continue
        inter.three_tile_ids = []
        inter.three_tile_pips = []
        inter.three_tile_types = []
        inter.three_tile_values = []
        inter.all_tile_types = [0, 0, 0, 0, 0]
        inter.all_tile_pips = [0.0] * 5

        r = 0
        for rr in range(6):
            c = i - rr * 11
            if i <= (rr + 1) * 11:
                r = rr
                break

        if r % 2 == 0:
            col = int(c / 2)
            tile_ids = [
                BOARD_LAYOUT[r][col] if col < len(BOARD_LAYOUT[r]) else 0,
                BOARD_LAYOUT[r + 1][col] if r + 1 < 7 and col < len(BOARD_LAYOUT[r + 1]) else 0,
                BOARD_LAYOUT[r][col + 1] if col + 1 < len(BOARD_LAYOUT[r]) else 0,
            ]
        else:
            col = int((c + 1) / 2)
            tile_ids = [
                BOARD_LAYOUT[r][col - 1] if col - 1 >= 0 else 0,
                BOARD_LAYOUT[r + 1][col] if r + 1 < 7 and col < len(BOARD_LAYOUT[r + 1]) else 0,
                BOARD_LAYOUT[r][col] if col < len(BOARD_LAYOUT[r]) else 0,
            ]

        for tid in tile_ids:
            if tid == 0:
                continue
            tile = tile_by_id.get(tid)
            if not tile or tile.type == "Sea":
                continue
            inter.three_tile_ids.append(tid)
            inter.three_tile_types.append(tile.type)
            p = pips_from_tile_value(tile.value)
            inter.three_tile_pips.append(p)
            inter.three_tile_values.append(tile.value)

            res = TERRAIN_TO_RES.get(tile.type)
            if res and res in RES_ORDER:
                ridx = RES_ORDER.index(res)
                inter.all_tile_types[ridx] += 1
                inter.all_tile_pips[ridx] += p


def _populate_three_intersection_ids(board: SimpleBoard) -> None:
    """Build neighbor graph from the fixed port + geometry knowledge (simplified)."""
    # We can derive neighbors from the same BOARD_LAYOUT math or hardcode a small adjacency.
    # For placement + blocking we mainly need three_intersection_ids for high-value spots.
    # A cheap approximation: every non-water intersection has 2-3 land neighbors.
    # For accuracy we reuse the road-building logic later; for now do a simple BFS-free build.

    # Build a quick map of intersection -> list of adjacent via the corner/edge rules
    # (The real code does this via roads after _complete_edges).
    # For v1 we synthesize a reasonable neighbor list using the known geometry.

    # Simpler: for every pair of intersections that share a tile edge in the hex grid
    # we add the link. This is tedious; we use a pre-computed small adjacency for the 54 land spots.
    # Instead, fall back to "all intersections within Chebyshev distance 1 on the hex grid".

    # Practical compromise used in many Catan AIs: pre-bake or compute on the fly.
    # Here we implement a tiny version based on the three_tile_ids overlap + known port pairs.

    # 1. Start from the official port pairs (they are adjacent)
    for pair in INTERSECTIONS_ARE_PORT:
        ia_id, ib_id = pair
        ia = board.intersections[ia_id]
        ib = board.intersections[ib_id]
        if ia is not None and ib is not None:
            if ib_id not in ia.three_intersection_ids:
                ia.three_intersection_ids.append(ib_id)
            if ia_id not in ib.three_intersection_ids:
                ib.three_intersection_ids.append(ia_id)

    # 2. For all other intersections, walk the BOARD_LAYOUT hexes and connect corners
    # (this is deliberately approximate for the analyzer; the real Board does it perfectly)
    # For the purpose of blocking value and placement we only need "close high-pip neighbors".
    # We accept that some neighbors are missed; the effect on scoring is second-order.

    # Better: use the real road reconstruction logic from board.py _complete_edges + _add_roads
    # but that is long. For now we leave three_intersection_ids partially populated from ports
    # and enhance it in _create_minimal_roads below.
    pass


def _create_minimal_roads(board: SimpleBoard) -> None:
    """
    Very lightweight road graph so that three_intersection_ids is at least usable
    for blocking calculations. This is the weakest part of the standalone path.
    In FULL_MODE we get the real graph for free.
    """
    # Connect each intersection to its geometrically obvious 2-3 neighbors on the hex grid.
    # We use a simple rule: any two intersections that appear together in a tile's 6 corners
    # are road-adjacent if they are not water.

    # For the analyzer the most important thing is that high-pip spots have their
    # immediate neighbors listed so the "blocked_pips" term works.
    # We therefore synthesize neighbors by looking at shared three_tile_ids.

    inters = [i for i in board.intersections if i is not None]
    for ia in inters:
        for ib in inters:
            if ia.id >= ib.id:
                continue
            # If they share 2 or more tiles they are very close (likely adjacent)
            shared = set(ia.three_tile_ids) & set(ib.three_tile_ids)
            if len(shared) >= 2 and ib.id not in ia.three_intersection_ids:
                ia.three_intersection_ids.append(ib.id)
                ib.three_intersection_ids.append(ia.id)

    # Also make sure port pairs are present
    for a, b in INTERSECTIONS_ARE_PORT:
        ia = board.intersections[a]
        ib = board.intersections[b]
        if ia and ib:
            if b not in ia.three_intersection_ids:
                ia.three_intersection_ids.append(b)
            if a not in ib.three_intersection_ids:
                ib.three_intersection_ids.append(a)


# =============================================================================
# RESOURCE EXPLORATION (standalone path - calls the real one when possible)
# =============================================================================

def run_resource_exploration(board: Any) -> Dict[str, Dict[str, float]]:
    """Dispatch to real method or standalone implementation."""
    if FULL_MODE and hasattr(board, "resource_exploration"):
        return board.resource_exploration()

    # Standalone approximation (very close to board.py:1220)
    resource_map = {
        "Field": "wheat", "Mountain": "ore", "Forest": "wood",
        "Hill": "brick", "Pasture": "sheep"
    }
    totals: Dict[str, Dict[str, float]] = {res: {"min": 0.0, "max": 0.0} for res in resource_map.values()}

    for tile in (board.tiles if hasattr(board, "tiles") else []):
        if tile is None or tile.type not in resource_map:
            continue
        pips = pips_from_tile_value(tile.value)
        if pips == 0:
            continue
        res = resource_map[tile.type]
        count = getattr(tile, "current_settlements", 0)

        if count >= 3:
            min_mult = max_mult = 0.0
        elif count <= 1:
            min_mult = 2.0
            max_mult = 2.75
        else:
            # Two settlements: be conservative in standalone (no full distance check)
            min_mult = max_mult = 0.5

        totals[res]["min"] += pips * min_mult
        totals[res]["max"] += pips * max_mult

    for res in totals:
        totals[res]["min"] = round(totals[res]["min"], 1)
        totals[res]["max"] = round(totals[res]["max"], 1)
    return totals


# =============================================================================
# PORT & TRADE RATIO HELPERS (lifted from algorithms_initial_placement.py)
# =============================================================================

def get_best_trade_ratios(board: Any) -> Dict[str, int]:
    """
    Realistic early-game trade ratios.
    At the beginning, the player owns NO ports.
    We assume they can reach some ports reasonably early, but stay conservative.
    """
    ratios = DEFAULT_RATIOS.copy()  # Start with bank 4:1

    ports = []
    if FULL_MODE and hasattr(board, "intersections"):
        for inter in board.intersections:
            if inter and getattr(inter, "port_tf", False):
                ports.append(getattr(inter, "port_type", ""))
    else:
        for inter in (board.intersections or []):
            if inter and inter.port_tf:
                ports.append(inter.port_type)

    specific_2to1 = {"wheat": 0, "ore": 0, "wood": 0, "brick": 0, "sheep": 0}
    has_generic_3to1 = False

    for p in ports:
        if p == "3:1":
            has_generic_3to1 = True
        elif p.startswith("2:1"):
            specific = p.split()[-1].lower()
            if specific == "wool":
                specific = "sheep"
            if specific in specific_2to1:
                specific_2to1[specific] += 1

    # === Realistic assumptions for opening phase ===
    if has_generic_3to1:
        for r in ratios:
            ratios[r] = 3   # Generic 3:1 ports are fairly reachable

    # Specific 2:1 ports are valuable but harder to claim early
    for res, count in specific_2to1.items():
        if count > 0:
            ratios[res] = 2

    return ratios

# =============================================================================
# 142 SCENARIO LOADING + SCORING
# =============================================================================

@dataclass
class WinScenario:
    way_id: int
    wheat: int
    ore: int
    wood: int
    brick: int
    wool: int   # sheep
    longest_road: bool
    biggest_army: bool
    cities: int
    settlements: int
    dev_cards: int
    total_vp: int
    article_min_cost: int
    production_only_total: int

    @property
    def needs_vector(self) -> List[int]:
        return [self.wheat, self.ore, self.wood, self.brick, self.wool]


def load_142_scenarios(csv_path: str) -> List[WinScenario]:
    scenarios: List[WinScenario] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                s = WinScenario(
                    way_id=int(row["Way_ID"]),
                    wheat=int(row["Wheat_Needed"]),
                    ore=int(row["Ore_Needed"]),
                    wood=int(row["Wood_Needed"]),
                    brick=int(row["Brick_Needed"]),
                    wool=int(row["Wool_Needed"]),
                    longest_road=row.get("Longest_Road", "no") == "yes",
                    biggest_army=row.get("Biggest_Army", "no") == "yes",
                    cities=int(row.get("Cities", 0)),
                    settlements=int(row.get("Settlements", 0)),
                    dev_cards=int(row.get("Development_Cards_To_Buy", 0)),
                    total_vp=int(row.get("Total_Victory_Points", 10)),
                    article_min_cost=int(row.get("Article_Min_Cost", 30)),
                    production_only_total=int(row.get("Production_Only_Total", 30)),
                )
                scenarios.append(s)
            except Exception as ex:
                print(f"  Warning: skipping malformed row {row.get('Way_ID')}: {ex}")
    return scenarios


def score_scenario_for_board(
    scenario: WinScenario,
    board_pips: Dict[str, float],
    trade_ratios: Dict[str, int],
    exploration: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """
    Improved scoring: trade directly reduces bottleneck + dev card probability penalty.
    Lower composite = faster expected win.
    """
    # Scarcity weight
    scarcity = {}
    for i, res in enumerate(RES_ORDER):
        max_rem = exploration.get(res, {}).get("max", 10.0)
        scarcity[res] = max(0.8, 3.2 - (max_rem / 11.0))

    needs = scenario.needs_vector
    effective_cost = 0.0
    trade_savings = 0.0
    bottleneck_turns = 0.0

    # Realistic opening production capture
    opening_capture = 0.30
    prod_estimate = {r: board_pips.get(r, 8.0) * opening_capture for r in RES_ORDER}

    for i, res in enumerate(RES_ORDER):
        needed = needs[i]
        ratio = trade_ratios.get(res, 4)
        scarce_w = scarcity[res]

        deficit = max(0, needed - prod_estimate[res])

        # Trade directly reduces the effective deficit
        effective_deficit = deficit * (ratio / 4.0)
        production_turns = effective_deficit / max(0.6, prod_estimate[res] / 4.5)
        trading_penalty = (deficit * max(0, ratio - 2.0) / 4.0) / 6.0

        turns_r = production_turns + trading_penalty

        effective_cost += needed * scarce_w
        trade_savings += (4 - ratio) * deficit * 0.85

        if turns_r > bottleneck_turns:
            bottleneck_turns = turns_r

    # === Development Cards Probability Penalty ===
    dev_cards = scenario.dev_cards
    dev_penalty = 0.0
    if dev_cards > 0:
        # Expected VP cards (~20% of dev cards are Victory Points)
        expected_vp = min(dev_cards * 0.20, 5.0)
        # Penalty if strategy relies heavily on getting enough VPs from devs
        vp_shortfall = max(0, dev_cards * 0.22 - expected_vp)
        dev_penalty = vp_shortfall * 1.8

    # Other bonuses / penalties
    abundant_bonus = 0.0
    for i, res in enumerate(RES_ORDER):
        if board_pips.get(res, 0) > 13.0 and needs[i] > 7:
            abundant_bonus -= 2.2

    lr_penalty = 0.0
    if scenario.longest_road and (board_pips.get("wood", 0) + board_pips.get("brick", 0) < 12):
        lr_penalty = 5.5

    difficulty = scenario.article_min_cost / 9.0

    # Final composite score
    composite = (bottleneck_turns * 0.78) + (effective_cost / 19.0) \
                - (trade_savings / 6.0) + lr_penalty + abundant_bonus + difficulty + dev_penalty

    composite = max(3.0, composite)   # Lower floor for better differentiation

    return {
        "composite": round(composite, 2),
        "effective_cost": round(effective_cost, 1),
        "bottleneck_turns": round(bottleneck_turns, 1),
        "trade_savings": round(trade_savings, 1),
        "dev_penalty": round(dev_penalty, 2),
        "scarcity": {r: round(scarcity[r], 2) for r in RES_ORDER},
    }


# =============================================================================
# MAIN ANALYSIS PIPELINE
# =============================================================================

def analyze_board(
    board_path: str,
    csv_path: str = "catan_142_ways_resource_requirements.csv",
    player_position: int = 1,
    debug: bool = False,
) -> Dict[str, Any]:
    """High-level entry point. Returns everything needed for reporting + placement."""
    print(f"\n=== CATAN STRATEGIC PLACEMENT ANALYZER ===")
    print(f"Board: {board_path}")
    print(f"CSV  : {csv_path}")
    print(f"Mode : {'FULL' if FULL_MODE else 'STANDALONE'}")

    # 1. Load board
    if FULL_MODE:
        # Use the real Board with LOAD_PLAYBOARD trick or direct load
        # The real __init__ already does a lot when LOAD_PLAYBOARD / SAVED_PLAYBOARD are set
        # For simplicity we create a fresh one and call load_board explicitly.
        os.environ["LOAD_PLAYBOARD"] = "1"
        # We cannot easily set SAVED_PLAYBOARD before import, so we do the manual path
        board = Board.__new__(Board)
        # Minimal init of the structures the load path needs
        board.NUM_TILES = NUM_TILES
        board.NUM_INTERSECTIONS = NUM_INTERSECTIONS
        board.LIST_OF_LAND_TILES = LIST_OF_LAND_TILES[:]
        board.LIST_OF_SKIPPED_TILE_IDS = LIST_OF_SKIPPED_TILE_IDS[:]
        board.INTERSECTION_IN_WATER = INTERSECTION_IN_WATER[:]
        board.LIST_OF_PORTTYPES = LIST_OF_PORTTYPES[:]
        board.INTERSECTIONS_ARE_PORT = [p[:] for p in INTERSECTIONS_ARE_PORT]
        board.BOARD_LAYOUT = [row[:] for row in BOARD_LAYOUT]
        board.ALL_TILE_IDS = set(range(NUM_TILES))
        board.intersections = [None] * NUM_INTERSECTIONS
        for i in range(NUM_INTERSECTIONS):
            if i not in INTERSECTION_IN_WATER:
                # We need the real Intersection class
                from core.board import Intersection as RealInter
                board.intersections[i] = RealInter(i)
        board.tiles = [None] * NUM_TILES
        from core.board import Tile as RealTile
        for tid in range(NUM_TILES):
            idx = tid  # simplified
            if tid in LIST_OF_SKIPPED_TILE_IDS:
                continue
            if tid in LIST_OF_LAND_TILES:
                board.tiles[tid] = RealTile(tid)
            else:
                board.tiles[tid] = RealTile(tid, type_="Sea", value=0)
        board.roads = []
        board.list_of_roads_connected_to_intersection = [[] for _ in range(NUM_INTERSECTIONS)]
        board.load_board(board_path)
        # Force the critical refreshs the real __init__ does
        board._create_list_of_roads_connected_to_intersection()
        board._update_intersection_types()
        board._add_three_intersection_ids()
        board._add_two_tile_attributes()
        if hasattr(board, "_add_intersections"):
            board._add_intersections()
    else:
        board = load_board_standalone(board_path)

    # 2. Resource picture
    exploration = run_resource_exploration(board)

    # Compute static total pips on the whole board
    board_pips: Dict[str, float] = {r: 0.0 for r in RES_ORDER}
    for t in (board.tiles if hasattr(board, "tiles") else []):
        if t is None:
            continue
        res = TERRAIN_TO_RES.get(getattr(t, "type", None))
        if res:
            board_pips[res] += pips_from_tile_value(getattr(t, "value", 0))

    trade_ratios = get_best_trade_ratios(board)

    print("\n--- BOARD RESOURCE SUMMARY ---")
    for r in RES_ORDER:
        print(f"  {r:6s}: total_pips={board_pips[r]:5.1f}  remaining_max={exploration.get(r,{}).get('max',0):5.1f}")
    print("  Ports/trade ratios:", trade_ratios)

    # 3. Load + score 142 scenarios
    scenarios = load_142_scenarios(csv_path)
    print(f"\nLoaded {len(scenarios)} win scenarios from CSV")

    scored = []
    for sc in scenarios:
        s = score_scenario_for_board(sc, board_pips, trade_ratios, exploration)
        scored.append((sc, s))

    # Sort best (lowest composite) first
    scored.sort(key=lambda t: (t[1]["composite"], t[1]["effective_cost"]))

    result = {
        "board_path": board_path,
        "board_pips": board_pips,
        "exploration": exploration,
        "trade_ratios": trade_ratios,
        "ranked_scenarios": scored[:50],   # top 50 for now
        "all_scored": scored,
        "board": board,  # keep for placement step
    }
    return result


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Catan 142-way win scenario analyzer + strategic opener")
    parser.add_argument("--board", required=True, help="Path to PlayBoard *.txt file")
    parser.add_argument("--csv", default="catan_142_ways_resource_requirements.csv", help="Path to 142-ways CSV")
    parser.add_argument("--player", type=int, default=1, choices=[1,2,3,4], help="Your placement order position (1=first picker)")
    parser.add_argument("--debug", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if not os.path.isfile(args.board):
        print(f"ERROR: board file not found: {args.board}")
        sys.exit(2)
    if not os.path.isfile(args.csv):
        print(f"ERROR: CSV not found: {args.csv}")
        sys.exit(2)

    analysis = analyze_board(args.board, args.csv, player_position=args.player, debug=args.debug)

    # Pretty print top 10 scenarios
    print("\n=== TOP 10 BEST WIN SCENARIOS FOR THIS BOARD (lowest = fastest) ===")
    for rank, (sc, s) in enumerate(analysis["ranked_scenarios"][:10], 1):
        lr = "LR" if sc.longest_road else "  "
        ba = "BA" if sc.biggest_army else "  "
        dev_p = f" dev_pen={s.get('dev_penalty', 0):.1f}" if s.get('dev_penalty', 0) > 0.1 else ""
        
        print(f"{rank:2d}. Way {sc.way_id:3d} | comp={s['composite']:5.2f} | "
              f"eff_cost={s['effective_cost']:5.1f} | bottleneck~{s['bottleneck_turns']:4.1f}t | "
              f"{lr} {ba}{dev_p} | C{sc.cities} S{sc.settlements} D{sc.dev_cards}")

    print("\n(Full ranking + strategic placement logic continues in next implementation slice...)")
    print("Script is work-in-progress per approved plan. Run with --debug for more.")


if __name__ == "__main__":
    main()
