## CURRENT MILESTONE:

- let pkm build and install itself

## RUNNING TASKS:
- create project that reference venv(s?), pyproject & other configuration files, source roots
- support non src layouts, try to build pkm using pkm 

## TASKS DONE IN THIS VERSION
- design pkm toml project namespace
- support backend-path in build-system (as described in pep 518, 517)
- test backend-path by attempting to build poetry-core

## BACKLOG TASKS:
- check, are cycles detected correctly in sdist builds? (especially under parallelization conditions)
- content information (author and maintainer) name and email should be validated, 
  - name can be whatever can be put as a name, before an email, in RFC #822 and not contain commas
  - email should be a valid email address
  - see also https://jkorpela.fi/rfc/822addr.html and https://www.python.org/dev/peps/pep-0621/#authors-maintainers
- buildsys support editable installs
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- build the monitor framework and start composing the cli
- consider creating a wrapper class for object_reference, it seems that it is used in multiple locations (projects,
  build system)
- implement pep660 editable source installer
    - check the editables module, decide if you want to support this behavior
- move standard model zoo to pkm
- bug: leftover __pycache__ on site packages dir after uninstall 
- add some flag to disable parallelizm in installation (mainly useful for debug?)
- allow dependency exclusion
- allow forced versions
- allow additional repositories, check pytorch recipe
- hierarchical site packages:
    - the ability to depend upon other module environment in a hierarchical manner (may pose a problem with dependency
      resolution?)
    - project x can be a child of project px and inherit its environment using pth and import hooks
- when installation fails, environment is dirty
    - wheel installer, when installation failed during the copying phase need to revert into a stable system state (
      probably by removing what we have already written)
    - dont forget to handle overwriten files
- hierarchical PyProjectConfiguration
- `pkm shell` support custom environment variables loading like in pipenv
- lightweight environment support `pkm shell, pkm shell -c, pkm shell -e executeable -c, ...` use cases
- documentation for simple parser
- test pkm on windows, think how to test it on osx
- support the `pkm build [installer] --fat` usecase (creates a standalone .py installer with embedded data), without
  fat, dependencies will get downloaded
- find a dependency that requires the "include" directory and check if it is handled correctly (maybe download spacy by
  source)
- in pubgrub output replace package induced boundaries like * with actual boundaries like '> 2.7' or somehow let it know
  that we drop some dependencies with a specific reason (e.g., preinstalled user requested version, etc.)
- implement entrypoints awareness for installer
- support the `pkm new notebook` usecase 
- local pythons repository - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- commandline: pkm install -g, -ga, -ge env
- check that when downloading packages for install, the hash is being validated
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- create problem exporter for debug
- git and url dependencies installation support
- publish project
- project operations: install dependency, remove dependency, create project, build project
- move to src layout?
- manage multiple envs per project
- cli
- make-like task system
- source definition and configuration (can it be translated to pep508 dependency?)
- properties and build profiles (note that properties should only apply on pkm namespace)
- documentation site
- entry_points in pyproject
- python installation repository (no sudo! - download for os and install in data files - if possible)
- try and treat python dependency like any other dependency (and suggest installing it if we must)

## Ideas (may be irrelevant to pkm and may have their own library):

- automatic monkey patching of a module by import hooks - this hooks can be defined in the project level = extension
  methods, this can be done with pth files and import hooks!  