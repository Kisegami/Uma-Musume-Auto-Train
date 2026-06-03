# Trackblazer Item System Plan

## Summary
The first implementation target is Trackblazer item handling in API mode only. OCR mode remains the main runtime for the project overall, but item automation should be developed behind API-mode checks first because the item state is already available from `/status` and is much simpler to integrate safely.

The goal of this base is to support:
- reading item-related state every turn
- planning shop purchases from user templates and item-related config options
- planning item usage from hardcoded runtime rules
- supporting multiple item uses within the same turn when rules allow it
- preventing duplicate use of already-active multi-turn effects
- integrating item logic into the Trackblazer turn loop without breaking current training, race, and rest flow

Race logic is included in this plan where the behavior is now known. OCR-based item handling remains out of scope for this first pass.

## Current Repo State
There is already partial item groundwork in the repo:
- `assets/trackblazer/items/items_list.json` defines the Trackblazer item catalog
- `gui/tabs/items_tab.py` already exposes item template selection
- `gui/tabs/item_priority_window.py` already supports item purchase priority templates
- `ref/trackblazer_status_api.json` shows API payloads already include:
  - `shop_items`
  - `inventory_items`
  - `active_item_effects`
  - `conditions`
- `ref/api/status.json` now also shows `shop_coin` in the status payload
- `ref/api/training.json` already includes training `level` and support-card `bond_level`
- `core/Trackblazer/state.py` currently parses API status, but it does not yet expose item data to runtime logic

This means the missing part is not GUI setup. The missing part is the runtime decision layer, the item-specific config layer, and execute-loop integration.

## Scope for V1
V1 should include:
- API-mode item state parsing
- normalized item state model
- purchase planner
- hardcoded usage planner
- item-related config and GUI options
- active-effect dedup and anti-repeat protection
- Trackblazer execute-loop integration

V1 should not include:
- OCR-based item detection
- OCR-based item purchase or use execution
- per-item user-authored usage conditions
- a generic rule DSL for future item logic

## Proposed Architecture

### 1. Item Catalog Layer
Add a Trackblazer item module that loads and normalizes item metadata from `assets/trackblazer/items/items_list.json`.

The normalized catalog entry should include:
- `item_id`
- `name`
- `group`
- `effect_type`
- `stat_type`
- `value`
- `base_price`
- `effect_text`

This layer should also derive runtime helper fields such as:
- `usage_family`
- `effect_conflict_key`
- `target_stat`
- `target_condition`
- `duration_turns` where applicable, with multi-turn persistence only for Training Buff items

Example conflict keys:
- `training_buff:any`
- `specialized_training_buff:spd`
- `race_bonus:any`
- `fan_gain:any`
- `positive_condition:hot_topic`

These keys are needed so the runtime can block reusing items whose effect is already active.

### 2. API Item State Layer
Extend Trackblazer API parsing so item-related status is available to runtime logic every turn.

Normalized turn item state should include:
- `shop_items`
- `inventory_items`
- `active_item_effects`
- `conditions`
- `year`
- `stats`
- `energy_current`
- `energy_max`
- `energy_pct`
- `mood_name`
- `mood_value`
- `training_results`
- `chosen_action`
- `chosen_training`

This should be implemented in a way that does not break current `check_status_api()` consumers. The cleanest path is to keep current status helpers stable and add item-focused helpers such as:
- `get_turn_item_state_api()`
- `get_shop_items_api()`
- `get_inventory_items_api()`
- `get_active_item_effects_api()`

API dependency rule:
- item runtime should read only `status` and `training` APIs
- do not read `state` in the item system
- available shop budget should come from `status.shop_coin`

### 3. Config and GUI Layer
Remove user-authored item usage conditions completely. Item usage must be driven by hardcoded runtime rules plus explicit top-level options in config and GUI.

The purchase priority template remains as:
- `items_priority`

Add item-related config fields for behavior that is intentionally player-controlled. These should live in normal config, not inside the item template file.

Required option groups for V1:
- mood item behavior
- negative condition cure auto-buy behavior
- friendship item buy threshold
- Good-luck Charm usage settings
- training buff score threshold
- specialized buff dependency on global buff
- buff time-window restriction
- training level item buy settings
- training shuffle settings
- race bonus reserve settings
- Glowstick usage settings

