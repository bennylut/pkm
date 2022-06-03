Templates
=========

Templates are reusable file-system structures that are designed to help the user generate common artifacts like
projects, environments, common files, etc.

The most used template type is a "project template" which is designed to help a user to setup some common project
structure.


Writing Templates
-----------------

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

``pkm`` looks for templates inside the :package:`pkm_templates` namespace-package.
It searches for that package inside the environment it is installed in.

To start template generation you can use the ``pkm new`` command. For example, using the template defined above, running:

..  code-block:: console

    $ pkm new my-template

will generate, inside the current directory, the directory:

::

    .
    └── my-project
        ├── README.md
        └── src
            └── main.py


Template Arguments
------------------

Templates can get arguments from the user in two main ways, as arguments in the commandline and interactively.

Templates Execution Life-Cycle
------------------------------

Template Extended-Builtins
--------------------------

Documenting Templates
---------------------

Groupping Templates
-------------------

Install and Publish Templates
------------------------------