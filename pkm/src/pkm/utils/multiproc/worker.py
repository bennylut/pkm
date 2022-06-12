if __name__ == '__main__':
    from pkm.utils.multiproc import _Worker
    # from pkm.api.pkm import pkm
    # pkm.global_flags.package_installation_parallelizm = "thread"

    _Worker().run()
