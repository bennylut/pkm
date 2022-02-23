# from pkm_torch_repository.cuda_compatibility import CudaCompatibilityTable
#
# print(CudaCompatibilityTable.load().compatible_cuda_versions())
from pkm.api.dependencies.dependency import Dependency
from pkm_torch_repository.cuda_compatibility import CudaCompatibilityTable
from pkm_torch_repository.torch_repository import TorchRepository

repo = TorchRepository('torch', True, CudaCompatibilityTable.load().compatible_cuda_versions())
matches = repo.match(Dependency.parse("torch"))
print(f"matches: {matches}")
