import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vigilar_feeds import attempts,broken,source_key

def run(rid,name,when,conclusion="success"):
    return {"id":rid,"name":name,"created_at":when,"status":"completed","conclusion":conclusion}
def job(name,ok=True,when="",conclusion=None):
    return {"name":name,"started_at":when,"conclusion":conclusion or ("success" if ok else "failure"),
            "steps":[{"name":"Auditar","conclusion":"success" if ok else "failure"}]}

class VigilarTests(unittest.TestCase):
    def test_source_key(self):
        self.assertEqual(source_key("España","auditar (CC)"),"CC")
        self.assertEqual(source_key("BOP Cadiz","auditar"),"BOP Cadiz / auditar")

    def test_backup_source_failing_on_github_but_ok_at_home_is_fine(self):
        runs=[run(1,"España","2026-11-28T06:23:00Z"),run(2,"Casa","2026-11-28T06:46:00Z"),
              run(3,"España","2026-11-27T16:33:00Z"),run(4,"Casa","2026-11-27T16:47:00Z")]
        jobs={1:[job("auditar (CC)",False,"2026-11-28T06:23:00Z")],2:[job("auditar (CC)",True,"2026-11-28T06:46:00Z")],
              3:[job("auditar (CC)",False,"2026-11-27T16:33:00Z")],4:[job("auditar (CC)",True,"2026-11-27T16:47:00Z")]}
        self.assertEqual(broken(attempts(runs,jobs.get)),[])

    def test_two_failures_in_a_row_are_reported_even_if_run_is_green(self):
        # revisar-cadiz.yml tiene continue-on-error: la ejecución sale en verde.
        runs=[run(1,"BOP Cadiz","2026-11-28T07:38:00Z"),run(2,"BOP Cadiz","2026-11-27T17:26:00Z")]
        jobs={1:[job("auditar",False,"2026-11-28T07:38:00Z")],2:[job("auditar",False,"2026-11-27T17:26:00Z")]}
        r=broken(attempts(runs,jobs.get))
        self.assertEqual([x["fuente"] for x in r],["BOP Cadiz / auditar"])

    def test_single_failure_or_cancelled_runs_are_not_reported(self):
        runs=[run(1,"BOP Girona","2026-11-28T07:00:00Z","cancelled"),run(2,"BOP Girona","2026-11-27T17:00:00Z"),
              run(3,"BOP Girona","2026-11-27T13:00:00Z"),run(9,"OpoAlert - Publicar portada nacional y feeds","2026-11-28T07:00:00Z","failure")]
        jobs={2:[job("auditar",False,"2026-11-27T17:00:00Z")],3:[job("auditar",True,"2026-11-27T13:00:00Z")],
              9:[job("publicar",False)]}
        self.assertEqual(broken(attempts(runs,jobs.get)),[])

if __name__=="__main__":
    unittest.main()
