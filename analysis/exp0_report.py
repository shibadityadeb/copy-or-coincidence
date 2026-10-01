"""Experiment 0 sanity report: parse rate, accuracy, error classes, truncation, rerun determinism.

python analysis/exp0_report.py outputs/exp0_dev/exp0_dev-run1__qwen35-4b-A.jsonl [..run2..jsonl]
"""
import sys

import pandas as pd


def load(path: str) -> pd.DataFrame:
    return pd.read_json(path, lines=True)


def report(df: pd.DataFrame) -> None:
    n = len(df)
    print(f"trials: {n}   items: {df.task_id.nunique()}   samples/item: {n / df.task_id.nunique():.1f}")
    print(f"backend: {df.backend.iloc[0]} ({df.framework_version.iloc[0]}), quant {df.quantization.iloc[0]}")
    print(f"JSON parse ok: {df.parse_ok.mean():.0%}   any answer read: {df.answer_norm.notna().mean():.0%}")
    print(f"how parsed: {df.parse_how.value_counts().to_dict()}")
    print(f"truncated at max_tokens: {df.truncated.mean():.0%}   output tokens: median "
          f"{df.output_tokens.median():.0f}, max {df.output_tokens.max()}   "
          f"sec/answer: {df.latency_ms.median() / 1000:.1f}")
    print(f"\naccuracy overall: {df.correct.mean():.0%}")
    print(df.groupby("template_id").agg(acc=("correct", "mean"), lure=("lure_hit", "mean"),
                                        n=("correct", "size")).round(2).to_string())
    print("\nerror classes:", df.error_class.value_counts().to_dict())


def determinism(a: pd.DataFrame, b: pd.DataFrame) -> None:
    key = lambda d: d.assign(k=d.trial_id.str.split(":", n=2).str[2]).set_index("k")  # drop run prefix
    a, b = key(a), key(b)
    common = a.index.intersection(b.index)
    same = (a.loc[common, "raw_output"] == b.loc[common, "raw_output"])
    print(f"\nrerun: {same.sum()}/{len(common)} trials byte-identical")
    if not same.all():
        for k in list(common[~same.values])[:3]:
            print(f"  differs: {k}\n    run1: {a.loc[k, 'raw_output'][:120]!r}\n    run2: {b.loc[k, 'raw_output'][:120]!r}")


if __name__ == "__main__":
    first = load(sys.argv[1])
    report(first)
    if len(sys.argv) > 2:
        determinism(first, load(sys.argv[2]))
