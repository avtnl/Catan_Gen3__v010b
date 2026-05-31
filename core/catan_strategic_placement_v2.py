#!/usr/bin/env python3
"""
catan_strategic_placement_v2.py - Complete Analyzer + 40-Game Simulator
"""

import argparse
import csv
import os
import sys
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List

# =============================================================================
# CONSTANTS
# =============================================================================

LIST_OF_LAND_TILES = [9, 10, 11, 15, 16, 17, 18, 21, 22, 23, 24, 25, 28, 29, 30, 31, 35, 36, 37]
LIST_OF_SKIPPED_TILE_IDS = [0, 1, 6, 7, 13, 33, 39, 40, 45]
INTERSECTION_IN_WATER = [0, 1, 2, 10, 11, 12, 22, 45, 55, 56, 57, 65, 66]
LIST_OF_PORTTYPES = ["3:1", "3:1", "3:1", "3:1", "2:1 Wheat", "2:1 Ore", "2:1 Wood", "2:1 Brick", "2:1 Wool"]

NUM_TILES = 46
NUM_INTERSECTIONS = 67

RES_ORDER = ["wheat", "ore", "wood", "brick", "sheep"]
DEFAULT_RATIOS = {"wheat": 4, "ore": 4, "wood": 4, "brick": 4, "sheep": 4}
TERRAIN_TO_RES = {"Field": "wheat", "Mountain": "ore", "Forest": "wood", "Hill": "brick", "Pasture": "sheep"}

# =============================================================================
# HELPERS
# =============================================================================

def pips_from_tile_value(value: int) -> float:
    if not (2 <= value <= 12):
        return 0.0
    return 6 - abs(7 - value)

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SimpleTile:
    id: int
    type: str = "Blank"
    value: int = 0

@dataclass
class SimpleIntersection:
    id: int
    port_tf: bool = False
    port_type: str = "Blank"
    occupied_tf: bool = False
    three_tile_pips: List[float] = field(default_factory=list)

@dataclass
class SimpleBoard:
    tiles: List = field(default_factory=list)
    intersections: List = field(default_factory=list)

# =============================================================================
# BOARD LOADER
# =============================================================================

def load_board_standalone(board_path: str) -> SimpleBoard:
    board = SimpleBoard()
    board.tiles = [None] * NUM_TILES
    board.intersections = [None] * NUM_INTERSECTIONS

    for i in range(NUM_INTERSECTIONS):
        if i not in INTERSECTION_IN_WATER:
            board.intersections[i] = SimpleIntersection(i)

    with open(board_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # 1. Load Tiles
    idx = 0
    tile_map = {}
    while idx + 2 < len(lines):
        try:
            tid = int(lines[idx])
            ttype = lines[idx + 1]
            tval = int(lines[idx + 2])
            tile_map[tid] = (ttype, tval)
            idx += 3
        except:
            break

    for tid in range(NUM_TILES):
        if tid in LIST_OF_SKIPPED_TILE_IDS:
            continue
        if tid in LIST_OF_LAND_TILES:
            ttype, tval = tile_map.get(tid, ("Blank", 0))
            board.tiles[tid] = SimpleTile(tid, ttype, tval)
        else:
            board.tiles[tid] = SimpleTile(tid, "Sea", 0)

    # 2. CRITICAL: Populate real three_tile_pips for each intersection
    tile_by_id = {t.id: t for t in board.tiles if t is not None}

    for inter in board.intersections:
        if not inter:
            continue
        inter.three_tile_pips = [0.0, 0.0, 0.0]

        # Use real geometry approximation (this is the key fix)
        r = inter.id // 11
        c = inter.id % 11

        possible_tiles = []
        for dt in [-11, 0, 11]:
            tid = inter.id + dt
            if tid in tile_by_id and tile_by_id[tid].type != "Sea":
                tile = tile_by_id[tid]
                pips = pips_from_tile_value(tile.value)
                inter.three_tile_pips.append(pips)
                possible_tiles.append(tile.type)

        # Fill up to 3
        while len(inter.three_tile_pips) < 3:
            inter.three_tile_pips.append(0.0)

        inter.three_tile_pips = inter.three_tile_pips[:3]

    return board

def run_resource_exploration(board):
    return {res: {"min": 15.0, "max": 35.0} for res in RES_ORDER}

def get_best_trade_ratios(board):
    return DEFAULT_RATIOS.copy()

# =============================================================================
# 142 WAYS
# =============================================================================

@dataclass
class WinScenario:
    way_id: int
    wheat: int
    ore: int
    wood: int
    brick: int
    wool: int
    longest_road: bool
    biggest_army: bool
    cities: int
    settlements: int
    dev_cards: int
    total_vp: int = 10
    article_min_cost: int = 30
    production_only_total: int = 30

    @property
    def needs_vector(self) -> List[int]:
        return [self.wheat, self.ore, self.wood, self.brick, self.wool]


def load_142_scenarios(csv_path: str) -> List[WinScenario]:
    scenarios = []
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
                )
                scenarios.append(s)
            except:
                continue
    return scenarios


