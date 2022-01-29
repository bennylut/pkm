---
layout: documentation
---

### Available Commands
{:.no_toc}

* toc 
{:toc}

## Manage Dependencies

### `pkm install ...`

> <i tag>⏳ TLDR</i> installs the given set of dependencies <br>
> ```console
> $> pkm install p1 p2==v2 "p3>=v3" ...
> ```
> <i case>* in project context *</i> installs in the assigned venv and also update pyproject. <br>
> <i case>* in venv context *</i> installs in that venv. <br>
> <i case>* otherwise *</i> installs in system env.

### `pkm remove ...`

> <i tag>⏳ TLDR</i> remove the given set of package names <br>
> ```console
> $> pkm remove p1 p2 p3 ...
> ```
> <i case>* in project context *</i> remove from the assigned venv and also update pyproject. <br>
> <i case>* in venv context *</i> remove from that venv. <br>
> <i case>* otherwise *</i> remove from system env.

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

## Manage Virtual Environments

### `pkm shell ...`

> <i tag>⏳ TLDR</i> starts a new shell using an environment - <i str>"activate"<i> on steroids <br>
> ```console
> $> pkm shell
> ```
> <i case>* in project context *</i> starts the shell for its assigned venv. <br>
> <i case>* in venv context *</i> starts the shell for that venv. <br>
> <i case>* otherwise *</i> starts the shell on the system venv.

## Creating stuff - new projects, environments, etc.

### `pkm new ...`

> <i>⏳ TLDR</i> creates new stuff <br>
> ```console
> $> pkm new <template-name> <template-args>
> ``` 
> to create new project named <i str>"prj"</i>:  `pkm new project prj` <br>
> to create new project group named <i str>"prg"</i>: `pkm new project-group prg` <br>
> to create new virtual environment named <i str>"my-env"</i>: `pkm new venv my-env` <br>

