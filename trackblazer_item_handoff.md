# Trackblazer Item System Handoff

## Summary
This file is a handoff note for continuing Trackblazer item-system work on another machine.

The current state is:
- the item system foundation is implemented for API mode
- item decision logic exists
- item config and GUI options exist
- execute-loop planning hooks exist
- actual item buy/use execution is **not** implemented yet

The most important limitation right now is:
- the bot can plan and log what items it wants to buy/use
- the bot does **not** yet open the item UI and click those items in-game

## What Has Been Done

### 1. Item runtime foundation
Created [core/Trackblazer/items.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/items.py).

This file currently handles:
- item catalog loading from `assets/trackblazer/items/items_list.json`
- item normalization
- condition normalization
- active-effect normalization
- API item-state normalization
- purchase planning
- immediate-use planning
- training-item planning
- race-item planning
- local state updates after planned purchases/uses

Key implemented rule areas:
- stat items
- energy items
- mood items
- negative condition cures
- positive condition items
- Grilled Carrots
- Good-luck Charm
- Training Buff
- Specialized Training Buff
- Training Level items
- Training Shuffle
- Cleat Hammers
- Glowstick

### 2. API data support
Updated [core/Trackblazer/state.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/state.py).

Added raw/item-related helpers:
- `get_status_api_raw()`
- `get_shop_coin_api()`
- `get_shop_items_api()`
- `get_inventory_items_api()`
- `get_conditions_api()`
- `get_active_item_effects_api()`

Current API assumption:
- Trackblazer item logic uses `status` and `training`
- it does **not** use `state`

### 3. Training API level support
Updated [core/Trackblazer/training_handling.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/training_handling.py).

`check_training_api()` now includes:
- `level` for each training facility

This is used by Training Level item logic.

### 4. Execute-loop integration
Updated [core/Trackblazer/execute.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/execute.py).

What is integrated:
- load item config/template in API mode
- build normalized item state from API
- plan purchases
- plan immediate-use items
- plan race items
- plan training items
- log those plans during the turn loop

Important:
- this is currently planning/logging integration
- not physical in-game item execution

### 5. Race config compatibility
Updated [core/Trackblazer/races_handling.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/races_handling.py).

Custom race config now supports both formats:
- old format:
  - `"Classic Year Late Jun": "Takarazuka Kinen"`
- new format:
  - `"Classic Year Late Jun": { "race": "Takarazuka Kinen", "use_glowstick": true }`

Added:
- `get_custom_race_selection()`

### 6. Items tab GUI
Updated [gui/tabs/items_tab.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/gui/tabs/items_tab.py).

Current GUI work includes:
- template selector
- `Edit` button for item purchase priority
- budget strategy option
- mood auto-buy option
- cure auto-buy option
- condition selection list
- Grilled Carrots subgroup
- Good-luck Charm subgroup
- Training Buff settings
- multi-select buff time window
- Training Level settings
- Training Shuffle settings
- race-item settings

Conditional UI behavior already added:
- cure-condition list only appears when cure auto-buy is enabled
- Grilled Carrots extra controls only appear when its main option is enabled
- Good-luck Charm options only appear when enabled
- Training Level extra controls only appear when enabled

### 7. Hover preview in main Items tab
Also in [gui/tabs/items_tab.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/gui/tabs/items_tab.py):

Hover preview was added to the main Items tab text/checkboxes.

It currently shows item icon/name previews for:
- mood items
- cure items
- Grilled Carrots
- Good-luck Charm
- Training Buff
- Specialized Training Buff
- Training Level items
- Training Shuffle
- Cleat Hammers
- Glow Sticks

Note:
- hover preview was intentionally removed from the priority editor window

### 8. Priority editor cleanup
Updated [gui/tabs/item_priority_window.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/gui/tabs/item_priority_window.py).

Current state:
- plain priority editor
- no hover preview there

