## Table Of Content
{:.no_toc}
 
* toc 
{:toc}

--- 
## Creating projects
--- 
## Project structure
--- 

## The <i str>"pyproject.toml"</i> file

`pkm` projects follows PEPs
[631](https://www.python.org/dev/peps/pep-0631/), [621](https://www.python.org/dev/peps/pep-0621/),
[517](https://www.python.org/dev/peps/pep-0517)
and [518](https://www.python.org/dev/peps/pep-0518). It reads the project configuration from the standard
<i str>"pyproject.toml"</i> file. `toml` is a fairly human-readable format, you can learn more about
it [here](https://toml.io/en/).

There are two main tables which contains the configuration relevant to pkm:

- The <i tag>[project]</i> table, holds the standard project's metadata
- The <i tag>[tool.pkm]</i> table, holds pkm-specific features configuration

### The <i tag>[project]</i> table

> ☝️️ The following documentation is based mainly on [PEP 621](https://www.python.org/dev/peps/pep-0621/), you may want to refer to it for further details.

<br>
The <i tag>[project]</i> section is the main section to configure your project metadata, since most of the values in
this section are self-explanatory, we will begin with an example ([source](https://www.python.org/dev/peps/pep-0621/)):

```toml
# pyproject.toml
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
```

<br>
<br>
Following, is a table containing a short explanation for the supported fields of this section:

<table>
    <tr>
        <th>Field</th> <th>Description</th>  
    </tr>

    <tr> 
        <td> name </td> 
        <td> The name of the project. </td>
    </tr>

    <tr> 
        <td> version </td> 
        <td> The version of the project as supported by [PEP 440](https://www.python.org/dev/peps/pep-0440) </td>
    </tr>

    <tr> 
        <td> description </td> 
        <td> The summary description of the project. </td>
    </tr>

    <tr> 
        <td> readme </td> 
        <td> 
            The field accepts either a string or a table. 
            
            If it is a string then it is the relative path to the project readme (rst or md). 
            
            If it is a table, the <i str> file </i> key accepts the relative path to the readme, 
            while the <i str> text </i> key accepts the actual description. 
            <i emp> These keys are mutually-exclusive </i>
        </td>
    </tr>

    <tr> 
        <td> requires-python </td> 
        <td> The Python version requirements of the project.</td>
    </tr>

    <tr> 
        <td> license </td> 
        <td> The field accepts a table, the <i str> file </i> key accepts the relative path to a license file.
             The <i str> text </i> key accepts a license identifier. <i emp> These keys are mutually exclusive </i>
        </td>
    </tr>

    <tr> 
        <td> authors/maintainers </td> 
        <td> Array of name+email tables holding the contact information for the authors and maintainers </td>
    </tr>
    
    <tr> 
        <td> keywords </td> 
        <td> Array of keywords for the project </td>
    </tr>

    <tr> 
        <td> classifiers </td> 
        <td> Array of <a href="https://pypi.org/classifiers/">Trove classifiers</a> 
             which apply to the project. 
        </td>
    </tr>

    <tr> 
        <td> urls </td> 
        <td> Table of name to url mapping </td>
    </tr>


    <tr> 
        <td> entry-points </td> 
        <td> Table which contains sub-tables for each of the project entrypoint's groups.
             Each of the entrypoints group table contains the project-provided name to 
             <a href="https://packaging.python.org/en/latest/specifications/entry-points/">entrypoint</a> mapping.
        </td>
    </tr>

    <tr> 
        <td> scripts </td> 
        <td> special entrypoints table that contains the <i str> 'console_scripts' </i> group of entrypoints </td>
    </tr>

    <tr> 
        <td> gui-scripts </td> 
        <td> special entrypoints table that contains the <i str> 'gui_scripts' </i> group of entrypoints </td>
    </tr>

    <tr> 
        <td> dependencies </td> 
        <td> Array of <a href="https://www.python.org/dev/peps/pep-0508">PEP 508</a> strings which represents 
             the dependencies of the project 
        </td>
    </tr>

    <tr> 
        <td> optional-dependencies </td> 
        <td> Table which contains arrays of dependencies for each of the project <i str>extra</i> dependencies. </td>
    </tr>

</table>

### The <i tag>[tool.pkm]</i> table

> 🚧 TODO, this is mainly a reference section, document after we have other sections to refer to 🚧

--- 

## Managing project dependencies

### install/remove

### Defining Repositories

### Package locking

Package locking is a mechanism that attempt to reduce package versioning dissimilarities on multi-user projects. It actually
sounds more complex than it is, Lets first try to understand the problem that it tries to solve using an example.
<br> <br>
Say that there are two developers working on your project - <i eg1>Alice</i> and <i eg2>Bob</i>. 

<i eg1>Alice</i> added a dependency to the project: <i str> "x >= 1.0.0" </i>, when installing it she got in her environment 
the package <i str> "x == 1.1.0" </i> (which satisfies the required dependency). Later this week, 
<i eg2>Bob</i> started to work and fetched <i str>"x == 1.1.1"</i> (which also satisfied the required dependency).

<i eg1> Alice </i> filled a bug which unknowingly, happens because of a behavior specific to  <i str> "x == 1.1.0" </i>. 
When <i eg2>Bob</i> tried to fix the bug he could not reproduce it, which of-course lead to both of them fighting and
not talking to each-other for more than a year.  

`pkm`'s Package locking mechanism stores the exact version of the package that was installed inside the file 
<i str> "etc/pkm/packages-lock.toml" </i> alongside other environment specific information. It then tries to use this information 
to reduce dissimilarities across the developers. Unlike many other package locking mechanisms, it takes into consideration 
the fact that different developers may work on totally different environments: they may have different operating systems or may 
use a different version of python, etc. Therefore, it is usable even on these scenarios.

`pkm` automatically updates <i str>"etc/pkm/packages-lock.toml"</i> when you install new dependencies, all you need to do
is to make sure that you commit this file to your version control system.

--- 

## Build & Publish

### Self-contained applications

--- 

## Running project tasks

--- 

## Project groups



