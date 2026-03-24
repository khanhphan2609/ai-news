# run_eval.py
import subprocess

steps = [
    # ("Sinh nhãn tự động", "auto_label.py"),
    ("Đánh giá Retrieval", "eval_retrieval.py"),
    ("Đánh giá Generation", "eval_generation.py"),
]

for name, script in steps:
    print(f"\n{'='*40}")
    print(f"▶ {name}")
    print('='*40)
    subprocess.run(["python", script], check=True)