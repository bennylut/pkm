from pathlib import Path

from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor
from pkm.api.versions.version import Version
from pkm.distributions.source_distribution import SourceDistribution
from pkm.api.pkm import pkm

env = Environment(Path('/home/bennyl/projects/pkm-new/workspace/env-zoo/envs/yyy'))

SourceDistribution(PackageDescriptor('poetry-core', Version.parse('1.0.0')),
                   Path('/home/bennyl/projects/pkm-new/workspace/tmp/poetry-core')).install_to(env, pkm.repositories.pypi)
