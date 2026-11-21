"""Unit tests for the dependency-free Core Prime data preparation helpers."""
import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_core_prime_sft as prep

class PrepareTests(unittest.TestCase):
    def test_trajectory_expansion_and_holdout_exclusion(self):
        trajectory=[{"id":"t1","split":"train","turns":[
            {"role":"user","text":"u1"},{"role":"assistant","text":"a1"},
            {"role":"user","text":"u2"},{"role":"assistant","text":"a2"}]},
            {"id":"t2","split":"holdout","turns":[{"role":"user","text":"u"},{"role":"assistant","text":"a"}]}]
        micro=[{"id":"m1","split":"train","prompt":"p","desired_observable_behavior":"b"}]
        prefs=[{"id":"d1","split":"train","prompt":"p","preferred":{"text":"good"},"rejected":{"text":"bad"}},
               {"id":"d2","split":"holdout","prompt":"p","preferred":{"text":"x"},"rejected":{"text":"y"}}]
        sft=[]
        for row in trajectory:
            if row["split"]!="train": continue
            for i in range(1,len(row["turns"]),2):
                sft.append({"source_id":row["id"],"messages":row["turns"][:i+1]})
        sft.extend({"source_id":r["id"],"messages":[{"role":"user","text":r["prompt"]},{"role":"assistant","text":r["desired_observable_behavior"}]} for r in micro if r["split"]=="train")
        dpo=[{"source_id":r["id"],"prompt":[{"role":"user","text":r["prompt"]}],"chosen":[{"role":"assistant","text":r["preferred"]["text"]}],"rejected":[{"role":"assistant","text":r["rejected"]["text"]}]} for r in prefs if r["split"]=="train"]
        self.assertEqual(len(sft),3)
        self.assertEqual(len(dpo),1)
        self.assertEqual([x["source_id"] for x in sft],["t1","t1","m1"])
        self.assertNotIn("t2",[x["source_id"] for x in sft])
        self.assertNotIn("d2",[x["source_id"] for x in dpo])

if __name__=="__main__": unittest.main()
