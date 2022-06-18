from __future__ import annotations

import ast
import hashlib
import importlib.util as iu
import os
import re
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from functools import reduce
from pathlib import Path
from typing import Optional, Dict, List, Union, Iterable, Callable, Any, cast

from sphinx.application import Sphinx
from sphinx.util.rst import escape

TypeID = str
_DOC_PARAM_RX = re.compile(":param [^:]+:.*")
BUILD_API_LIST_CONFIG_KEY = 'build_apis'

# just force they type checker to ignore input type to this function 
ast_unparse = cast(Callable[[Any], str], ast.unparse)


class TypesLookup:
    def __init__(self):
        self.id2type = {}

    def add_import(self, imp: Union[ast.ImportFrom, ast.Import]):
        if isinstance(imp, ast.ImportFrom):
            for alias in imp.names:
                self.id2type[alias.asname or alias.name] = f"{imp.module}.{alias.name}"
        elif isinstance(imp, ast.Import):
            for alias in imp.names:
                self.id2type[alias.asname or alias.name] = alias.name
        else:
            raise ValueError(f"unsupported type: {imp}")

    def resolve_type(self, type_: str):
        package, dot, name = type_.partition(".")
        if dot:
            return self.id2type.get(package, package) + "." + name
        else:
            return self.id2type.get(type_, type_)


@dataclass
class FieldDoc:
    name: str
    definition: str
    type: Optional[TypeID]

    @classmethod
    def parse(cls, node: Union[ast.AnnAssign, ast.Assign]) -> List[FieldDoc]:
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if isinstance(target, ast.Tuple):
                # noinspection PyUnresolvedReferences
                return [FieldDoc(ast_unparse(t), f"{ast_unparse(t)} = {ast_unparse(v)}", None)
                        for t, v in zip(target.elts, node.value.elts)]
            return [FieldDoc(ast_unparse(target), ast_unparse(node), None)]
        return [FieldDoc(ast_unparse(node.target), ast_unparse(node), ast_unparse(node.annotation))]


@dataclass
class ArgumentDoc:
    name: str
    type: Optional[TypeID]
    default: Optional[str]
    variadic: Optional[str] = None  # None, 'vararg', 'kwarg'

    def __str__(self):
        result = "*" if self.variadic else ""
        if self.variadic == "kwarg":
            result = "**"

        result += self.name
        if self.type:
            result += f": {self.type}"
        if self.default:
            result += f" = {self.default}"

        return result

    @classmethod
    def parse_for(cls, fdef: ast.FunctionDef) -> List[str, ArgumentDoc]:
        result_args: List[Union[str, ArgumentDoc]] = []

        args = fdef.args
        defaults: List[Optional[str]] = [None] * (
                len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
                - len(args.defaults) - len(args.kw_defaults))

        defaults.extend(ast_unparse(v) if v else None for v in args.defaults)
        defaults.extend(ast_unparse(v) if v else None for v in args.kw_defaults)
        defaults.reverse()

        # noinspection PyTypeChecker
        def annotation(a: ast.arg) -> Optional[str]:
            return ast_unparse(a.annotation) if a.annotation else None

        if args.posonlyargs:
            result_args.extend(
                ArgumentDoc(it.arg, annotation(it), defaults.pop())
                for it in args.posonlyargs)
            result_args.append("/")

        result_args.extend(ArgumentDoc(it.arg, annotation(it), defaults.pop()) for it in args.args)

        if args.kwonlyargs:
            result_args.append("*")
            result_args.extend(
                ArgumentDoc(it.arg, annotation(it), defaults.pop())
                for it in args.kwonlyargs)

        if it := args.vararg:
            result_args.append(ArgumentDoc(it.arg, annotation(it), None, "vararg"))

        if it := args.kwarg:
            result_args.append(ArgumentDoc(it.arg, annotation(it), None, "kwarg"))

        return result_args


