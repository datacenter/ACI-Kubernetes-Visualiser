#!/usr/local/bin/python3
from flask import Flask, render_template, request, redirect
from  graph import VkaciGraph, VkaciBuilTopology, VkaciEnvVariables, ApicMethodsResolve


app = Flask(__name__, template_folder='template',static_folder='template/assets')
env = VkaciEnvVariables()
topology = VkaciBuilTopology(env, ApicMethodsResolve())
graph = VkaciGraph(env,topology)

f = open("version.txt", "r")
__build__ = f.read()

graph.update_database()

@app.route('/')
def index():
    return render_template('index.html', version=__build__, env=env, pod_names = topology.get_pods(), node_names = topology.get_nodes(), namespaces = topology.get_namespaces(), leaf_names = topology.get_leafs())

@app.route('/re-generate',methods=['GET', 'POST'])
def regenerate():
    if request.method == 'POST':
        # Update neo4j with topology data using graph
        graph.update_database()
    return redirect("/", code=302)

if __name__ == '__main__':
	app.run(debug=False, host="0.0.0.0", port=8080)