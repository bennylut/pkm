## RUNNING TASKS:
- cmd: pkm uninstall -o (orphans)
- create pyproject from environment - usecase: user already has an environment that he worked on and want to have a
  project based on it, I think I also saw this possibility in conda
- cmd: pkm uninstall - display the packages being removed
- add the self: install, remove, update, ... commands
- documentation: document builtin templates


## DONE IN THIS VERSION
- create installation script for pkm
- when searching for python interpreter, always add the current running interpreter

## BACKLOG TASKS:
- look at the SimpleHTTPRequestHandler::send_header for better parsing of "if-modified-since"
- extract the docs-builder to a template together with relevant tasks - this may be usefull to many other projects
- documentation: environments
- documentation: how to work with multiprojects in pycharm
- documentation: mostly rewrite and extend the projects documentation
- bug: `pkm install package`, if failed (say package not in repo) still updates `pyproject.toml`
- bug: `pkm uninstall package` can fail if other unrelated dependency in `pyproject.toml` is not installed yet
- integrate bash* autocomplete (can we also do so for `pkm run`?)
- display: create (indentation based) subprocess/subtask contextual display, this can be used to seperate progress of
  sub builds from main build
- add test support (maybe extendable test engine?)
- bug: uninstall does not delete the ".lib" directories but installer did created them
- refactor: there are several instances where dynamic args are provided as a dictionary - create DynamicArguments class
  with common functionality (may be used in repository builder, in publish credentials,etc.)
- documentation: repositories - how to build your own
- add git repository type
- pkm shell should be moved into its own project (optionally automatically installed when requested)
- when publishing into a (closed) index (like pypi) - all dependencies should be available in this index (except urls
  and git)
- refactoring: project.install_dev and project.uninstall_dev belongs to the cli flow and not to main pkm
- refactoring: rename version specifiers according to pep440
- cli consider moving install and remove into a "save" paradigm instead of '-o' use `-s` or `-S where`
- clarification: Source distributions using a local version identifier SHOULD provide the python.integrator extension
  metadata (as defined in PEP 459).
- qof: ability to specify max cache size
- simplification: remove the coerced dependnecies and package names support in env install/remove
- enhancement: delegation should also support abstract properties
- cli: read about parents in argparse - may help improve code readability
- `pkm show *` should also show containerized applications
- `pkm show context` should changed for a simple `pkm show`
- bug: generated pyc files are not getting signed
- shell: `pkm -v` print pkm version
- replace dependency resolution progressbar with spinner?
- bug: copy transaction should be used at the level of the full installation as sometimes it has to upgrade packages
  which means that they will get deleted - bypassing the copy transaction realm
- package artifact hash validation: pypi, simple, torch
- qof: when running in "build-sys" mode, basic monitoring should be on
- improve configuration infra - somehow reduce the boilerplate code that is needed in order to add new configuration
- pkm show : print cache size, attached repository, etc.
- repositories: pyvenv
- cli: if building packages during dependency resolution, output is very convoluted
- pkm build: cycle detection is not good enough (may fail on multithreading) should move to build session
- pkm show: add repositories information
- enhancement: build using pkm own buildsys is too quiet, cannot use the output for effective debugging
- documentation: explain about PKM_HOME, maybe show its value in one of the reports
- cmd: pkm show - on envs, show all the installed script entrypoints (and who installed them)
- environment naming (for project for example..)
- shell aliases: p (= python x.py ... or python -m x ...), project-dir, env-dir, l, ll
- documentation site: sidebar responsive to phones
- toml parser/writer need unit tests
- pubgrub - introduce package opening cost (package that needs download in order to be open can cost like its size)
- content information (author and maintainer) name and email should be validated before publishing,
    - name can be whatever can be put as a name, before an email, in RFC #822 and not contain commas
    - email should be a valid email address
    - see also https://jkorpela.fi/rfc/822addr.html and https://www.python.org/dev/peps/pep-0621/#authors-maintainers
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- add some flag to disable parallelizm in installation (mainly useful for debug?)
- `pkm shell` support custom environment variables loading like in pipenv
- local pythons repository - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- shell venv - alias to print environment and project in context
- feature: namespace guard file (in a namespace package add a `.namespace` file and `pkm` will guard it to not
  allow `__init__.py` files to be accedantly added to it)

## Ideas (may be irrelevant to pkm and may have their own library):

- automatic monkey patching of a module - can be defined in the project level = extension methods, this can be done with
  pth files and import hooks!
- mechanism for lazy importing (like in java) that use the new module level "get attr" or locals:
    - can be made by a preprocessor (like: '#preprocessor: lazy imports' on the beginning of the file)
    - it will then have to replace all the type annotations into string based or something similar..
- shim dependencies (pkm can choose to install them with the shim name instead of the lib name)
- python installation repository (no sudo! - download for os and install in data files - if possible)
- tranpilation between python version (babel kind) in the build process to produce suitable wheels