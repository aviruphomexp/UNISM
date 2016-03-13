# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 17:20:26 2016

@author: avirup
"""


import networkx as nx
from gurobipy import *
#import random

TG=nx.DiGraph()
TG.add_node(0,name=1)
TG.add_node(1,name=2)
TG.add_node(2,name=3)
TG.add_node(3,name=4)
TG.add_node(4,name=5)

TG.add_edges_from([(0,1),(1,2),(0,3),(3,4)],volume=200)
TG.add_edge(2,4,volume=100)

NOC=nx.DiGraph()
NOC.add_node(0,name='a',exec_time={0:1,1:10,2:1,3:10,4:10},power=1)
NOC.add_node(1,name='b',exec_time={0:10,1:10,2:10,3:10,4:10},power=1)
NOC.add_node(2,name='c',exec_time={0:10,1:10,2:10,3:10,4:10},power=1)
NOC.add_node(3,name='d',exec_time={0:10,1:10,2:10,3:10,4:10},power=1)

NOC.add_edges_from([(0,1),(1,0),(0,2),(2,0),(2,3),(3,2)],cost_per_bit=0.01,latency=0.02)
NOC.add_edges_from([(1,3),(3,1)],cost_per_bit=0.02,latency=0.01)

w=[[1,10,10,10],[10,10,10,10],[1,10,10,10],[10,10,10,10],[10,10,10,10]]
#w=[[1,10,10,10],[10,1,10,10],[1,10,10,10],[10,10,1,10],[10,10,10,1]]
N=5
M=4

###########################################################################3
m=Model("UNISM")

#Add X_ij variables
X={i:{} for i in range(N)}
for i in range(N):
    for j in range(M):
        X[i][j]=m.addVar(vtype=GRB.BINARY,name='X_'+str(i)+'_'+str(j))
m.update()

#Add constraint (2)
for i in range(N):
    tc=LinExpr()
    tc.add(quicksum(X[i][j] for j in range(M)))
    m.addConstr(tc,GRB.EQUAL,1,'Task_Core_Constr_'+str(i))
m.update()
'''
#Add constraint to specify the max no of tasks on each core, which we set to 2 here
for j in range(M):
    my=LinExpr()
    my.add(quicksum(X[i][j] for i in range(N)))
    m.addConstr(my,GRB.LESS_EQUAL,2,'My_constr[for_each_core]_'+str(j))
m.update()
'''

#Calculate E_core
E_core=LinExpr()
E_core.add(quicksum(X[i][j]*w[i][j]*NOC.node[j]['power'] for j in range(M) for i in range(N)))


#Calculate h
h={}
for i in range(N):
    h[i]=LinExpr()
    h[i].add(quicksum(X[i][j]*w[i][j] for j in range(M)))
    
#Add t_i variables
t={}
for i in range(N):
    t[i]=m.addVar(vtype=GRB.INTEGER,name='t_'+str(i))
m.update()

#Add s_ij varibales
s={i:{} for i in range(N)}
for i in range(N):
    for j in range(N):
        s[i][j]=m.addVar(vtype=GRB.BINARY,name='s_'+str(i)+'_'+str(j))
m.update()

#Add constraint for "two tasks which are scheduled on the same core cannot be executed at the same time"
BigA=100
BigAsqr=100**2

for i in range(N):
    for j in range(i+1,N):
        f=LinExpr()
        #f.add(t[i]+h[i]-t[j]+BigAsqr*s[i][j])
        f.add(BigAsqr*s[i][j])
        f.add(quicksum(k*X[i][k]*BigA for k in range(M)))
        f.add(-quicksum(k*X[j][k]*BigA for k in range(M)))
        m.addConstr(f+t[i]+h[i]-t[j],GRB.LESS_EQUAL,BigAsqr,'Task_Schedule[0]_'+str(i)+'_'+str(j))
        f=LinExpr()
        #f.add(t[j]+h[j]-t[i]-BigAsqr*s[i][j])
        f.add(-BigAsqr*s[i][j])
        f.add(quicksum(k*X[j][k]*BigA for k in range(M)))
        f.add(-quicksum(k*X[i][k]*BigA for k in range(M)))
        m.addConstr(f+t[j]+h[j]-t[i],GRB.LESS_EQUAL,0,'Task_Schedule[1]_'+str(i)+'_'+str(j))
        
m.update()

#Add Y_ij variables
Y={i:{} for i in range(M)}
for i in range(M):
    for j in range(M):
        Y[i][j]=m.addVar(vtype=GRB.BINARY,name='Y_'+str(i)+'_'+str(j))
m.update()

#Add constraint (5)
for i in range(M):
    ct=LinExpr()
    ct.add(quicksum(Y[i][j] for j in range(M)))
    m.addConstr(ct,GRB.EQUAL,1,'Core_Tile_Constr[for_each_core]_'+str(i))
m.update()

for j in range(M):
    ct=LinExpr()
    ct.add(quicksum(Y[i][j] for i in range(M)))
    m.addConstr(ct,GRB.EQUAL,1,'Core_Tile_Constr[for_each_tile]_'+str(j))
m.update()

#Add Z_ij variables
Z={i:{} for i in range(N)}
for i in range(N):
    for j in range(M):
        Z[i][j]=m.addVar(vtype=GRB.BINARY,name='Z_'+str(i)+'_'+str(j))
m.update()

#Add quadratic constraint Z_ij= sum (X_ik * Y_kj)
for i in range(N):
    for j in range(M):
        f=QuadExpr()
        f.add(quicksum(X[i][k]*Y[k][j] for k in range(M)))
        m.addConstr(Z[i][j],GRB.EQUAL,f,'Constraint_Z_'+str(i)+'_'+str(j))
m.update()
'''
#Add constraint (8)
for i in range(N):
    f=LinExpr()
    f.add(quicksum(Z[i][j] for j in range(M)))
    m.addConstr(f,GRB.EQUAL,1,'Task_Tile_Constr_'+str(i))
    
m.update()
'''
#Generate shortest paths for communication cost
E_c=nx.floyd_warshall(NOC,'cost_per_bit')

#Frame quadratic expression for e_ij
e={}
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    if i not in e:
        e[i]={}
    e[i][j]=QuadExpr()
    e[i][j].add(quicksum(Z[i][m]*Z[j][n]*E_c[m][n] for m in range(M) for n in range(M)))
    
#Calculate E_com
E_com=QuadExpr()
E_com.add(quicksum(TG.edge[i][j]['volume']*e[i][j] for (i,j) in TG.edges()))

#Generate shortest paths for latency
L_c=nx.floyd_warshall(NOC,'latency')

#Frame quadratic expression for l_ij
l={}
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    if i not in l:
        l[i]={}
    l[i][j]=QuadExpr()
    l[i][j].add(quicksum(Z[i][m]*Z[j][n]*L_c[m][n] for m in range(M) for n in range(M)))

'''
#Modify l_ij to ldash_ij
#Model n_ij

n={}
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    f=QuadExpr()
    f.add(quicksum(Z[i][m]*Z[j][l]*nx.dijkstra_path_length(NOC,m,l) for m in range(M) for l in range(M)))
    if i not in n:
        n[i]={}
    n[i][j]=f
    
beta=0.2
gamma=0.2
cMAX=max(TG.edge[e[0]][e[1]]['volume'] for e in TG.edges_iter())
nMAX=max(nx.dijkstra_path_length(NOC,i,j) for i in range(M) for j in range(M))
ldash={}
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    if i not in ldash:
        ldash[i]={}
    
    ldash[i][j]=l[i][j]*(1+beta*TG.edge[i][j]['volume']/cMAX)*(1+gamma*n[i][j]/nMAX)
''' 

#Add constraint (17)
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    m.addConstr(t[j],GRB.GREATER_EQUAL,t[i]+h[i]+TG.edge[i][j]['volume']*l[i][j],'Data_dependency_'+str(i)+'_'+str(j))
m.update()

#Model T
T=m.addVar(vtype=GRB.CONTINUOUS,name='T')
m.update()

#Add constraints for T>=t_i+h_i
for i in range(N):
    m.addConstr(T,GRB.GREATER_EQUAL,t[i]+h[i],'Total_time_'+str(i))

m.update()


#Set objective fucntion
m.setObjective(1*E_core+1*E_com+1*T,GRB.MINIMIZE)
m.update()
m.optimize()
m.write('test.lp')
m.write('test.sol')

    
