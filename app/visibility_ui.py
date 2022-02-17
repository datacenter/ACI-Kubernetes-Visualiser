#!/usr/local/bin/python3
from flask import Flask, render_template, request
from  graph import vkaci_graph, vkaci_build_topology, vkaci_env_variables, apic_methods_resolve


app = Flask(__name__, template_folder='template',static_folder='template/assets')
env = vkaci_env_variables()
topology = vkaci_build_topology(env, apic_methods_resolve())
graph = vkaci_graph(env,topology)

f = open("version.txt", "r")
__build__ = f.read()

topology.update()

@app.route('/',methods=['GET', 'POST'])
def index():
    if request.method == 'POST':

        # Update neo4j with topology data using graph
        graph.update_database()

    return render_template('index.html', version=__build__, env=env, pod_names = topology.get_pods(), node_names = topology.get_nodes())

if __name__ == '__main__':
	app.run(debug=True, host="0.0.0.0", port=8080)
    
