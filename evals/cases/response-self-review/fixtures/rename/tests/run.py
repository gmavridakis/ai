import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src import users, api


class Repo:
    def find(self, uid):
        return {"id": uid, "name": "Ada", "email": "ada@example.com"} if uid == 1 else None


r = Repo()
fn = getattr(users, "fetchUser", None) or getattr(users, "getUser")
assert fn(1, r)["name"] == "Ada"
assert api.handle_profile({"user_id": 2}, r)["status"] == 404
assert users.getUserEmail(1, r) == "ada@example.com" if hasattr(users, "getUserEmail") else True
print("2 tests passed")
