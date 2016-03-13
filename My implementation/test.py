from gurobipy import *

m=Model("mpil")

x=m.addVar(vtype=GRB.BINARY,name="x")
y=m.addVar(vtype=GRB.BINARY,name="y")
z=m.addVar(vtype=GRB.BINARY,name="z")

m.update()

m.setObjective(x+y+2*z,GRB.MAXIMIZE)

m.addConstr(x+2*y+3*z<=4,"c0")
m.addConstr(x+y>=1,"c1")

m.optimize()

m.printAttr('X')

import networkx as nx

G=nx.read_graphml('NOC.xml.gz')