### 9. Config defaults
Updated:
- [gui/main_window.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/gui/main_window.py)
- [config.example.json](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/config.example.json)

Added base `items` config support.

## Important Behavior Decisions Already Applied

### API and phase naming
- Trackblazer should use `TS Climax`, not `Finale Underway`
- `Year 4` is normalized to `TS Climax`

This was updated in:
- [core/Trackblazer/state.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/state.py)
- [core/Trackblazer/items.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/items.py)
- [core/Trackblazer/execute.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/execute.py)
- [core/Trackblazer/races_handling.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/races_handling.py)

### Usage-condition system
- user-authored item usage conditions were removed
- item usage is now hardcoded runtime logic plus top-level config options

### Training buff timing
- buff time window is now multi-select in GUI
- config currently supports `training_buff_periods`
- legacy single `training_buff_period` is still tolerated for compatibility

## What Still Needs To Be Done

### 1. Real item execution
This is the biggest missing part.

Still needed:
- how to open the Trackblazer item/shop UI
- how to buy items from shop
- how to use items from inventory
- how to confirm item usage
- how to return to lobby/training/race flow after item actions

This must be implemented in runtime code after exact UI steps are known.

Suggested place:
- continue in [core/Trackblazer/execute.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/execute.py)
- likely add dedicated executor helpers, probably new module(s), instead of bloating `execute.py`

### 2. Replanning after real item use
The planner already assumes training-related items may require refresh.
But once real execution exists, this must be completed end-to-end:
- use training item
- refresh `/training`
- rebuild chosen training
- possibly repeat

This is especially relevant for:
- Training Buff
- Specialized Training Buff
- Good-luck Charm
- Training Shuffle

### 3. Connect planned actions to actual action flow
Current integration logs plans, but does not alter final behavior enough yet.

Still needed:
- item purchase pass should actually run before immediate-use pass
- immediate-use pass should actually change current turn state
- race-item pass should run before race execution
- training-item pass should affect final training decision

### 4. Good-luck Charm actual bypass behavior
Planner logic exists.
Actual execution behavior still needs to be enforced cleanly when item use is real:
- bypass low-energy rejection
- bypass failure-rate rejection

### 5. More GUI polish
The new Items tab works, but can still be improved:
- spacing/alignment cleanup
- hover preview for individual bad-condition names if desired
- clearer microcopy for some labels if needed

### 6. Plan document cleanup
[trackblazer_item_plan.md](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/trackblazer_item_plan.md) still contains some older wording from the planning phase.

It should be updated to reflect final implementation state, especially:
- `TS Climax` naming instead of `Finale Underway`
- what is already implemented vs still pending

## Suggested Next Steps

Recommended order:

1. Implement actual item buy/use executor
2. Wire executor into current planned purchase/use passes
3. Add training refresh loop after real training-item use
4. Test with API mode on real turns
5. Update the plan doc and example configs

## Files Most Important To Continue From

Start here:
- [core/Trackblazer/items.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/items.py)
- [core/Trackblazer/execute.py](/c:/Users/Kise/Downloads/UMAT_0.1\UMAT/core/Trackblazer/execute.py)
- [core/Trackblazer/state.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/state.py)
- [core/Trackblazer/races_handling.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/core/Trackblazer/races_handling.py)
- [gui/tabs/items_tab.py](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/gui/tabs/items_tab.py)

Supporting references:
- [assets/trackblazer/items/items_list.json](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/assets/trackblazer/items/items_list.json)
- [ref/api/status.json](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/ref/api/status.json)
- [ref/api/training.json](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/ref/api/training.json)
- [template/items/default.json](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/template/items/default.json)
- [template/races/custom_races.json](/c:/Users/Kise/Downloads/UMAT_0.1/UMAT/template/races/custom_races.json)

## Current Practical Status
- planning logic exists
- GUI exists
- config exists
- API parsing exists
- no real item clicking yet

So the system is currently at:
- `decision-ready`
- not yet `execution-ready`
