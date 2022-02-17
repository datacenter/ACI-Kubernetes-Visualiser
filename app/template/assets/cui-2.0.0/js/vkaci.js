var server_url = "";
var server_user = "";
var server_password = "";

function neo_viz_config(showPodName, container, cypher) {
    var podCaption = "pod"
    if (showPodName) {
        podCaption = "name"
    }

    var config = {
        container_id: container,
        server_url: server_url,
        server_user: server_user,
        server_password: server_password,
        initial_cypher: cypher,
        arrows: showPodName,
        fix_nodes_in_place_on_drag: true,
        physics: {

            adaptiveTimestep: true,
            barnesHut: {
            },

            stabilization: {
                iterations: 350, // CHANGEME: If want different stabilisation,
                fit: true
            }
        },

        labels: {
            "Node": {
                caption: "name",
                "size": 3,
                image: './assets/cui-2.0.0/img/node.svg',
                "font": {
                    "size": 26,
                    "color": "#6e1313",
                },
            },
            "Pod": {
                caption: podCaption,
                size: 2,
                image: './assets/cui-2.0.0/img/pod.svg'
            },
            "VM_Host": {
                caption: "name",
                size: 5,
                image: './assets/cui-2.0.0/img/esxi.png',
                "font": {
                    "size": 26,
                    "color": "#000000"
                },
            },
            "Switch": {
                caption: "name",
                size: 4,
                image: './assets/cui-2.0.0/img/switch.png',
                "font": {
                    "size": 26,
                    "color": "#000000"
                },
            },
        },
        relationships: {
            "PEERED_INTO": {
                "color": "#CD5C5C",
                "dashes": "true"
            },

            "CONNECTED_TO": {
                "color": "#7A8A24"
            },

            [NeoVis.NEOVIS_DEFAULT_CONFIG]: {
                "thickness": "defaultThicknessProperty",
                "caption": "defaultCaption"
            },
        }
    };

    return config
}

function draw_all() {
    draw("MATCH (n)-[r]-(m) RETURN n,r,m")
}

function draw_without_pods() {
    draw("MATCH (n:Node)-[r*1..2]->(m) Return n,m,r")
}

function draw_without_bgp_peers() {
    draw("MATCH (n1)-[r1:RUNNING_IN]-(n2)-[r2:CONNECTED_TO]-(n3) RETURN r1, r2, n1, n2, n3")
}

function draw_pods_and_nodes() {
    draw("MATCH (n1:Pod)-[r]->(n2) RETURN r, n1, n2", true)
}

function draw_only_bgp_peers() {
    draw("MATCH (n1)-[r:PEERED_INTO]->(n2) RETURN r, n1, n2")
}

function draw(query, pods = false) {
    var config = neo_viz_config(pods, "viz", query)
    console.log(config)
    var viz = new NeoVis.default(config);
    viz.render();
    console.log(viz);
}

function draw_node() {
    var str = $("#nodename").val();
    var config_node = neo_viz_config(true, "viz_node", 'MATCH (p:Pod)-[r]->(n:Node)-[r1*1..3]->(m) WHERE n.name= "' + str + '" RETURN *')
    var viz_node = new NeoVis.default(config_node);
    viz_node.render();
}

function draw_pod() {
    var str = $("#podname").val();
    var config_pod = neo_viz_config(true, "viz_pod", 'MATCH (p:Pod)-[r*1..3]->(m) WHERE p.name= "' + str + '" RETURN p, r,m')
    var viz_pod = new NeoVis.default(config_pod);
    viz_pod.render();
}