# Success Memory Item 1
## Title
Process Objects Individually
## Description
Handle multi-object tasks by completing the full pickup-to-place cycle for one item before initiating the next.
## Content
Avoid attempting to carry multiple items simultaneously. After successfully placing the first object, verify you are empty-handed, then navigate to locate and pick up the second object. This sequential approach prevents inventory conflicts, simplifies state tracking, and aligns with environment constraints that typically limit holding capacity to one item at a time.

# Success Memory Item 2
## Title
Verify and Prepare Target Containers
## Description
Always inspect the state of the destination container before placement and open it if necessary.
## Content
When approaching a drawer or cabinet to store an item, check its closure status. If closed, execute an open command immediately. Keeping the container open after the first placement allows for efficient sequential storage of additional items, eliminating redundant navigation and opening cycles for subsequent objects.

# Success Memory Item 3
## Title
Confirm Holding Status with Inventory Checks
## Description
Use inventory queries to validate current carrying state before critical transitions.
## Content
Insert `inventory` commands after placing an item or before searching for the next target to confirm whether you are holding anything. This verification step prevents invalid pickup attempts, clarifies spatial reasoning when returning to previous locations, and ensures smooth progression through complex multi-step sequences.
