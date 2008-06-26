# 01.06.2007, c
# last revision: 25.02.2008

fileName_mesh = 'database/tests/small2d.mesh'

material_1 = {
    'name' : 'coef',
    'mode' : 'here',
    'region' : 'Omega',
    'coef' : 1.0,
}

region_1000 = {
    'name' : 'Omega',
    'select' : 'all',
}
region_1 = {
    'name' : 'Left',
    'select' : 'nodes in (x < -0.499)',
}
region_2 = {
    'name' : 'Right',
    'select' : 'nodes in (x > 0.499)',
}
region_22 = {
    'name' : 'Bottom',
    'select' : 'nodes in (y < -0.499)'
}
region_23 = {
    'name' : 'Top',
    'select' : 'nodes in (y > 0.499)'
}

field_1 = {
    'name' : '2_displacement',
    'dim' : (2,1),
    'flags' : (),
    'domain' : 'Omega',
    'bases' : {'Omega' : '2_3_P2'}
}

field_2 = {
    'name' : 'pressure',
    'dim' : (1,1),
    'flags' : (),
    'domain' : 'Omega',
    'bases' : {'Omega' : '2_3_P1'}
}

variable_1 = {
    'name' : 'u',
    'kind' : 'unknown field',
    'field' : '2_displacement',
    'order' : 0,
}
variable_2 = {
    'name' : 'v',
    'kind' : 'test field',
    'field' : '2_displacement',
    'dual' : 'u',
}
variable_3 = {
    'name' : 'p',
    'kind' : 'unknown field',
    'field' : 'pressure',
    'order' : 1,
}
variable_4 = {
    'name' : 'q',
    'kind' : 'test field',
    'field' : 'pressure',
    'dual' : 'p',
}

ebcs = {}
epbc_10 = {
    'name' : 'rl',
    'region' : ['Left', 'Right'],
    'dofs' : {'u.all' : 'u.all', 'p.0' : 'p.0'},
    'match' : 'matchYLine',
}
epbc_12 = {
    'name' : 'tb',
    'region' : ['Top', 'Bottom'],
    'dofs' : {'u.all' : 'u.all', 'p.0' : 'p.0'},
    'match' : 'matchXLine',
}

fe = {
    'chunkSize' : 1000
}

from sfepy.fem.periodic import *
from sfepy.base.testing import TestCommon

##
# 01.06.2007, c
class Test( TestCommon ):

    ##
    # 01.06.2007, c
    def fromConf( conf, options ):
        from sfepy.fem.problemDef import ProblemDefinition
        problem = ProblemDefinition.fromConf( conf, initEquations = False )

        test = Test( problem = problem,
                     conf = conf, options = options )
        return test
    fromConf = staticmethod( fromConf )

    ##
    # c: 01.06.2007, r: 18.02.2008
    def test_pbc( self ):
        problem  = self.problem
        conf = self.conf
        
        problem.variables.equationMapping( conf.ebcs, conf.epbcs,
                                           problem.domain.regions,
                                           None, conf.funmod )
        state = problem.createStateVector()
        problem.applyEBC( state )
        return problem.variables.hasEBC( state )
