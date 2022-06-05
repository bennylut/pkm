
Templates
=========

Templates are reusable file-system structures that are designed to help the user generate common artifacts like
projects, environments, common files, etc.

The most used template type is a "project template" which is designed to help a user to setup some common project
structure.


Creating Templates
-----------------

For your convinience, to create a new template in the current working directory
you can use the ``pkm new template`` command

..  code-block:: console

    $ pkm new template my-template

pkm's template is a directory which contains at least a :file:`render.py` file.

The :file:`render.py` should contain at least a `setup` function which returns a dictionary containing values that will be used while generating the template

..  code-block:: python
    :caption: render.py

    def setup() -> dict:
        return {
            'project_name': 'my-project',
            'readme_file_name': 'README.md',
            'description': 'my project description',
            'author': 'me'
        }

The directory containing :file:`render.py` also contains the directory tree to be copied into the target path when generating this template.

Pkm uses jinja to render its templates, the rendering happens both on the file/dir names and inside any file that ends
with .tmpl.

For example, following is a valid directory structure of a template.

::

    my-template/
    ├── {{project_name}}
    │   ├── {{readme_file_name}}.tmpl
    │   ├── src
    │   │   └── main.py
    │   └── {{tests_dir}}
    └── render.py

Note that we have a directory named :file:`{{project_name}}` and a file named :file:`{{readme_file_name}}`
(yes, the file and directory names include the double-curly-braces, just as you see them here),
This means that this template expects :file:`render.py` to return values to those variables from its ``setup`` function.

Since the :file:`{{readme_file_name}}.tmpl` has the ``tmpl`` extension, its content will also be rendered using jinja.
Here is an example content of the {{readme_file_name}} file:

..  code-block:: markdown
    :caption: {{readme_file_name}}.tmpl

    # {{project_name}}

    > Created By {{author}}

    {{description}}

Using our example :file:`render.py`, the :file:`{{readme_file_name}}.tmpl` file will be named :file:`README.md` and
its content will be

..  code-block:: markdown
    :caption: README.md

    # my-project

    > Created By me

    my project description

Next, we can see that there is a directory named :file:`{{tests_dir}}` in our template,
by examining the :file:`render.py` file we can see that the ``setup`` function did not return any value
corresponding to a ``tests_dir`` key, this will result in a file/directory without a name in the rendering phase
which will cause the file/dir to not be rendered (in other words the :file:`{{tests_dir}}` directory
will not be created).


Using Templates
---------------

To start template generation you can use the ``pkm new <template-name>`` command.
Given a template name, ``pkm`` attempts to find a matching template in two main places

1. In the path: ``template_name.replace('.', '/')`` relative the current working directory
2. Inside the :package:`pkm_templates` namespace-package, it searches for that package inside the environment it is installed in.


 For example, using the template defined above inside the current working directory, running:

..  code-block:: console

    $ pkm new my-template

will generate, inside the current directory, the directory structure:

::

    .
    └── my-project
        ├── README.md
        └── src
            └── main.py


Template Arguments
------------------

Templates can get arguments from the user in two main ways, as arguments in the commandline and interactively.

Commandline Arguments
^^^^^^^^^^^^^^^^^^^^^

To get arguments from the commandline, you can require them as parameters to your ``setup`` function.
For example, assume the following directory structure:

::

    my-template/
    ├── result.tmpl
    └── render.py


..  code-block:: python
    :caption: pkm_templates/with_args.py

    def setup(arg1: str, arg2: int, optional_arg1: int = 7, optional_arg2: str = None):
        return locals()


..  code-block:: text
    :caption: result.tmpl

    arg1 = {{arg1}}
    arg2 = {{arg2}}
    optional_arg1 = {{optional_arg1}}
    optional_arg2 = {{optional_arg2}}

In the above code snippet, the :file:`with_args` template setup's function is defined to get 4 arguments,
2 of them are optional.

The user can use this template by running the command:

..  code-block:: console

    $ pkm new with_args arg1-value 42 optional_arg2='value for arg2'

The generated content will include the :file:`result` file containing the following text:

..  code-block:: text
    :caption: result

    arg1 = arg1-value
    arg2 = 42
    optional_arg1 = 7
    optional_arg2 = value for arg2


The :file:`with_args` template also used type annotations to indicate the type of its arguments, pkm automatically converted the
parameter passed by the commandline to this types.
It does so by passing the string received in the command line to the type constructor (e.g., ``arg2=int("42")`` in the
above shell snippet). This means that arguments can only be of types that support construction by single-string (e.g.,
int, bool, str, Path or any user defined type that follows this rule)