GUI layout requirement for V1:
- the Items tab should be grouped into separate sections by item family or behavior group instead of one flat block
- at minimum, separate groups should exist for:
  - purchase priority template selection
  - mood item settings
  - condition item settings
  - training item settings
  - race item settings

### 4. Purchase Planner
Use two purchase sources:
- explicit item template priority from `template/items/*.json`
- hardcoded conditional auto-buy rules driven by config for item families that should be opportunistically bought

Planner behavior:
- build an ordered list of candidate purchases for the current turn
- start with `items_priority` in template order
- append eligible opportunistic auto-buy items after all template-driven purchases
- match candidates against current `shop_items`
- skip if:
  - item is not in shop
  - item is sold out
  - shop buy count reached the limit
  - owned count already meets the planned reserve or limit
  - price cannot be paid from the current shop state available in API mode

The planner must understand that some items can be bought even if they are not in the purchase template:
- mood items when low mood auto-buy is enabled
- negative condition cure items when cure auto-buy is enabled
- Grilled Carrots when friendship auto-buy conditions pass
- training level items when training level buy conditions pass

Opportunistic auto-buy rule:
- auto-buy items that are not in purchase priority should be bought only when they are immediately useful on the current turn
- most of these cases will naturally resolve to buying one item, or a calculated quantity for mood or energy-style logic

Additional purchase constraint:
- all stat items must be skipped for purchase when their target stat already meets or exceeds the user-configured stat cap for that stat
- `item_limit` should apply to both template-priority purchases and opportunistic auto-buy purchases

In API mode, purchase execution should use `status.shop_coin` as the available budget source and `shop_items[].price` as the cost source.

Budget strategy option:
- add a GUI and config option for budget handling when current coin cannot afford every valid candidate:
  - `Buy as much as possible`
  - `Save for higher priority items`
- `Buy as much as possible` means if a higher-priority item is unaffordable, the planner may continue to cheaper later candidates
- `Save for higher priority items` means if a higher-priority valid item is in shop but unaffordable, the planner should stop and preserve coin instead of buying lower-priority items

### 5. Usage Planner
Use inventory plus hardcoded Trackblazer item rules to decide which items to use. The runtime logic should combine:
- item effect family
- current year or career phase
- current conditions
- current active item effects
- current training results
- chosen training or race action
- user-configured item behavior options

This planner should be deterministic and pure as much as possible so it can be tested independently from taps or OCR.

Turn-use model:
- items can be used multiple times in the same turn
- the planner should be able to emit an ordered list of multiple item uses for one turn instead of assuming at most one use
- any item bought on the current turn can also be used on the same turn if its rules say it is usable

## Hardcoded Usage Rules by Item Family

### All Stat Items
Includes notepad, manual, and scroll stat items.

Rule:
- if the item is in inventory, use it immediately
- if multiple copies are in inventory, use all copies in the same turn

Notes:
- no extra player condition in V1
- later cap-aware behavior can be added if needed

Purchase behavior:
- skip buying a stat item if its target stat is already at or above the configured stat cap for that stat

Usage-cap behavior:
- the stat cap only blocks purchase, not usage
- if stat items already exist in inventory, use all copies even if this pushes the stat above the configured cap

### Energy Items

#### Energy Cap
Rule:
- if the item is in inventory, use it immediately

#### Energy Recovery
Rule:
- use as soon as useful based on current energy left
- do not waste recovery by sending energy above max
- choose the recovery item or item combination that gives the closest useful fill to current missing energy
- do not use energy recovery on race turns

Decision requirement:
- calculate missing energy as `energy_max - energy_current`
- compare with each recovery item `value`
- allow stacking multiple recovery items in the same turn when one item is insufficient
- do not allow overfill above max
- stop stacking once further recovery would exceed max

### Mood Items
Rule:
- if a mood item is already in inventory and mood is below the configured minimum mood threshold, use it
- if multiple mood items are available, calculate the required mood gain before buying or using them
- use only the amount needed by that calculation, not every owned mood item blindly

Purchase behavior:
- if the item is in purchase priority, normal purchase logic handles it
- also add an optional config and GUI setting to buy a mood item opportunistically when mood is low and a mood item is in the shop on that turn
- opportunistic mood auto-buy may buy multiple mood items in one turn if the logic determines they are useful
- if mood items are bought on the current turn, use them immediately on that same turn

