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
4. **Transform before placing**: Perform required state changes (clean/heat/cool) at the appropriate appliance before delivering. Ensure the appliance is open and ready before initiating the transformation, and close it afterward.
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

## Appliance & State Verification Rules
- **Mandatory Retrieval Step**: After using a microwave, fridge, or sink for transformation, the object typically remains inside. You must explicitly `open <appliance>` and `take <object> from <appliance>` before moving to the final destination. Skipping this step causes immediate failure.
- **Object Identity & State Check**: Verify the exact name and state of your carried object (`examine <object>` or `inventory`) before attempting placement. Mismatched names or untransformed states will block admissible actions.

## Systematic Exploration Guidelines
- **Break Number-Cycling Traps**: Do not blindly iterate through numbered items (e.g., drawer 1, 2, 3...) if they yield nothing. Once a category is exhausted, pivot to entirely different furniture types (countertops, shelves, tables, dressers) or adjacent rooms.
- **Mark & Move**: Mentally mark every opened container or examined surface as 'checked'. If you find yourself returning to a previously verified empty location, immediately abort that path and explore a new unvisited zone.

## Stuck-State Recovery
- **Admissible Action Audit**: If `put`, `take`, or `open` actions are missing from your admissible list, pause and diagnose: check inventory, verify receptacle state, or confirm object compatibility. Do not guess or repeat failed moves.
- **Forced Strategy Shift**: If three consecutive steps yield no progress or loop back to previous locations, execute `inventory` to reset context, then deliberately choose a location you have not visited in the last 5 steps.
