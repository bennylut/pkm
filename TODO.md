## RUNNING TASKS:


## DONE IN THIS VERSION
- documentation: describe containerized applications

## BACKLOG TASKS:
- feature: environment export
- bug: app plugin install does not register newly created files in the container records
- bug: generated pyc files are not getting signed 
- shell: `pkm -v` print pkm version
- test: check shared + container
- pkm: update package installation / update all packages (include support for locks and shared)
- bug `pkm clean dist` should remove all but current version of dist
- enhancement: if pkm is installed on some environment we cannot choose a different global environment
- replace dependency resolution progressbar with spinner?
- enhancement: shared package installation - use to the new package installation target schema
- test: install project with optionals and then just install should keep optionals
- bug: copy transaction should be used at the level of the full installation as sometimes it has to upgrade packages
  which means that they will get deleted - bypassing the copy transaction realm
- documentation: describe repositories,
    - describe repositories extensions + torch repository
    - describe inheritance mode
- repositories: conda
    - it seems that it will be simple enough to implement
      myself: https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html
- package artifact hash validation: pypi, simple, torch
- pkm repositories: rename torch to download-torch-pkm-repo (to follow new standard)
- `pkm install torch --repo download-torch +arch=cpu`, `pkm install torch --repo conda +channel=main`
    - if such source is not defined will auto define it with the same type
    - if type not defined will search pypi for download-torch-pkm-repo, if found will ask the user if can install
    - for the conda, repository instance builder should support "url" based configuration
    - cli managed configuration
- refactoring: repositories should by itself be a project group
- check pkm installation in app mode on system environment + torch-repo in app mode
- bug: when running in "build-sys" mode should not "implicitly install" cache files
    - also when running in this mode some basic monitoring should be made
- documentation: document the application usage
- pkm shell: automatic zoo export (zoo should have a bin directory), think about that, do we need it as non pkm shell
  extension?
- improve configuration infra - somehow reduce the boilerplate code that is needed in order to add new configuration
- test pkm on os where platlib and purelib are different (centos?)
- pkm stat : print cache size, attached repository, etc.
- repositories: pyvenv
- consider exposing application script entrypoint using the old application loader
- applications can also provide repositories configuration, those should be specified in its table
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
- containerized applications (a prototype was previously made, it requires some hacking but it is possible)