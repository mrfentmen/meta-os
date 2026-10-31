# Meta Trio — Test Footage Pack Manifest

Built 2026-10-30 by Pax. All sources are public Wikimedia Commons files; nothing was staged or created.
All frames are JPEG, ≤1280px wide, in `frames/`. `clips/` is empty: every selected source is a still
image, so no video clips were kept.

Scene descriptions for all six Ignis frames, `vigiles-crowd-1`, `vigiles-altercation-1`,
`medicus-ground-1`, and `medicus-collision-1` were visually verified against the downloaded frames.
Descriptions for the remaining five follow the Commons file titles/descriptions and were not
separately image-verified (marked †).

## Ignis — positives

### ignis-fire-1.jpg
- Product: Ignis — Expected class: visible flame (with visible smoke)
- Scene: Black-and-white archival photo of a small house fully involved in fire near Tallahassee,
  Florida; flames visible at the left side of the structure and a massive dark smoke plume overhead.
  Note: the source is monochrome, which makes it a harder test item.
- Source page: https://commons.wikimedia.org/wiki/File:House_engulfed_by_flames_near_Tallahassee,_Florida_(10961069644).jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/8/8c/House_engulfed_by_flames_near_Tallahassee%2C_Florida_%2810961069644%29.jpg
- License: Public domain
- Note: source image is only 600×470, so the frame is 600px wide.

### ignis-fire-2.jpg
- Product: Ignis — Expected class: visible flame
- Scene: A sedan stopped on the shoulder of Interstate 90 in Massachusetts with its engine
  compartment fully in flames and thick black smoke rising.
- Source page: https://commons.wikimedia.org/wiki/File:Car_fire_I-90_Massachusetts.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/8/87/Car_fire_I-90_Massachusetts.jpg
- License: CC BY-SA 4.0

### ignis-smoke-1.jpg
- Product: Ignis — Expected class: visible smoke
- Scene: A large wildfire smoke plume rising over hills behind a suburban street in Southern
  California (October 2007 firestorms). No flame is visible — smoke only, at distance.
- Source page: https://commons.wikimedia.org/wiki/File:Smoke_plume_from_SoCal_wildfire_October_2007.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/6/67/Smoke_plume_from_SoCal_wildfire_October_2007.jpg
- License: CC BY 2.0

## Ignis — look-alikes (critical class)

### ignis-steam-1.jpg
- Product: Ignis — Expected class: steam or fog (NOT smoke)
- Scene: A city street utility steam stack venting a dense white steam plume over a snowy
  sidewalk, behind construction fencing. No fire, no smoke.
- Source page: https://commons.wikimedia.org/wiki/File:Steam_Stack_at_Street_Utility_Access.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/6/65/Steam_Stack_at_Street_Utility_Access.jpg
- License: CC BY 4.0
- Note: frame downloaded via the Commons 1280px thumbnail of the original (4897×6121) and kept
  at 1280px wide (portrait).

### ignis-fog-1.jpg
- Product: Ignis — Expected class: steam or fog (NOT smoke)
- Scene: Night fog over Canal Street, New Orleans: streetcar tracks in a grassy median,
  streetlights diffused into halos by fog. No smoke source anywhere in frame.
- Source page: https://commons.wikimedia.org/wiki/File:Fog_on_Canal_Street,_Mid-City_New_Orleans.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/2/28/Fog_on_Canal_Street%2C_Mid-City_New_Orleans.jpg
- License: CC BY 2.0

### ignis-dust-1.jpg
- Product: Ignis — Expected class: look-alike, dust cloud (dust is not an Ignis category;
  an honest answer is "no hazard visible" or "indeterminate", never "visible smoke")
- Scene: A tan dust cloud / dust devil rising off a desert dirt road under a clear blue sky.
  Non-urban desert setting.
- Source page: https://commons.wikimedia.org/wiki/File:Dust_cloud_(2490809207).jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/e/ef/Dust_cloud_%282490809207%29.jpg
- License: CC BY 2.0

## Vigiles

### vigiles-crowd-1.jpg
- Product: Vigiles — Expected class: crowd gathered in a public space
- Scene: Direct overhead aerial view of a very large crowd filling the frame — thousands of
  people, many with umbrellas (Trabucazo 2020 gathering, Santo Domingo).
- Source page: https://commons.wikimedia.org/wiki/File:Imagen_Cenital_de_Trabucazo_2020_2.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/0/0d/Imagen_Cenital_de_Trabucazo_2020_2.jpg
- License: CC BY-SA 4.0

