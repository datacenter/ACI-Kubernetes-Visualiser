var server_url = "";
var server_user = "";
var server_password = "";

function neo_viz_config(showPodName, container, cypher, seed = null) {
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

        layout: {
            improvedLayout: true,
        },

        physics: {

            adaptiveTimestep: true,
            timestep: 0.3,
            barnesHut: {
                gravitationalConstant: -3000,
            },

            stabilization: {
                iterations: 400, // CHANGEME: If want different stabilisation,
                fit: true
            }
        },

        labels: {
            "Node": {
                caption: "name",
                "size": 3,
                image: './assets/cui-2.0.0/img/node.svg',
                "font": {
                    "size": 20,
                    "color": "#6e1313",
                    strokeWidth: 5
                },
            },
            "Pod": {
                caption: podCaption,
                size: 2,
                image: './assets/cui-2.0.0/img/pod.svg',
                "font": {
                    "size": 18,
                    "color": "#41136e",
                    strokeWidth: 5
                },
            },
            "VM_Host": {
                caption: "name",
                size: 5,
                image: './assets/cui-2.0.0/img/esxi.png',
                "font": {
                    "size": 22,
                    "color": "#000000",
                    strokeWidth: 5
                },
            },
            "Switch": {
                caption: "name",
                size: 4,
                image: './assets/cui-2.0.0/img/switch.png',
                "font": {
                    "size": 22,
                    "color": "#000000",
                    strokeWidth: 5
                },
            },
        },
        relationships: {
            "PEERED_INTO": {
                "color": "#CD5C5C",
                "dashes": "true"
            },

            "CONNECTED_TO": {
                "color": "#7A8A24",
                "caption": "interface",
                "font": {
                    "size": 18,
                    "color": "#000099", 
                    strokeWidth: 5
                },
            },

            "RUNNING_IN": {
                "color": "#0047AB"
            },

            "RUNNING_ON": {
                "color": "#DAA520"
            },

            [NeoVis.NEOVIS_DEFAULT_CONFIG]: {
                "thickness": "defaultThicknessProperty",
                "caption": "defaultCaption"
            },
        }
    };

    if (seed) {
        config.layout.randomSeed = seed
    }

    return config
}

// Views enums can be grouped as static members of a class
class View {
    // Create new instances of the same class as static attributes
    static All = new View("All", draw_all)
    static WithoutPods = new View("WithoutPods", draw_without_pods)
    static WithoutBgpPeers = new View("WithoutBgpPeers", draw_without_bgp_peers)
    static PodsAndNodes = new View("PodsAndNodes", draw_pods_and_nodes)
    static OnlyBgpPeers = new View("OnlyBgpPeers", draw_only_bgp_peers)

    constructor(name, drawFunc) {
        this.name = name
        this.drawFunc = drawFunc
    }
}

selectedView = View.WithoutPods
selectedNamespace = ".*"

function draw_all() {
    selectedView = View.All
    // draw("MATCH (n)-[r]-(m) RETURN n,r,m")
    draw("MATCH (p:Pod)-[r]->(m:Node)-[r2*1..2]->(a) where p.ns =~ '" + selectedNamespace + "' return *")
}

function draw_without_pods() {
    selectedView = View.WithoutPods
    // draw("MATCH (n:Node)-[r*1..2]->(m) Return n,m,r")
    draw("MATCH (p:Pod)-[r]->(m:Node)-[r2*1..2]->(a) where p.ns =~ '" + selectedNamespace + "' return m,r2,a")
}

function draw_without_bgp_peers() {
    selectedView = View.WithoutBgpPeers
    // draw("MATCH (n1)-[r1:RUNNING_IN]-(n2)-[r2:CONNECTED_TO]-(n3) RETURN r1, r2, n1, n2, n3")
    draw("MATCH (p:Pod)-->(n:Node)-[r:RUNNING_IN]-(v:VM_Host)-[r1:CONNECTED_TO]-(l:Switch) WHERE p.ns =~ '" + selectedNamespace + "' RETURN r, r1, n, v, l")
}

function draw_pods_and_nodes() {
    selectedView = View.PodsAndNodes
    // draw("MATCH (n1:Pod)-[r]->(n2) RETURN r, n1, n2", true)
    draw("MATCH (p:Pod)-[r]->(n2) WHERE p.ns =~ '" + selectedNamespace + "' RETURN *", true)
}

