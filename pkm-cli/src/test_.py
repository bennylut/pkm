from pkm.api.environments.environment import Environment

env = Environment.load("/home/bennyl/projects/pkm-new/workspace/test-env")
env.install("allennlp")
