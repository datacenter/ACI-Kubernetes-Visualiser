#!/usr/local/bin/python3
from flask import Flask, render_template, request
from  graph import vkaci_draw, vkaci_build_topology, vkaci_env_variables, apic_methods_resolve
app = Flask(__name__, template_folder='template',static_folder='template/assets')
topology = vkaci_build_topology(vkaci_env_variables(), apic_methods_resolve())

f = open("version.txt", "r")
__build__ = f.read()

@app.route('/',methods=['GET', 'POST'])

def index():
    if request.method == 'POST':
        if 'podname' in request.form:
            # Only re-calculate topology if you press Submit
            if request.form['submit_button'] == 'Submit':
                pod_topo = vkaci_draw(topology.update())
            else:
                pod_topo = vkaci_draw(topology.get())
            pod_topo.add_pod(request.form['podname'])
            pod_topo.svg('template/assets/pod')
        else:
            cluster_topo = vkaci_draw(topology.update())
            cluster_topo.add_nodes()
            cluster_topo.svg('template/assets/cluster')
        return render_template('index.html', version=__build__)
    return render_template('index.html', version=__build__)

if __name__ == '__main__':
	app.run(debug=True, host="0.0.0.0", port=8080)
    
