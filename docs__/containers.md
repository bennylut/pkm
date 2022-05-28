* toc 
{:toc}

## What is it?

`pkm`'s containerized applications is a special installation method for application packages. Packages installed as
containerized applications creates their own container (think about it like a "sub environment") inside the environment
they are installed at. During the installation process, all the package dependencies are installed inside this
container. The installed dependencies are encapsulated in the container and does not interfere with other dependencies
in the environment. The installed application itself is exposed to the main environment only by its registered script
entrypoints.

## Why is it needed?

Python packages comes in two main flavors

- **applications** like: pip, twine, jupyterlab, poetry, pkm-cli, etc.
- **libraries** like: numpy, pandas, requests, etc.

In most cases, when installing applications, the end users are mainly interested in its provided scripts. Full
applications by nature has relatively large amount of dependencies and these dependencies should not interfere with
other applications.

one way to achieve such dependencies' separation is to install each application in their own environment, but this
requires managing multiple environments or using a program that manages them for you like `pipx`. It also requires the
end-user to be aware of the distinction between libraries and applications and install it with the correct means.

There are benefits for installing several applications inside the same environment. Having all your current requirements
encapsulated in one environment allows you to simply delete it when you are not need it anymore or just switch to
another environment to get a different version of the application. You also gain the ability to fully export your
environment, including the required applications so that other team member may import it. Finally, from the end-user
points of view, they already used to install packages into their own environment and does not need to think about
installing a specific application in a different way.

## How can I use it?

### As an end-user

If you want to install an existing package as a containerized application you can run:

```bash
$ pkm install --app <package>
```

for example, you can install `jupyterlab` inside your global environment, without the fear of breaking any other package
by:

```bash
$ pkm install --app jupyterlab
...

$ jupyter-lab -h 
JupyterLab - An extensible computational environment for Jupyter.
...
```

### As an application developer

You can distribute your application as a "containerized app" by adding the following to `pyproject.toml`

```toml
# ... pyproject.toml

[tool.pkm.distribution]
type = 'cnt-app'
```

Distributing your package as a containerized application will make sure that normal installation of your package in any
environment will use the containerized application installation mode. The installation process itself does not
require `pkm` to be installed on the end-user machine. It will work for any pep517 supported package manager (like pip).

## difference from vendoring

Vendoring is the act of including 3rd party software directly in your distribution, with the main reason to avoid
version conflicts when the dependencies are installed. While vendoring your dependencies can achieve a similar outcome
like containerizing them, vendoring have a considerable drawback that does not happen with containerized applications.

1. Vendoring is relatively hard to perform correctly and many times requires patching the 3rd party code. In contrast,
   marking project for containerized application distribution requires adding a couple of lines in `pyproject.toml`.
2. Vendoring is a huge maintenance burden, for every 3rd party dependency you are vendoring, you have to make sure you
   keep adding all security updates and bugfixes of it to your software as it releases. On the other hand, containerized
   applications uses regular dependency resolution which makes sure to use the most up-to-date matching dependency, and
   in addition the user can update the application which will update both the version of the application and all its
   dependencies automatically

## application plugins

Some applications may support plugins, which are packages that can be installed alongside the application and will be "
picked" and used by the application to extend its functionality. If you installed an application in a containerized
mode, you can install/uninstall plugin packages inside its container using

```bash

# install the application
$ pkm install --app myapp
...

# install plugins: plugin1 & plugin2
$ pkm install --app myapp plugin1 plugin2
...

# uninstall plugin1:
$ pkm uninstall --app myapp plugin1
...
```

---

TODO:
- advanced container packaging with [tool.pkm.application]
- dependencies override

--- 