Notes:
- item `value` is not required for the first implementation
- mood comparison should use the same minimum mood config already used by training logic
- when multiple mood items are available to buy, calculate the exact purchase combination needed to reach minimum mood
- mood-item auto-buy should calculate first and then use immediately on the same turn

### Condition Items

#### Negative Condition Cure
Rule:
- if a relevant cure item is in inventory and the matching bad condition is currently active, use it
- this rule applies even if the user did not explicitly prioritize buying that cure item

Purchase behavior:
- add an optional config and GUI setting to auto-buy cure items when the character currently has a bad condition and the matching cure item is in the shop
- exclude `Miracle Cure` from this auto-buy behavior because it is expensive
- if multiple selected bad conditions are currently active and multiple matching cure items are in shop, the bot may buy multiple cure items in one turn
- for any single specific condition, the bot should not buy more than one matching cure item in the same turn

Use preference:
- if both a specific cure and `Miracle Cure` are already in inventory, prefer the specific cure first

Same-turn behavior:
- if cure items are bought on the current turn, use them immediately on that same turn when still valid

GUI behavior:
- provide a master `All conditions` checkbox enabled by default
- provide individual checkboxes for each negative condition
- if any individual condition is unchecked, automatically clear `All conditions`
- if `All conditions` is checked, all individual conditions become selected

#### Positive Condition
Rule:
- if a positive-condition item is in inventory and the character does not already have that condition, use it immediately

Purchase behavior:
- only buy positive-condition items if they are in the user's purchase priority list
- before buying or using a positive-condition item, verify the condition is not already active
- if bought on the current turn and the condition is not already active, use it immediately on the same turn

Copy-count rule:
- positive-condition items should never be planned or bought in redundant duplicate quantities for the same turn because the condition can only be applied once

### Training Items

#### Friendship
Applies only to `Grilled Carrots`.

Purchase behavior:
- add an option in GUI and config to buy `Grilled Carrots` if there are at least `N` support cards with bond level below 4

Rule:
- if `Grilled Carrots` is in inventory, use it immediately
- if multiple copies are in inventory, use all copies in the same turn

Stocking behavior:
- if multiple copies are available in shop and the buy condition is valid, the bot may buy multiple copies
- if Grilled Carrots are bought on the current turn, use them immediately on that same turn

#### Safety
Applies to `Good-luck Charm`.

Behavior:
- this item changes training decision behavior while it is present in inventory
- it should not be treated as a buff that only matters after consumption
- if the bot chooses to consume it for the turn, its effect applies only for that turn

Use rule:
- if in inventory, evaluate against two selectable user conditions:
  - chosen training score is greater than the configured threshold
  - either Training Buff or Specialized Training Buff is used this turn when applicable
- the user may enable either condition or both
- the enabled Good-luck Charm conditions are selectable independently
- if both conditions are enabled, both must pass
- if only one condition is enabled, only that one must pass
- even if its conditions pass, Good-luck Charm should only be consumed if the chosen training would otherwise be rejected by low energy or failure rate

Integration requirement:
- the training decision path must support an item flag that temporarily bypasses:
  - low energy rejection
  - maximum failure-rate rejection

Effect note:
- one Good-luck Charm use covers both low-energy rejection and failure-rate rejection for that turn

#### Training Buff
Examples are megaphones.

Rule:
- if chosen training score is greater than the configured threshold and the buff is not already active, use it
- when multiple Training Buff items are available in inventory, prefer the higher percentage buff first
- because Training Buff does not stack, use only the single highest-value Training Buff item for that turn

Notes:
- these items have multi-turn duration and must not be reused while active
- if a Training Buff item is bought on the current turn and its use conditions pass, it may be used on that same turn

#### Specialized Training Buff
Examples are ankle weights.

Rule:
- if the chosen training type matches the buff stat type and chosen training score is greater than the configured training-buff threshold, use it if not already active

Additional option:
- add a config and GUI option to use Specialized Training Buff only if Training Buff is used this turn or still active this turn

Notes:
- Specialized Training Buff is a single-turn item
- it should not be tracked as a multi-turn active effect
- only Training Buff items are multi-turn in the entire item system
- only one Specialized Training Buff item may be used per turn
- if a Specialized Training Buff item is bought on the current turn and its use conditions pass, it may be used on that same turn

