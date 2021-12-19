## RUNNING:

## DONE IN THIS VERSION

- virtual environment - install
- record the REQUESTED and INSTALLER metadata in dist-info (following pep-376)
- SitePackages scanning: be able to read metadata and find packages for an environment without relying on being executed
  inside that environment
- checkout distlib
- define prioritizing repository
- move pubgrub to core (outside of the api)

## BACKLOG:
- installation can be made parallel
- the way sync work will make packages installed by the environment itself (wheel, pip and setuptools) to be removed and
  also any build related package, what should we do? should we keep build related packages until explicitly told to remove them?
- in pubgrub output replace package induced boundaries like * with actual boundaries like '> 2.7' or somehow let it know
  that we drop some dependencies with a specific reason (e.g., preinstalled user requested version, etc.)
- implement entrypoints awareness for installer
- read and expose package metadata
- the environment `installed_packages` can be pre-implemented as part of the api (since we now know how get it without
  running the process and also have the ability to get the sitepackages path from the api)
- wheel installer, when installation failed during the copying phase need to revert into a stable system state (probably
  by removing what we have already written)
- implement pep517, pep518, pep660 source installer
- support `pkm new notebook`
- implement pep621 and 631 for project layout in toml (note that it goes very good with the source override vision)
- consider implementing virtualenv myself (pep 405)
- local pythons repository - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- commandline: pkm install -g, -ga, -ge env
- virtual environment - remove + autoremove + sync
- check that when downloading packages for install, the hash is being validated
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- implement version prefetching for pubgrub
- create problem exporter for debug
- create project that reference venv(s?), pyproject & other configuration files, source roots
- design pkm toml namespace
- git and url dependencies installation support
- pypi package installation support
- create buildsys (with buildable project)
- publish project
- project operations: install dependency, remove dependency, create project, build project
- move to src layout?
- manage multiple envs per project
- cli
- make-like task system
- source definition and configuration (can it be translated to pep508 dependency?)
- properties and build profiles
- documentation site
- entry_points in pyproject
- python installation repository (no sudo! - download for os and install in data files - if possible)
- try and treat python dependency like any other dependency (and suggest installing it if we must)