## RUNNING TASKS:
- documentation: document VersionSpecifier
- documentation: document the application classes and usage
- documentation: describe repositories
- documentation: describe verbose option
- pkm: git and url dependencies installation support
- repositories: conda
- enhance tool.pkm.application:
  - installer-package = 'name'
  - forced-dependencies { package: version }
  - expose non script entrypoint using the new application loader 
  - expose script entrypoint using the old application loader 
  - applications can also provide repositories configuration, those should be specified in its table
- bug: when running in "build-sys" mode should not "implicitly install" cache files
  - also when running in this mode some basic monitoring should be made
- bug: different build sdists (coming from different urls) are cached as the same one: SourceDistribution
  - package should use its artifact as a key to the cache, some repositories may even add information to invalidate the cache
    - we may also want to un-repositorize the cache - change it to something like "build-cache" to be able to expose more functionality without breaking the api

## DONE IN THIS VERSION
- etc chain: now configuration in etc can be context dependent
- utils: bug in http client (deadlock) was fixed 
- add specific-url version specifier and url-version
- reduce indirection for some version fields 
- bug: minor adjustment heuristic could have backtrack to a stage before the adjusted package is required 
- introduce url version and url version specifier

## BACKLOG TASKS:
- cli: if building packages during dependency resolution, output is very convoluted 
- util: create a @delegate decorator for _GitPackageWrapper and many more
- pkm: generalize repository publisher: accept the project and distribution types
- pkm build: cycle detection is not good enough (may fail on multithreading) should move to build session
- pkm: support * in packages but not default (just scan before usage on supported repositories)
- misc: build readme, set github's site
- pkm show: add repositories information
- cmd: pkm install - support installation of wheel and sdist from path
- enhancement: build using pkm own buildsys is too quiet, cannot use the output for effective debugging
- cmd: pkm cache clear
- bug: pkm new - cannot cancel creation - it just continues to the next question
- documentation: explain about PKM_HOME, maybe show its value in one of the reports
- cmd: pkm remove - display the packages being removed 
- cmd: pkm show - on envs, show all the installed script entrypoints (and who installed them)
- documentation - describe the lock, explain why this type of lock is better for multi user projects
- pkm: update package installation
- pkm: support installing applications which were not built as self-contained ones
- documentation site: projects and project groups, self-contained applications 
- repositories: light the torch repository
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
- shim dependencies (pkm can choose to install them with the shim name instead of the lib name)
- site: sidebar responsive to phones
- toml parser/writer need unit tests
- toml - lists user style - support column and grid and auto detect it
- check that when downloading packages for install, the hash is being validated correctly
- check the "editables" module, decide if you want to support this behavior
- version local label - check if specific version can ask for a local-label
- pubgrub - introduce package opening cost (package that needs download in order to be open can cost like its size)
- check if metadata 2.2 and then when dependencies are none and not dynamic we dont need to download the archive
- pkm.repository_builders should be pluggable
- handle project install with extras, usecase: test dependencies
- multi venv in project - usecase and flow (maybe explicitly create an environment zoo)
- bug: cached_property: mutation lock should be instance dependent and not global
- content information (author and maintainer) name and email should be validated,
    - name can be whatever can be put as a name, before an email, in RFC #822 and not contain commas
    - email should be a valid email address
    - see also https://jkorpela.fi/rfc/822addr.html and https://www.python.org/dev/peps/pep-0621/#authors-maintainers
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- bug: leftover __pycache__ on site packages dir after uninstall
- add some flag to disable parallelizm in installation (mainly useful for debug?)
- hierarchical site packages:
    - a dependency can be marked as shared and then pkm will install it as a pth to a shared lib installation
    - will need some sort of reference counting?
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
- decide the difference for when installing in application mode and in library mode (some sort of manifast?)
- prepare an installation test from export that uses many known python packages and several python versions
- create problem exporter for debug
- attach environment zoo to project
- make-like task system
- properties and build profiles (note that properties should be resolved before sdist packaging)
- python installation repository (no sudo! - download for os and install in data files - if possible)
- common tasks: test, build doc, etc.
- create pyproject from environment - usecase: user already has an environment that he worked on and want to have a
  project based on it

## Ideas (may be irrelevant to pkm and may have their own library):

- automatic monkey patching of a module by import hooks - this hooks can be defined in the project level = extension
  methods, this can be done with pth files and import hooks!
- mechanism for lazy importing (like in java) that use the new module level "get attr" or locals:
  - include('module', 'name1 as x', 'name2', ...), maybe also specify that you want to import the type only
  - can be also made by a preprocessor (like: '#preprocessor: lazy imports' on the beginning of the file)
