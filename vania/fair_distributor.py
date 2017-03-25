"""
This module allows fair distribution of any number of **objects** through a group of **targets**.
By means of a linear programming solver, the module takes into consideration the **weights**/self._weights of the **targets** relative to the **objects**.
and distributes them in the **fairest way possible**.
"""
from pulp import *
from itertools import dropwhile


class FairDistributor:

    """
    This class represents a general fair distributor.
    Objects of this class allow solving fair distribution problems.
    """

    def __init__(self, targets=[], objects=[], weights=[]):
        """
        This constructor is simply a way to simplify the flow of solving a problem.
        """
        self.set_data(targets, objects, weights)

    def set_data(self, targets, objects, weights):
        """
        This method is a general setter for the data associated with the problem.
        Data is being validated by the validator method.
        """
        self._targets = targets
        self._objects = objects
        self._weights = weights

    def validate(self):
        """
        This method validates the current data.
        """
        try:
            self._validate()
            return True
        except ValueError:
            return False

    def _validate(self):
        if len(self._weights) != len(self._targets):
            raise ValueError(
                "The number of lines on the weights should match the targets' length")

        # All values should be positive
        s = list(
            dropwhile(lambda x: len(x) == len(self._objects), self._weights))
        if len(s) != 0:
            raise ValueError(
                "The number of columns on the weights should match the objects' length")
        for lines in self._weights:
            for i in lines:
                if i < 0:
                    raise ValueError(
                        "All values on the weights should be positive")

    def distribute(self, fairness=True, output=None):
        """
        This method is responsible for actually solving the linear programming problem.
        It uses the data in the instance variables.
        The optional parameter **fairness** indicates if the solution should minimize individual effort. By default the solution will enforce this condition.
        """

        # State problem
        problem = LpProblem("Fair Distribution Problem", LpMinimize)

        # Prepare variables
        targets_objects = {}
        for (t, target) in enumerate(self._targets):
            for (o, object) in enumerate(self._objects):
                variable = LpVariable(
                    'x' + str(t) + str(o), lowBound=0, cat='Binary')
                position = {'target': t, 'object': o}
                targets_objects['x' + str(t) + str(o)] = (variable, position)

        # Generate linear expression for self._weights (Summation #1)
        weights = [(variable, self._weights[weight_position['target']][weight_position['object']])
                   for (variable, weight_position) in targets_objects.values()]
        weight_expression = LpAffineExpression(weights)

        # Generate linear expression for effort distribution (Summation #2)
        weight_diff_vars = []
        if fairness:
            total_targets = len(self._targets)
            for (t, target) in enumerate(self._targets):
                weight_diff_aux_variable = LpVariable(
                    'weight_diff_'+str(t), lowBound=0)
                weight_diff_vars.append(weight_diff_aux_variable)

                negative_factor = -1 * total_targets
                negative_effort_diff = LpAffineExpression(
                    [(targets_objects['x' + str(t) + str(o)][0], negative_factor *
                      self._weights[t][o]) for (o, object) in enumerate(self._objects)]
                ) + weight_expression
                positive_factor = 1 * total_targets

                positive_effort_diff = LpAffineExpression(
                    [(targets_objects['x' + str(t) + str(o)][0], negative_factor *
                      self._weights[t][o]) for (o, object) in enumerate(self._objects)]
                ) - weight_expression

                problem += negative_effort_diff <= weight_diff_aux_variable, 'abs negative effort diff ' + \
                    str(t)
                problem += positive_effort_diff <= weight_diff_aux_variable, 'abs positive effort diff ' + \
                    str(t)

        # Constraints - Each task must be done
        objects_constraints = [lpSum([targets_objects['x' + str(t) + str(o)][0] for (t, target)
                                      in enumerate(self._targets)]) for (o, object) in enumerate(self._objects)]
        for (oc, object_constraint) in enumerate(objects_constraints):
            problem += object_constraint == 1, 'Task ' + \
                str(oc) + ' must be done'

        # Set objective function
        problem += weight_expression + \
            lpSum(weight_diff_vars), "obj"

        if output:
            problem.writeLP(output)

        problem.solve()

        # Build output
        data = {}
        for v in filter(lambda x: x.varValue > 0, problem.variables()):
            if v.name not in targets_objects:
                continue
            position = targets_objects[v.name][1]
            target = self._targets[position['target']]
            object = self._objects[position['object']]

            if target not in data:
                data[target] = []

            data[target].append(object)

        return data
