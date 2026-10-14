import sys
from notes.store import NoteStore


def run(argv):
    store = NoteStore()
    store.add("Standup", "Discuss the release", ["work", "meeting"])
    store.add("Groceries", "Milk, eggs", ["home"])
    store.add("Sprint review", "Demo the export feature", ["work"])
    if len(argv) >= 2 and argv[0] == "search":
        for n in store.search(argv[1]):
            print(f'{n["id"]}: {n["title"]} [{", ".join(n["tags"])}]')
        return 0
    print("usage: python -m notes search <text>")
    return 2


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