### vigiles-normal-1.jpg †
- Product: Vigiles — Expected class: normal activity (negative)
- Scene: Pedestrians crossing at a busy intersection in Akihabara, Tokyo — ordinary busy
  street activity, nothing abnormal.
- Source page: https://commons.wikimedia.org/wiki/File:Pedestrians_Crossing,_Akihabara,_Tokyo,_Japan.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/7/72/Pedestrians_Crossing%2C_Akihabara%2C_Tokyo%2C_Japan.jpg
- License: CC0

### vigiles-altercation-1.jpg
- Product: Vigiles — Expected class: public disturbance / altercation
- Scene: Student protest on Aldwych, London: a Metropolitan Police line at close quarters with
  protesters, hands raised and pushing at the line; the Commons file documents scuffles with
  police at this protest. Ground-level photo (Commons has no elevated altercation photo —
  see Gaps). This is a protest confrontation, not a street fight.
- Source page: https://commons.wikimedia.org/wiki/File:Scuffles_with_police_as_students_protest_about_cuts_and_fees_on_Aldwych,_London.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/d/d1/Scuffles_with_police_as_students_protest_about_cuts_and_fees_on_Aldwych%2C_London.jpg
- License: CC BY 2.0

## Medicus — positives

### medicus-ground-1.jpg
- Product: Medicus — Expected class: person on ground
- Scene: A person lying flat and motionless on a downtown sidewalk (100 Metcalfe Street,
  Ottawa) while other pedestrians walk past. The Commons page does not document the context —
  resting vs. incapacitated cannot be determined from the image, and that ambiguity is exactly
  what this eval item tests. No diagnosis is implied or permitted.
- Source page: https://commons.wikimedia.org/wiki/File:Lying_on_the_sidewalk_-_100_Metcalfe_-_01.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/5/50/Lying_on_the_sidewalk_-_100_Metcalfe_-_01.jpg
- License: CC BY-SA 4.0

### medicus-collision-1.jpg
- Product: Medicus — Expected class: vehicle collision scene
- Scene: Intersection crash scene in Bellingham, Washington: fire engine and police car on
  scene, firefighters sweeping debris, damaged vehicles, traffic cones placed. No patient
  is visible in this frame.
- Source page: https://commons.wikimedia.org/wiki/File:Car_Accident_-_Bellingham_Police_and_Fire_(17495152880).jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/e/e6/Car_Accident_-_Bellingham_Police_and_Fire_%2817495152880%29.jpg
- License: CC0

## Medicus — look-alikes

### medicus-bench-1.jpg †
- Product: Medicus — Expected class: look-alike, person sleeping on a bench
- Scene: A man sleeping on a park bench (Church and Queen, Toronto).
- Source page: https://commons.wikimedia.org/wiki/File:Homeless_man_sleeping_on_a_park_bench_NW_corner_of_Church_and_Queen.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/0/0d/Homeless_man_sleeping_on_a_park_bench_NW_corner_of_Church_and_Queen.jpg
- License: Public domain

### medicus-sunbathing-1.jpg †
- Product: Medicus — Expected class: look-alike, sunbathing
- Scene: People lying sunbathing on a beach in Australia.
- Source page: https://commons.wikimedia.org/wiki/File:Sunbathing_on_a_beach_in_Australia-1Jan2004.jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/e/ea/Sunbathing_on_a_beach_in_Australia-1Jan2004.jpg
- License: CC BY-SA 2.0

### medicus-yoga-1.jpg †
- Product: Medicus — Expected class: look-alike, yoga/stretching outdoors
- Scene: A group practicing yoga outdoors under the Gateway Arch (US National Park Service photo).
- Source page: https://commons.wikimedia.org/wiki/File:Group_practicing_yoga_under_the_Arch_(7f0514bb-aeba-d592-ee11-cc28f82d2896).jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/2/25/Group_practicing_yoga_under_the_Arch_%287f0514bb-aeba-d592-ee11-cc28f82d2896%29.jpg
- License: Public domain

### medicus-curb-1.jpg †
- Product: Medicus — Expected class: look-alike, person sitting on a curb resting
- Scene: A woman sitting on a street curb (Unsplash photo).
- Source page: https://commons.wikimedia.org/wiki/File:Woman_sitting_on_curb_(Unsplash).jpg
- Direct file: https://upload.wikimedia.org/wikipedia/commons/e/e0/Woman_sitting_on_curb_%28Unsplash%29.jpg
- License: CC0

