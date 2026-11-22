"""Unit tests for ASH PRIME dataset preparation, including split isolation."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_ash_prime_sft as prep

class PrepareTests(unittest.TestCase):
    def test_prepare_uses_root_and_excludes_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=root / "data/personality"; data.mkdir(parents=True)
            sources={
                "ash-prime-multiturn-trajectories-v1.jsonl":[
                    {"id":"t1","split":"train","turns":[{"role":"user","text":"u1"},{"role":"assistant","text":"a1"},{"role":"user","text":"u2"},{"role":"assistant","text":"a2"}]},
                    {"id":"t2","split":"holdout","turns":[{"role":"user","text":"u"},{"role":"assistant","text":"a"}]}],
                "ash-prime-behavioral-micro-scenarios-v1.jsonl":[{"id":"m1","split":"train","prompt":"p","desired_observable_behavior":"b"},{"id":"m2","split":"holdout","prompt":"h","desired_observable_behavior":"hb"}],
                "ash-prime-contrastive-preferences-v1.jsonl":[{"id":"d1","split":"train","prompt":"p","preferred":{"text":"good"},"rejected":{"text":"bad"}},{"id":"d2","split":"holdout","prompt":"h","preferred":{"text":"x"},"rejected":{"text":"y"}}]}
            for name,rows in sources.items(): (data/name).write_text("".join(json.dumps(r)+"\n" for r in rows),encoding="utf-8")
            output=root/"out"; manifest=prep.prepare(root=root,output=output)
            sft=[json.loads(x) for x in (output/"sft-train.jsonl").read_text().splitlines()]
            dpo=[json.loads(x) for x in (output/"dpo-train.jsonl").read_text().splitlines()]
            self.assertEqual(len(sft),3); self.assertEqual(len(dpo),1)
            self.assertEqual([x["source_id"] for x in sft],["t1","t1","m1"])
            self.assertEqual(dpo[0]["prompt"][0]["content"],"p")
            self.assertEqual(manifest["holdout_excluded"],{"trajectories":1,"micro":1,"preferences":1})
            self.assertTrue((output/"prepared-manifest.json").exists())

if __name__=="__main__": unittest.main()
