global ask


def setup(group_name: str = None) -> dict:
    group_name = group_name or ask("Group Name")
    return locals()
