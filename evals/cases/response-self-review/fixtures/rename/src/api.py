from src.users import getUser


def handle_profile(request, repo):
    user = getUser(request["user_id"], repo)
    if user is None:
        return {"status": 404}
    return {"status": 200, "body": {"name": user["name"]}}
