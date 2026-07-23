# Digest — qwen

## q4
- A_coding pass_rate (avg): **0.991**  (n=12)
- C_edit  pass_rate (avg): **0.894**  | surgical_score avg: 0.25 | noise acted-on: 4/6
- B_review recall/precision (avg): **0.5 / 0.778**  | hallucinated total: 4
- D_text: 6 units run (qualitative grade — analysis phase)
- Speed probe: decode **86.8** t/s | prefill 907.2 t/s   ·   in-task decode avg: 59.092 t/s
- Tool-calls: total 157 / malformed 51 (**32%**)
- Termination: {'clean': 25, 'no_tools': 3}   ·   RAM peak: 24.9 GB

## q5
- A_coding pass_rate (avg): **0.97**  (n=12)
- C_edit  pass_rate (avg): **0.863**  | surgical_score avg: 0.15 | noise acted-on: 6/6
- B_review recall/precision (avg): **0.556 / 0.834**  | hallucinated total: 3
- D_text: 6 units run (qualitative grade — analysis phase)
- Speed probe: decode **92.6** t/s | prefill 890.1 t/s   ·   in-task decode avg: 57.459 t/s
- Tool-calls: total 162 / malformed 45 (**28%**)
- Termination: {'clean': 26, 'no_tools': 3}   ·   RAM peak: 27.6 GB
