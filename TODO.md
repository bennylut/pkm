## RUNNING:

## DONE IN THIS VERSION
- implement lightweight virtualenv (pep 405) will be used for installation and maybe later for main environments
- remove uninitialized-environment (instead the same functionality can be achived with simple environment)
- pypi package installation support
- sync will not make packages installed by the environment itself (wheel, pip and setuptools) to be removed 

## BACKLOG:
- lightweight environment support `pkm shell, pkm shell -c, pkm shell -e executeable -c, ...` use cases
- decide on a single "singleton" pattern implementation and stick with it!
- documentation for simple parser
- test pkm on windows, think how to test it on osx
- if we get rid of urlib3 we can rename pkm-main into pkm-cli and have a lightweight installation in pkm without any
  dependencies! it seems that the http.client is lowlevel enough to be used without limitations 
- support the `pkm build [installer] --fat` usecase (creates a standalone .py installer with embedded data), without
  fat, dependencies will get downloaded
- implement pep517, pep518, pep660 source installer
- find a dependency that requires the "include" directory and check if it is handled correctly (maybe download spacy by
  source)
- installation can be made parallel
- in pubgrub output replace package induced boundaries like * with actual boundaries like '> 2.7' or somehow let it know
  that we drop some dependencies with a specific reason (e.g., preinstalled user requested version, etc.)
- implement entrypoints awareness for installer
- wheel installer, when installation failed during the copying phase need to revert into a stable system state (probably
  by removing what we have already written)
- support `pkm new notebook`
- implement pep621 and 631 for project layout in toml (note that it goes very good with the source override vision)
- local pythons repository - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- commandline: pkm install -g, -ga, -ge env
- check that when downloading packages for install, the hash is being validated
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- implement version prefetching for pubgrub, consider prefetching previous version also
- create problem exporter for debug
- create project that reference venv(s?), pyproject & other configuration files, source roots
- design pkm toml namespace
- git and url dependencies installation support
- create buildsys (with buildable project), how to create platform/abi dependent projects?  
- publish project
- project operations: install dependency, remove dependency, create project, build project
- move to src layout?
- manage multiple envs per project
- cli
- make-like task system
- source definition and configuration (can it be translated to pep508 dependency?)
- dependency forced versions 
- properties and build profiles
- documentation site
- entry_points in pyproject
- python installation repository (no sudo! - download for os and install in data files - if possible)
- try and treat python dependency like any other dependency (and suggest installing it if we must)

## Ideas (may be irrelevant to pkm and should have their own library):
- automatic monkey patching of a module by import hooks - this hooks can be defined in the project level = extension methods  