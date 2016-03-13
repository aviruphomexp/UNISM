# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 12:38:30 2016

@author: Avirup
"""

import networkx as nx
from gurobipy import *
import numpy as np
#Load the DFG

dfg=nx.read_graphml('mat_vec_product.xml.gz')

#graph is now loaded
#create local copies of the internal prop maps for easy naming

vtype=nx.get_node_attributes(dfg,'type')
vname=nx.get_node_attributes(dfg,'name')
vweight=nx.get_node_attributes(dfg,'vweight')
eweight=nx.get_edge_attributes(dfg,'eweight')
is_scheduled=nx.get_node_attributes(dfg,'schedule_status')
vindex=nx.get_node_attributes(dfg,'vindex')
eindex=nx.get_edge_attributes(dfg,'eindex')


#Create Task lists
A=[['+',1,2],['load',1,2],['*',1,2],['fpsh',1,1],['fpul',1,1]]
op_nodes=0
no_edges=0
for v in dfg.nodes_iter():
    if vtype[v]==1:
        op_nodes=op_nodes+1
        
#maintain a list of indices for each type of operation (first element: operation name, second element:hardware constraint, third:weight, rest: list of indices)    
        for i in range(len(A)):
            if vname[v]==A[i][0]:
                A[i].append(op_nodes)
                break
    elif vtype[v]==0:
        no_edges=no_edges+dfg.out_degree(v)
no_tasks=op_nodes

#Network topology data (get labeled graphs)
from queue import Queue
node_queue=Queue()
NOC=nx.read_graphml("NOC.xml.gz")
node_potential={v:None for v in NOC.nodes_iter()}
pot_done={v:None for v in NOC.nodes_iter()}
noc_ind=0
no_cores=NOC.number_of_nodes()
no_tiles=no_cores
tile_potentials=[]

for v in NOC.nodes_iter():
    for v1 in NOC.nodes_iter():
        pot_done[v1]=False
        node_potential[v1]=0
    v_o=v
    node_potential[v_o]=0
    pot_done[v_o]=True
    node_queue.put(v_o)
    while node_queue.empty()==False:
        h=node_queue.get()
        for v1 in NOC.successors_iter(h):
            if pot_done[v1]==False:
                node_queue.put(v1)
                node_potential[v1]=node_potential[h]+1
                pot_done[v1]=True
    tile_potentials.append(np.zeros(no_tiles))
    i=0
    for v2 in NOC.nodes_iter():
        tile_potentials[noc_ind][i]=node_potential[v2]
        i=i+1
    noc_ind=noc_ind+1

           
q=np.ones(no_cores)
total_variables=no_tasks+no_tasks*no_cores+no_cores*no_tiles+no_tasks*no_tiles+no_tasks*no_tasks


m=Model("unism")
start_time={}
for i in range(no_tasks):
    start_time[i]=m.addVar(vtype=GRB.INTEGER,name='t_'+str(i))


X={i:{} for i in range(no_tasks)}
for i in range(no_tasks):
    for j in range(no_cores):
        X[i][j]=m.addVar(vtype=GRB.BINARY,name='X_'+str(i)+'_'+str(j))

M={i:{} for i in range(no_cores)}
for i in range(no_cores):
    for j in range(no_tiles):
        M[i][j]=m.addVar(vtype=GRB.BINARY,name='M_'+str(i)+'_'+str(j))

Y={i:{} for i in range(no_tasks)}
for i in range(no_tasks):
    for j in range(no_tiles):
        Y[i][j]=m.addVar(vtype=GRB.BINARY,name='Y_'+str(i)+'_'+str(j))
        
f=open("sname.txt",'w')
s={i:{} for i in range(no_tasks)}
for i in range(no_tasks):
    for j in range(no_tasks):
        s[i][j]=m.addVar(vtype=GRB.BINARY,name='s_'+str(i)+'_'+str(j))
        f.write('s_'+str(i)+'_'+str(j)+'   '+str(i*no_tasks+j)+'\n')
f.close()

m.update()

###############################################################################

#Objective formulation**********************************************************

s = np.ones(op_nodes)
H = np.zeros((no_tasks,no_cores)) #initialized an array of the right size but without the correct values

#Populate H  
for v in dfg.nodes_iter():
    if vtype[v]==1:
        for k in range(len(A)):
            if vname[v]==A[k][0]:
                for i in range(no_cores):
                    H[vindex[v],i]=A[k][2]
                    
#First objective
L=LinExpr()
L.add(quicksum(s[i]*start_time[i] for i in range(no_tasks))+quicksum(s[i]*H[i][j]*X[i][j] for i in range(no_tasks) for j in range(no_cores)))
m.setObjective(L,GRB.MINIMIZE)
m.update()
###############################################################################

#Task to core mapping constraints
for i in range(no_tasks):
    tc=LinExpr()
    tc.add(quicksum(X[i][j] for j in range(no_cores)))
    m.addConstr(tc,GRB.EQUAL,1,'Task_Core_Constr_'+str(i))
   
m.update()

#Core to tile mapping constraints

for i in range(no_cores):
    ct=LinExpr()
    ct.add(quicksum(M[i][j] for j in range(no_tiles)))
    m.addConstr(ct,GRB.EQUAL,1,'Core_Tile_Constr_'+str(i))
    
m.update()

#Task to tile mapping constraints    

for i in range(no_tasks):
    tt=LinExpr()
    tt.add(quicksum(Y[i][j] for j in range(no_tiles)))
    m.addConstr(tt,GRB.EQUAL,1,'Task_Tile_Constr_'+str(i))
    
m.update()

BigD=50*no_cores

for i in range(no_tasks):
    for l in range(no_cores):
        f=LinExpr()
        f.add(quicksum(j*(X[i][j]-M[j][l]) for j in range(no_cores))+BigD*Y[i][l])
        m.addConstr(f,GRB.LESS_EQUAL,BigD,'Quadratic_Relax_TT(0)_'+str(i)+'_'+str(l))
        f=LinExpr()
        f.add(quicksum(-j*(X[i][j]-M[j][l]) for j in range(no_cores))+BigD*Y[i][l])
        m.addConstr(f,GRB.LESS_EQUAL,BigD,'Quadratic_Relax_TT(0)_'+str(i)+'_'+str(l))

#m.update()

#Flow dependency constraints
for v in dfg.nodes_iter():
    if vtype[v]==1:
        i=vindex[v]
        for p in dfg.predecessors_iter(v):
            for p1 in dfg.predecessors_iter(p):
                idash=vindex[p1]
                f=LinExpr()
                f.add(start_time[i]-start_time[idash])
                f.add(quicksum(X[idash][j]*H[idash][j] for j in range(no_cores)))
                vii=vweight[p]
                for k in range(len(tile_potentials)):
                    f.add(-quicksum(Y[i][l1]*tile_potentials[k][l1]*vii for l1 in range(no_tiles)))
                    f.add(quicksum(Y[idash][l1]*tile_potentials[k][l1]*vii for l1 in range(no_tiles)))
                    m.addConstr(f,GRB.GREATER_EQUAL,0,'Flow_Constr_'+str(i)+'_'+str(idash)+'_'+str(k))
                    for l1 in range(no_tiles):
                        f.remove(Y[i][l1])
                        f.remove(Y[idash][l1])
                
m.update()

#One instruction at a time constraint
BigA=50
BigAsq=2500

