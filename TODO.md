## RUNNING TASKS:

- documentation: document the application classes and usage
- documentation: describe repositories
- documentation: extensions + torch repository
- check pkm installation in app mode on system environment + torch-repo in app mode
- entrypoint to allow for default repository instances (pkm-torch /-repository)

## DONE IN THIS VERSION
- cli: pkm clean shared | pkm clean cache | pkm clean dist
- make dependency resolution less verbose
- bug: cached_property: mutation lock should be instance dependent and not global
- `pkm shell -e` : like `npm run` and `poetry run`
- bug: shared libs with different abi ware not differentiables 

## BACKLOG TASKS:
- pkm shell: automatic zoo export (zoo should have a bin directory), think about that, do we need it as non pkm shell
  extension?
- improve configuration infra - somehow reduce the boilerplate code that is needed in order to add new configuration
- test pkm on os where platlib and purelib are different (centos?)
- pkm stat : print cache size, attached repository, etc.
- refactoring: repositories should by itself be a project group
- support application-only packages (the package itself is the installer)
- repositories: conda (currently requires that conda itself is installed as it cannot be built or fetched from pypi)
    - it seems that it will be simple enough to implement
      myself: https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html
- repositories: pyvenv
- consider exposing application script entrypoint using the old application loader
- applications can also provide repositories configuration, those should be specified in its table
- bug: when running in "build-sys" mode should not "implicitly install" cache files
    - also when running in this mode some basic monitoring should be made
- cli: if building packages during dependency resolution, output is very convoluted
- pkm build: cycle detection is not good enough (may fail on multithreading) should move to build session
- misc: build readme, set github's site
- pkm show: add repositories information
- cmd: pkm install - support installation of wheel and sdist from path, also from project dir (w/editables)
- enhancement: build using pkm own buildsys is too quiet, cannot use the output for effective debugging
- bug: pkm new - cannot cancel creation - it just continues to the next question
- documentation: explain about PKM_HOME, maybe show its value in one of the reports
- cmd: pkm remove - display the packages being removed
- cmd: pkm show - on envs, show all the installed script entrypoints (and who installed them)
- pkm: update package installation / update all packages
- pkm: support installing as applications packages which were not built as self-contained ones
- documentation site: projects and project groups, self-contained applications
- environment naming (for project for example..)
- cli: publish keyring
- optimization: if the resource we are fetching is already compressed (like wheels and sdist) there is no need to
  request compression from the webserver and then reopen it locally
- cmd: pkm remove -o (orphans)
- cmd: pkm remove -f (force single)
- shell aliases: p (= python x.py ... or python -m x ...), project-dir, env-dir
- shell aliases: l, ll
- documentation: templates docs
- site: sidebar responsive to phones
- toml parser/writer need unit tests
- toml - lists user style - check the pre-last delimiter and repeat it
- check that when downloading packages for install, the hash is being validated correctly
- pubgrub - introduce package opening cost (package that needs download in order to be open can cost like its size)
- handle project install with extras, usecase: test dependencies
- content information (author and maintainer) name and email should be validated,
    - name can be whatever can be put as a name, before an email, in RFC #822 and not contain commas
    - email should be a valid email address
    - see also https://jkorpela.fi/rfc/822addr.html and https://www.python.org/dev/peps/pep-0621/#authors-maintainers
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- bug: leftover __pycache__ on site packages dir after uninstall
- add some flag to disable parallelizm in installation (mainly useful for debug?)
- `pkm shell` support custom environment variables loading like in pipenv
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
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- create problem exporter for debug
- make-like task system
- common tasks: test, build doc, etc.
- create pyproject from environment - usecase: user already has an environment that he worked on and want to have a
  project based on it, I think I also saw this possibility in conda
- shell venv - alias to print environment and project in context

## Ideas (may be irrelevant to pkm and may have their own library):

- automatic monkey patching of a module by import hooks - this hooks can be defined in the project level = extension
  methods, this can be done with pth files and import hooks!
- mechanism for lazy importing (like in java) that use the new module level "get attr" or locals:
    - can be made by a preprocessor (like: '#preprocessor: lazy imports' on the beginning of the file)
    - it will then have to replace all the type annotations into string based or something similar..
- shim dependencies (pkm can choose to install them with the shim name instead of the lib name)
- python installation repository (no sudo! - download for os and install in data files - if possible)