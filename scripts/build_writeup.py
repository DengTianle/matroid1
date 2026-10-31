"""Audit the saved result, generate the paper's tables, and render offline HTML.

Run certificate replay through Slurm, for example:
  sbatch slurm/research.slurm sat scripts/build_writeup.py --recheck-certificates

Only paper/ is written; the search and its original evidence are preserved.
The HTML uses native MathML and embeds its CSS, requiring no network access.
"""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gf5minors.compact import unpack
from gf5minors.matroid import verify_representation


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_json(path):
    return json.loads(path.read_text())


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def expand_inputs(path):
    """Expand only local paper includes before the HTML conversion."""
    def include(match):
        target = (path.parent / match[1]).resolve()
        require(target.is_relative_to(ROOT / "paper"), "Input outside paper directory")
        return expand_inputs(target)
    return re.sub(r"\\input\{([^{}]+)\}", include, path.read_text())


def html_source(source):
    """Make LaTeX counters and cross-references explicit for Pandoc's reader.

    Pandoc does the actual LaTeX and mathematical parsing. This pass supplies
    the amsthm numbering and bibliography labels normally supplied by TeX.
    """
    labels = {}
    section = subsection = theorem = table = 0
    appendix = False
    current = ""
    token = re.compile(
        r"\\appendix\b|\\(section|subsection)\{([^{}]*)\}|"
        r"\\begin\{(theorem|lemma|proposition|corollary|definition|table)\}"
        r"(?:\[([^\]]*)\])?|\\label\{([^{}]+)\}"
    )

    def number(match):
        nonlocal section, subsection, theorem, table, appendix, current
        if match[0] == r"\appendix":
            appendix = True
            section = 0
            return ""
        if match[1] == "section":
            section += 1
            subsection = theorem = 0
            current = chr(64 + section) if appendix else str(section)
            return rf"\section{{{current}. {match[2]}}}"
        if match[1] == "subsection":
            subsection += 1
            prefix = chr(64 + section) if appendix else str(section)
            current = f"{prefix}.{subsection}"
            return rf"\subsection{{{current}. {match[2]}}}"
        if match[3] == "table":
            table += 1
            current = str(table)
            return match[0]
        if match[3]:
            theorem += 1
            prefix = chr(64 + section) if appendix else str(section)
            current = f"{prefix}.{theorem}"
            name = match[3].capitalize()
            title = f" ({match[4]})" if match[4] else ""
            return rf"\begin{{quote}}\textbf{{{name} {current}{title}.}} "
        labels[match[5]] = current
        return rf"\hypertarget{{{match[5]}}}{{}}"

    source = token.sub(number, source)
    source = re.sub(
        r"\\end\{(?:theorem|lemma|proposition|corollary|definition)\}",
        r"\\end{quote}", source,
    )
    source = re.sub(
        r"\\begin\{proof\}(?:\[([^\]]*)\])?",
        lambda m: rf"\par\emph{{{m[1] or 'Proof'}.}} ", source,
    )
    source = source.replace(r"\end{proof}", r"\hfill\(\square\)\par")

    def reference(match):
        require(match[1] in labels, f"Unresolved reference: {match[1]}")
        return rf"\href{{#{match[1]}}}{{{labels[match[1]]}}}"

    source = re.sub(r"\\ref\{([^{}]+)\}", reference, source)
    bibliography = {}

    def bibitem(match):
        bibliography[match[1]] = len(bibliography) + 1
        return rf"\par\hypertarget{{ref-{match[1]}}}{{}}\textbf{{[{bibliography[match[1]]}]}} "

    source = re.sub(r"\\bibitem\{([^{}]+)\}", bibitem, source)
    source = re.sub(r"\\begin\{thebibliography\}\{[^{}]*\}",
                    r"\\section*{References}", source)
    source = source.replace(r"\end{thebibliography}", "")

    def cite(match):
        keys = match[1].split(",")
        require(all(key in bibliography for key in keys), "Unresolved citation")
        return ", ".join(rf"\href{{#ref-{key}}}{{[{bibliography[key]}]}}" for key in keys)

    return re.sub(r"\\cite\{([^{}]+)\}", cite, source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recheck-certificates", action="store_true")
    parser.add_argument("--render-only", action="store_true",
                        help="Refresh HTML after prose/layout edits, preserving the certificate audit")
    parser.add_argument("--pandoc", type=Path)
    args = parser.parse_args()
    started = monotonic()
    result = ROOT / "results/r4-n11"
    paper = ROOT / "paper"
    if args.render_only:
        require(not args.recheck_certificates, "Choose full validation or render-only")
        report = read_json(paper / "validation.json")
        require(digest(result / "excluded.jsonl") == report["catalogue_sha256"], "Catalogue changed")
        summary = read_json(result / "summary.json")
        for group in ("inputs", "critical_sources"):
            for relative, expected in summary[group].items():
                require(digest(ROOT / relative) == expected, f"Changed proof input/source: {relative}")
        render_html(paper, args.pandoc)
        report["html_sha256"] = digest(paper / "gf5-r4-n11.html")
        report["paper_source_sha256"] = digest(paper / "main.tex")
        report["html_refreshed_without_replaying_unchanged_certificates"] = True
        (paper / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"rendered": "paper/gf5-r4-n11.html", "seconds": monotonic() - started}))
        return
    generated = paper / "generated"
    generated.mkdir(exist_ok=True)
    summary = read_json(result / "summary.json")
    verification = read_json(result / "verification.json")
    records = read_jsonl(result / "excluded.jsonl")
    descriptions = read_json(result / "hyperplanes.json")
    statistics = read_json(result / "statistics.json")
    catalogue_digest = digest(result / "excluded.jsonl")
    require(catalogue_digest == summary["catalogue_sha256"] == verification["catalogue_sha256"],
            "Catalogue digest mismatch")
    require(summary["search_complete"] and verification["search_complete"], "Incomplete search")
    require(len(records) == len(descriptions) == len(statistics) == 35, "Catalogue length mismatch")

    for group in ("inputs", "critical_sources"):
        for relative, expected in summary[group].items():
            require(digest(ROOT / relative) == expected, f"Changed proof input/source: {relative}")

    statuses = Counter()
    methods = Counter()
    covered = set()
    candidate_count = 0
    shard_rows = []
    for shard in summary["shards"]:
        rows = read_jsonl(ROOT / shard["directory"] / "parents.jsonl")
        indices = [row["parent"] for row in rows]
        require(indices == list(range(shard["start"], shard["stop"])), "Parent range mismatch")
        require(not covered.intersection(indices), "Overlapping parent ranges")
        covered.update(indices)
        require(shard["complete_for_range"] and not shard["unknown_parents"], "Incomplete shard")
        for row in rows:
            statuses[row["status"]] += 1
            if row["status"] == "EXHAUSTED":
                candidate_count += row["models_count"]
                methods[row.get("method", "sat")] += 1
        shard_rows.append(
            f"{shard['start']:,} & {shard['stop']:,} & {len(rows):,} & "
            f"{shard['deletion_minimal_candidates']:,} & {shard['seconds']:.2f} " + r"\\"
        )
    require(covered == set(range(58756)), "Missing parent indices")
    require(statuses == {"EXHAUSTED": 58672, "DISCONNECTED_PARENT": 84}, "Unexpected parent statuses")
    require(candidate_count == summary["deletion_minimal_candidates"] == 659, "Candidate count mismatch")

    levels = {(4, 4): (1, 1)}
    for level in verification["parent_catalogue_levels"]:
        rank, size = level["rank"], level["size"]
        directory = ROOT / ("data/parents" if rank == 4 else "data/parents-r3")
        rep = directory / f"representations-r{rank}-n{size}.jsonl"
        abstract = directory / f"abstract-r{rank}-n{size}.jsonl"
        require(level["complete"], "Incomplete represented catalogue")
        require(digest(rep) == level["representations_sha256"], "Represented catalogue changed")
        require(digest(abstract) == level["abstracts_sha256"], "Abstract catalogue changed")
        rep_count = sum(1 for line in rep.open() if line.strip())
        abstract_count = sum(1 for line in abstract.open() if line.strip())
        require(rep_count == level["representation_classes"] and abstract_count == level["abstract_classes"],
                "Represented catalogue count mismatch")
        levels[rank, size] = rep_count, abstract_count
    labelled = read_jsonl(ROOT / "data/parents/labelled-r4-n10.jsonl")
    require(len(labelled) == 58756 and sum(len(row["matrices"]) for row in labelled) == 71547,
            "Labelled representation count mismatch")

    proofs = read_jsonl(result / "nonrepresentation/verification.jsonl")
    witnesses = read_jsonl(result / "minors/minor-witnesses.jsonl")
    require(len(proofs) == len(witnesses) == len(records), "Missing certificate records")
    for relative in ("minors/summary.json", "nonrepresentation/summary.json"):
        certificate_summary = read_json(result / relative)
        require(certificate_summary["complete"] and certificate_summary["input_sha256"] == catalogue_digest,
                "Certificate input/completion mismatch")
        require((certificate_summary["start"], certificate_summary["stop"]) == (0, 35),
                "Incomplete certificate range")

    replayed = checked_matrices = 0
    triangle_histogram = Counter()
    catalogue_lines = ["% Generated by scripts/build_writeup.py from the checked catalogue."]
    for index, (record, desc, stats, proof, witness) in enumerate(
            zip(records, descriptions, statistics, proofs, witnesses)):
        m = unpack(record, validate=False)
        class_id = f"GF5-r4-n11-{index+1:04d}"
        require((m.n, m.r) == (11, 4), "Wrong dimensions")
        require(record["class_id"] == desc["class_id"] == stats["class_id"] == class_id, "Class order mismatch")
        require(proof["index"] == witness["index"] == index, "Certificate order mismatch")
        require(proof["matroid_id"] == witness["matroid_id"] == m.labelled_id(), "Certificate matroid mismatch")
        require(proof["status"] == "UNSAT" and proof["proof_checked"], "Unchecked nonrepresentation proof")
        require(witness["all_immediate_minors_checked"], "Unchecked immediate minors")
        expected = {(operation, e) for operation in ("delete", "contract") for e in range(11)}
        require(len(witness["witnesses"]) == 22 and
                {(w["operation"], w["element"]) for w in witness["witnesses"]} == expected,
                "Missing immediate-minor witness")
        hyperplanes = [frozenset(h) for h in desc["hyperplanes_size_at_least_rank"]]
        reconstructed = frozenset(frozenset(s) for s in combinations(range(11), 4)
                                  if not any(set(s) <= h for h in hyperplanes))
        require(reconstructed == m.bases, "Hyperplanes do not reconstruct the matroid")
        triangles = [list(t) for t in combinations(range(11), 3) if m.rank(t) < 3]
        require(triangles == stats["triangles"] and len(triangles) == stats["triangle_count"],
                "Triangle count mismatch")
        require(len(m.bases) == desc["basis_count"] == stats["basis_count"], "Basis count mismatch")
        triangle_histogram[len(triangles)] += 1
        directory = result / "nonrepresentation" / f"matroid-{index:04d}"
        saved = read_json(directory / "matroid.json")
        require(saved["n"] == 11 and saved["rank"] == 4 and
                frozenset(map(frozenset, saved["bases"])) == m.bases, "Wrong matroid in proof directory")
        require("s VERIFIED" in (directory / "drat-check.txt").read_text(), "Missing saved proof-check success")

        if args.recheck_certificates:
            from gf5minors.representation import encode_representation
            circuit, expressions, metadata = encode_representation(m)
            cnf_hash = sha256(f"p cnf {circuit.nv} {len(circuit.clauses)}\n".encode())
            for clause in circuit.clauses:
                cnf_hash.update((" ".join(map(str, clause)) + (" " if clause else "") + "0\n").encode())
            require(cnf_hash.hexdigest() == digest(directory / "representation.cnf"),
                    "Saved determinant CNF differs from regeneration")
            require(json.loads(json.dumps(metadata)) == read_json(directory / "encoding.json"),
                    "Saved normalization differs from regeneration")
            checked = subprocess.run(
                [str(ROOT / "vendor/drat-trim/drat-trim"), str(directory / "representation.cnf"),
                 str(directory / "proof.drat"), "-t", "30"],
                text=True, capture_output=True, timeout=40, check=False,
            )
            require(any(line.strip() == "s VERIFIED" for line in checked.stdout.splitlines()),
                    f"DRAT replay failed for {class_id}")
            replayed += 1
            for w in witness["witnesses"]:
                minor = m.minor(w["element"], w["operation"])
                require(verify_representation(minor, w["matrix"]), f"Invalid minor matrix for {class_id}")
                checked_matrices += 1

        catalogue_lines.extend([
            "", rf"\paragraph{{$M_{{{index+1}}}$: {len(m.bases)} bases; {len(triangles)} triangles.}}",
            ", ".join(r"\(\{" + ",".join(map(str, sorted(h))) + r"\}\)" for h in hyperplanes) + ".",
        ])
    require(dict(sorted(triangle_histogram.items())) ==
            {int(k): v for k, v in verification["triangle_count_distribution"].items()},
            "Triangle distribution mismatch")

    parent_rows = []
    for size in range(4, 11):
        r3 = levels[3, size]
        r4 = levels[4, size]
        parent_rows.append(" & ".join(f"{x:,}" for x in (size, *r3, *r4)) + " " + r"\\")
    (generated / "parent-counts.tex").write_text(
        "\\begin{tabular}{rrrrr}\n\\toprule\n"
        "Size & Rank 3 field & Rank 3 abstract & Rank 4 field & Rank 4 abstract \\\\\n"
        "\\midrule\n" + "\n".join(parent_rows) + "\n\\bottomrule\n\\end{tabular}\n"
    )
    (generated / "search-ranges.tex").write_text(
        "\\begin{tabular}{rrrrr}\n\\toprule\n"
        "Start & Stop & Parents & Candidates & Seconds \\\\\n\\midrule\n" +
        "\n".join(shard_rows) + "\n\\bottomrule\n\\end{tabular}\n"
    )
    (generated / "triangle-counts.tex").write_text(
        r"\begin{array}{c|" + "r" * len(triangle_histogram) + "}\n"
        + r"\text{triangles} & " + " & ".join(map(str, sorted(triangle_histogram))) + r"\\ \hline" + "\n"
        + r"\text{classes} & " + " & ".join(str(triangle_histogram[t]) for t in sorted(triangle_histogram))
        + "\n" + r"\end{array}" + "\n"
    )
    (generated / "catalogue.tex").write_text("\n".join(catalogue_lines) + "\n")

    render_html(paper, args.pandoc)
    report = {
        "catalogue_sha256": catalogue_digest,
        "classes": len(records), "hyperplane_descriptions_reconstructed": len(records),
        "parents_covered": len(covered), "parent_statuses": dict(statuses),
        "enumeration_methods": dict(methods), "deletion_minimal_candidates": candidate_count,
        "critical_source_digests_match": True, "input_digests_match": True,
        "certificate_replay_requested": args.recheck_certificates,
        "determinant_cnfs_regenerated_and_matched": replayed,
        "drat_proofs_replayed": replayed, "minor_matrices_rechecked": checked_matrices,
        "html_sha256": digest(paper / "gf5-r4-n11.html"),
        "paper_source_sha256": digest(paper / "main.tex"),
        "seconds": monotonic() - started,
    }
    (paper / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


def render_html(paper, pandoc=None):
    pandoc = pandoc or shutil.which("pandoc")
    if not pandoc:
        bundled = Path("/home/t/tianle51/miniconda3/envs/my-sage/bin/pandoc")
        if bundled.exists():
            pandoc = bundled
    require(pandoc, "Pandoc is required to build the HTML copy")
    with tempfile.TemporaryDirectory(prefix="gf5-writeup-") as temporary:
        temporary = Path(temporary)
        expanded = temporary / "source.tex"
        expanded.write_text(html_source(expand_inputs(paper / "main.tex")))
        header = temporary / "style.html"
        header.write_text("<style>\n" + (paper / "style.css").read_text() + "\n</style>\n")
        rendered = subprocess.run(
            [str(pandoc), str(expanded), "--from=latex", "--to=html5", "--standalone",
             "--math-method=mathml", "--table-of-contents", "--toc-depth=2", "--include-in-header", str(header),
             "--output", str(paper / "gf5-r4-n11.html")],
            text=True, capture_output=True, timeout=60, check=True,
        )
        if rendered.stderr:
            print(rendered.stderr, file=sys.stderr)
        require("Could not convert" not in rendered.stderr, "Unconverted mathematics in HTML")
    html = (paper / "gf5-r4-n11.html").read_text()
    require("<math" in html and "Theorem 1.1" in html, "HTML mathematics/theorems missing")
    require(not re.search(r'class="[^"]*math[^\"]*"[^>]*>\\\(', html), "Unconverted HTML mathematics")


if __name__ == "__main__":
    main()
