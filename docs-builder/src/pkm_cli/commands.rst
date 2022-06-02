Cli Command Reference
=====================

The Main ``pkm`` Command
------------------------

.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :nosubcommands:

Contextual Commands
-------------------
Many of ``pkm``'s commands are context dependent, for example, the command:

.. code-block:: console

   $ pkm install some_package

installs :package:`some_package` into **some** python environment, but which? this depends on the context it runs in:

*   If the above executes inside a virtual environment directory - pkm will install it on that virtual environment.
*   If on the other hand, it executes inside a project directory, pkm will install the dependency inside the virtual environment that belongs to that project (the *"attached virtual environment"*) and also update the :file:`pyproject.toml` configuration file.

Finding context
^^^^^^^^^^^^^^^
The way ``pkm`` find the corrent context is very simple, upon execution of context dependent command,
pkm looks at the current directory and try to findout if it runs inside a supported context
(venv, project, project-group, etc.) if it does - it uses that context, otherwise it goes up a directory and retries.
If ``pkm`` reaches the root directory it stops and reports that no context could be found for the given command.

Controlling Context
^^^^^^^^^^^^^^^^^^^
if you want pkm to use a specific context (instead of searching for one itself) you can do so using the ``-c`` flag. For example,

.. code-block:: console

   $ pkm install -c path/to/context some_package

The above command will use the path :file:`path/to/context` as its context (failing if no supported context found in this path).

Global context
^^^^^^^^^^^^^^
``pkm`` considers the environment it was installed in as the global context.
If you installed ``pkm`` directly on your system installation, the global environment will be that installation.
you can ask ``pkm`` to use the global context in your commands by using the flag ``-g``, for example:

.. code-block:: console

   $ pkm install -g some_package

This command will install the :package:`some_package` package in the same environment as the one that ``pkm`` was installed into.


Package Management Commands
---------------------------

This section outlines the ``pkm`` sub-commands that are related to package management

``pkm install``
^^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: install

``pkm uninstall``
^^^^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: uninstall

Project Management Commands
---------------------------

``pkm build``
^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: build


``pkm publish``
^^^^^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: publish

``pkm vbump``
^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: vbump

Repositories Management Commands
--------------------------------

``pkm repos install``
^^^^^^^^^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: repos install

``pkm repos uninstall``
^^^^^^^^^^^^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: repos uninstall

``pkm repos add``
^^^^^^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: repos add

``pkm repos remove``
^^^^^^^^^^^^^^^^^^^^^
.. argparse::
   :module: pkm_cli.main
   :func: prepare_parser
   :prog: pkm
   :path: repos remove
