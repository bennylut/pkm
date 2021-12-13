## RUNNING:

- change to single type dependency
- remove named-version specifier and replace with named-version version type
- create package installation plan

## DONE IN THIS VERSION

## BACKLOG:
- generating a versioning problem from repositories, requirements, installation and lock
- populating the package installation plan using the versioning problem solution
- prepare an installation test from export that uses many known python packages and several python versions 
- implement version prefetching for pubgrub
- benchmark pubgrub implementation
- create problem exporter for debug
- environment zoo (pkm install -g, -ga, -ge env)~~~~
- create project that reference venv(s?), pyproject & other configuration files, source roots
- design pkm toml namespace
- virtual environment - create
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