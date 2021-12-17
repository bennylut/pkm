## RUNNING:

## DONE IN THIS VERSION
- test the wheel installer - basic tests only, no automation yet
- implement wheel installer

## BACKLOG:
- implement entrypoints awareness for installer
- virtual environment - install
- implement pep517, pep518, pep660 source installer
- checkout distlib
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
- manage multiple envs per project (lock should have a section per env)
- cli
- make-like task system
- source definition and configuration (can it be translated to pep508 dependency?)
- properties and build profiles
- documentation site
- entry_points
- python installation repository (no sudo! - download for os and install in data files - if possible)
- try and treat python dependency like any other dependency (and suggest installing it if we must)