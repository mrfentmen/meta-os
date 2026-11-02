"""Tests for the NYC DOT live camera source. All offline: the fetch seam
is faked and the fixture carries the API shape verified live on
2026-11-02 (fields id/name/latitude/longitude/area/isOnline/imageUrl,
isOnline as the string "true"/"false")."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server", "queue"))

import livecams

FIXTURE = json.dumps([
    {"id": "cam-bay", "name": "Bay Pkwy @ 78 St (Kings Hwy)",
     "latitude": 40.60632, "longitude": -73.989087, "area": "Brooklyn",
     "isOnline": "true",
     "imageUrl": "https://webcams.nyctmc.org/api/cameras/cam-bay/image"},
    {"id": "cam-off", "name": "Offline @ Nowhere", "latitude": 0,
     "longitude": 0, "area": "Brooklyn", "isOnline": "false",
     "imageUrl": "https://webcams.nyctmc.org/api/cameras/cam-off/image"},
    {"id": "cam-bway", "name": "Broadway @ 45 St", "latitude": 40.757953,
     "longitude": -73.98549, "area": "Manhattan", "isOnline": "true",
     "imageUrl": "https://webcams.nyctmc.org/api/cameras/cam-bway/image"},
    {"id": "cam-nourl", "name": "No URL @ Missing", "latitude": 0,
     "longitude": 0, "area": "Queens", "isOnline": "true"},
]).encode()

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def fake_fetch(routes):
    def fetch(url):
        if url not in routes:
            raise OSError(f"no route for {url}")
        value = routes[url]
        if isinstance(value, Exception):
            raise value
        return value
    return fetch


class ParseTests(unittest.TestCase):
    def test_parse_filters_offline_and_urlless(self):
        cams = livecams.parse_cameras(FIXTURE)
        self.assertEqual([c["id"] for c in cams], ["cam-bay", "cam-bway"])
        self.assertEqual(cams[0]["source"], "NYC DOT public traffic camera")

    def test_parse_rejects_non_json(self):
        with self.assertRaises(livecams.LiveCamError):
            livecams.parse_cameras(b"<html>not json</html>")

    def test_parse_rejects_non_list(self):
        with self.assertRaises(livecams.LiveCamError):
            livecams.parse_cameras(b'{"cameras": []}')


class PickTests(unittest.TestCase):
    def setUp(self):
        self.cams = livecams.parse_cameras(FIXTURE)

    def test_pick_area(self):
        got = livecams.pick(self.cams, area="Brooklyn", count=5)
        self.assertEqual([c["id"] for c in got], ["cam-bay"])

    def test_pick_name_substring_case_insensitive(self):
        got = livecams.pick(self.cams, name_contains="broadway")
        self.assertEqual(got[0]["id"], "cam-bway")

    def test_pick_is_deterministic_sorted(self):
        got = livecams.pick(self.cams, count=2)
        self.assertEqual([c["name"] for c in got],
                         sorted(c["name"] for c in got))


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.cam = livecams.parse_cameras(FIXTURE)[0]

    def test_snapshot_returns_image_bytes(self):
        fetch = fake_fetch({self.cam["imageUrl"]: JPEG})
        self.assertEqual(livecams.fetch_snapshot(self.cam, fetch), JPEG)

    def test_snapshot_refuses_error_page(self):
        fetch = fake_fetch({self.cam["imageUrl"]: b"<html>404</html>"})
        with self.assertRaises(livecams.LiveCamError):
            livecams.fetch_snapshot(self.cam, fetch)


class SourceTests(unittest.TestCase):
    def routes(self, broken_first=False):
        cams = {c["id"]: c for c in livecams.parse_cameras(FIXTURE)}
        routes = {livecams.API_URL: FIXTURE}
        for cam in cams.values():
            routes[cam["imageUrl"]] = JPEG
        if broken_first:
            first = livecams.pick(list(cams.values()), count=1)[0]
            routes[first["imageUrl"]] = OSError("camera down")
        return routes

    def test_frame_round_robin(self):
        src = livecams.LiveCamSource(fetch=fake_fetch(self.routes()))
        cam1, img1, stamp1 = src.frame()
        cam2, img2, stamp2 = src.frame()
        self.assertNotEqual(cam1["id"], cam2["id"])
        self.assertTrue(livecams.is_image_bytes(img1))
        self.assertIn("T", stamp1)

    def test_frame_skips_dead_camera(self):
        src = livecams.LiveCamSource(
            fetch=fake_fetch(self.routes(broken_first=True)))
        cam, img, _ = src.frame()
        self.assertTrue(livecams.is_image_bytes(img))

    def test_frame_raises_when_all_dead(self):
        routes = {livecams.API_URL: FIXTURE}
        cams = livecams.parse_cameras(FIXTURE)
        for cam in cams:
            routes[cam["imageUrl"]] = OSError("down")
        src = livecams.LiveCamSource(fetch=fake_fetch(routes))
        with self.assertRaises(livecams.LiveCamError):
            src.frame()

    def test_source_empty_filter_raises(self):
        routes = {livecams.API_URL: FIXTURE}
        with self.assertRaises(livecams.LiveCamError):
            livecams.LiveCamSource(fetch=fake_fetch(routes),
                                   area="Atlantis")


if __name__ == "__main__":
    unittest.main()