Use order:
- when both Training Buff and Specialized Training Buff are valid on the same turn, use Training Buff first and then Specialized Training Buff

#### Buff Time Restriction
Applies to both Training Buff and Specialized Training Buff.

Add a config and GUI option to restrict usage time:
- `Any time` as default
- `Classic/Senior Summer (July/August)`
- `Senior Year`
- `TS Climax (Final Year)`

This exists to avoid spending buffs too early.

Period interpretation:
- `Senior Year` includes both ordinary Senior-year turns and `Finale Underway` / TS Climax turns
- `TS Climax (Final Year)` remains the narrower final-year-only restriction

Restriction scope:
- buff time restriction applies to usage timing, not purchase timing

#### Training Level
Rule:
- add an option to buy and use training-level items if a training facility level is lower than a configured threshold

GUI and config fields:
- enable toggle
- target maximum or minimum acceptable training level threshold
- checkbox list for the 5 training stats

The planner should only buy and use the corresponding training-level item for stats selected by the user.

Data source:
- training facility levels should be taken from the training API data already used during training score evaluation, not from separate OCR logic
- support-card bond levels should also come from the same training API payload

Multi-item behavior:
- if multiple selected training stats are below threshold in the same turn, the bot should prefer purchases by the normal training priority order from training config
- if affordable and valid, the bot may buy and use all qualifying Training Level items in that prioritized order

Score interaction note:
- Training Level is a permanent progression item and does not affect the training score calculation used for action choice
- summer training is always level 5
- because Training Level does not change training score, using it does not require a training-score refresh cycle

#### Training Shuffle
Rule:
- if the item is in inventory, use it when highest training score is below the configured threshold

Additional option:
- `Only use Training Shuffle in Summer and TS Climax`

This means the decision must check both:
- best available training score
- current career period restriction if enabled

Repeat-use behavior:
- after using Training Shuffle and refreshing training data, if the new best training score is still below threshold and another Shuffle exists in inventory, the bot may use another Shuffle in the same turn
- Training Shuffle may continue repeating until the score passes threshold or inventory runs out

### Race Items

#### Race Bonus
Applies to Artisan and Master Cleat Hammer.

Rule:
- add an option to reserve at least 3 Cleat Hammers for TS Climax races
- prefer reserving 3 Master Cleat Hammers if possible
- if there are excess Cleat Hammers beyond the reserve, use the excess before doing any custom race
- during the 3 TS Climax races, spend all reserved race bonus items

This requires reserve-aware inventory planning, not just immediate use.

Reserve upgrade behavior:
- if the bot already holds 3 reserved Cleat Hammers but some of them are Artisan and a Master Cleat Hammer becomes available in shop before TS Climax, the bot may buy the Master and treat one Artisan as excess inventory
- that excess Artisan is then available for earlier non-TS-Climax race usage

TS Climax use order:
- during TS Climax races, spend the strongest available Cleat Hammer first

Per-turn limit:
- only one Cleat Hammer may be used per race turn

Duration note:
- Race Bonus items only affect the same turn in which they are used
- if bought on the current turn, they are still usable on that same turn

#### Fan Gain
Applies to Glowstick.

Rule:
- add a `Use Glowstick` checkbox to the custom race window for each configured race entry
- if that race entry is selected and Glowstick exists in inventory, use it before the race
- also add a config and GUI option to use Glowstick at TS Climax races

GUI default:
- the per-race `Use Glowstick` checkbox should default to unchecked

Duration note:
- Glowstick only affects the same turn in which it is used
- if bought on the current turn, it is still usable on that same turn

## Multi-turn Effect Protection
This is mandatory in V1.

The runtime must avoid using an item if a conflicting multi-turn effect is already active. This should not depend only on item name matching. It should depend on normalized effect family.

Examples:
- do not use another global training buff if one is already active

If `active_item_effects` from API is too raw or inconsistent, add a normalization layer that maps API effect names to the same conflict keys derived from the catalog.

Scope note:
- only Training Buff items need cross-turn active-effect persistence tracking
- all other item families are same-turn effects and do not need cross-turn active tracking

## Execute Loop Integration

### 1. Turn Start Item State Refresh
At the start of each turn iteration in API mode:
- fetch item-related status
- normalize shop, inventory, conditions, and active effects
- build a turn item context object