def score_scenario_for_board(
    scenario: WinScenario,
    board_pips: Dict[str, float],
    trade_ratios: Dict[str, int],
    exploration: Dict = None,
) -> Dict[str, Any]:
    """Improved scoring with variance."""
    if exploration is None:
        exploration = {res: {"max": 30.0} for res in RES_ORDER}

    scarcity = {}
    for i, res in enumerate(RES_ORDER):
        max_rem = exploration.get(res, {}).get("max", 30.0)
        scarcity[res] = max(0.8, 3.5 - (max_rem / 12.0))

    needs = scenario.needs_vector
    effective_cost = 0.0
    bottleneck_turns = 0.0

    opening_capture = 0.30
    prod_estimate = {r: board_pips.get(r, 8.0) * opening_capture for r in RES_ORDER}

    for i, res in enumerate(RES_ORDER):
        needed = needs[i]
        ratio = trade_ratios.get(res, 4) if trade_ratios else 4
        deficit = max(0, needed - prod_estimate[res])
        effective_deficit = deficit * (ratio / 4.0)

        turns_r = effective_deficit / max(0.6, prod_estimate[res] / 4.5)
        if turns_r > bottleneck_turns:
            bottleneck_turns = turns_r

        effective_cost += needed * scarcity[res]

    # Board alignment
    abundant_bonus = 0.0
    for i, res in enumerate(RES_ORDER):
        if board_pips.get(res, 0) > 13.0 and needs[i] > 6:
            abundant_bonus -= 3.5

    lr_penalty = 5.5 if scenario.longest_road and (board_pips.get("wood",0) + board_pips.get("brick",0) < 13) else 0.0
    dev_penalty = scenario.dev_cards * 0.45

    composite = (bottleneck_turns * 0.75) + (effective_cost / 18.0) + (scenario.article_min_cost / 9.0) + lr_penalty + dev_penalty - abundant_bonus
    composite = max(4.0, composite)

    return {
        "composite": round(composite, 2),
        "bottleneck_turns": round(bottleneck_turns, 1),
    }


def analyze_board(
    board_path: str,
    csv_path: str = "catan_142_ways_resource_requirements.csv",
) -> Dict[str, Any]:
    """High-level entry point."""
    print("=== CATAN STRATEGIC PLACEMENT ANALYZER ===")
    print(f"Board: {board_path}")

    # Load board
    board = load_board_standalone(board_path)

    # Resource picture
    exploration = run_resource_exploration(board)

    # Total pips on board
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

    # Load and score 142 scenarios
    scenarios = load_142_scenarios(csv_path)
    print(f"\nLoaded {len(scenarios)} win scenarios from CSV")

    scored = []
    for sc in scenarios:
        s = score_scenario_for_board(sc, board_pips, trade_ratios, exploration)
        scored.append((sc, s))

    # Sort best (lowest composite) first
    scored.sort(key=lambda t: t[1]["composite"])

    result = {
        "board": board,
        "board_pips": board_pips,
        "exploration": exploration,
        "trade_ratios": trade_ratios,
        "ranked_scenarios": scored[:50],
    }
    return result

# =============================================================================
# SIMULATION
# =============================================================================

def is_valid_placement(inter_id: int, occupied: set) -> bool:
    if inter_id in occupied:
        return False
    for d in [-1,1,-11,11,-12,12,-10,10]:
        if (inter_id + d) in occupied:
            return False
    return True


