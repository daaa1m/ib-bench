- this folder will contain the evaluation results for different eval runs
- run resumes from last task / instance if innterupted
- preliminary structure will be as per below. open to changes for simplicity, efficiency or robustness

├── results/
│ └── {hash-of-run}-{model}/
│ ├── config.json # How this run was configured
│ ├── responses/ # Expensive, hence cached
│ │ ├── e-001.json
│ │ └── e-002.json
│ ├── scores/ # Cheap, regenerate freely  
│ │ ├── e-001.json
│ │ └── e-002.json
│ └── summary.json
