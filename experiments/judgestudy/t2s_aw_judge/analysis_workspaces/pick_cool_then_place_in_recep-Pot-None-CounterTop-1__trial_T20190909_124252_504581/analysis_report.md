# Failure Cause Item 1
## Title
Incorrect Object Selection (Pan vs Pot)
## Description
The agent mistakenly identified and interacted with a 'pan' instead of the required 'pot'.
## Content
In the task "cool some pot and put it in countertop", the agent needs to find a 'pot'. At step 7, the agent took 'pan 1' from 'stoveburner 2' instead of locating a 'pot'. This fundamental error caused the agent to perform the correct actions (cooling, placing) on the wrong object, leading to a failure state where it later searched for a 'pot' without success in the remaining steps.

# Failure Memory Item 1
## Title
Object Type Specificity
## Description
Ensure the object being manipulated matches the specific type requested in the task.
## Content
When the task specifies a particular object type (e.g., 'pot'), the agent must verify the object's identity before performing actions like 'take', 'cool', or 'move'. Do not substitute similar objects (e.g., 'pan') unless the task allows for any container of that class or if no other options are available.

# Failure Memory Item 2
## Title
Systematic Search Strategy
## Description
Continue searching all relevant locations for the target object before settling for an alternative.
## Content
If the target object is not found in the first few checked locations (like cabinet 1, cabinet 2), the agent should continue its systematic search through other potential storage locations (like other cabinets, drawers, or shelves) rather than switching to a different object type or giving up.

ACTION: TASK_COMPLETE
