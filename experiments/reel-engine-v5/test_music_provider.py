import io
import json
from pathlib import Path
import tempfile
from unittest import TestCase,main,mock
import music_provider as music


def example(lic="cc0"):
    url={"cc0":"https://creativecommons.org/publicdomain/zero/1.0/",
         "pdm":"https://creativecommons.org/publicdomain/mark/1.0/",
         "by":"https://creativecommons.org/licenses/by/4.0/",
         "by-nc":"https://creativecommons.org/licenses/by-nc/4.0/"}[lic]
    return {"id":"12345678-1234-1234-1234-123456789abc",
            "title":"An Open Recording","creator":"Example Artist",
            "license":lic,"license_url":url,"license_version":"4.0",
            "foreign_landing_url":"https://freesound.org/people/example/sounds/1234/",
            "url":"https://cdn.freesound.org/audio/example.wav",
            "attribution":"An Open Recording by Example Artist"}

class FakeResponse:
    def __init__(self,data):
        self.data=io.BytesIO(json.dumps(data).encode())
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def read(self,n):
        return self.data.read(n)


class MusicProviderTests(TestCase):
    def test_search_is_openverse_only_and_metadata_unverified(self):
        urls=[]
        def fake(req,timeout=20):
            urls.append(req.full_url)
            return FakeResponse({"results":[example("cc0"),example("by-nc"),example("by")]})
        data=music.search("serene nature piano",limit=6,opener=fake)
        self.assertEqual(len(data["candidates"]),2)
        self.assertFalse(data["candidates"][0]["approved_for_final_render"])
        self.assertFalse(data["candidates"][0]["media_downloaded"])
        self.assertFalse(data["composed_audio"])
        self.assertIn("api.openverse.org/v1/audio/",urls[0])
        self.assertIn("license=cc0%2Cby%2Cpdm",urls[0])

    def test_noncommercial_and_nd_licenses_excluded(self):
        self.assertIsNone(music.candidate(example("by-nc")))
        self.assertIsNotNone(music.candidate(example("by")))

    def test_insecure_url_rejected(self):
        x=example()
        x["url"]="http://localhost/sound.mp3"
        self.assertIsNone(music.candidate(x))
        x=example()
        x["foreign_landing_url"]="https://user:pass@malicious.example/file"
        self.assertIsNone(music.candidate(x))

    def test_licence_without_source_evidence_cannot_ingest(self):
        t=music.candidate(example())
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"proof.json"
            p.write_text(json.dumps({
                "track_id":t["id"],"license_url":t["license_url"],
                "original_source_page":t["original_source_page"],
                "reviewer_confirmed_rights":False,
                "source_license_proof_url":t["original_source_page"],
                "reviewed_on":"2026-11-02","reviewed_by":"Owner"}))
            with self.assertRaises(music.LicenseError):
                music.read_evidence(p,t)

    def test_licence_evidence_and_cc_by_attribution_required(self):
        t=music.candidate(example("by"))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"proof.json"
            p.write_text(json.dumps({
                "track_id":t["id"],"license_url":t["license_url"],
                "original_source_page":t["original_source_page"],
                "reviewer_confirmed_rights":True,"attribution_approved":False,
                "source_license_proof_url":t["original_source_page"],
                "reviewed_on":"2026-11-02","reviewed_by":"Owner"}))
            with self.assertRaisesRegex(music.LicenseError,"attribution"):
                music.read_evidence(p,t)
            proof=json.loads(p.read_text());proof["attribution_approved"]=True
            p.write_text(json.dumps(proof))
            self.assertTrue(music.read_evidence(p,t)["reviewer_confirmed_rights"])

    def test_absent_audio_fails_closed(self):
        with self.assertRaises(music.LicenseError):
            music.verify_audio("/tmp/mad-v5-no-track-here.mp3")

    def test_mix_requires_provenance_before_using_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"music_provenance.json").write_text(json.dumps({"license_verified_by_reviewer":False}))
            with self.assertRaises(music.LicenseError):
                music.mix("/tmp/test-video.mp4",p,p/"out.mp4")

    def test_input_bounds_and_no_source_scraping(self):
        with self.assertRaises(ValueError):
            music.search("x",limit=100)
        with self.assertRaises(ValueError):
            music.search("")

    def test_license_provenance_preserved_for_attribution(self):
        t=music.candidate(example("by"))
        self.assertEqual(t["creator"],"Example Artist")
        self.assertEqual(t["license"],"by")
        self.assertIn("creativecommons.org/licenses/by",t["license_url"])

if __name__=="__main__":
    main()