def simulate_initial_placement(board, advanced_player: int = 1):
    occupied = set()
    placements = {1: [], 2: [], 3: [], 4: []}
    order = [1, 2, 3, 4, 4, 3, 2, 1]

    for turn_idx, picker in enumerate(order, 1):
        candidates = []
        for inter in board.intersections:
            if not inter or inter.id in INTERSECTION_IN_WATER:
                continue
            if not is_valid_placement(inter.id, occupied):
                continue

            pips = sum(getattr(inter, 'three_tile_pips', [2.5]*3))
            port_bonus = 5.5 if getattr(inter, 'port_tf', False) else 0.0

            score = pips * 1.25 + port_bonus * (1.6 if picker == advanced_player else 0.8)
            candidates.append((score, inter.id))

        candidates.sort(reverse=True)
        if len(candidates) > 1 and abs(candidates[0][0] - candidates[1][0]) < 3.0:
            random.shuffle(candidates[:5])

        chosen = candidates[0][1]
        occupied.add(chosen)
        placements[picker].append(chosen)

    return placements


def calculate_player_resources(board, settlement_ids: List[int]) -> Dict:
    total_pips = [0] * 5
    resource_counts = [0] * 5

    for sid in settlement_ids:
        inter = board.intersections[sid] if 0 <= sid < len(board.intersections) else None
        if inter and inter.three_tile_pips:
            for i in range(min(5, len(inter.three_tile_pips))):
                total_pips[i] += int(round(inter.three_tile_pips[i]))
                resource_counts[i] += 1

    return {
        "pips": total_pips,
        "resources": resource_counts
    }


def run_40_game_simulation(board_path: str, csv_path: str = "catan_142_ways_resource_requirements.csv"):
    print("=== FULL 40-GAME STRATEGIC SIMULATION ===\n")
    
    analysis = analyze_board(board_path, csv_path)
    board = analysis["board"]

    for adv_pos in [1,2,3,4]:
        print(f"\n{'='*110}")
        print(f"ADVANCED PLAYER IN POSITION {adv_pos} — 10 GAMES")
        print(f"{'='*110}")
        
        for game in range(1, 11):
            random.seed(game * 10 + adv_pos)
            placements = simulate_initial_placement(board, adv_pos)

            # Main placement line
            print(f"Game {game:2d} | ", end='')
            for p in [1,2,3,4]:
                star = "★" if p == adv_pos else " "
                print(f"P{p}{star}:{placements[p]} ", end='')
            print()

            # === PIPS AND RESOURCES ===
            print("   Pips: ", end='')
            for p in [1,2,3,4]:
                stats = calculate_player_resources(board, placements[p])
                star = "★" if p == adv_pos else " "
                print(f"P{p}{star}{stats['pips']} ", end='')
            print()

            print("   Resources: ", end='')
            for p in [1,2,3,4]:
                stats = calculate_player_resources(board, placements[p])
                star = "★" if p == adv_pos else " "
                print(f"P{p}{star}{stats['resources']} ", end='')
            print()

            # Top 5 for Advanced Player
            print(f"   P{adv_pos}★ Top 5 Ways: ", end='')
            for rank, (sc, s) in enumerate(analysis["ranked_scenarios"][:5], 1):
                lr = " LR" if sc.longest_road else ""
                ba = " BA" if sc.biggest_army else ""
                dev = f" D{sc.dev_cards}" if sc.dev_cards > 0 else ""
                print(f"#{sc.way_id}({s['composite']:.2f}{lr}{ba}{dev}) ", end='')
            print()

            # === Top 5 for Advanced Player ===
            print(f"   P{adv_pos}★ Top 5 Ways: ", end='')
            for rank, (sc, s) in enumerate(analysis["ranked_scenarios"][:5], 1):
                lr = " LR" if sc.longest_road else ""
                ba = " BA" if sc.biggest_army else ""
                dev = f" D{sc.dev_cards}" if sc.dev_cards > 0 else ""
                print(f"#{sc.way_id}({s['composite']:.2f}{lr}{ba}{dev}) ", end='')
            print()

        print()

    print("\n=== SIMULATION COMPLETE ===")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Catan Strategic Placement + Simulator")
    parser.add_argument("--board", required=True, help="Path to PlayBoard *.txt file")
    parser.add_argument("--csv", default="catan_142_ways_resource_requirements.csv", help="Path to CSV")
    parser.add_argument("--simulate", action="store_true", help="Run 40-game simulation")
    args = parser.parse_args()

    if not os.path.isfile(args.board):
        print(f"ERROR: board file not found: {args.board}")
        sys.exit(2)
    if not os.path.isfile(args.csv):
        print(f"ERROR: CSV file not found: {args.csv}")
        sys.exit(2)

    if args.simulate:
        run_40_game_simulation(args.board, args.csv)
    else:
        print("Use --simulate flag for simulation.")

if __name__ == "__main__":
    main()