## What are Repositories

Python repositories are services that holds python packages, one well known example is pypi - the PYthon Package Index.

pkm has an extendable repositories mechanism, it comes with support for the most common repositories and allows you to
install and even develop your own support for the less common ones.

Finally, pkm also allows you to configure repositories - both on a global level and on a context level.

### Context Attached Repositories

pkm chooses the repositories to use based on the context of your commands.
When installing packages globally (using the `-g` flag) pkm uses its "global" repositories configuration to choose the
most appropriate repository for the required package.
When installing packages in a specific context (like project or environment) it uses the "contextual" repository
configuration.
Unless specified otherwise, the contextual configuration inherits the global configuration and extends it.

See the [managing attached repositories](#managing-attached-repositories) for more details.

## Managing Repository Support

Pkm defines an extendable repository support mechanism, you can install and develop your own repository support and then
configure pkm to use them. The following

### Installing New Repository Support

New repository support must be installed in a global manner. It can be done via the command
```console
$> pkm repos install -g <repository-dependency>
```

The syntax for providing repository-dependency is the standard [PEP-508](https://peps.python.org/pep-0508/) syntax for
dependency specification.

You can use the `-u,--update` flag to upgrade your repository installation
```console
$> pkm repos install -g --update <repository-dependency>
```

### Removing Installed Repository

You can remove previously installed repository via the command

```console
$> pkm repos uninstall -g <repository-package-name>
```

### Listing Installed Repositories

To list all the repositories that was installed with some additional information about them, you can use the command

```console
$> pkm repos show installed
```

## Managing Attached Repositories

adding/removing repository support does not add any actual repository instances to pkm, to do so you need to manage your
attached repositories (= the repositories attached to different pkm contextes).

The repositories configuration is located in the file: `repositories.toml`.
For the global repository configuration, this file is located at `$PKM_HOME/etc/pkm/repositories.toml`.
For context specific configuration (like projects, environments, environment-zoos, etc.) the file is located
at `etc/pkm/repositories.toml` relative to the root of the context.

You can modify the file manually or via the pkm cli as described in the following subsections.

### Adding and Configuring a Repository

to add a repository via command line you can use:

```console
$> pkm repos add <repo-name> <repo-type> +arg1=val1 +arg2=val2 ... 
```

you can choose to add the repository to the global configuration via the `-g` flag, otherwise it will be added to the
current context.

for example, to add a project-group locally stored at `/my-projects` as a repository named my-projects you can execute:

```console
$> pkm repos add my-projects file-system +path=/my-projects 
```

The commands above will just modify the repositories.toml to reflect your request. You can do so yourself using the
following syntax

```toml
# ... repositories.toml
[repos.repo-name]
type = "repo-type"
arg1 = "val1"
arg2 = "val2"
```

or, to follow our previous example, to add the "my-projects" repository you can add the following to the "
environments.toml" file

```toml
# ... repositories.toml
[repos.my-projects]
type = "file"
path = "/my-projects"
```

### Package Search Order

When installing new packages, pkm searches for the required dependency in the repositories listed in its "
repositories.toml" configuration file from top to bottom. It will stop on the first repository that has a package
matching the dependency.

If pkm run inside a specific context and could not find a suitable repository for a requested dependency, it will try
and search a "parent" context if it exists, going up to the global context. For example, for a project that reside
within a project group, the project group is the parent context of the project.

You can control this behaviour via the inheritance option by giving it the following values:

context
: the default - when package not found, go to the repositories defined in the upper context

global
: when package not found, go directly to the repositories defined in the global context

none
: when package not found, dont try any other repositories

For example:

```toml
# ... repositories.toml
inheritance = "global"
```

If you want to instruct pkm, that for a specific package it should use a specific repository, regardless of the search
order, you can use the "package-binding" section in "repositories.toml"

```toml
# ... repositories.toml
[package-binding]
package1 = "repo-1" # reference preconfigured repository by name
package2 = { type = 'repo-type', arg1 = 'arg1', arg2 = 'arg2' } # bind to inline, unnamed repository configuration
```

You can also bind a package to a preconfigured repository upon installation using the `-r, --repo` option in the
installation command

```console
$> pkm install -r <repo-name> <dependency>
```
You can use `-r default` to remove previous binding to the given packages and reinstall them.

```console
$> pkm install -r default <dependency>
```

In addition, you can use the `-R, --unnamed-repo` to bind a package to an unnamed repo

```console
$> pkm install -R <repo-type> +arg1=val1 +arg2=val2 <dependency>
```

One additional way you can effect the package search order is by defining a repository as "bind-only".
Repository defined as bind-only will not be searched for a dependency unless the dependency package was bound to this
repository.
In addition, repositories defined in such way improve the search performance of pkm as it dont need to query this
repository in most cases.

To define a repository as "bind-only", you can use the flag `-b, --bind-only` of the `pkm repos add` command

```console
$> pkm repos add --bind-only <repo-name> <repo-type> +arg1=val1 +arg2=val2   
```

or specify it directly in the configuration file

```toml
# ... repositories.toml
[repos.repo-name]
type = "repo-type"
bind-only = true # <<<
arg1 = "val1"
arg2 = "val2"
```

### Removing a Configured Repository

to remove a preconfigured repository you can use the command

```console
$> pkm repos remove <repo-name>
```

this will remove the "repo-name" repository and any package binding to it.
Of course, removing repositories or package binding directly from the configuration file works the same.

### Listing Configured Repositories

to show information about the configured repositories in the current context (or globally using the `-g` flag) you can
use the command

```console
$> pkm repos show configured
```

## Publishing Your Project to a Repository

If a configured repository supports publishing, you can use the publish command to publish your project

```console
$> pkm publish <repo-name> 
```

Some repositories may require authentication/credentials in order to publish.

You can provide those directly in the commandline

```console
$> pkm publish <repo-name> <user-name> <password> # in case the auth are simple user-password type
$> pkm publish <repo-name> --auth +arg1=val1 +arg2=val2 # for more advanced cases
```

You can instruct pkm to store these credentials in a password protected storage using the `pkm repos publish-auth store`
command

```console
$> pkm repos publish-auth <repo-name> <user-name> <password> # in case the auth are simple user-password type
$> pkm repos publish-auth <repo-name> --auth +arg1=val1 +arg2=val2 # for more advanced cases
Enter password for authentication storage: ******
Authentication info stored. 
```

if authentication info stored you can publish using:

```console
$> pkm publish <repo-name>
```

remove the stored credentials using:

```console
$> pkm repos publish-auth remove <repo-name>
```

show information about the stored credentials using:

```console
$> pkm repos publish-auth show
```

## Available Repositories

pkm comes with several types of repositories that you can use out of the box, it also has several experimental
repositories you can install. These repositories are listed below.

### File-System Repository

A repository that fetch packages from files and directories in your file system.

#### Installation
not required

#### Properties

type
: file-system

path
: absolute path to any of the following:
* project directory, the repository will be able to match this project
* project group directory, the repository will be able to match all the projects in the group
* wheel or sdist file, the repository will be able to match the packaged library
* library containing wheels or sdist files, the repository will be able to match the packaged libraries

#### Example
```console
$> pkm repo add repo-name file-system +path="/supported/path"
```

### Pypi Repository

A repositry supporting the [pypi json api](https://warehouse.pypa.io/api-reference/json.html)

#### Installation
not required

#### Properties

type
: pypi

url
: the base url of the repository

publish-url
: optional, if given, the defined reporitory becomes publishable and will use the given url as the publish endpoint

#### Example
```console
$> pkm repo add repo-name pypi +url="https://.." 
```

### Simple Repository

A repositry supporting PEP503 [simple repository api](https://peps.python.org/pep-0503/)

#### Installation
not required

#### Properties

type
: simple

url
: the base url of the repository

#### Example
```console
$> pkm repo add repo-name simple +url="https://.." 
```

### "Download-Torch" Repository (experimental)

A repository that automatically download torch to match your gpu type

#### Installation
```console
$> pkm repos install download-torch-pkm-repo
```

#### Properties

type
: download-torch

arch
: gpu or cpu (defaults to gpu if not given)

#### Example
```console
$> pkm repo add repo-name download-torch +arch=gpu
```

### Conda Repository (experimental)

A repository that download from a conda channels

#### Installation
```console
$> pkm repos install conda-pkm-repo
```

#### Properties

type
: conda

channel
: url for the conda channel, or the string "main" as a shortcut to the main conda channel url

#### Example
```console
$> pkm repos add repo-name conda +channl=main
```

## Creating Your Own Repository
TODO: after api documentation will be uploaded