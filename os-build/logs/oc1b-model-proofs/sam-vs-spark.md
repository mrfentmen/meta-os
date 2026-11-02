# OC1B-206 SAM vs Spark region comparison (frame test-footage/frames/ignis-fire-1.jpg, tree 94010c76)

SAM 3.1 live (models.segment, prompt "the burning building engulfed in flames",
latency 1755ms, model sam-3.1, mask 71,049 chars):
- box_px: x1=10 y1=0 x2=599 y2=353 on 600x470
- region (0-1000 scale): x=17 y=0 w=982 h=751

Muse Spark 1.3 live (spark_gen.generate, division ignis, latency 15787ms,
model muse-spark-1.3, category "structure fire"):
- structure fire: region x=200 y=545 w=435 h=210 ("Single-story structure actively burning ...")
- visible flame: region x=140 y=525 w=500 h=170 ("Bright flames visible on left side ...")
- dark smoke: region x=15 y=0 w=975 h=600 ("Large dense dark smoke plume ...")
- indeterminate: region x=0 y=780 w=30 h=120 (distant person figure)

Reading as they fell: SAM returns ONE coarse box over the whole burning
scene (full width, upper three-quarters). Spark returns one box per
observation: the structure-fire and visible-flame boxes sit INSIDE the SAM
box's horizontal span; the smoke box overlaps SAM's upper band almost fully
(x15 y0 w975 h600 vs SAM x17 y0 w982 h751). Both readings agree the frame
shows a structure fire; the numeric regions overlap substantially but are
not identical — SAM localises the scene, Spark localises its parts.
No region invented on either side; full records in sam-direct.json and
the Spark receipt line in server/queue/model_receipts.jsonl.
