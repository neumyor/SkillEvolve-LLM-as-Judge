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
2. **Systematic exploration & Loop Breaking**: Prioritize searching closed containers (cabinets, drawers, fridges) before open surfaces. Maintain a mental map of visited locations; never re-examine a container or surface that has already yielded nothing. If you visit the same location twice without progress, force a move to a completely different furniture category or room section. Only stop searching when the target is found or all logical locations are exhausted.
3. **Grab immediately**: When a required object is visible and reachable, take it right away before moving elsewhere.
4. **Transform before placing**: If the task requires cleaning, heating, or cooling, perform the state change at the appropriate appliance before heading to the final destination.

5. **Appliance Workflow**: For heating/cooling/cleaning tasks: 1) Open appliance, 2) Place object inside, 3) Perform transform action, 4) Close appliance, 5) Take object out immediately. Never navigate away from an appliance while an object is inside it without retrieving it first. Always verify the object's state (hot/cold/clean) after transformation.
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

---

## Troubleshooting & Edge Cases

- **Placement Blocked**: If `put <obj> in/on <recep>` is unavailable or fails, run `inventory` to confirm possession. Run `examine <recep>` to check if it needs opening. Resolve the block before moving.
- **Object Identity & Equivalence**: Match exact names/types from the goal. In ALFWorld, task descriptions often use generic names (e.g., "pot", "container") while the environment provides specific instances (e.g., "pan", "bowl"). Accept the first reachable object that functionally matches the goal. Do not substitute similar items unless no other option exists, and do not abandon a valid match to search for a literal name match.
- **State Persistence**: Objects retain their transformed state (hot/cold/clean) until placed or dropped. Do not re-transform unless explicitly stated or state changed to normal.

### Completion Protocol
1. **Final Verification**: After placing the object in the target receptacle, read the observation carefully. If the goal object is listed as present in the receptacle, the task is complete.
2. **Immediate Termination**: Execute `done` immediately upon verification. Do not follow up with `look`, `inventory`, or any other exploratory actions. Continuing after success wastes steps.

9. **Close appliances after use**: After completing a transformation (heating, cooling, cleaning), close the appliance door (e.g., microwave, fridge) to finalize the action and maintain a clean state.
10. **State inference via actions**: Use the admissible action list to deduce your current state. If `take X` is unavailable, you likely hold X. If `inventory` is listed, use it to verify contents or resolve naming discrepancies.
12. **Verify state during stalls**: If the task stalls or you lose track of your inventory during long searches, use the `inventory` command to confirm what you are carrying or if you are empty-handed.