function draw_only_bgp_peers() {
    selectedView = View.OnlyBgpPeers
    // draw("MATCH (n1)-[r:PEERED_INTO]->(n2) RETURN r, n1, n2")
    draw("MATCH (p:Pod)-->(n:Node)-[r:PEERED_INTO]->(s:Switch) WHERE p.ns =~ '" + selectedNamespace + "' RETURN r, n,s")
}

function draw_namespace(namespace) {
    selectedNamespace = namespace
    selectedView.drawFunc()
}

function selectView() {
    $("#selected_views").find("a").each(function () {
        var a = $(this)
        if (a.attr("id") == selectedView.name) {
            a.addClass("selected")
        }
        else {
            a.removeClass("selected")
        }
    })

    $("#selected_namespace").find("a").each(function () {
        var a = $(this)
        if (a.attr("id") == selectedNamespace) {
            a.addClass("selected")
        }
        else {
            a.removeClass("selected")
        }
    })
}
// draw cluster topology with different views
function draw(query, pods = false) {
    selectView()
    var config = neo_viz_config(pods, "viz", query)
    console.log(config)
    var viz = new NeoVis.default(config);
    viz.render();
    console.log(viz);
}

function draw_leaf() {
    var str = $("#leafname").val();
    if (!str.trim()) return;
    var seed = "0.8455348811333163:1645676676633"
    var config_leaf = neo_viz_config(true, "viz_leaf", 'MATCH (s:Switch)<-[r]-(m) WHERE s.name= "' + str + '" RETURN *', seed)
    var viz_leaf = new NeoVis.default(config_leaf);
    viz_leaf.render();
    // Get seed method: This number is printed when you use getSeed in order for the objects within a certain view to not overlap each ther everytime you click show 
    // viz_leaf.registerOnEvent("completed", function (){
    //     console.log(viz_leaf._network.getSeed())
    //  })
}

function draw_node() {
    var str = $("#nodename").val();
    if (!str.trim()) return;
    var seed = "0.7578607868826415:1645663636870"
    // var config_node = neo_viz_config(true, "viz_node", 'MATCH (p:Pod)-[r]->(n:Node)-[r1*1..3]->(m) WHERE n.name= "' + str + '" RETURN *', seed)
    q = `MATCH (p:Pod)-[r]->(n:Node)-[r1]->(v:VM_Host)-[r2]->(s:Switch)
         MATCH (n)-[r3:PEERED_INTO]->(s1)
         WHERE n.name = "${str}" AND n.name IN r2.nodes RETURN *
    `;
    var config_node = neo_viz_config(true, "viz_node", q, seed)
    var viz_node = new NeoVis.default(config_node);
    viz_node.render();
    // Get seed method: This number is printed when you use getSeed in order for the objects within a certain view to not overlap each ther everytime you click show 1645580358235
    //viz_node.registerOnEvent("completed", function (){
    //console.log(viz_node._network.getSeed())
    //})
}


function draw_pod() {
    var str = $("#podname").val();
    if (!str.trim()) return;
    var seed = "0.8660747593468698:1645662423690"
    t = "name"
    if (checkIfValidIP(str)) {
        t = "ip"
    }
    p = `MATCH (p:Pod)-[r]->(n:Node)-[r1]->(v:VM_Host)-[r2]->(s:Switch)
        MATCH (n)-[r3:PEERED_INTO]->(s1)
        WHERE p.${t} = "${str}" AND n.name IN r2.nodes RETURN *
    `;
    var config_pod = neo_viz_config(true, "viz_pod", p , seed)
    var viz_pod = new NeoVis.default(config_pod);
    viz_pod.render();
    // Get seed method: This number is printed when you use getSeed in order for the objects within a certain view to not overlap each ther everytime you click show 1645578356529
    //viz_pod.registerOnEvent("completed", function (){
    //console.log(viz_pod._network.getSeed())
    //})
}


/* Check if string is IP */
function checkIfValidIP(str) {
    // Regular expression to check if string is a IP address
    const regexExp = /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/gi;

    return regexExp.test(str);
}
