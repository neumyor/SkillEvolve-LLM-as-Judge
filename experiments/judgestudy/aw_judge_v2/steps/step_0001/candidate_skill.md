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
2. **Systematic exploration**: Maintain an explicit mental list of visited surfaces and containers. Never revisit a location you have already inspected. Open closed containers before judging them empty. If you find yourself returning to a checked location, immediately pivot to an unexplored area.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Use atomic appliance actions**: For heating, cooling, or cleaning tasks, rely directly on the provided interaction commands (e.g., `heat X with Y`, `cool X with Y`, `clean X with Y`). These actions are typically atomic and handle internal placement/retrieval automatically. Do not manually open/close appliances or move objects in/out unless the admissible actions explicitly require it.
5. **Receptacle Access & Delivery**: Always **open the target receptacle** (fridge, cabinet, shelf) before attempting to place an object. For multi-object tasks, place the first item at the destination immediately to free inventory, then continue searching for the remainder.
6. **Verify state before placing**: If the expected `put` or `place` action is missing from the admissible list at the destination, immediately check your inventory. Confirm you are holding the correct item. If holding, examine the receptacle or reconsider if the item requires further transformation. Avoid cycling between locations without verifying your current state.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.
9. **Accept functional substitutes**: If the exact target object is not found after exhaustive searching, consider accepting functionally equivalent items (e.g., 'pot' for 'pan', 'bowl' for 'plate') that satisfy the task constraints. Do not halt progress solely due to a naming mismatch if a suitable alternative is available.
10. **Manage inventory constraints**: You can only hold one object at a time. If holding an item, you must place it down (`move <item> to <location>`) before attempting to take another. Do not attempt to pick up a second item while holding one.
11. **Sequential location search**: Visit numbered containers and surfaces in ascending order (e.g., shelf 1 → shelf 2 → shelf 3) rather than jumping randomly. This ensures thorough coverage without unnecessary backtracking.
12. **Direct appliance interaction**: For heating/cooling tasks, try the direct action (`heat <object> with <appliance>` or `cool <object> with <appliance>`) while standing at the appliance. If unavailable, place the object inside and follow the open/close cycle.
13. **Inventory checkpoints**: If you are unsure what you are carrying or why actions are unavailable, execute `inventory` to verify your current state before deciding the next move.

**Appliance Location Heuristic**: When searching for appliances like desklamps, prioritize checking desks and shelves, as these are the most common locations for such items.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Mismatched object types**: Verify the object name matches the goal exactly before taking. Picking up similar but incorrect items (e.g., 'pan' instead of 'pot') wastes steps and may block progress.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.
