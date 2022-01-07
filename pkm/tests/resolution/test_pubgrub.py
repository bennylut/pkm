from typing import Callable
from unittest import TestCase

from pkm.resolution.pubgrub import *


class TestSolver(TestCase):

    def test_star_version(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo *'],
            'foo 1.0.0': [],
            'foo 2.0.0': [],
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '2.0.0'}, solution)

    def test_no_conflict(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo ~=1.0.0'],
            'foo 1.0.0': ['bar ~=1.0.0'],
            'bar 1.0.0': [],
            'bar 2.0.0': []
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '1.0.0', 'bar': '1.0.0'}, solution)

    def test_avoiding_conflict_during_decision_making(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo ~=1.0', 'bar ~=1.0'],
            'foo 1.1.0': ['bar ~=2.0'],
            'foo 1.0.0': [],
            'bar 1.0.0': [],
            'bar 1.1.0': [],
            'bar 2.0.0': []
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '1.0.0', 'bar': '1.1.0'}, solution)

    def test_performing_conflict_resolution(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo >=1.0.0'],
            'foo 2.0.0': ['bar ~=1.0'],
            'foo 1.0.0': [],
            'bar 1.0.0': ['foo ~=1.0'],
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '1.0.0'}, solution)

    def test_conflict_resolution_with_partial_satisfier(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo ~=1.0', 'target ~=2.0'],
            'foo 1.1.0': ['left ~=1.0', 'right ~=1.0'],
            'foo 1.0.0': [],
            'left 1.0.0': ['shared >=1.0.0'],
            'right 1.0.0': ['shared <2.0.0'],
            'shared 2.0.0': [],
            'shared 1.0.0': ['target ~=1.0'],
            'target 2.0.0': [],
            'target 1.0.0': [],
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '1.0.0', 'target': '2.0.0'}, solution)

    def test_linear_error_reporting(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo ~=1.0', 'baz ~=1.0'],
            'foo 1.0.0': ['bar ~=2.0'],
            'foo 1.1.0': ['bar ~=2.0'],  # mod
            'foo 1.2.0': ['bar ~=2.0'],  # mod
            'bar 2.0.0': ['baz ~=3.0'],
            'baz 1.0.0': [],
            'baz 3.0.0': [],
        })

        assert_failure(lambda: Solver(problem).solve())

    def test_branching_error_reporting(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo ~=1.0'],
            'foo 1.0.0': ['a ~=1.0', 'b ~=1.0'],
            'foo 1.1.0': ['x ~=1.0', 'y ~=1.0'],
            'a 1.0.0': ['b ~=2.0'],
            'b 1.0.0': [],
            'b 2.0.0': [],
            'x 1.0.0': ['y ~=2.0'],
            'y 1.0.0': [],
            'y 2.0.0': [],
        })

        assert_failure(lambda: Solver(problem).solve())


class ExampleProblem(Problem):

    def __init__(self, depency_graph: Dict[str, List[str]]):
        def parse_term(term: str):
            package, constraint = term.split(' ', 2)
            return Term.create(package, constraint)

        parsed_graph: Dict[str, Dict[str, List[Term]]] = defaultdict(lambda: defaultdict(list))
        for package, dependencies in depency_graph.items():
            p, v = package.split(' ', 2)
            parsed_graph[p][v].extend(parse_term(term) for term in dependencies)

        self._graph = parsed_graph

    def get_dependencies(self, package: str, version: Version) -> List[Term]:
        return self._graph[package][str(version)]

    def get_versions(self, package: str) -> List[Version]:
        result = [Version.parse(it) for it in self._graph[package].keys()]
        result.sort(reverse=True)
        return result


def assert_solution(expected: Dict[str, str], solution: Dict[str, Version]):
    assert len(expected) == len(solution), \
        f'expected {expected} and solution {solution}, does not have the same length'

    for k, v in expected.items():
        assert k in solution, f"solution {solution} missing expected key {k}"
        assert str(solution[k]) == v, f"resolved version {k}={solution[k]} is different than expected: {v}"


def assert_failure(runner: Callable[[], Any]):
    try:
        runner()
        assert True, "Expecting, solution failure but somehow solver found a solution"
    except:  # noqa
        ...
