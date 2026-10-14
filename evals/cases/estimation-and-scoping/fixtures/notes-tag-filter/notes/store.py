"""In-memory note store. Notes are dicts: id, title, body, tags (list of str), created (ISO date)."""
from datetime import date


class NoteStore:
    def __init__(self):
        self._notes = []
        self._next = 1

    def add(self, title, body, tags=None):
        note = {"id": self._next, "title": title, "body": body,
                "tags": list(tags or []), "created": date.today().isoformat()}
        self._notes.append(note)
        self._next += 1
        return note

    def all(self):
        return list(self._notes)

    def search(self, text):
        """Case-insensitive substring match on title and body."""
        q = text.lower()
        return [n for n in self._notes if q in n["title"].lower() or q in n["body"].lower()]
