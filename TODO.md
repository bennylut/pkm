## RUNNING TASKS:
- documentation site -> update cli, docs
- cli (and api): operations over project-groups => build, publish, install
- allennlp test on windows
- bug: pkm shell needs to create an environment if it does not find one in a project directory
- resolution improvement: add "minor adjustment" heuristic

## DONE IN THIS VERSION
- bug: pep517 installation failure lead to whole installation failure - need to instead lead to "bad package"

## BACKLOG TASKS:
- environment naming (for project for example..) 
- cli: publish keyring
- optimization: if the resource we are fetching is already compressed (like wheels and sdist) there is no need to request
  compression from the webserver and then reopen it locally
- cmd: pkm remove -o (orphans)
- cmd: pkm remove -f (force single)
- shell aliases: p (= python x.py ... or python -m x ...), project-dir, env-dir
- shell aliases: l, ll
- new pyproject-group template
- documentation: templates docs
- support publishing self-contained-application packages
- support * in packages but not default (just scan before usage on supported repositories)
- pkm install wheel from path
- shim dependencies (pkm can choose to install them with the shim name instead of the lib name)
- site: sidebar responsive to phones
- site: add page transition: https://codepen.io/johnheiner/pen/JdRybK
- consider interactive ui mode
- toml parser/writer need unit tests
- toml - lists user style - support column and grid and auto detect it
- check that when downloading packages for install, the hash is being validated
- check the "editables" module, decide if you want to support this behavior
- version local label - check if specific version can ask for a local-label
- pubgrub - introduce package opening cost (package that needs download in order to be open can cost like its size)
- check if metadata 2.2 and then when dependencies are none and not dynamic we dont need to download the archive
- pkm.repository_builders should be pluggable
- handle project install with extras, usecase: test dependencies
- multi venv in project - usecase and flow (maybe explicitly create an environment zoo)
- bug: cached_property: mutation lock should be instance dependent and not global
- check, are cycles detected correctly in sdist builds? (especially under parallelization conditions)
- content information (author and maintainer) name and email should be validated,
    - name can be whatever can be put as a name, before an email, in RFC #822 and not contain commas
    - email should be a valid email address
    - see also https://jkorpela.fi/rfc/822addr.html and https://www.python.org/dev/peps/pep-0621/#authors-maintainers
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- bug: leftover __pycache__ on site packages dir after uninstall
- add some flag to disable parallelizm in installation (mainly useful for debug?)
- tool.pkm.dependency-overwrites: allow forced versions and dependency exclusion
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
- improve api documentation
- test pkm on windows, think how to test it on osx
- support the `pkm build [installer] --fat` usecase (creates a standalone .py installer with embedded data), without
  fat, dependencies will get downloaded
- find a dependency that requires the "include" directory and check if it is handled correctly (maybe download spacy by
  source)
- in pubgrub output replace package induced boundaries like * with actual boundaries like '> 2.7' or somehow let it know
  that we drop some dependencies with a specific reason (e.g., preinstalled user requested version, etc.)
- support the `pkm new notebook` usecase
- local pythons repository - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- commandline: pkm install -g, -ga, -ge env
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- create problem exporter for debug
- git and url dependencies installation support
- manage multiple envs per project
- make-like task system
- properties and build profiles (note that properties should be resolved before sdist packaging)
- python installation repository (no sudo! - download for os and install in data files - if possible)
- try and treat python dependency like any other dependency (and suggest installing it if we must)
- common tasks: test, build doc, etc.
- create pyproject from environment - usecase: user already has an environment that he worked on and want to have a
  project based on it

## Ideas (may be irrelevant to pkm and may have their own library):

- automatic monkey patching of a module by import hooks - this hooks can be defined in the project level = extension
  methods, this can be done with pth files and import hooks!
- mechanism for lazy importing (like in java) that use the new module level "get attr" or locals:
  - include('module', 'name1 as x', 'name2', ...), maybe also specify that you want to import the type only
  - can be also made by a preprocessor (like: '#preprocessor: lazy imports' on the beginning of the file)
