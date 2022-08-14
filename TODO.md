## RUNNING TASKS:
- integrate bash* autocomplete (can we also do so for `pkm run`?)
- documentation: environments
- cli hook into warnings and display them using Display
- build hook print - should be named in log according to the package being built and not the process building
- `pkm run` support custom environment variables loading like in pipenv
- qol: package build log should allways be sent into a file, this file can then be suggested to the user if he run on
  non verbose mode

## DONE IN THIS VERSION


## BACKLOG TASKS:
- pkm -p to execute command on a project in group, -P to execute command on all projects in the group
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