@dataclass
class FuncDoc:
    name: str
    decorators: List[str]
    arguments: List[Union[str, ArgumentDoc]]
    returns: Optional[TypeID]
    doc: DocString

    @classmethod
    def parse(cls, fdef: ast.FunctionDef) -> FuncDoc:
        return FuncDoc(
            fdef.name, [ast_unparse(it) for it in fdef.decorator_list], ArgumentDoc.parse_for(fdef),
            ast_unparse(fdef.returns) if fdef.returns else None, DocString.parse(ast.get_docstring(fdef) or "")
        )

    def _build_signature(self):
        result: List[str] = ["def ", self.name, "("]
        result_args: List[str] = []

        current_line_length = sum(len(it) for it in result)

        for arg in self.arguments:
            arg_str = str(arg)
            to_write = arg_str
            if current_line_length + len(arg_str) > 77:  # pep8 + ', '
                to_write = "\n    " + arg_str
                current_line_length = 4

            result_args.append(to_write)
            current_line_length += len(arg_str) + 2

        result.append(', '.join(result_args))
        result.append(")")

        if self.returns:
            result.append(" -> ")
            result.append(self.returns)

        prefix = ""
        if self.decorators:
            prefix = '\n'.join(f"@{it}" for it in self.decorators) + "\n"
        return prefix + ''.join(result)

    def write_to(self, rst: RstBuilder):
        rst.codeblock(
            "python", self._build_signature())

        self.doc.write_to(rst)
        if self.arguments:
            with rst.section("Arguments"):
                rst.args_table((it for it in self.arguments if isinstance(it, ArgumentDoc)), self.doc)

        if self.doc.returns:
            with rst.section("Returns"):
                rst.paragraph(self.doc.returns[len(":return:"):].strip())


@dataclass
class ClassDoc:
    name: str
    bases: List[TypeID]
    decorators: List[str]
    docstr: DocString
    methods: List[FuncDoc]

    @classmethod
    def parse(cls, cdef: ast.ClassDef):
        methods = []
        for node in cdef.body:
            if isinstance(node, ast.FunctionDef):
                methods.append(FuncDoc.parse(node))

        methods = [m for m in methods if not m.name.startswith("_")]

        return ClassDoc(
            cdef.name, [ast_unparse(it) for it in cdef.bases], [ast_unparse(it) for it in cdef.decorator_list],
            DocString.parse(ast.get_docstring(cdef, True) or ""), methods
        )

    @property
    def signature(self) -> str:
        signature = f"class {self.name}"
        if self.bases:
            signature += "(" + ', '.join(self.bases) + ")"

        return signature

    def write_to(self, rst: RstBuilder):
        with rst.section(self.name + " (Class)"):
            signature = ""
            if self.decorators:
                signature = '\n'.join(f"@{it}" for it in self.decorators) + "\n"
            signature += self.signature

            rst.codeblock("python", signature)

            with rst.section("Class Methods"):
                first = True
                for m in self.methods:
                    if first:
                        first = False
                    else:
                        rst.hr()

                    m.write_to(rst)


