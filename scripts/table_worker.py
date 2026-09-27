"""Persistent JSON-lines worker; launched by the Sage search within its allocation."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gf5minors.table_sat import solve_problem
from gf5minors.table_join import solve_join

for line in sys.stdin:
    problem = json.loads(line)
    try:
        method = problem.get("method", "sat")
        if method == "sat":
            answer = solve_problem(problem,seconds=problem.get("seconds",60))
        else:
            answer = solve_join(problem,seconds=problem.get("seconds",60))
            if method == "both" or answer["status"] == "UNKNOWN":
                sat = solve_problem(problem,seconds=problem.get("seconds",60))
                if answer["status"] == "EXHAUSTED" and sat["status"] == "EXHAUSTED":
                    assert set(answer["models"]) == set(sat["models"]), "SAT/join disagreement"
                    answer["sat_crosscheck"] = True
                    answer["sat_seconds"] = sat["seconds"]
                elif answer["status"] == "UNKNOWN":
                    answer = sat
                else:
                    answer["sat_crosscheck"] = False
    except Exception as error:
        answer = {"error":repr(error)}
    print(json.dumps(answer),flush=True)
