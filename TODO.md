## CURRENT STORY:

- pkm cli
    - requires its own project -> support multi-module projects
        - ~~requires multi-module repository -> support repository instances and configuration~~

## RUNNING TASKS:


## DONE IN THIS VERSION
- connect lock to project

## BACKLOG TASKS:

- modules support
- check that when downloading packages for install, the hash is being validated
- check the "editables" module, decide if you want to support this behavior
- version local label - check if specific version can ask for a local-label
- pubgrub - introduce package opening cost (package that needs download in order to be open can cost like its size)
- validate the usefulness of the `Repository.accepts` method
- check if metadata 2.2 and then when dependencies are none and not dynamic we dont need to download the archive
- pkm.repository_builders should be pluggable
- handle project install with extras, usecase: test dependencies
- multi venv in project - usecase and flow
- bug: cached_property: mutation lock should be instance dependent and not global
- check, are cycles detected correctly in sdist builds? (especially under parallelization conditions)
- content information (author and maintainer) name and email should be validated,
    - name can be whatever can be put as a name, before an email, in RFC #822 and not contain commas
    - email should be a valid email address
    - see also https://jkorpela.fi/rfc/822addr.html and https://www.python.org/dev/peps/pep-0621/#authors-maintainers
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- build the monitor framework and start composing the cli
- consider creating a wrapper class for object_reference, it seems that it is used in multiple locations (projects,
  build system)
- bug: leftover __pycache__ on site packages dir after uninstall
- add some flag to disable parallelizm in installation (mainly useful for debug?)
- allow dependency exclusion
- allow forced versions
- hierarchical site packages:
    - the ability to depend upon other module environment in a hierarchical manner (may pose a problem with dependency
      resolution?)
    - project x can be a child of project px and inherit its environment using pth and import hooks
- when installation fails, environment is dirty
    - wheel installer, when installation failed during the copying phase need to revert into a stable system state (
      probably by removing what we have already written)
    - dont forget to handle overwriten files
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
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- create problem exporter for debug
- git and url dependencies installation support
- move to src layout?
- manage multiple envs per project
- cli
- make-like task system
- properties and build profiles (note that properties should only apply on pkm namespace)
- documentation site
- entry_points in pyproject
- python installation repository (no sudo! - download for os and install in data files - if possible)
- try and treat python dependency like any other dependency (and suggest installing it if we must)
- common tasks: test, build doc, etc.

## Ideas (may be irrelevant to pkm and may have their own library):

- automatic monkey patching of a module by import hooks - this hooks can be defined in the project level = extension
  methods, this can be done with pth files and import hooks!  