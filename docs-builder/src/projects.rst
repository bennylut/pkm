PKM Projects
==================

The :file:`pyproject.toml` File
--------------------------------

``pkm`` projects follows :pep:`631`, :pep:`621`, :pep:`517` and :pep:`518`.
It reads the project configuration from the standard :file:`pyproject.toml` file.
:program:`toml` is a fairly human-readable format, you can learn more about it [here](https://toml.io/en/).

The :toml-table:`project` Table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   The following documentation is based mainly on :pep:`621`, you may want to refer to it for further details.


The :toml-table:`project` table is the main section to configure your project metadata, since most of the values in
this section are self-explanatory, we will begin with an example (taken directly from :pep:`621`):

.. code-block:: toml
   :caption: pyproject.toml

    [project]
    name = "spam"
    version = "1.2.3"
    description = "Lovely Spam! Wonderful Spam!"
    readme = "README.rst"
    requires-python = ">=3.8"
    license.file = "LICENSE.txt"
    keywords = ["egg", "bacon", "sausage", "tomatoes", "Lobster Thermidor"]
    authors = [
        { email = "hi@pradyunsg.me" },
        { name = "Tzu-Ping Chung" }
    ]
    maintainers = [
        { name = "Brett Cannon", email = "brett@python.org" }
    ]
    classifiers = [
        "Development Status :: 4 - Beta",
        "Programming Language :: Python"
    ]

    dependencies = [
        "httpx",
        "gidgethub[httpx]>4.0.0",
        "django>2.1; os_name != 'nt'",
        "django>2.0; os_name == 'nt'"
    ]

    [project.optional-dependencies]
    test = [
        "pytest < 5.0.0",
        "pytest-cov[all]"
    ]

    [project.urls]
    homepage = "example.com"
    documentation = "readthedocs.org"
    repository = "github.com"
    changelog = "github.com/me/spam/blob/master/CHANGELOG.md"

    [project.scripts]
    spam-cli = "spam:main_cli"

    [project.gui-scripts]
    spam-gui = "spam:main_gui"

    [project.entry-points."spam.magical"]
    tomatoes = "spam:main_tomatoes"


Following, is  short explanation for the supported fields in this table:

:name: The name of the project.
:version: The version of the project as supported by :pep:`440`
:description: The summary description of the project.
:readme:
   The field accepts either a string or a table.

   - If it is a string then it is the relative path to the project readme (rst or md).
   - If it is a table, the :toml-key:`file` key accepts the relative path to the readme,
     while the :toml-key:`text` key accepts the actual description.

   **These keys are mutually-exclusive**
:requires-python: The Python version requirements of the project.
:license:
   The field accepts a table with the following keys:

   - The :toml-key:`file` key accepts the relative path to a license file.
   - The :toml-key:`text` key accepts a license identifier.

   **These keys are mutually exclusive**
:authors/maintainers:
   Array of :toml-key:`name` + :toml-key:`email` tables
   holding the contact information for the authors and maintainers
:keywords: Array of keywords for the project
:classifiers: Array of `Trove classifiers <https://pypi.org/classifiers/>`_ which apply to the project.
:urls: Table of name to url mapping
:entry-points:
   Table which contains sub-tables for each of the project entrypoint's groups.

   Each of the entrypoints group table contains the project-provided name to
   `entrypoint <https://packaging.python.org/en/latest/specifications/entry-points/>`_ mapping.
:scripts: special entrypoints table that contains the *'console_scripts'* group of entrypoints
:gui-scripts: special entrypoints table that contains the *'gui_scripts'* group of entrypoints
:dependencies:
   Array of :pep:`508` strings which represents the dependencies of the project
:optional-dependencies:
   Table which contains arrays of dependencies for each of the project *extra* dependencies.


The :toml-table:`tool.pkm` table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. attention::
   🚧 This section is not documented yet 🚧



Package locking
----------------

Package locking is a mechanism that attempts to reduce package versioning dissimilarities on multi-user projects. It
actually sounds more complex than it is..

.. admonition::
   Lets try to understand the problem that it tries to solve using an example

   Say that there are two developers working on your project - :name:`Alice` and :name:`Bob`.

   :name:`Alice` added a dependency to the project: :package:`x >= 1.0.0`, upon installation, she got in her
   environment the package :package:`x == 1.1.0` (which satisfies the required dependency). Later this week,
   :name:`Bob` started to work and fetched :package:`x == 1.1.1` (which also satisfied the required dependency).

   :name:`Alice` filled a bug which unknowingly, happens because of a behavior specific to :package:`x == 1.1.0`.
   When :name:`Bob` tried to fix the bug he could not reproduce it, which of-course lead to both of them fighting and
   not talking to each-other for more than a year.

``pkm``'s Package locking mechanism stores the exact version of the package that was installed inside the file
:file:`etc/pkm/packages-lock.toml` alongside other environment specific information. It then tries to use this
information to reduce dissimilarities across the developers. Unlike many other package locking mechanisms, it takes into
consideration the fact that different developers may work on totally different environments: they may have different
operating systems or may use a different version of python, etc. Therefore, it is usable even on these scenarios.

``pkm`` automatically updates :file:`etc/pkm/packages-lock.toml` when you install new dependencies, all you need to
do is to make sure that you commit this file to your version control system.


Distribution Types
------------------

Regular (library) Distribution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TODO

Containerized Application Distribution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Projects can be distributed as containerized application

packages installed as containerized applications creates their own container "sub environment" inside the environment
they are installed at. they install all their dependencies inside this container and are exposed to the main environment
only by their registered script entrypoints

To distribute your application as a "containerized application" all you needs to do is to add the following
into :file:`pyproject.toml`:

.. code-block:: toml
   :caption: pyproject.toml

   [tool.pkm.distribution]
   type = 'cnt-app'

when building and publishing your project, a special *'sdist'* will be created which will take care of containerizing your
application when it is installed. (it can be installed regularly like any other package with any modern python package
management that supports :pep:`517`, e.g., :program:`pip`)

If you like, :doc:`read more about containerized applications <containers>`.




