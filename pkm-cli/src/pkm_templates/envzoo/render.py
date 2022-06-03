global confirm
global ask


def setup(zoo_name: str = None) -> dict:
    zoo_name = zoo_name or ask("Zoo Name")
    package_sharing_enabled = confirm("Enable Package Sharing")
    package_sharing_enabled_v = str(package_sharing_enabled).lower()

    return locals()
