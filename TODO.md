## RUNNING TASKS:

## DONE IN THIS VERSION
- simplification: env - join remove and force remove
- bug: `pkm install package`, if failed (say package not in repo) still updates `pyproject.toml`
- cmd: pkm uninstall - display the packages being removed
- simplification: remove the coerced dependnecies and package names support in env install/remove
- refactoring: project.install_dev and project.uninstall_dev belongs to the cli flow and not to main pkm
- bug: configuration framework default factory was not transferred to data class
- bug: current intepreter shown twice on templates
- bug: incorrect default configuration on pkm-project
- refactoring: global_flags move into general configuration with interpreters search path
- ".pyenv" installations are searched for by default

## BACKLOG TASKS:
- multiproc: pipe monitoring events, currently download is not shown when multiproc
- simplification: remove the repository:sort_by_priority function - do that as part of the match for repostiries that
  this important to
- documentation: dependency overrides, what is the use flow?
- try and break multiproc, when broken - add code that handles it by switching to multithread
- publishing without authentication available, an exception shown but help does not describe how to provide auth
- check ideas for multiple progress bar tui here: https://github.com/Textualize/rich/discussions/1500 also, consider
  putting the progressbar on the left ([===>  ] task description)
- consider replacing questionary with rich.prompt
- bug: uninstall does not delete the ".lib" directories but installer did created them
- `pkm run` support custom environment variables loading like in pipenv
- bug: installing installed package should make it user requested but it does not
- replace copy-transaction with "temp-env" install and then sync to actual env if successfull (this should be made
  outside of the package control, by the installer itself)
- qol: package build log should allways be sent into a file, this file can then be suggested to the user if he run on
  non verbose mode
- bug: version printing expand the ~= operator
- pkm build: cycle detection is not good enough (may fail on multithreading) should move to build session
- documentation: document builtin templates
- bug: running in dumb terminal log almost nothing
- look at the SimpleHTTPRequestHandler::send_header for better parsing of "if-modified-since"
- extract the docs-builder to a template together with relevant tasks - this may be usefull to many other projects
- documentation: environments
- documentation: how to work with multiprojects in pycharm
- documentation: mostly rewrite and extend the projects documentation
- integrate bash* autocomplete (can we also do so for `pkm run`?)
- display: create (indentation based) subprocess/subtask contextual display, this can be used to seperate progress of
  sub builds from main build
- add test support (maybe extendable test engine?)
- documentation: repositories - how to build your own
- add git repository type
- when publishing into a (closed) index (like pypi) - all dependencies should be available in this index (except urls
  and git)
- refactoring: rename version specifiers according to pep440
- clarification: Source distributions using a local version identifier SHOULD provide the python.integrator extension
  metadata (as defined in PEP 459).
- enhancement: delegation should also support abstract properties
- bug: generated pyc files are not getting signed
- replace dependency resolution progressbar with spinner?
- bug: copy transaction should be used at the level of the full installation as sometimes it has to upgrade packages
  which means that they will get deleted - bypassing the copy transaction realm
- package artifact hash validation: pypi, simple, torch
- qof: when running in "build-sys" mode, basic monitoring should be on
- repositories: pyvenv
- cli: if building packages during dependency resolution, output is very convoluted
- enhancement: build using pkm own buildsys is too quiet, cannot use the output for effective debugging
- documentation: explain about PKM_HOME, maybe show its value in one of the reports
- environment naming (for project for example..)
- documentation site: sidebar responsive to phones
- toml parser/writer need unit tests
- pubgrub - introduce package opening cost (package that needs download in order to be open can cost like its size)
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- local pythons repository - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- content information (author and maintainer) name and email should be validated before publishing,
    - should use the email.utils.formataddr

## Ideas (may be irrelevant to pkm and may have their own library):

- automatic monkey patching of a module - can be defined in the project level = extension methods, this can be done with
  pth files and import hooks!
- mechanism for lazy importing (like in java) that use the new module level "get attr" or locals:
    - can be made by a preprocessor (like: '#preprocessor: lazy imports' on the beginning of the file)
    - it will then have to replace all the type annotations into string based or something similar..
- shim dependencies (pkm can choose to install them with the shim name instead of the lib name)
- python installation repository (no sudo! - download for os and install in data files - if possible)
- tranpilation between python version (babel kind) in the build process to produce suitable wheels
- feature: namespace guard file (in a namespace package add a `.namespace` file and `pkm` will guard it to not
  allow `__init__.py` files to be accedantly added to it)