Interactive Arguments
^^^^^^^^^^^^^^^^^^^^^

There are seveal functions that are available as part of the :ref:`template-extended-builtins` which can be used to get
input interactively from the user.

For example, assume the following directory structure:

::

    my-template/
    ├── result.tmpl
    └── render.py


..  code-block:: python
    :caption: pkm_templates/with_args.py

    def setup():
        name = ask("Your name")
        likes_pkm = confirm("Do you like pkm")
        return locals()

..  code-block:: text
    :caption: result.tmpl

    name = {{name}}
    likes_pkm = {{likes_pkm}}

Executing the command

..  code-block:: console

    $ pkm new my-template
    ? Your name: Mario
    ? Do you like pkm: Yes

You can ofcours combine commandline arguments with interactive ones,
asking the user only if they did not provide values in the commandline


..  code-block:: python
    :caption: pkm_templates/with_args.py

    def setup(name: str = None):
        name = name or ask("Your name") # ask only if name is not provided
        likes_pkm = confirm("Do you like pkm")
        return locals()





Template Extended-Builtins
--------------------------

When pkm executes a template it adds to the render-script's builtins several functions and attributes that are usefull in the
context of its execution. These builtins extension are listed below.

The ask Function
^^^^^^^^^^^^^^^^^

..  code-block:: python

    def ask(prompt: str, default: Any = "", options: Optional[List[str]] = None,
            secret: bool = False, autocomplete: bool = False, multiselect: bool = False,
            path: bool = False):

ask the user using the given `prompt`, limiting its answers using the different arguments of this function

:prompt: the prompt to show to the user
:default: the default value to show to the user
:options: limited options for the user to select from
:secret: if True, the caracters the user insert will not be visible
:autocomplete: use in combination with `options`, will autocomplete the user answers using the options
:multiselect: use in combination with `options`, allow to select several options
:path: if True, limit the user to entering a filesystem path
:return: the response of the user


The confirm Function
^^^^^^^^^^^^^^^^^^^^

..  code-block:: python

    def confirm(self, prompt: str, default: bool = True) -> bool

ask the user a yes/no question

:prompt: the prompt to show to the user
:default: the default to show to the user
:return: True if the user enter yes, False otherwise

The target_dir Variable
^^^^^^^^^^^^^^^^^^^^^^^
The target_dir variable holds the path into which the template is asked to be rendered,
The target_dir variable is only available inside the ``setup`` and ``post_render`` functions


Excluding and Preserving  Files in the Template
------------------------------------------------
Sometimes, your template may contain files that you want to exclude from the rendering process. You can use a
:file:`.templateignore` file for that (just add glob patterns to it similar to .gitignore file)

In other cases, your template may contain directories that you want to copy as is
(without passing through the template engine). To do so, all you need to do is to include a
:file:`.tempalatepreserve` file inside the directory that you want to preserve as is.


Templates Execution Life-Cycle
------------------------------
When ``pkm`` executes a template it follows a specific life-cycle:

1. Parse commandline arguments
2. Call the ``setup`` function with the parsed commandline arguments to get the rendering context
3. Find and evaluate the :file:`templateignore` and :file:`templatepreserve` files along the template directory
4. Render the files in the template directory using the rendering context and the ignore/preserve information into the ``target_directory``
5. Call the ``post_render`` function in :file:`render.py` if such exists.

Documenting Templates
---------------------
To document your template write a module-level docstring, for example:

..  code-block:: python
    :caption: pkm_templates/nothing.py

    """
    This templates does absolutely nothing!
    """

    def setup():
        return {}

A user can print the documentation of a template using the ``-h`` flag:

..  code-block:: console

    $ pkm new nothing -h
    This templates does absolutely nothing!


Install and Publish Templates
------------------------------

Since ``pkm`` searches for templates inside the :package:`pkm_templates` namespace package, you can create a project adding templates to this package and
publish it. To avoid stepping on eachother toes, please only add templates to a sub package of `pkm_templates` named after your project name.

Here is an example :pacakge:`my_awsome_template` project directory structure:

::

    my_awsome_template
    ├── src
    │   └── pkm_templates
    │       └── my_awsome_template
    │           ...
    └── pyproject.toml


Once published, a user can install :package:`my_awsome_template` via the command:

..  code-block:: console

    $ pkm self install my_awsome_template


