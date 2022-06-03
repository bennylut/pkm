Project Tasks
=============
Project tasks is a pkm feature that allows you to define tasks that may assist you during your project
developement. These tasks can be then executed using ``pkm run @task`` or by attaching them to one of pkm's commands
(like build, install, publish etc.)


Writing Tasks
-------------
Tasks are python scripts that are found inside your project's :file:`tasks` directory or the :package:`pkm_tasks`
namespace package. The name of the task's script file reflects the name of the task (without the ".py" extension).

The task script must define a ``run`` function, which is the function that gets executed when pkm is asked to runs the
task.

for example, the following defines a task named "hello" that print "world" to the screen

..  code-block:: python
    :caption: tasks/hello.py

    def run():
        print("world")

For your conviniance, you can generate a new task using the cli

..  code-block:: console

    $ pkm new task <task name>

The project's :file:`tasks` directory can contain any python module, tasks can import these modules and use
them for a common functionality.

Running Tasks
-------------

To execute tasks, you can use the ``pkm run`` command and give it as its first argument the task name prefixed with ``@``

..  code-block:: console

    $ pkm run @hello
    world

The command will get executed inside the environment attached to the project context of the ``pkm run`` command, or fail
if ``pkm run`` was not called in a project context.

Task Arguments
------------------------
The task's ``run`` function can define arguments, these will get supplied by the user in the command line

..  code-block:: python
    :caption: tasks/with_args.py

    from typing import Optional


    def run(arg1: str, arg2: int, optional_arg1: int = 7, optional_arg2: Optional[str] = None):
        print(locals())

In the above code snippet, the :file:`with_args` task is defined to get 4 arguments, 2 of them are optional.

The user can call this task by running the command:

..  code-block:: console

    $ pkm run @with_args arg1-value 42 optional_arg2='value for arg2'
    {'arg1': 'arg1-value', 'arg2': 42, 'optional_arg1': 7, 'optional_arg2': 'value for arg2'}

The :file:`with_args` task also used type annotations to indicate the type of its arguments, pkm automatically converted the
parameter passed by the commandline to this types.
It does so by passing the string received in the command line to the type constructor (e.g., ``arg2=int("42")`` in the
above shell snippet). This means that arguments can only be of types that support construction by single-string (e.g.,
int, bool, str, Path or any user defined type that follows this rule)

..  note::
    For any argument ``arg`` of type ``bool``, you can use ``--arg`` in the commandline as a syntactic sugar for ``arg=True``.

Documenting tasks
-----------------

To document your task, just add a doc-string to your ``run`` function. You can view the task documentation using
the ``-h, --help`` flag of the ``pkm run`` command with the given task.

..  code-block:: console

    $ pkm run @task -h

Task Extended-Builtins
-----------------------
When pkm executes a task it adds to the task-script's builtins several functions and attributes that are usefull in the
context of task execution.
These builtins extension are listed below.

The run_task Function
^^^^^^^^^^^^^^^^^^^^^^

The ``run_task(name: str, *args, **kwargs)`` function can be used inside a task in order to call another task.

..  code-block:: python
    :caption: tasks/call_another.py

    def run():
        run_task('another', arg1="value1")

The project_info Variable
^^^^^^^^^^^^^^^^^^^^^^^^^
When pkm runs a task it allways do so in the context of a project, the ``project_info`` variable is a dictionary that
holds information about that project.

its keys are:

:name: (str): The name of the project
:version: (str): The version of the project
:path: (str): absolute path to the root of the project
:group_path: (Optional[str]): absolute path to the root of the project-group or None if this project is not part of a group.

Groupping Tasks
----------------

If you have large number of tasks it can be convinient to group them into packages.
for example, you can define tasks in :file:`tasks/printers/print_hello.py` and :file:`tasks/printers/print_word.py` and then call
them by running the command

..  code-block:: console

    $ pkm run @printers.print_hello
    $ pkm run @printers.print_world

Attaching Tasks to pkm Commands
-------------------------------

You can attach tasks to be executed before or after one of pkm commands, this can be done by adding a :file:`before.py`
or :file:`after.py` to the :file:`tasks/commands/path/to/command` directory where the path to the command is the same as the space
seperated path to the command in the pkm cli.

both :file:`before.py` and :file:`after.py` should define a ``run`` function with a single ``command`` argument
(of type dict). this argument contains all the commandline flags passed to the command being executed.

For example, to attach a task to be executed before the ``pkm repos add`` command, you can create the
file :file:`tasks/commands/repos/add/before.py`

..  code-block:: python
    :caption: tasks/commands/repos/add/before.py

    def run(command):
        print(f"you are going to add the repository {command.repo_name}")

Then, it will get executed when you executes the corresponding command

..  code-block:: console

    $ pkm repos add some-repo some-repo-type
    you are going to add the repository some-repo
    ...

To run commands without attached tasks you can use the pkm's ``--no-tasks, -nt`` flag, e.g.,:

..  code-block:: console

    $ pkm -nt repos add some-repo some-repo-type

..  note::
    throwing exception in the "before" script will stop the command execution

Publish and Install 3rd Party Tasks
-----------------------------------
In some cases you may want to create and publish your tasks so that they can be used by other projects.
You can create a project and add tasks to the :package:`pkm_tasks` namespace-package, this tasks can then be used by
other projects that installed your project.

pkm does not allow implicit command attachements by 3rd party tasks. Therefore, if your :package:`pkm_tasks`
namespace package contains the :package:`commands` subpackage, it will be ignored by the task attachement mechanism.