@dataclass
class ModuleDoc:
    name: str
    doc: DocString
    functions: List[FuncDoc]
    fields: List[FieldDoc]
    classes: List[ClassDoc]
    types: TypesLookup

    @classmethod
    def parse(cls, name: str, mdef: ast.Module) -> ModuleDoc:
        fields: List[FieldDoc] = []
        functions: List[FuncDoc] = []
        classes: List[ClassDoc] = []
        types = TypesLookup()

        doc = DocString.parse(ast.get_docstring(mdef, True) or "")

        for node in mdef.body:
            if isinstance(node, (ast.AnnAssign, ast.Assign)):
                fields.extend(FieldDoc.parse(node))
            elif isinstance(node, ast.FunctionDef):
                functions.append(FuncDoc.parse(node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                types.add_import(node)
            elif isinstance(node, ast.ClassDef):
                classes.append(ClassDoc.parse(node))

        # remove private members
        fields = [f for f in fields if not f.name.startswith("_")]
        functions = [f for f in functions if not f.name.startswith("_")]
        classes = [c for c in classes if not c.name.startswith("_")]

        return ModuleDoc(name, doc, functions, fields, classes, types)

    def write_to(self, rst: RstBuilder):
        with rst.section(self.name + " (Module)"):

            with rst.section("Module Fields"):
                if self.fields:
                    rst.codeblock("python", '\n'.join(f.definition for f in self.fields))
                else:
                    rst.paragraph("No fields defined in module.")

            if self.functions:
                with rst.section("Module Functions"):
                    first = True
                    for function in self.functions:
                        if first:
                            first = False
                        else:
                            rst.hr()

                        function.write_to(rst)

            if self.classes:
                with rst.section("Module Classes"):
                    for class_ in self.classes:
                        with rst.container('class-def-with-link'):
                            rst.lines(f":doc:`[DOC] <{self.name}.{class_.name}>`", "")
                            rst.codeblock("python", class_.signature)

            return self


@dataclass
class DocString:
    desc: str
    params: Dict[str, str]
    returns: str

    def write_to(self, rst: RstBuilder):
        with rst.section("Description"):
            if self.desc:
                rst.paragraph(self.desc)
            else:
                rst.paragraph("Not Documented")

    @classmethod
    def parse(cls, docstr: str) -> DocString:
        lines: List[str] = docstr.splitlines(keepends=False)

        desc, params, returns, junk = [], [], [], []
        output = desc

        for line in lines:
            stripped = line.strip()
            if _DOC_PARAM_RX.match(stripped):
                output = params
            elif stripped.startswith(":return:"):
                output = returns
            elif stripped.startswith(":"):
                output = junk

            output.append(stripped)

        parsed_params = {}
        params.reverse()
        while params:
            param: str = params.pop()
            name, _, pdesc = param[len(":param "):].partition(':')
            while params and not _DOC_PARAM_RX.match(params[-1]):
                pdesc += ' ' + params.pop()

            parsed_params[name] = pdesc

        return DocString('\n'.join(desc), parsed_params, '\n'.join(returns))


class RstBuilder:
    def __init__(self):
        self._lines = []
        self._level = 0
        self._indent = 0

    @contextmanager
    def section(self, title: str):
        tchars = "#=-^~*"
        self.title(title, tchars[self._level])
        self._level += 1
        yield
        self._level -= 1

    @contextmanager
    def indent(self):
        self._indent += 1
        yield
        self._indent -= 1

    def comment(self, comment: str) -> RstBuilder:
        return self.lines("..", *(f"    {line.strip()}" for line in comment.splitlines()), "")

    def directive(
            self, name: str, arg: Optional[str] = None, options: Optional[Dict[str, Optional[str]]] = None,
            body: Optional[str] = None) -> RstBuilder:

        arg_str = arg or ""
        self.line(f"..\t{name}:: {arg_str}")
        with self.indent():
            if options:
                for k, v in options.items():
                    if v is not None:
                        self.line(f":{k}: {v}")
                    else:
                        self.line(f":{k}:")

            self.line("")
            if body:
                self.paragraph(body)

        return self

    def hr(self) -> RstBuilder:
        return self.lines("-----------------------", "")

    def args_table(self, args: Iterable[ArgumentDoc], doc: DocString) -> RstBuilder:
        body = ["Name", "Type", "Description"]
        for arg in args:
            body.extend((arg.name, arg.type or "Any", doc.params.get(arg.name) or "No Description"))

        prx = ["*   -   ", "    -   ", "    -   "]
        body_str = '\n'.join(prx[i % 3] + it for i, it in enumerate(body))

        self.rst_class("args-table")

        self.directive("list-table", options={
            'widths': 'auto',
            'header-rows': 1
        }, body=body_str)

        return self

    def hash_marker(self, hash_hex: str) -> RstBuilder:
        return self.comment(f"HASH:{hash_hex}")

    def line(self, line: str) -> RstBuilder:
        self._lines.append('    ' * self._indent + line)
        return self

    def lines(self, *lines: str) -> RstBuilder:
        for line in lines:
            self.line(line)
        return self

    def paragraph(self, txt: str) -> RstBuilder:
        return self.lines(*txt.splitlines(keepends=False), "")

    def title(self, title: str, marker_char: str = "=") -> RstBuilder:
        etitle = escape(title)
        return self.lines(etitle, marker_char * len(etitle), "")

    def toctree(self, caption: str, entries: Dict[str, str]) -> RstBuilder:
        body = '\n'.join(f"{title} <{file}>" for title, file in entries.items())
        options = {"titlesonly": None}
        if caption:
            options["caption"] = caption

        return self.directive("toctree", options=options, body=body)

    def rst_class(self, name: str) -> RstBuilder:
        return self.directive("rst-class", name)

    def codeblock(self, language: str, code: str) -> RstBuilder:
        return self.directive("code-block", language, body=code)

    @contextmanager
    def container(self, rst_class: str):
        self.directive("container", rst_class)
        with self.indent():
            yield

    def save(self, file: Path):
        file.write_text(os.linesep.join(self._lines))


def _bytes_xor(a: bytes, b: bytes) -> bytes:
    return bytes(i ^ j for i, j in zip(a, b))


class APIGenerator:
    def __init__(self):
        self._hashmem: Dict[Path, bytes] = {}

    def _source_hash(self, source: Path):
        init = bytes(16)
        if not (result := self._hashmem.get(source)):
            if source.is_dir():
                result = reduce(_bytes_xor, (self._source_hash(child) for child in source.rglob("*.py")), init)
            else:
                result = hashlib.md5(source.read_text().encode()).digest()

            self._hashmem[source] = result

        return result

    # noinspection PyMethodMayBeStatic
    def _requires_rebuild(self, file: Path, new_hash_hex: str):
        if file.exists():
            if (before := file.read_text().strip().splitlines()) and len(before) > 1:
                header, sep, hash_ = before[1].strip().partition(':')
                if header == 'HASH' and hash_ == new_hash_hex:
                    return False
            print(f"rebuilding source doc: {file}")
        return True

    def _generate_module(self, module_name: str, source: Path, target_dir: Path) -> List[Path]:
        output = (target_dir / f"{module_name}.rst")
        generated_files = [output]
        module_hash_hex = self._source_hash(source).hex()

        if self._requires_rebuild(output, module_hash_hex):

            try:
                module_ast: ast.Module = ast.parse(source.read_text())
            except Exception as e:  # noqa
                warnings.warn(f"could not parse {module_name} - {e}")
                return []

            module_doc = ModuleDoc.parse(module_name, module_ast)

            module_rst = RstBuilder().hash_marker(module_hash_hex)
            module_doc.write_to(module_rst)
            module_rst.save(output)

            for class_ in module_doc.classes:
                class_output = (target_dir / f"{module_name}.{class_.name}.rst")
                class_rst = RstBuilder()
                class_rst.lines(":orphan:", "")
                class_.write_to(class_rst)
                class_rst.save(class_output)
                generated_files.append(class_output)
        else:
            generated_files.extend(target_dir.glob(f"{module_name}.*"))

        return generated_files

    def _generate_pacakge(self, package_name: str, source: Path, target_dir: Path) -> List[Path]:
        output = (target_dir / f"{package_name}.rst")
        package_hash_hex = self._source_hash(source).hex()

        if self._requires_rebuild(output, package_hash_hex):

            rst = RstBuilder().hash_marker(package_hash_hex).title(package_name + " (Package)", '=')

            if (init_source := source / "__init__.py").exists() and init_source.read_text().strip():
                module_ast: ast.Module = ast.parse(init_source.read_text())
                module_doc = ModuleDoc.parse(package_name, module_ast)
                module_doc.write_to(rst)

            modules, packages = [], []
            for child in source.iterdir():
                if child.name.startswith("_"):
                    continue
                if child.is_dir():
                    packages.append(child)
                elif child.suffix == ".py":
                    modules.append(child)

            if modules:
                rst.title("Modules", "-") \
                    .rst_class("child-modules") \
                    .toctree("", {m.stem: f"{package_name}.{m.stem}.rst" for m in modules})

            if packages:
                rst.title("Packages", "-") \
                    .rst_class("child-packages") \
                    .toctree("", {p.name: f"{package_name}.{p.name}.rst" for p in packages})

            rst.save(output)

        return [output]

    def _sync(self, base_dir: Path, source: Path, target_dir: Path):
        target_dir.mkdir(exist_ok=True, parents=True)
        elements = set()
        generated_files = set()

        def _build(element: Path):
            if element.name.startswith("_") or (not element.is_dir() and element.suffix != '.py'):
                return

            qn = '.'.join(element.relative_to(base_dir).with_suffix("").parts)
            elements.add(qn)

            if element.is_dir():
                generated_files.update(self._generate_pacakge(qn, element, target_dir))
                for child in element.iterdir():
                    _build(child)
            else:
                generated_files.update(self._generate_module(qn, element, target_dir))

        _build(source)
        for file in target_dir.iterdir():
            if file not in generated_files:
                file.unlink()

    @staticmethod
    def path_for(package: str) -> Optional[Path]:
        spec = iu.find_spec(package)

        if spec.submodule_search_locations:
            return Path(spec.submodule_search_locations[0])
        return None

    def sync(self, package_name: str, target_dir: Path):
        package_path = self.path_for(package_name)

        if not package_path:
            print(f"Not a package: {package_name}, will not generate documentation")
        else:
            base_dir = reduce(lambda x, _: x.parent, range(package_name.count(".") + 1), package_path)
            self._sync(base_dir, package_path, target_dir)


def generate(spx: Sphinx, *_, **__):
    output_directory = Path(spx.srcdir) / "apis"
    apigen = APIGenerator()

    for api in getattr(spx.config, BUILD_API_LIST_CONFIG_KEY):
        print(f"Generating api documentation for {api}")
        api_output_directory = output_directory / api
        api_output_directory.mkdir(exist_ok=True, parents=True)

        apigen.sync(api, api_output_directory)


def setup(spx: Sphinx):
    spx.setup_extension('sphinx.ext.autodoc')
    spx.connect('env-before-read-docs', generate)
    spx.add_config_value(BUILD_API_LIST_CONFIG_KEY, [], True)
    return dict(parallel_read_safe=True)