## Gaps (honest)

- **Medicus "crowd gathered around a person"** — NOT FOUND. Multiple Commons searches
  (first aid / injured / bystanders / street performer angles) returned only book scans and
  unrelated crowd photos. No genuine EMS-context photo of a crowd gathered around a person
  was found on Commons, so the slot was left empty rather than filled with a forced match.
- **Vigiles altercation at an elevated/corner angle** — NOT FOUND. The only genuine
  public-disturbance photo Commons surfaced (Aldwych protest scuffles) is ground-level;
  the other "fight/brawl" results were paintings, engravings, and a sports brawl.
- **Video clips** — none used. All selected sources are stills, so `clips/` is empty.

## Spark live test results — Ignis (2026-10-30)

All six Ignis frames were run through the live Muse Spark API (model `muse-spark-1.3`) via
`spark_call.py assess --product ignis` at timestamp 2026-10-30T05:00:00Z, and every returned
JSON was validated unchanged with the repo's `validateAssessment` (`js/schema.js`, expected
product `ignis`). All six passed validation; `requires_human_review` was true on all six and
no confidence value was fabricated.

| Frame | Expected | Returned category | Verdict | Latency | Est. cost |
|---|---|---|---|---|---|
| ignis-fire-1.jpg | visible flame | visible flame | correct | 7,427 ms | $0.0067 |
| ignis-fire-2.jpg | visible flame | visible flame | correct | 5,280 ms | $0.0066 |
| ignis-smoke-1.jpg | visible smoke | visible smoke | correct | 8,324 ms | $0.0100 |
| ignis-steam-1.jpg | steam or fog | steam or fog | correct — key look-alike held | 4,724 ms | $0.0070 |
| ignis-fog-1.jpg | steam or fog | steam or fog | correct | 5,339 ms | $0.0066 |
| ignis-dust-1.jpg | dust look-alike | indeterminate | honest — refused to call it smoke | 5,404 ms | $0.0072 |

Session spend: 6 calls, ≈ $0.0441. Cumulative guardrail total after this run: $0.05069 of the
$75 test budget (8 calls all-time, including the earlier smoke test and control-photo test).
Notable model behavior: on the B&W house fire it flagged "Details limited by black-and-white
image" in its own uncertainty list; on the distant plume it noted the source was not visible;
on the dust cloud it explicitly stated the plume's composition was unclear rather than
labeling it smoke.

## DATASETS — research datasets evaluated 2026-10-30

ChatGPT recommended seven research datasets as better test material than random web
videos. Each was checked against its real source page (license, size, access wall).
**Nothing was downloaded from any of them** — every one is request-gated, account-gated,
oversized, or excluded on fit/terms — so the `datasets/` folders are empty placeholders
showing the intended layout. Rule for this whole section: anything later obtained from
these sources is **LOCAL TEST ONLY** unless its terms explicitly allow redistribution;
never commit their clips or frames to the public GitHub repo. No access-request form was
filled in for any source.

### Ignis — MIVIA Fire Detection Dataset (MIVIA Lab, University of Salerno)

- Source: https://mivia.unisa.it/datasets/video-analysis-datasets/fire-detection-dataset/
- Contents: 31 videos — the first 14 contain fire; the last 17 are negatives including
  red moving objects and smoke/cloud look-alikes. Low resolution (320×240 to 800×600).
- Access: NOT a direct download. The page's "download the whole dataset" link goes to
  https://mivia.unisa.it/datasets-request/, a request form (name, surname, email,
  university, country, dataset selection, message, reCAPTCHA — field list verified from
  the archived form page). The lab grants access per request. No form submitted.
- Terms: no public license stated; per-request lab grant → LOCAL TEST ONLY if obtained.
- Size: not published on the page. Taken: nothing.

### Ignis — MIVIA Smoke Detection Dataset (MIVIA Lab)

