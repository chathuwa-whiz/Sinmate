# Sinmate Teacher Ingest Report

- **Total Raw Inputs**: 117
- **Accepted**: 117 (106 train, 11 val)
- **Rejected**: 0
- **DPO Preference Pairs**: 117
- **Flagged for Review**: 31

---

### 1. Persona Distribution
| Persona | Count | Current % | Target % | Status |
| :--- | :--- | :--- | :--- | :--- |
| `BEST_FRIEND` | 32 | 27.4% | 27.0% | ✅ OK |
| `SPECIAL_PARTNER` | 32 | 27.4% | 25.0% | ✅ OK |
| `MOTHER_FIGURE` | 29 | 24.8% | 23.0% | ✅ OK |
| `TEACHER` | 24 | 20.5% | 25.0% | ✅ OK |

### 2. Input Type Distribution
| Input Type | Count | Current % | Target % | Status |
| :--- | :--- | :--- | :--- | :--- |
| `sinhala_unicode` | 51 | 43.6% | 45.0% | ✅ OK |
| `singlish` | 36 | 30.8% | 35.0% | ✅ OK |
| `code_switched` | 30 | 25.6% | 20.0% | ✅ OK |

### 3. Emotion Distribution
| Emotion | Count | Current % | Target % | Status |
| :--- | :--- | :--- | :--- | :--- |
| `neutral` | 42 | 35.9% | 36.0% | ✅ OK |
| `work_burnout_exhaustion` | 14 | 12.0% | 15.0% | ✅ OK |
| `celebration_and_joy` | 12 | 10.3% | 15.0% | ✅ OK |
| `panic_and_anxiety` | 19 | 16.2% | 12.0% | ✅ OK |
| `frustration_and_anger` | 10 | 8.5% | 12.0% | ✅ OK |
| `grief_and_loss` | 11 | 9.4% | 8.0% | ✅ OK |
| `crisis_support` | 9 | 7.7% | 2.0% | ✅ OK |

### 4. Exchange Length Distribution
| Exchanges | Count | Current % | Target % | Status |
| :--- | :--- | :--- | :--- | :--- |
| `1` exchange(s) | 68 | 58.1% | 50.0% | ✅ OK |
| `2` exchange(s) | 39 | 33.3% | 30.0% | ✅ OK |
| `3+` exchange(s) | 10 | 8.5% | 20.0% | ℹ️ Imbalanced |

### 5. ADR-006 Category Distribution
| Category | Count | Share |
| :--- | :--- | :--- |
| `<unmapped/dropped>` | 40 | 34.2% |
| `family_and_home` | 20 | 17.1% |
| `exam_and_study` | 20 | 17.1% |
| `work_stress` | 13 | 11.1% |
| `food_and_cravings` | 9 | 7.7% |
| `tech_and_coding` | 7 | 6.0% |
| `commute_and_traffic` | 4 | 3.4% |
| `late_night_insomnia` | 3 | 2.6% |
| `cricket_and_sports` | 1 | 0.9% |

### 6. Flagged Dialogues for Human Review
Found 31 flagged dialogue(s):

| ID | File:Line | Scenario | Flags |
| :--- | :--- | :--- | :--- |
| `sinmate_00011` | `accepted_dialogs.jsonl:11` | User is leaving for tuition class early  | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00013` | `accepted_dialogs.jsonl:13` | User is nervous right before an online j | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00014` | `accepted_dialogs.jsonl:14` | User cooked chicken curry by themselves  | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00015` | `accepted_dialogs.jsonl:15` | User is washing clothes on the weekend | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00016` | `accepted_dialogs.jsonl:16` | Student asks how inflation works in simp | `specific_prices_or_stats` |
| `sinmate_00021` | `accepted_dialogs.jsonl:21` | Friends deciding where to eat after even | `hearsay_stated_as_fact` |
| `sinmate_00025` | `accepted_dialogs.jsonl:25` | User has sore legs from standing all day | `health_claim_or_remedy` |
| `sinmate_00026` | `accepted_dialogs.jsonl:26` | User baked a chocolate cake that turned  | `gendered_user_assumption` |
| `sinmate_00028` | `accepted_dialogs.jsonl:28` | Monkeys came into the garden and ruined  | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00029` | `accepted_dialogs.jsonl:29` | User just got back to their boarding pla | `clumsy_idiom_le_inuwe, gendered_mother_figure_putha_or_duwa` |
| `sinmate_00031` | `accepted_dialogs.jsonl:31` | User received their first salary from a  | `archaic_phrase_hahapura, gendered_mother_figure_putha_or_duwa` |
| `sinmate_00035` | `accepted_dialogs.jsonl:35` | User is sitting in the campus canteen wa | `hearsay_stated_as_fact` |
| `sinmate_00044` | `accepted_dialogs.jsonl:44` | User brought homemade rice and curry to  | `literary_malupini` |
| `sinmate_00045` | `accepted_dialogs.jsonl:45` | Dark clouds are gathering while clothes  | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00046` | `accepted_dialogs.jsonl:46` | User cleaned the entire bedroom and rear | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00047` | `accepted_dialogs.jsonl:47` | User accidentally burned the dhal curry  | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00048` | `accepted_dialogs.jsonl:48` | User has a slight scratchy throat in the | `gendered_mother_figure_putha_or_duwa, health_claim_or_remedy` |
| `sinmate_00049` | `accepted_dialogs.jsonl:49` | User is at the weekend pola buying veget | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00057` | `accepted_dialogs.jsonl:57` | User managed to buy tickets for a popula | `hearsay_stated_as_fact` |
| `sinmate_00064` | `accepted_dialogs.jsonl:64` | User is lighting the oil lamp in the eve | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00065` | `accepted_dialogs.jsonl:65` | User just returned after a long six-hour | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00066` | `accepted_dialogs.jsonl:66` | User cut their finger slightly while cho | `gendered_mother_figure_putha_or_duwa, health_claim_or_remedy` |
| `sinmate_00067` | `accepted_dialogs.jsonl:67` | Water supply was cut off suddenly withou | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00068` | `accepted_dialogs.jsonl:68` | User's younger sister got selected to un | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00079` | `accepted_dialogs.jsonl:79` | User tells mother figure they feel worth | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00080` | `accepted_dialogs.jsonl:80` | User says the mental pain is too much an | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00093` | `accepted_dialogs.jsonl:93` | User's older brother had to undergo an e | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00100` | `accepted_dialogs.jsonl:100` | User remarks that although they call the | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00101` | `accepted_dialogs.jsonl:101` | User asks the mother persona if she is a | `gendered_mother_figure_putha_or_duwa` |
| `sinmate_00112` | `accepted_dialogs.jsonl:112` | User overslept on the first day of their | `gendered_mother_figure_putha_or_duwa` |

*(and 1 more flags)*
