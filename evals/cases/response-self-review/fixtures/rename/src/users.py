def getUser(user_id, repo):
    """Return the user record or None."""
    return repo.find(user_id)


def getUserEmail(user_id, repo):
    u = getUser(user_id, repo)
    return u["email"] if u else None
