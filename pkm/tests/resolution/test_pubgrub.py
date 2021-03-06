from typing import Callable
from unittest import TestCase

from pkm.resolution.pubgrub import *


class TestSolver(TestCase):

    def test_cycle_dependency(self):
        problem = ExampleProblem({
            'root 1.0.0': ['root >=1.0.0'],
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0'}, solution)

    def test_exact_local_labels_version(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo ==1.0.0'],
            'foo 1.0.0+local': [],
            'foo 2.0.0': [],
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '1.0.0+local'}, solution)

    def test_range_local_labels_version(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo <=1.0.0+local'],
            'foo 1.0.0+local': [],
            'foo 1.0.0': [],
            'foo 2.0.0': [],
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '1.0.0+local'}, solution)

    def test_range_with_unrelated_local_involved_version(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo <=1.0.0'],
            'foo 1.0.0+local': [],
            'foo 1.0.0': [],
            'foo 2.0.0': [],
        })

        solution = Solver(problem).solve()
        assert_solution({'root': '1.0.0', 'foo': '1.0.0'}, solution)

    def test_url_versions(self):
        problem = ExampleProblem({
            'root 1.0.0': ['foo @http://foo', 'bar *'],
            'foo @http://foo': ['bar ==1.0.1'],
            'bar 1.0.1': ['foo ==1.0.0'],
        })

        # should fail because foo cannot be both url and standard version
        assert_failure(lambda: Solver(problem).solve())

        problem = ExampleProblem({
            'root 1.0.0': ['foo @http://foo', 'bar *'],
            'foo @http://foo': ['bar ==1.0.1'],
            'bar 1.0.1': [],
        })

        assert_solution({'root': "1.0.0", 'foo': "http://foo", 'bar': "1.0.1"}, Solver(problem).solve())

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

    # def test_error_reporting(self):
    #     # GOOD
    #     # problem = ExampleProblem({
    #     #     'root 1.0.0': ['foo ==1.0.0']
    #     # })
    #
    #     problem = ExampleProblem({
    #         'root 1.0.0': ['foo *'],
    #         'foo 1.0.0': ['bar ==1.0.0'],
    #         'foo 2.0.0': ['bar ==2.0.0'],
    #         'foo 3.0.0': ['bar ==2.0.0']
    #     })
    #
    #     Solver(problem).solve()


class ExampleProblem(Problem):

    def __init__(self, depency_graph: Dict[str, List[str]]):
        def parse_term(term: str):
            package_, constraint = term.split(' ', 2)
            return Term.create(package_, constraint)

        parsed_graph: Dict[str, Dict[str, List[Term]]] = defaultdict(lambda: defaultdict(list))
        for package, dependencies in depency_graph.items():
            p, v = package.split(' ', 2)
            parsed_graph[p][v].extend(parse_term(term) for term in dependencies)

        self._graph = parsed_graph

    def get_dependencies(self, package: str, version: Version) -> List[Term]:
        return self._graph[package][str(version)]

    def get_versions(self, package: str) -> List[StandardVersion]:
        result = [v for it in self._graph[package].keys() if isinstance(v := Version.parse(it), StandardVersion)]
        result.sort(reverse=True)
        return cast(List[StandardVersion], result)

    def has_version(self, package: PKG, version: Version) -> bool:
        return True


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