### 2. Immediate Usage Pass
Run after purchase pass and before final training or race execution for items that should be consumed immediately:
- all stat items
- energy cap items
- useful energy recovery items
- mood items when mood is below minimum
- positive condition items
- negative condition cures
- Grilled Carrots

There is no required semantic order inside this immediate-use phase. All currently valid immediate-use items can be used in the same turn.

This pass may change energy, mood, conditions, and active effects, so the context should be refreshed or updated after use.

### 3. Purchase Pass
Run once per turn in lobby state before action execution:
- process purchase-template priorities
- process opportunistic auto-buy rules
- update local inventory state after successful purchases

Order rule:
- purchase happens before immediate-use evaluation
- after purchase finishes, re-evaluate inventory for immediate-use items on the same turn

### 4. Action Selection
Run normal training or race decision logic, but expose the chosen action and chosen training score to the item planner.

### 5. Pre-Action Buff Pass
Run after the concrete action is known:
- Training Buff
- Specialized Training Buff
- Good-luck Charm
- Training Shuffle when applicable
- race items before race execution

Training refresh requirement:
- after using any training-related item, re-check training data before finalizing the chosen training
- this applies to at least:
  - Training Buff
  - Specialized Training Buff
  - Training Shuffle
  - Good-luck Charm when its inventory-driven behavior changes whether a training becomes acceptable
- the refreshed training check must rebuild scores and chosen action from updated API data
- this refresh-and-replan cycle may happen multiple times in the same turn when multiple training items are used
- Training Level is excluded from this refresh requirement because it does not affect training score

### 6. Execution Overrides
If Good-luck Charm was used for the chosen training:
- bypass low-energy block
- bypass failure-rate block

This should be implemented as an explicit action-context override, not as a hidden side effect spread across unrelated functions.

## Proposed Runtime Interfaces
Suggested helper functions:

- `load_item_catalog()`
- `get_turn_item_state_api()`
- `normalize_active_item_effects(...)`
- `plan_item_purchases(template, shop_state, inventory_state, context, config)`
- `plan_item_usage(inventory_state, context, config)`
- `build_item_conflict_key(catalog_item)`
- `select_energy_recovery_item(...)`
- `should_use_training_buff(...)`
- `should_use_specialized_training_buff(...)`
- `should_use_good_luck_charm(...)`
- `should_use_training_shuffle(...)`
- `refresh_training_context_after_item_use(...)`
- `plan_race_item_usage(...)`
- `execute_item_purchase_plan(...)`
- `execute_item_usage_plan(...)`

The planner functions should be pure as much as possible so they are easy to test.

## Data and Config Compatibility
Keep the item template structure limited to purchase priority only:
- `items_priority`

Do not reintroduce `items_usage_conditions`.

Add normal config fields for player-controlled behavior. The exact names can be finalized during implementation, but the plan should expect fields equivalent to:
- low mood auto-buy toggle
- bad condition auto-buy toggle
- selected bad conditions to auto-buy cures for
- friendship buy threshold
- Good-luck Charm score threshold
- Good-luck Charm enabled-condition selection
- training buff score threshold
- specialized buff requires training buff toggle
- buff time restriction selection
- training level buy toggle
- training level threshold
- selected training stats for training-level items
- training shuffle score threshold
- training shuffle seasonal restriction toggle
- reserve 3 Cleat Hammers for TS Climax toggle
- use Glowstick in TS Climax toggle
- budget strategy mode: `Buy as much as possible` vs `Save for higher priority items`

Turn normalization rule:
- in Trackblazer API mode, `Year 4` should be normalized to `Finale Underway`
- for item logic, normalized `Finale Underway` is the TS Climax / Final Year bucket

## Test Plan

### API parsing tests
- parse the provided Trackblazer status example
- confirm `shop_coin` is parsed from `status`
- confirm shop items normalize correctly
- confirm inventory items normalize correctly
- confirm active item effects normalize correctly
- confirm conditions are exposed to item logic

