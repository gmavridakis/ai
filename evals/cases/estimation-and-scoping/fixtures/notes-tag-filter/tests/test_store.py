import unittest
from notes.store import NoteStore


class SearchTest(unittest.TestCase):
    def test_search_matches_title_and_body(self):
        s = NoteStore()
        s.add("Standup", "Discuss the release", ["work"])
        s.add("Groceries", "Milk, eggs", ["home"])
        self.assertEqual([n["id"] for n in s.search("release")], [1])
        self.assertEqual([n["id"] for n in s.search("GROC")], [2])


if __name__ == "__main__":
    unittest.main()
