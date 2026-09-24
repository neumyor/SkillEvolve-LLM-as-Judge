# ALFWorld Embodied Agent Skill

## Overview
This skill guides agents operating in the ALFWorld text-based embodied environment.
The agent must complete household tasks by navigating rooms, interacting with objects,
and using appliances. Actions must be chosen from the admissible action list provided
at each step.

**Output format**: Always output `<think>...</think>` for reasoning, then `<action>...</action>` for the chosen action.

---

## Task Types

| Type | Goal | Key Steps |
|------|------|-----------|
| Pick & Place | Put object X in/on receptacle Y | Find X -> take X -> go to Y -> put X in/on Y |
| Pick Two & Place | Put two instances of X in/on Y | Find X1 -> take -> place -> find X2 -> take -> place |
| Examine in Light | Examine object X under desklamp | Find X -> take X -> find desklamp -> use desklamp |
| Clean & Place | Clean object X and put in/on Y | Find X -> take X -> go to sink -> clean X -> go to Y -> put X |
| Heat & Place | Heat object X and put in/on Y | Find X -> take X -> go to microwave -> heat X -> go to Y -> put X |
| Cool & Place | Cool object X and put in/on Y | Find X -> take X -> go to fridge -> cool X -> go to Y -> put X |

---

## General Principles

1. **Decompose the task**: Parse the goal into ordered sub-goals (locate, acquire, transform, deliver). Complete each before moving to the next.
2. **Systematic exploration**: Categorize locations into Containers (drawers, cabinets, fridge) and Surfaces (countertops, tables, shelves, dressers). Check every Container and Surface in the room exactly once before any revisit. Always open closed containers before judging them empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

- **Fixating on one furniture type**: Cycling through only drawers or only shelves ignores other high-probability locations. Alternate between containers and surfaces.
- **Object identity confusion**: Picking up a 'pot' when asked for a 'pan' (or vice versa) wastes steps. Always verify the exact object name in observations and admissible actions before interacting.
- **Redundant appliance cycling**: Do not return to appliances multiple times for the same object unless explicitly instructed. Track internal state flags for transformations.
- **Silent failure recovery**: When placement yields no result, do not immediately navigate away. Verify inventory possession and receptacle openness at the location before leaving.

9. **Open before interact/place**: Always open closed containers (cabinets, drawers, fridge) or appliances (microwave) before placing objects inside or performing state changes (clean, heat, cool). Do not attempt to place or transform while the receptacle is closed.
10. **Sequential placement for multi-object tasks**: When tasked with moving multiple items, place the first acquired item at the target receptacle immediately. This frees your inventory/hands to retrieve and transport the remaining items without unnecessary backtracking.
11. **Verify state with inventory**: During long searches or if unsure about your current load, use the `inventory` action to confirm whether you are holding the target object before navigating elsewhere.
12. **Close appliances after use**: After heating, cooling, or cleaning with an appliance (microwave, fridge, sink), close it to clear the workspace and prevent blocking future interactions.
13. **Prioritize transformation appliances**: When searching for food or perishables, check the fridge or microwave early in the episode. These locations often store the target item and are required later for the transformation step, saving travel time.
14. **Use object priors**: Guide your initial search by targeting locations where the object type is commonly found (e.g., sponges near sinks, knives on counters, CDs on desks, statues in drawers) to minimize random exploration.

## Loop Recovery Protocol
When systematic searching yields no results or you detect a loop:
1. **Check Inventory**: Run `inventory` to confirm what you are holding. If holding the goal object, go directly to the destination.
2. **Switch Category**: If you have exhausted Containers, pivot entirely to Surfaces (and vice versa).
3. **Verify Admissible Actions**: Only choose actions explicitly listed. Do not assume object names; match exact strings (e.g., 'pan' vs 'pot').
4. **Break Cycles**: If you return to a previously checked location, force a move to an unvisited location immediately.
