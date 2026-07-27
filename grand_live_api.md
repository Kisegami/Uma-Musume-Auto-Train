# Grand Live API

This document covers all Grand Live additions to the KUC API.

Base URL:

```text
http://localhost:8123
```

All responses include the current KUC API `version`.

## Endpoints

### Grand Live state

```http
GET /api/scenario/grand-live
```

Alias:

```http
GET /scenario/grand-live
```

Returns the current Grand Live scenario state. Before a Grand Live packet has
been captured, the endpoint returns:

```json
{
  "version": "0.35",
  "status": "waiting"
}
```

### Full state

```http
GET /api/state
```

The full state response now includes a `grand_live` object containing the same
scenario data.

### Training

```http
GET /api/training
```

Each training now includes `performance_gains` during Grand Live.

### Status summary

```http
GET /api/status
```

When Grand Live data is available, the normal status response includes a
compact `grand_live` summary:

```json
{
  "scenario": "Grand Live",
  "grand_live": {
    "hype": {
      "current": 1,
      "required": 3,
      "ready": false
    },
    "songs_learned": 8,
    "next_concert_songs": 1,
    "activated_songs": 7,
    "performance": {
      "dance": 17,
      "passion": 10,
      "vocal": 10,
      "visual": 10,
      "composure": 10
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| `hype.current` | Songs learned since the previous concert. |
| `hype.required` | Songs required for Great Success at the next concert. |
| `hype.ready` | Whether the Great Success requirement has been met. |
| `songs_learned` | Cumulative songs learned during the run. |
| `next_concert_songs` | Number of songs assigned to the upcoming concert. |
| `activated_songs` | Songs whose concert bonuses have activated. |
| `performance` | Current balance of each Performance Point type. |

The field is omitted for non-Grand Live scenarios. Use
`/api/scenario/grand-live` for detailed song objects, lesson choices, maximum
Performance Point values, concert schedule, results, and raw ID arrays.

## Complete Grand Live response

Example based on the newest captured packet:

```json
{
  "version": "0.35",
  "performance": {
    "dance": {
      "current": 0,
      "max": 200
    },
    "passion": {
      "current": 0,
      "max": 200
    },
    "vocal": {
      "current": 0,
      "max": 200
    },
    "visual": {
      "current": 0,
      "max": 200
    },
    "composure": {
      "current": 0,
      "max": 200
    }
  },
  "song_progress": {
    "learned_total": 8,
    "next_concert": 1,
    "activated": 7,
    "hype": {
      "current": 1,
      "great_success_required": 3,
      "great_success_ready": false
    }
  },
  "next_concert": {
    "id": 3,
    "live_type": 3,
    "turn": 48,
    "great_success_required": 3,
    "total_song_requirement": 0,
    "normal_music_id": 0,
    "special_music_id": 0
  },
  "next_concert_songs": [
    {
      "live_id": 1012,
      "command_id": 1012,
      "level": 1,
      "square_id": 40004,
      "title": "Grow Up and Shine!",
      "effect": "Training Skill Pt Gain +3",
      "live_bonus_type": 2,
      "live_bonus_value": 15
    }
  ],
  "learned_songs": [],
  "lesson_choices": [],
  "member_states": [],
  "master_live_ids": [
    1003,
    1006,
    1012,
    1023,
    1032,
    1040,
    1042,
    1044
  ],
  "next_live_ids": [
    1012
  ],
  "effected_live_ids": [
    1003,
    1006,
    1023,
    1032,
    1040,
    1042,
    1044
  ],
  "blocked_performance_types": [],
  "live_results": [
    {
      "live_type": 1,
      "result_state": 2
    },
    {
      "live_type": 2,
      "result_state": 2
    }
  ],
  "reserve_square_id": 0,
  "training_bonuses": [
    {
      "target_type": 6,
      "effect_value": 2
    }
  ]
}
```

The Performance Point numbers above are placeholders for illustrating the
shape; their actual values always come from the latest packet.

## Performance Points

`performance` contains current and maximum values for all five Grand Live
Performance Point types:

| Packet type | API key | Display name |
| ---: | --- | --- |
| 1 | `dance` | Dance |
| 2 | `passion` | Passion |
| 3 | `vocal` | Vocal |
| 4 | `visual` | Visual |
| 5 | `composure` | Composure |

Example:

```json
{
  "dance": {
    "current": 17,
    "max": 200
  }
}
```

## Song progress and hype

```json
{
  "learned_total": 8,
  "next_concert": 1,
  "activated": 7,
  "hype": {
    "current": 1,
    "great_success_required": 3,
    "great_success_ready": false
  }
}
```

Field meanings:

| Field | Meaning |
| --- | --- |
| `learned_total` | Total songs learned during the entire run. |
| `next_concert` | Songs learned since the previous concert. |
| `activated` | Songs whose concert bonuses have already activated. |
| `hype.current` | Current hype, equal to the number of songs for the next concert. |
| `hype.great_success_required` | Songs required for Great Success at the next concert, resolved from the MDB. |
| `hype.great_success_ready` | Whether current hype meets the Great Success requirement. |

The packet sources are:

| API value | Packet source |
| --- | --- |
| `learned_total` | Length of `master_live_id_array`. |
| `next_concert` | Length of `next_live_id_array`. |
| `activated` | Length of `effected_live_id_array`. |
| `hype.current` | Length of `next_live_id_array`. |

`master_live_id_array` is cumulative. `next_live_id_array` resets after a
concert and tracks the current concert cycle.

## Next concert

`next_concert` is resolved from `single_mode_live_live_data` using the current
turn and completed concert types:

```json
{
  "id": 3,
  "live_type": 3,
  "turn": 48,
  "great_success_required": 3,
  "total_song_requirement": 0,
  "normal_music_id": 0,
  "special_music_id": 0
}
```

| Field | Meaning |
| --- | --- |
| `id` | MDB concert schedule row ID. |
| `live_type` | Packet/MDB concert type. |
| `turn` | Turn on which the concert occurs. |
| `great_success_required` | Required current-cycle songs for Great Success. |
| `total_song_requirement` | Total-run song requirement, used by the final concert. |
| `normal_music_id` | Normal concert music ID when configured. |
| `special_music_id` | Special concert music ID when configured. |

## Song objects

`next_concert_songs` contains details for songs currently counting toward the
next concert. `learned_songs` contains the details for all songs learned during
the run.

```json
{
  "live_id": 1012,
  "command_id": 1012,
  "level": 1,
  "square_id": 40004,
  "title": "Grow Up and Shine!",
  "effect": "Training Skill Pt Gain +3",
  "live_bonus_type": 2,
  "live_bonus_value": 15
}
```

| Field | Meaning |
| --- | --- |
| `live_id` | ID found in the packet song arrays. |
| `command_id` | Song command ID from `single_mode_live_song_list`. |
| `level` | Song level. |
| `square_id` | Song lesson square/master bonus content ID. |
| `title` | Localized MDB song title. |
| `effect` | Immediate lesson effect. |
| `live_bonus_type` | Encoded persistent concert bonus type. |
| `live_bonus_value` | Persistent concert bonus value. |

Starting songs that do not have selectable square records are resolved through
the general music-title text table.

## Lesson choices

`lesson_choices` contains the current three lesson slots from
`next_square_info_array`.

Technique example:

```json
{
  "slot": 1,
  "id": 11001,
  "category": "stat",
  "square_type": 1,
  "title": "Dance Step Basics",
  "effect": "Speed +5",
  "cost": [
    {
      "performance_type": 1,
      "performance": "Dance",
      "value": 10
    }
  ],
  "master_bonus_id": 11001,
  "affordable": true
}
```

Song lesson example:

```json
{
  "slot": 1,
  "id": 40020,
  "category": "song",
  "square_type": 4,
  "title": "Zero Is Where the Center Stands!",
  "effect": "Training Speed Gain +1",
  "cost": [
    {
      "performance_type": 1,
      "performance": "Dance",
      "value": 21
    },
    {
      "performance_type": 4,
      "performance": "Visual",
      "value": 21
    }
  ],
  "master_bonus_id": 40020,
  "affordable": false,
  "song": {
    "command_id": 1057,
    "live_id": 1057,
    "level": 1,
    "live_bonus_type": 2,
    "live_bonus_value": 15
  }
}
```

Categories:

| `square_type` | `category` |
| ---: | --- |
| 1 | `stat` |
| 2 | `skill_hint` |
| 3 | `recovery` |
| 4 | `song` |

`affordable` is calculated by comparing every cost component with the current
Performance Point balances.

## Training Performance gains

Each record returned by `/api/training` now includes:

```json
{
  "name": "spd",
  "performance_gains": [
    {
      "performance_type": 1,
      "performance": "Dance",
      "key": "dance",
      "value": 15
    }
  ]
}
```

These values are separate from normal character-stat gains.

## Member states

`member_states` resolves Grand Live member character IDs:

```json
{
  "target_id": 1,
  "chara_id": 1030,
  "chara_name": "Rice Shower",
  "member_state": 1
}
```

`member_state` remains numeric because the current MDB and captures do not
provide a confirmed user-facing label mapping.

## Concert results and bonuses

`live_results` contains completed concert results:

```json
{
  "live_type": 1,
  "result_state": 2
}
```

`training_bonuses` contains active concert training bonuses:

```json
{
  "target_type": 6,
  "effect_value": 2
}
```

These values are retained as packet-native numeric types until their complete
type mappings are confirmed.

## Raw song arrays

The resolved fields are accompanied by the original ID arrays:

| Field | Meaning |
| --- | --- |
| `master_live_ids` | All songs learned during the run. |
| `next_live_ids` | Songs learned for the next concert. |
| `effected_live_ids` | Songs with activated concert bonuses. |

Keeping these arrays allows API consumers to perform their own MDB resolution
or packet-history analysis.

## Historical concert song groups

A single current packet identifies:

- All songs learned during the run.
- Songs assigned to the upcoming concert.
- All songs activated by previous concerts.

It does not preserve the grouping of activated songs by older concert.
Historical groupings require comparing `effected_live_ids` across saved packet
states and recording newly added IDs after each concert.
