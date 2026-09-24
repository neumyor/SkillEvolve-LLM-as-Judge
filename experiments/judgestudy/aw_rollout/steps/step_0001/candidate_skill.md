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
2. **Heuristic & Systematic Exploration**: Begin searches in high-probability locations based on object type (e.g., food -> fridge/countertops; utensils -> cabinets/drawers/sink; electronics -> desks/shelves). Once started, search each surface/container exactly once before revisiting. Always open closed containers/appliances before searching inside.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: Perform cleaning/heating/cooling at the correct appliance *before* navigating to the final destination. Follow full appliance interaction cycles: open closed appliances, execute the transform action, close/reopen as required, and retrieve items if deposited.
5. **Direct delivery**: Once holding the transformed (or untransformed) goal object, navigate straight to the target receptacle and place it.
6. **Track progress**: Maintain an internal count of how many objects still need to be found and placed. Only stop searching when the count reaches zero.
7. **Avoid loops**: Never repeat the same action more than twice in a row. If stuck, move to a different unexplored location.
8. **Only choose admissible actions**: Always pick an action from the admissible action list. Do not invent actions.

9. **Verify holdings & identity**: If the target object is not visible, check your inventory (`inventory`) before continuing to search. Before applying a transformation, confirm the acquired object exactly matches the task's target noun (e.g., 'pot' vs 'pan').
10. **Strict multi-object sequencing**: For tasks requiring multiple instances, fully resolve one sub-task (locate -> acquire -> transform -> deliver) before starting the next. Never attempt to hold multiple objects simultaneously; place the first item at its destination before retrieving the second.
11. **Appliance & Lamp protocols**: Interact with appliances according to their required state (open -> interact -> close). For examination tasks, locate the light source after picking up the object, verify you are holding it, then execute `use <lamp>` prior to examination.

---

## Common Mistakes to Avoid

- **Revisiting searched locations**: Keep track of which surfaces/containers have been checked; do not re-examine them.
- **Ignoring visible objects**: If the target object appears in the observation, pick it up immediately.
- **Skipping state changes**: Do not place an object at the destination without first cleaning/heating/cooling it when required.
- **Premature termination**: Do not stop the episode until all goal conditions are verified as met.
- **Action loops**: Repeatedly toggling or examining the same object wastes steps. Move on to new locations instead.

## Search Optimization
- **Category Switching**: If a specific container type (e.g., drawers, shelves, cabinets) yields no results after checking multiple instances, immediately pivot to a different furniture category (e.g., countertops, dressers, beds, sofas) rather than cycling through the same type.
- **Exact Object Matching**: Verify the exact object name matches the goal. Do not substitute similar items (e.g., 'pot' for 'pan', 'bowl' for 'plate'). If the target is not found, re-examine recently visited surfaces carefully before assuming it is hidden.
