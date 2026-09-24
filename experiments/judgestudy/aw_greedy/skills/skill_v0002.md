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

1. **Decompose & Sequence**: Parse goals into ordered sub-goals (locate, acquire, transform, deliver). Complete each before moving to the next.
2. **Grab Immediately**: When a target object is visible and reachable, take it immediately. Do not delay acquisition to search elsewhere.
3. **Co-located Efficiency**: If the target object and the required appliance (e.g., desklamp, sink, fridge) are on the same surface, perform actions sequentially at that location without navigating away.
4. **Manage Appliance States**: Always open closed appliances/containers before interacting. For heating or cleaning, prioritize performing the transformation while **holding the object** at the open appliance. Ensure doors are open for placement interactions.
5. **Clear Non-Target Inventory**: If you accidentally pick up an object that isn't the goal, place it down at your current location to free your inventory before resuming the search. Never hold multiple irrelevant items while searching.
6. **Verify Transformation State**: After using an appliance, explicitly check the object's state (e.g., via `examine`). If the state does not match the goal, return to the appliance to re-process immediately. Do not assume the transformation succeeded on the first try.
7. **Direct Delivery**: Once holding the transformed object, navigate straight to the target receptacle and place it. Minimize intermediate stops.
8. **Track Progress & Proactive Checks**: Maintain an internal count of remaining objectives. Use `inventory` immediately after picking up or transforming objects to confirm holdings and states before navigating. Adjust search strategy early if the expected item is missing.
9. **Leverage Admissible Actions**: Treat admissible actions as environmental probes. If `take [object] from [location]` appears despite the object not being visible, navigate there immediately to acquire it.
10. **Prioritize Search by Category**: Focus initial searches on high-probability locations based on object type (e.g., food on dining tables/counters/fridges, kitchenware on countertops/sinks, electronics on desks/shelves) to minimize blind exploration.
11. **Avoid Loops & Redundant Cycling**: Never repeat the same action more than twice. If stuck, switch to an unvisited location. Do not cycle back through previously checked empty spots unless absolutely necessary.
12. **Systematic Backtracking**: If the target is not found in the first logical location, do not assume it is absent. Cycle through other unvisited containers and surfaces systematically. Revisit room zones if necessary, but always prioritize unexplored locations first.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them or cycle through known empty spots. Prioritize unvisited high-probability locations first.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.
- **Ignoring admissible action hints**: Failing to navigate to locations suggested by `take [obj] from [loc]` in the admissible list wastes steps. These actions often indicate hidden or nearby targets.
- **Over-navigating co-located items**: Moving away to find an appliance when both the object and appliance are already on the same surface increases step count unnecessarily.
- **Holding non-target objects**: Failing to place down incorrectly picked items blocks further search. Always clear your hands if the held object doesn't match the goal.

## Search & Navigation Protocol

1. **Track Visited Locations**: Explicitly state which containers/surfaces have been checked in your thinking. Do not move to a location unless it is unvisited or contains a known target object.
2. **Remember Object Spots**: If you see a target object on a surface or inside a container, record its exact name and location. After completing transformations or deliveries, navigate directly back to that recorded location. Do not resume blind searching if the object's whereabouts are known.
3. **Verify Before Shuttling**: Check your inventory and object states (e.g., temperature, cleanliness) with a single `examine` or `inventory` call. Only travel between appliances and destinations when the current sub-goal is fully satisfied. Avoid oscillating between locations without advancing the task.

- **Placement & Receptacle States**: If the `put` action is unavailable, examine the receptacle to check if it is closed or requires a specific interaction. Do not attempt to place objects into closed or incompatible receptacles. Verify object states once, then proceed directly to the next step without unnecessary returns.

- **Location Exhaustion Rule**: If you visit a container or surface twice and find it empty, mark it as permanently searched. Immediately navigate to a completely different, unvisited location or room. Never repeat the same search pattern more than once.

## Advanced Handling Rules

- **Multi-Object Local Scan**: For tasks requiring multiple items (e.g., `pick_two_obj_and_place`), after successfully placing the first item, immediately scan your current location for the remaining target(s). Only leave the area if the second item is not visible or reachable here.
- **Appliance Retrieval Protocol**: When heating, cooling, or cleaning, always follow the sequence: interact with appliance -> close/appliance cycle -> open appliance -> **take/retrieve item** -> proceed to destination. Do not assume the item stays in your inventory automatically after appliance interactions.
- **State Verification Trust**: After a successful `heat`, `cool`, or `clean` action, proceed directly to the next step. Do not repeatedly `examine` the object to verify its state, as observations may lag or report generic names. Trust the action success and advance.
- **Object Synonymy**: If the exact goal object is missing after thorough searching, accept functionally equivalent items commonly used in the environment (e.g., treat `pot` as `pan`, `cup` as `mug`, `bowl` as `plate`) to prevent infinite search loops.