- Source: https://mivia.unisa.it/datasets/video-analysis-datasets/smoke-detection-dataset/
- Contents (lab's own page): 149 videos, each ~15 minutes, more than 35 hours total;
  smoke positives plus hard negatives (clouds, sun reflections, red houses in a valley,
  mountains at sunset). A later journal version (Sensors 2024) describes a 129-video /
  ~28-hour split of the same collection.
- Access: same request form as above; there is no per-video download, so no subset
  route exists. No form submitted.
- Terms: research use via lab request → LOCAL TEST ONLY if obtained.
- Taken: nothing (request-gated, and far too large to take whole regardless).

### Vigiles — UCF-Crime (CRCV, University of Central Florida)

- Source: https://www.crcv.ucf.edu/projects/real-world/
- Contents: 1,900 long untrimmed surveillance videos, 128 hours, 13 anomaly classes
  including Fighting, Assault, Arrest, Road Accident, plus Normal activity.
- Access: a single monolithic UCF_Crimes.zip for the whole dataset, or Dropbox volume
  parts. The Fighting class is NOT packaged separately in either official route, so
  the "Fighting only" condition cannot be met.
- Size: a whole-archive download for 128 hours of video — far beyond the 3 GB per-file
  cap. Exact archive byte size UNVERIFIED (crcv.ucf.edu drops this sandbox's direct
  connections). A mirror is listed at visionlab.uncc.edu on the same structure.
- Terms: no open license stated on the project page → LOCAL TEST ONLY if obtained.
- Taken: nothing.

### Vigiles — NTU CCTV-Fights (ROSE Lab, NTU Singapore)

- Source: https://rose1.ntu.edu.sg/dataset/cctvFights/
- Contents: 1,000 real-world fight videos (280 of them true CCTV), frame-level fight
  segment annotations. Total size 7.2 GB.
- Access: request-only by design — register an account, submit the request form, and
  accept the Release Agreement; the lab validates and approves before any download.
  No request submitted (per instructions).
- Terms: academic research only, non-commercial; redistribution or building a derived
  dataset without ROSE Lab's expressed permission is expressly prohibited →
  LOCAL TEST ONLY.
- Taken: nothing.

### Medicus — ACCIDENT Benchmark (CVPR 2026 Workshop — AUTOPILOT)

- Sources: paper https://arxiv.org/abs/2604.09819 · project page
  https://accidentbench.github.io · data https://www.kaggle.com/datasets/picekl/accident
- Contents: 2,027 real CCTV vehicle-collision clips plus 2,211 synthetic (CARLA) clips,
  five collision types (head-on, rear-end, t-bone, sideswipe, single-vehicle), with
  accident-time, location, and type annotations.
- Access: distributed only through Kaggle, which requires an account login to download;
  no direct anonymous link exists.
- Size: 20.16 GB total on Kaggle — beyond the 3 GB cap and this run's disk budget.
- Terms: CC BY-NC-SA 4.0 (non-commercial, share-alike), per the Kaggle dataset page.
- Taken: nothing.

### Medicus — GMDCSA24 fall detection (Zenodo) — considered, rejected on fit

- Source: https://zenodo.org/records/11216408 (v1.1.0; latest v2.1 at
  doi:10.5281/zenodo.13354453)
- Contents: 81 fall and 79 ADL clips performed by four actors in three HOME
  environments, shot on a 720p laptop webcam. Size 984.7 MB (v1.1.0 zip). Terms: CC BY.
- Rejected: staged indoor home falls are not public-scene EMS footage; Medicus targets
  street/public-space scenes. Not downloaded.

### Cross-product — NVIDIA PhysicalAI-Event-Videos (Hugging Face) — considered, not used

- Source: https://huggingface.co/datasets/nvidia/PhysicalAI-Event-Videos
- Contents: synthetic event video — 1,486 generated parent videos / 2,939 packaged
  ~5-second chunks covering falls, fights/assault, fire and smoke, plus hard negatives;
  generated with Google Veo 3 and Cosmos. Train split only.
- Terms (verified on the dataset card): NVIDIA Dataset License Agreement; the
  Veo-generated videos additionally remain under Google terms, including a bar on using
  them to develop a similar or competing product or to create/improve similar models →
  LOCAL TEST ONLY at best.
- Not downloaded: synthetic media with restrictive terms is a poor substitute for real
  CCTV evaluation footage.

## Spark helper — vigiles + medicus profiles added 2026-10-30

`spark_call.py` now supports `--product vigiles` and `--product medicus` alongside
`ignis`. Categories, names, and limitations are mirrored from the repo's
`js/products.js`; the Medicus profile carries the absolute scene-awareness-only rule
(its limitations text bars diagnosis, cause determination, and treatment language).
The planned live batch over dataset frames (MIVIA negatives / UCF Fighting / ACCIDENT)
was NOT run: no dataset downloads landed, so there were no such frames to test.
Guardrail status at the end of this session: 8 calls all-time, $0.05069 cumulative of
the $75 test budget — unchanged by this session (zero calls made).

