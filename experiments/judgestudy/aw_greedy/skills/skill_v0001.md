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
2. **Systematic exploration**: Search each surface and container exactly once before revisiting. Open closed containers (drawers, cabinets, fridge) before judging them empty.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Manage appliance states**: Always open closed appliances (microwave, fridge, sink) before attempting to heat, cool, clean, or place items. Ensure doors are open for placement interactions.
5. **Verify transformation state**: Before final placement, confirm the object's state matches the goal (e.g., 'hot', 'cold', 'clean'). If the state is incorrect, return to the appliance to re-process rather than placing a mismatched item.
6. **Clear inventory for multi-object tasks**: When handling multiple items, place the first acquired object at the destination to free your inventory before searching for and acquiring the remaining items.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

10. **Leverage admissible actions**: If an action like `take [object] from [location]` appears in the admissible list but the object isn't visible, navigate to that location immediately. Admissible actions often reveal hidden or nearby objects.
11. **Check inventory when stuck**: If unsure about held items or progress, use the `inventory` command to verify carried objects and adjust your search strategy accordingly.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

## Search & Navigation Protocol

1. **Track Visited Locations**: Explicitly state which containers/surfaces have been checked in your thinking. Do not move to a location unless it is unvisited or contains a known target object.
2. **Remember Object Spots**: If you see a target object on a surface or inside a container, record its exact name and location. After completing transformations or deliveries, navigate directly back to that recorded location. Do not resume blind searching if the object's whereabouts are known.
3. **Verify Before Shuttling**: Check your inventory and object states (e.g., temperature, cleanliness) with a single `examine` or `inventory` call. Only travel between appliances and destinations when the current sub-goal is fully satisfied. Avoid oscillating between locations without advancing the task.

- **Placement & Receptacle States**: If the `put` action is unavailable, examine the receptacle to check if it is closed or requires a specific interaction. Do not attempt to place objects into closed or incompatible receptacles. Verify object states once, then proceed directly to the next step without unnecessary returns.
