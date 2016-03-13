# -*- coding: utf-8 -*-
"""
Created on Sun Mar 13 01:34:08 2016

@author: Avirup
"""
import networkx as nx
#from gurobipy import *
import random
import queue

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

###########################################################################

X=[[0 for j in range(M)] for i in range(N)]
Y=[[0 for j in range(M)] for i in range(M)]
Z=[[0 for j in range(M)] for i in range(N)]

'''
#Generate inputs for X
x_str=''
for i in range(N):
    j=random.randint(0,M-1)
    x_str+=str(j)
    X[i][j]=1

#Generate inputs for Y
core_occupied=[False for i in range(M)]
y_str=''
for i in range(M):
    while True:
        j=random.randint(0,M-1)
        if not core_occupied[j]:
            break
    Y[i][j]=1
    y_str+=str(j)
    core_occupied[j]=True
    
if int(x_str+y_str) in results:
    continue


'''

X[0][0]=1
X[1][0]=1
X[2][0]=1
X[3][0]=1
X[4][0]=1

Y[0][3]=1
Y[1][0]=1
Y[2][1]=1
Y[3][2]=1


#Calculate Z
for i in range(N):
    for j in range(M):
        for k in range(M):
            Z[i][j]+=(X[i][k]*Y[k][j])
            
#Calculate E_core
E_core=0
for i in range(N):
    for j in range(M):
        E_core+=(X[i][j]*w[i][j]*NOC.node[j]['power'])            


#Calculate E_com
E_com=0
E_c=nx.floyd_warshall(NOC,'cost_per_bit')
for edge in TG.edges_iter():
    i,j=edge[0],edge[1]
    m=Z[i].index(1)
    n=Z[j].index(1)
    E_com+=(E_c[m][n]*TG.edge[i][j]['volume'])

t=[0 for i in range(N)]
sorted_nodes=nx.topological_sort(TG)

#Calculate execution time h[i]
h=[0 for i in range(N)]
for i in range(N):
    j=X[i].index(1)
    h[i]=w[i][j]
    
    
#Calculate time for each node
L_c=nx.floyd_warshall(NOC,'latency')
for i in sorted_nodes:
    for j in TG.predecessors_iter(i):
        m=Z[i].index(1)
        n=Z[j].index(1)
        t[i]=max(t[i],t[j]+h[j]+TG.edge[j][i]['volume']*L_c[m][n])

#Remove overlaps in each core
core_tasks1={}
for j in range(M):
    for i in range(N):
        if X[i][j]==1:
            if j not in core_tasks1:
                core_tasks1[j]=[]
            core_tasks1[j].append(i)
core_tasks={}
for core,tasks in core_tasks1.items():
    if len(tasks)>1:
        core_tasks[core]=tasks
del core_tasks1

flag=False
def modify_time(node):
    global t,Z,L_c,TG
    Q= queue.Queue()
    Q.put(node)
    while not Q.empty():
        i=Q.get()
        for j in TG.successors(i):
            m=Z[i].index(1)
            n=Z[j].index(1)
            t[j]=max(t[j],t[i]+h[i]+TG.edge[i][j]['volume']*L_c[m][n])
            Q.put(j)
 
while not flag:
    flag=True
    for core in core_tasks:
        sorted_task=sorted(core_tasks[core],key=lambda x:t[x])
        for i in range(1,len(sorted_task)):
            if t[sorted_task[i]]<t[sorted_task[i-1]]+h[sorted_task[i-1]]:
                t[sorted_task[i]]=t[sorted_task[i-1]]+h[sorted_task[i-1]]
                modify_time(sorted_task[i])
                flag=False
        
            

#Calculate total time T
T=max(t[i]+h[i] for i in range(N))
C=T+E_com+E_core