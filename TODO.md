## RUNNING:
 
## DONE IN THIS VERSION
- pubgrub should support explaining about compatibility problems instead of just output that it couldn't find a
  version
- test package installation plan
- BUG: pubgrub candidate packages are not seems to be sorted from largest to smallest
- BUG: crush when downloading package that has no PKG-INFO in archive, should just continue to the next version
- BUG: dependency accepts pre-release without it being a pre-release (dill * -> dill ==0.1a1)
- test prereleases filters

## BACKLOG:

- check that when downloading packages for install, the hash is being validated
- generating a versioning problem from repositories, requirements, installation and lock
- populating the package installation plan using the versioning problem solution
- prepare an installation test from export that uses many known python packages and several python versions
- implement version prefetching for pubgrub
- benchmark pubgrub implementation
- create problem exporter for debug
- environment zoo (pkm install -g, -ga, -ge env)
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