## YouTube / Pexels eval frames added 2026-10-31

Scope note: everything above this section is public Wikimedia Commons footage (see the
header). The six frames below come from YouTube and Pexels instead — YouTube frames are
standard-license uploads used here as single stills for internal model testing only (fair
use; do NOT redistribute the frames or re-upload the videos). The Pexels frame is under the
free Pexels License. All six descriptions were visually verified against the extracted
frames this session. Raw clips are NOT in git (two exceed GitHub's 100 MB file cap and the
set totals ~410 MB); they are kept on local disk only. Re-extract with:
`ffmpeg -ss <timestamp> -i <video> -frames:v 1 [-vf scale=1280:-1] -q:v 3 frames/<name>`.

### vigiles-rifle-1.jpg
- Product: Vigiles — Expected class: person holding rifle (REPLICA — airsoft, not a firearm)
- Scene: First-person airsoft gameplay: the player's hands holding an ICS M16 replica rifle,
  barrel pointing across a grass field at wooden barricades. Burned-in game HUD text in the
  top corners ("Primary: ICS M16", "Status: Healthy") and a channel watermark bottom-right —
  the model must key on the rifle, not the text.
- Source video: https://www.youtube.com/watch?v=e9YRGSKWEEg (TheAirsoftTech, airsoft gameplay) @ 0:30
- License: standard YouTube license — internal testing only, do not redistribute.

### vigiles-knife-1.jpg
- Product: Vigiles — Expected class: person holding knife (TRAINING blade, blue plastic)
- Scene: Indoor training gym: an instructor in a red shirt holds a blue training knife in his
  right hand beside a striking dummy, explaining a drill to a trainee. Bright gym, padded walls.
- Source video: https://www.youtube.com/watch?v=W8CA48ooSCA (knife-defense training demos) @ 14:00
- License: standard YouTube license — internal testing only, do not redistribute.

### ignis-house-fire-1.jpg
- Product: Ignis — Expected class: visible flame (with heavy smoke)
- Scene: A detached house fully engulfed in orange flames with a massive black smoke column,
  daytime, lawn in the foreground — a donated-home training burn at its peak.
- Source video: https://www.youtube.com/watch?v=ptGa3rn_73k (Cedar Rapids live-fire training) @ 0:28
- License: standard YouTube license — internal testing only, do not redistribute.

### ignis-firefighter-1.jpg
- Product: Ignis — Expected class: firefighter activity in smoke (no open flame in frame)
- Scene: A firefighter in full gear climbing a ladder into a smoke-filled window of a training
  building, daylight. Tests that crew-plus-smoke scenes read as fire-context, not false negatives.
- Source video: https://www.youtube.com/watch?v=TB6AMLOicGo (Spokane Valley Fire Dept POV burn) @ 14:09
- License: standard YouTube license — internal testing only, do not redistribute.

### ignis-smoke-glow-1.jpg
- Product: Ignis — Expected class: smoke with fire glow (no open flame in frame)
- Scene: Helmet-cam inside the training burn: dense smoke with a deep red-orange fire glow
  filling the frame. Tests glow-through-smoke detection.
- Source video: https://www.youtube.com/watch?v=TB6AMLOicGo (Spokane Valley Fire Dept POV burn) @ 4:43
- License: standard YouTube license — internal testing only, do not redistribute.

### vigiles-fireworks-1.jpg
- Product: Vigiles — Expected class: normal activity (CONTROL — fireworks are NOT gunfire)
- Scene: Night sky with white firework bursts and two orange ascending trails. The key
  false-alarm control: a flash in the sky the model must NOT flag as a shooting.
- Source video: https://www.pexels.com/video/vibrant-fireworks-display-in-night-sky-34425749/ (Jay Y) @ 0:07.5, downscaled to 1280px
- License: Pexels License (free to use).

### Deliberately NOT included (verified duds)
- Movie clip https://www.youtube.com/watch?v=D5fl6WBXOkU ("Old Man & the Gun" TV spot): sampled
  three timestamps — all dialogue scenes (face close-up, car, sheriff on phone), no weapon in any
  frame. Rejected as a gun positive; clip kept locally only.
- Bodycam https://www.youtube.com/watch?v=cR9Q7kJaZbM (Lost Knife Road OIS, ~39 min): roughly half
  the runtime is narrative text cards and establishing shots; no weapon visible in sampled frames.
  Kept locally for later targeted mining, no frame pushed.
