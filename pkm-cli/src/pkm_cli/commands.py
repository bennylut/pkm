from argparse import ArgumentParser

pkm_parser = ArgumentParser(description="pkm - python package management for busy developers")

pkm_subparsers = pkm_parser.add_subparsers()

pkm_new_parser = pkm_subparsers.add_parser('new')
