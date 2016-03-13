# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 12:20:40 2016

@author: Avirup
"""

import networkx as nx
from gurobipy import *
import random

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

#Add constraint to specify the max no of tasks on each core, which we set to 2 here
for j in range(M):
    my=LinExpr()
    my.add(quicksum(X[i][j] for i in range(N)))
    m.addConstr(my,GRB.LESS_EQUAL,2,'My_constr[for_each_core]_'+str(j))
m.update()


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
BigA=1000
BigAsqr=1000**2

for i in range(N):
    for j in range(N):
        f=LinExpr()
        #f.add(t[i]+h[i]-t[j]+BigAsqr*s[i][j])
        f.add(BigAsqr*s[i][j])
        f.add(quicksum(k*X[i][k]*BigA for k in range(M)))
        f.add(-quicksum(k*X[j][k]*BigA for k in range(M)))
        m.addConstr(f,GRB.LESS_EQUAL,BigAsqr,'Task_Schedule[0]_'+str(i)+'_'+str(j))
        f=LinExpr()
        #f.add(t[j]+h[j]-t[i]-BigAsqr*s[i][j])
        f.add(-BigAsqr*s[i][j])
        f.add(quicksum(k*X[j][k]*BigA for k in range(M)))
        f.add(-quicksum(k*X[i][k]*BigA for k in range(M)))
        m.addConstr(f,GRB.LESS_EQUAL,0,'Task_Schedule[1]_'+str(i)+'_'+str(j))
        
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
'''
#Add quadratic constraint Z_ij= sum (X_ik * Y_kj)
for i in range(N):
    for j in range(M):
        f=QuadExpr()
        f.add(quicksum(X[i][k]*Y[k][j] for k in range(M)))
        m.addConstr(Z[i][j],GRB.EQUAL,f,'Constraint_Z_'+str(i)+'_'+str(j))
m.update()
'''
#Modelling quadratic Z_ij to two linear constraints
#Add constraint (7)
BigD=50
for i in range(N):
    for j in range(M):
        f=LinExpr()
        f.add(BigD*Z[i][j])
        f.add(quicksum(k*(X[i][k]-Y[k][j]) for k in range(M)))
        m.addConstr(f,GRB.LESS_EQUAL,BigD,'Quad_Relax[0]_'+str(i)+'_'+str(j))
        f=LinExpr()
        f.add(BigD*Z[i][j])
        f.add(-quicksum(k*(X[i][k]-Y[k][j]) for k in range(M)))
        m.addConstr(f,GRB.LESS_EQUAL,BigD,'Quad_Relax[1]_'+str(i)+'_'+str(j))

m.update()        

#Add constraint (8)
for i in range(N):
    f=LinExpr()
    f.add(quicksum(Z[i][j] for j in range(M)))
    m.addConstr(f,GRB.EQUAL,1,'Task_Tile_Constr_'+str(i))
    
m.update()



#Create Labelled Graphs for communication cost
E_c=nx.floyd_warshall(NOC,'cost_per_bit')

L={} #Labelled graphs
covered={i:{j:False for j in range(M) if j!=i} for i in range(M)}

while any(covered[i][j]==False for j in range(M) for i in range(M) if j!=i):
    k=random.choice(NOC.nodes())
    if k in L:
        continue
    L[k]={}
    for j in range(M):
        L[k][j]=nx.dijkstra_path_length(NOC,k,j,'cost_per_bit')
    for i in range(M):
        for j in range(M):
            if i!=j:
                if E_c[i][j]==L[k][j]-L[k][i]:
                    covered[i][j]=True

#Model e_ij, add only those e_ij which are valid edges in TG
e={}
for edge in TG.edges_iter():
    if edge[0] not in e:
        e[edge[0]]={}
    e[edge[0]][edge[1]]=m.addVar(vtype=GRB.CONTINUOUS,name='e_'+str(edge[0])+'_'+str(edge[1]))
m.update()

#Add constraints for e_ij = max function
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    for k in range(len(L)):
        f=LinExpr()
        f.add(quicksum(Z[j][m]*L[k][m] for m in range(M))-quicksum(Z[i][l]*L[k][l] for l in range(M)))
        m.addConstr(e[i][j],GRB.GREATER_EQUAL,f,'e_ij_Constr_['+str(i)+']['+str(j)+']_'+str(k))
m.update()
'''

#Frame quadratic expression for e_ij
e={}
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    if i not in e:
        e[i]={}
    e[i][j]=QuadExpr()
    e[i][j].add(quicksum(Z[i][m]*Z[j][n]*E_c[m][n] for m in range(M) for n in range(M)))
'''    
#Calculate E_com
E_com=LinExpr()
E_com.add(quicksum(TG.edge[i][j]['volume']*e[i][j] for (i,j) in TG.edges()))

#Create Labelled Graphs for latency
L_c=nx.floyd_warshall(NOC,'latency')


L1={} #Labelled graphs
covered={i:{j:False for j in range(M) if j!=i} for i in range(M)}

while any(covered[i][j]==False for j in range(M) for i in range(M) if j!=i):
    k=random.choice(NOC.nodes())
    if k in L1:
        continue
    L1[k]={}
    for j in range(M):
        L1[k][j]=nx.dijkstra_path_length(NOC,k,j,'latency')
    for i in range(M):
        for j in range(M):
            if i!=j:
                if L_c[i][j]==L1[k][j]-L1[k][i]:
                    covered[i][j]=True

#Model l_ij, add only those l_ij which are valid edges in TG
l={}
for edge in TG.edges_iter():
    if edge[0] not in l:
        l[edge[0]]={}
    l[edge[0]][edge[1]]=m.addVar(vtype=GRB.CONTINUOUS,name='l_'+str(edge[0])+'_'+str(edge[1]))
m.update()

#Add constraints for l_ij = max function
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    for k in range(len(L1)):
        f=LinExpr()
        f.add(quicksum(Z[j][m]*L1[k][m] for m in range(M))-quicksum(Z[i][l]*L1[k][l] for l in range(M)))
        m.addConstr(l[i][j],GRB.GREATER_EQUAL,f,'l_ij_Constr_['+str(i)+']['+str(j)+']_'+str(k))
m.update()

'''
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
'''
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
m.setObjective(1*(E_core+E_com)+1*T,GRB.MINIMIZE)
m.update()
m.optimize()
m.write('test.lp')
m.write('test.sol')

    
