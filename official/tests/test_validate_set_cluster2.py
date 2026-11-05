"""Synthetic fail-closed tests; no study results or corpus data."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import validate_set_cluster2 as check


def rows(memory=None):
    return [{"trial": f"{task}-{i}", "task": task, "finished": True, "valid": True,
             "reward": 1.0, "passed": True, "model_unavailable": False,
             "judge_status": "completed" if task.startswith("apex-") else None,
             "memory_sha256": memory} for task in sorted(check.TASKS) for i in range(3)]


def test_control_and_memory_complete():
    assert check.validate(rows(), "control") == []
    assert check.validate(rows("a" * 64), "memory") == []


def test_invalid_counts_and_duplicates():
    sample = rows()
    assert check.validate(sample[:-1], "control")
    sample[-1]["trial"] = sample[0]["trial"]
    assert check.validate(sample, "control")


def test_failed_or_missing_judge_and_serving_are_rejected():
    sample = rows()
    apex = next(r for r in sample if r["task"].startswith("apex-"))
    apex["judge_status"] = None
    assert check.validate(sample, "control")
    apex["judge_status"] = "completed"
    apex["model_unavailable"] = True
    assert check.validate(sample, "control")
    del apex["model_unavailable"]
    assert check.validate(sample, "control")


def test_invalid_reward_and_mismatched_pass_rejected():
    for reward, passed in [(None, False), (float("nan"), False), (0, True)]:
        sample = rows(); sample[0].update(reward=reward, passed=passed)
        assert check.validate(sample, "control")


def test_memory_and_exposure_digest_checks():
    sample = rows("a" * 64)
    assert check.validate(sample, "exposure", expected_memory="a" * 64) == []
    assert check.validate(sample, "exposure")
    assert check.validate(sample, "exposure", expected_memory="b" * 64)
    changed = copy.deepcopy(sample); changed[0]["memory_sha256"] = "b" * 64
    assert check.validate(changed, "memory")
    assert check.validate(sample, "control")


def test_uncounted_single_task():
    sample = [r for r in rows("a" * 64) if r["task"] == "build-word2vec-pipeline"][:1]
    assert check.validate(sample, "exposure", task="build-word2vec-pipeline", expected_memory="a" * 64) == []
    assert check.validate(sample, "exposure", task="not-a-task", expected_memory="a" * 64)


def test_uncounted_gate_subset_and_attempt_count():
    names = ["customer-delivery-contextual-preferences", "apex-eurogrid-curtailment"]
    sample = []
    for name in names:
        sample.append({"trial": f"{name}-only", "task": name, "finished": True, "valid": True,
                       "reward": 0.8333 if name.startswith("apex-") else 0.0,
                       "passed": False, "model_unavailable": False,
                       "judge_status": "completed" if name.startswith("apex-") else None,
                       "memory_sha256": "a" * 64})
    assert check.validate(sample, "memory", tasks=names, expected_memory="a" * 64) == []
    assert check.validate(sample, "memory", tasks=names, attempts=3, expected_memory="a" * 64)
    assert check.validate(sample, "memory", tasks=names, expected_memory="b" * 64)
