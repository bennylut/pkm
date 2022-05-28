### Table Of Content
{:.no_toc}

* toc 
{:toc}

---
## Contextual Commands
Some of `pkm`'s commands are context dependent, for example, the command:
```console
$> pkm install some_package
```
will install <i str>"some_package"</i>, if it executes inside a virtual environment directory - pkm will install it on that virtual environment.
If on the other hand, it executes inside a project directory, pkm will install the dependency inside the virtual environment that belongs to that 
project and also update the <i> pyproject.toml </i> configuration file. 

### Finding context
The way `pkm` find the corrent context is very simple, upon execution of context dependent command, pkm looks at the current directory and try to find 
out if it runs inside a supported context (venv, project, project-group, etc.) if it does - it uses that context, otherwise it goes up a directory and retries.
If `pkm` reaches the root directory it stops and reports that no context could be found for the given command.

### Controlling Context 
if you want pkm to use a specific context (instead of searching for one itself) you can do so using the `-c` flag. For example,
```console
$> pkm install -c path/to/context some_package
```
The above command will use the path <i str>"path/to/context"</i> as its context (failing if no supported context found in this path).

### Global context
`pkm` considers the environment it was installed in as the global context. 
 If you installed `pkm` directly on your system installation, the global environment will be that installation.
you can ask `pkm` to use the global context in your commands by using the flag `-g`, for example:
```console
$> pkm install -g some_package
```
This command will install the <i str>"some_package"</i> package in the same environment as the one that `pkm` was installed into.

---
## Manage Packages

### `pkm install ...`

> <i tag>⏳ TLDR</i> installs the given set of dependencies <br>
> ```console
> $> pkm install p1 p2==v2 "p3>=v3" ...
> ```
> <i case>* in project context *</i> installs in the assigned venv and also update pyproject. <br>
> <i case>* in venv context *</i> installs in that venv. <br>
> <i case>* otherwise *</i> installs in system env.

### `pkm uninstall ...`

> <i tag>⏳ TLDR</i> uninstall the given set of package names <br>
> ```console
> $> pkm uninstall p1 p2 p3 ...
> ```
> <i case>* in project context *</i> uninstall from the assigned venv and also update pyproject. <br>
> <i case>* in venv context *</i> uninstall from that venv. <br>
> <i case>* otherwise *</i> uninstall from system env.

---
## Manage Projects

### `pkm build ...`

> <i tag>⏳ TLDR</i> build wheels and sdist for your project <br>
> ```console
> $> pkm build
> ```
> the built artifacts will be stored in `<project-dir>/dist/<project-version>`

### `pkm publish ...`

> <i tag>⏳ TLDR</i> publish project build artifacts into pypi <br>
> ```console
> $> pkm publish <user-name> <password>
> ```

### `pkm vbump ...`

> <i tag>⏳ TLDR</i> bumps (increase) the project version <br>
> ```console
> $> pkm vbump minor # can be also major, patch, a, b, rc
> ```
> will change the version <i str>"1.2.3"</i> into <i str>"1.3.0"</i>

---
## Manage Virtual Envs

### `pkm shell ...`

> <i tag>⏳ TLDR</i> starts a new shell using an environment - <i str>"activate"<i> on steroids <br>
> ```console
> $> pkm shell
> ```
> <i case>* in project context *</i> starts the shell for its assigned venv. <br>
> <i case>* in venv context *</i> starts the shell for that venv. <br>
> <i case>* otherwise *</i> starts the shell on the system venv.

---
## General

### `pkm new ...`

> <i tag>⏳ TLDR</i> creates new stuff <br>
> ```console
> $> pkm new <template-name> <template-args>
> ``` 
> to create new project named <i str>"prj"</i>:  `pkm new project prj` <br>
> to create new project group named <i str>"prg"</i>: `pkm new project-group prg` <br>
> to create new virtual environment named <i str>"my-env"</i>: `pkm new venv my-env` <br>


### `pkm show ...` 
> <i tag>⏳ TLDR</i> displays requested information  <br>
> ```console
> $> pkm show # displays report about the current context
> $> pkm show package package_name # displays report about the package "package_name"
> $> pkm show -h # will show you all other supported reports 
> ``` 
 
