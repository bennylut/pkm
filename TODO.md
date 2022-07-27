## RUNNING TASKS:
- move to the new dynamic cli
  - fix both template and tasks documentation (mainly modified environments)
  - publish arguments integration
  - integrate new task executor
  - when returning command - may also return status indicating if there was an error parsing the command
  - if a flag/option is used in help we can color it differently
  - move cached properties into symbols
  - remove the describe functionality from both tasks and templates - it is now done by default by the cli
  - cleanup old cli relics
  - new-cli: pkm run tasks
  - attached tasks are not integrated
  - new-cli: pkm install - test it - does not work!
  - for the pkm-run support "options terminator"
  
## DONE IN THIS VERSION
- new-cli: pkm new
- template engine integration
- new-cli: pkm run
- bug: subcommands options was not filled by their default values 
- new task execution implementation
- dynamic cli - support self command replacement
- positionals can have defaults - but once a single positional have a default all the rest must also heve a default
- support -h in template commands
- show the template subcommand description in the help of pkm new
- in help, option names should be sorted by size
- "-h" flag - support "global" flags
- context provide a way to access any "has repositories"
- change field provider into a class instead of a function
- repository builder needs a way to define its arguments and use it by pkm 
- bug: non parse errors are being swallowed
- command execute is not contextual
- bug: -R show the name parameter

## BACKLOG TASKS:
- refactoring unify all "missing" sentinals
- refactoring: cleanup the install command - it has too much logic 
- integrate bash* autocomplete (can we also do so for `pkm run`?)
- sphinx docgen for new commands
- documentation: environments
- cli hook into warnings and display them using Display
- build hook print - should be named in log according to the package being built and not the process building
- `pkm run` support custom environment variables loading like in pipenv
- qol: package build log should allways be sent into a file, this file can then be suggested to the user if he run on
  non verbose mode
- migration tool from poetry and pipenv
- build/publish with dependencies
- multiproc: pipe monitoring events, currently download is not shown when multiproc
- documentation: dependency overrides, what is the use flow?
- try and break multiproc, when broken - add code that handles it by switching to multithread
- check ideas for multiple progress bar tui here: https://github.com/Textualize/rich/discussions/1500 also, consider
  putting the progressbar on the left ([===>  ] task description)
- documentation: document builtin templates
- bug: running in dumb terminal log almost nothing
- documentation: how to work with multiprojects in pycharm
- documentation: mostly rewrite and extend the projects documentation
- display: create (indentation based) subprocess/subtask contextual display, this can be used to seperate progress of
  sub builds from main build
- add test support (maybe extendable test engine?), maybe add it as a prebuild hook (task?)
- documentation: repositories - how to build your own
- when publishing into a (closed) index (like pypi) - all dependencies should be available in this index (except urls
  and git)
- enhancement: delegation should also support abstract properties
- replace dependency resolution progressbar with spinner?
- qof: when running in "build-sys" mode, basic monitoring should be on
- cli: if building packages during dependency resolution, output is very convoluted
- enhancement: build using pkm own buildsys is too quiet, cannot use the output for effective debugging
- documentation: explain about PKM_HOME, maybe show its value in one of the reports
- documentation site: sidebar responsive to phones
- toml parser/writer need unit tests

## For version 1.0+
- post/pre processing and "compilers/transpilers" support  
- tranpilation between python version (babel kind) in the build process to produce suitable wheels (mainly use for pkm)
- how to create platform/abi dependent projects? need to collect usecases (maybe cython and numpy?)
- pubgrub - introduce package opening cost (package that needs download in order to be open can cost like its size)
- environment naming (for project for example..)
- repositories: pyvenv
- clarification: Source distributions using a local version identifier SHOULD provide the python.integrator extension
  metadata (as defined in PEP 459).
- feature: namespace guard file (in a namespace package add a `.namespace` file and `pkm` will guard it to not
  allow `__init__.py` files to be accedantly added to it)
- enhancement: failure during installation should revert fully to the previous environment state
- local pythons lookup - support windows (using PEP 514, virtualenv has a reference implementation in its source
  code under discovery pacakage)
- performance: pkm keeps rebuilding/resolving similar build environments - consider caching them or their solutions
- test "probe" framework (maybe there is already something like that)
- consider replacing questionary with rich.prompt
- extract the docs-builder to a template together with relevant tasks - this may be usefull to many other projects
- add git repository type

## Ideas (may be irrelevant to pkm and may have their own library):
- automatic monkey patching of a module - can be defined in the project level = extension methods, this can be done with
  pth files and import hooks! = extension methods
- mechanism for lazy importing (like in java) that use the new module level "get attr" or locals:
    - can be made by a preprocessor (like: '#preprocessor: lazy imports' on the beginning of the file)
    - it will then have to replace all the type annotations into string based or something similar..
