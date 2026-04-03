"""Extract baseline grade distributions from latest evaluation reports per family."""
import json
import os
import glob
import sys


def main():
    run_dirs = sorted(glob.glob("runs/*/evaluation_report.json"))
    families = {}
    for rd in run_dirs:
        rd_norm = rd.replace("\\", "/")
        run_id = os.path.dirname(rd_norm).split("/")[-1]
        tokens = run_id.split("_")
        if len(tokens) >= 4:
            key = f"{tokens[2]}_{tokens[3]}"
            families.setdefault(key, []).append((run_id, rd))

    for key in sorted(families):
        run_id, path = families[key][-1]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        pages = data.get("pages", [])
        total = len(pages)
        grades = {}
        for p in pages:
            g = p.get("grade", "U")
            grades[g] = grades.get(g, 0) + 1

        verdict = data.get("verdict", "unknown")

        ab = grades.get("A", 0) + grades.get("B", 0)
        df = grades.get("D", 0) + grades.get("F", 0)
        ab_pct = round(ab / total * 100) if total else 0
        df_pct = round(df / total * 100) if total else 0

        # go_criteria details
        go_list = data.get("go_criteria", [])
        failed = []
        for gc in go_list:
            if not gc.get("passed"):
                failed.append(f"{gc['criterion']}={gc['actual']}")

        # planned page count
        planner_path = os.path.join(os.path.dirname(path), "planner_checkpoint.json")
        planned = "?"
        if os.path.exists(planner_path):
            with open(planner_path, encoding="utf-8") as f:
                planner = json.load(f)
            planned = len(planner.get("pages", []))

        # generation stats
        gen_path = os.path.join(os.path.dirname(path), "generate_checkpoint.json")
        skipped = "N/A"
        if os.path.exists(gen_path):
            with open(gen_path, encoding="utf-8") as f:
                gen = json.load(f)
            stats = gen.get("generation_stats", {})
            skipped = stats.get("skipped_pages", "N/A")

        print(f"=== {key} ===")
        print(f"  Run: {run_id}")
        print(f"  Planned pages: {planned}")
        print(f"  Evaluated pages: {total}")
        print(f"  Skipped pages: {skipped}")
        print(f"  Grades: A={grades.get('A',0)} B={grades.get('B',0)} C={grades.get('C',0)} D={grades.get('D',0)} F={grades.get('F',0)}")
        print(f"  A+B={ab_pct}%  D+F={df_pct}%")
        print(f"  Verdict: {verdict}")
        if failed:
            print(f"  Failed criteria: {', '.join(failed)}")
        print()


if __name__ == "__main__":
    main()
