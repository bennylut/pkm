from pathlib import Path

import sass
from sphinx.application import Sphinx


def compile_scss(spx: Sphinx, _):
    input_path = Path(spx.project.srcdir) / spx.config.scss_dir
    output_path = Path(spx.outdir)
    if static_paths := spx.config.html_static_path:
        output_path = output_path / static_paths[0]

    assert input_path.exists(), f"input directory could not be found: {input_path}"
    output_path.mkdir(exist_ok=True, parents=True)

    print(f"Generating scss from {input_path} to {output_path}")
    sass.compile(dirname=(str(input_path), str(output_path)), output_style="compressed")


def setup(spx: Sphinx):
    spx.add_config_value('scss_dir', '_scss', 'html')
    spx.connect('build-finished', compile_scss)
    return dict(parallel_read_safe=True)