### Purchase planner tests
- buys priority items in user order
- skips items not currently in shop
- respects shop sold-out state
- respects template `item_limit`
- applies `item_limit` to opportunistic auto-buy as well
- skips stat items when their target stat is already at or above configured stat cap
- template-priority purchases always run before opportunistic auto-buy purchases
- purchase budget uses `status.shop_coin`
- budget strategy `Buy as much as possible` allows cheaper later candidates after an expensive miss
- budget strategy `Save for higher priority items` stops after an unaffordable higher-priority valid item
- opportunistically buys mood items when low mood auto-buy is enabled
- opportunistically buys matching cure items when bad-condition auto-buy is enabled
- excludes Miracle Cure from opportunistic cure auto-buy
- buys Grilled Carrots only when low-bond support count threshold is met
- buys training-level items only for selected stats and only when level is below threshold

### Usage planner tests
- all stat items are selected for immediate use
- multiple copies of stat items are all used in the same turn
- energy cap items are selected for immediate use
- energy recovery chooses the closest useful fill and avoids waste above max
- energy recovery is not used on race turns
- mood items trigger only when mood is below minimum mood config
- mood auto-buy may purchase multiple mood items in one turn
- mood item usage is calculated to the needed amount and does not blindly consume all copies
- mood items bought this turn are used immediately
- cure item triggers only when matching negative condition exists
- cure auto-buy may purchase multiple matching cure items in one turn
- cure purchase does not buy redundant duplicate cures for the same single condition in one turn
- cure items bought this turn are used immediately if still valid
- positive condition item does not trigger when condition is already active
- positive condition item bought this turn is used immediately if still valid
- positive condition items are only purchased from explicit purchase priority
- positive condition items are not redundantly duplicated in one turn
- Grilled Carrots trigger immediately when in inventory
- Grilled Carrots may be bought in multiple copies when the buy condition is valid
- multiple Grilled Carrot copies are all used in the same turn
- Grilled Carrots bought this turn are used immediately
- training buff does not trigger if conflicting effect is active
- higher percentage Training Buff is preferred over lower percentage Training Buff
- Training Buff is used before Specialized Training Buff when both are valid
- only one Training Buff item is used per turn
- Training Buff bought this turn is usable immediately
- specialized training buff only triggers for matching training type
- specialized training buff obeys the `requires training buff` option
- only one Specialized Training Buff item is used per turn
- Specialized Training Buff bought this turn is usable immediately
- time-window restriction blocks buff use outside allowed career periods
- time restriction applies to use timing only, not purchase timing
- Good-luck Charm obeys single-enabled-condition and dual-enabled-condition behavior correctly
- Good-luck Charm second condition treats Training Buff and Specialized Training Buff as either-or
- Good-luck Charm is only consumed when the chosen training would otherwise be rejected
- Training Shuffle only triggers when highest training score is below threshold
- Training Shuffle seasonal restriction works correctly
- Training Shuffle may repeat in the same turn after refresh if threshold is still not met
- Training Level purchases respect training priority order and may buy multiple items in one turn
- Training Level does not trigger a training-score refresh
- Cleat Hammer reserve logic preserves TS Climax stock
- Master Cleat Hammer upgrades can convert reserved Artisan hammers into excess stock
- TS Climax Cleat Hammer usage prefers the strongest available hammer first
- excess Cleat Hammers are used before custom races
- Glowstick is used for configured custom races when present in inventory
- Glowstick TS Climax option works correctly
- custom race Glowstick checkbox defaults to unchecked
- items bought this turn are usable on that same turn when their family rules allow it

### Integration tests
- item logic runs only in API mode
- item system reads `status` and `training` only, not `state`
- OCR mode behavior remains unchanged
- purchase, immediate-use, action-selection, and pre-action buff passes run in the correct order
- successful item use updates local context for the rest of the turn
- training API is refreshed after any training-related item use that can change the training decision
- multiple item uses in the same turn are planned and executed in stable order
- immediate-use items do not rely on a semantic internal order to become valid
- duplicate same-turn or same-effect usage is blocked
- Good-luck Charm correctly bypasses low-energy and failure-rate rejection for that turn

## Default Assumptions
Unless changed during review:
- API mode only for item execution in V1
- OCR item automation comes later
- current item templates remain the purchase config source
- item usage logic lives in code, not in item templates
- active-effect dedup is required
- item planners should be deterministic and testable
- `Year 4` API state is normalized to `Finale Underway` and treated as TS Climax for item rules
- same-turn item use count is not artificially limited by the planner
- `Classic/Senior Summer (July/August)` means any turn whose normalized year includes `Classic` or `Senior` and whose month is July or August
- the item system relies on `status.shop_coin` for available budget and does not require `state` API
