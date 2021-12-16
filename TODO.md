## RUNNING:

## DONE IN THIS VERSION
- environment zoo~~~~
- local pythons repository
- generating a versioning problem from repositories, requirements, installation and lock
- populating the package installation plan using the versioning problem solution
- benchmark pubgrub implementation
- virtual environment - create
- package installation plan: root should be given as a dependency and not as a package

## BACKLOG:
- support `pkm new notebook`
- implement pep621 and 631 for project layout in toml (note that it goes very good with the source override vision)
- implement pep517, pep518, pep660 source installer
- consider implementing virtualenv myself 
- local pythons repository - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- commandline: pkm install -g, -ga, -ge env
- virtual environment - install
- virtual environment - remove + autoremove + sync
- check that when downloading packages for install, the hash is being validated
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- implement version prefetching for pubgrub
- create problem exporter for debug
- create project that reference venv(s?), pyproject & other configuration files, source roots
- design pkm toml namespace
- git and url dependencies support
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