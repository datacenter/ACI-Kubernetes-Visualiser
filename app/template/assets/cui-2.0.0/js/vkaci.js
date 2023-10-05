var server_url = "";
var server_user = "";
var server_password = "";
var asnPresent = true;

function neo_viz_config(showPodName, container, cypher, seed = null) {
    var podCaption = showPodName ? "name" : "pod";

    var config = {
        container_id: container,
        server_url: server_url,
        server_user: server_user,
        server_password: server_password,
        initial_cypher: cypher,
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
                iterations: 400,
                fit: true,
            }
        },
        labels: {
            "Node": {
                caption: "name",
                size: 3,
                image: './assets/cui-2.0.0/img/node.svg',
                font: {
                    size: 20,
                    color: "#6e1313",
                    strokeWidth: 2,
                },
            },
            "Pod": {
                caption: podCaption,
                size: 2,
                image: './assets/cui-2.0.0/img/pod.svg',
                font: {
                    size: 18,
                    color: "#41136e",
                    strokeWidth: 2,
                },
            },
            "VM_Host": {
                caption: "name",
                size: 5,
                image: './assets/cui-2.0.0/img/esxi.png',
                font: {
                    size: 22,
                    color: "#000000",
                    strokeWidth: 2,
                },
            },
            "Switch": {
                caption: "name",
                size: 4,
                image: './assets/cui-2.0.0/img/switch.png',
                font: {
                    size: 22,
                    color: "#000000",
                    strokeWidth: 2,
                },
            },
            "Label": {
                caption: "name",
                size: 2,
                image: './assets/cui-2.0.0/img/label.svg',
                font: {
                    size: 20,
                    color: "#000000",
                    strokeWidth: 2,
                },
            },
        },
        relationships: {
            "PEERED_INTO": {
                color: "#CD5C5C",
                dashes: true,
            },
            "CONNECTED_TO": {
                color: "#FF4500",
                caption: "interface",
                font: {
                    size: 16,
                    color: "#000000",
                    strokeWidth: 2,
                    multi: true,
                },
            },
            "CONNECTED_TO_SEC": {
                color: "#800080",
                caption: "interface",
                font: {
                    size: 16,
                    color: "#000000",
                    strokeWidth: 2,
                    multi: true,
                },
            },
            "CONNECTED_TO_TER": {
                color: "#008080",
                caption: "interface",
                font: {
                    size: 16,
                    color: "#000000",
                    strokeWidth: 2,
                    multi: true,
                },
            },
            "RUNNING_IN": {
                color: "#0047AB",
            },
            "RUNNING_ON": {
                caption: "interface",
                font: {
                    size: 16,
                    color: "#000000",
                    strokeWidth: 2,
                    multi: true,
                    vadjust: -10,
                },
                color: "#FF4500",
            },
            "RUNNING_ON_SEC": {
                caption: "interface",
                font: {
                    size: 16,
                    color: "#000000",
                    strokeWidth: 2,
                    multi: true,
                    vadjust: -10,
                },
                color: "#800080",
            },
            "RUNNING_ON_TER": {
                caption: "interface",
                font: {
                    size: 16,
                    color: "#000000",
                    strokeWidth: 2,
                    multi: true,
                    vadjust: -10,
                },
                color: "#008080",
            },
            "ATTACHED_TO": {
                color: "#ff5050",
            },
            [NeoVis.NEOVIS_DEFAULT_CONFIG]: {
                thickness: "defaultThicknessProperty",
                caption: "defaultCaption",
                align: "top",
            },
        },
    };

    if (seed) {
        config.layout.randomSeed = seed;
    }

    return config;
}

// Views enums can be grouped as static members of a class
class View {
    // Create new instances of the same class as static attributes
    static All = new View("All", draw_all)
    static WithoutPods = new View("WithoutPods", draw_without_pods)
    static WithoutBgpPeers = new View("WithoutBgpPeers", draw_without_bgp_peers)
    static PodsAndNodes = new View("PodsAndNodes", draw_pods_and_nodes)
    static OnlyBgpPeers = new View("OnlyBgpPeers", draw_only_bgp_peers)
    static OnlyPrimarylinks = new View("OnlyPrimarylinks", draw_only_primary_links)
    static OnlySriovlinks = new View("OnlySriovlinks", draw_only_sriov_links)
    static OnlyMacvlanlinks = new View("OnlyMacvlanlinks", draw_only_macvlan_links)

    constructor(name, drawFunc) {
        this.name = name
        this.drawFunc = drawFunc
    }
}

selectedView = View.WithoutPods
selectedNamespace = ".*"
const selectedLabelFilters = new Map()
selectedPodNamespace = "!"

function getLabelFilterString() {
    const lbls = [];
    selectedLabelFilters.forEach((value) => lbls.push(`'${value}'`));
    let lblStr = lbls.join(",")
    console.log(lblStr)
    return lblStr
}

function addLabelQuery() {
    if (selectedLabelFilters.size > 0) {
        var lblStr = getLabelFilterString();
        return `AND l.name IN [${lblStr}] `;
        // q += `AND l2.name IN [${lblStr}]) `
    }
    return "";
}

function draw_all() {
    selectedView = View.All
    let q = `OPTIONAL MATCH (p:Pod)-[r:RUNNING_ON_SEC]->(n:Node)-[r1:RUNNING_IN]->(v:VM_Host)-  [r2:CONNECTED_TO_SEC]->(a) WHERE p.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p1:Pod)-[r3:RUNNING_ON_SEC]->(n1:Node)-[r4:CONNECTED_TO_SEC]->(b) WHERE p1.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p2:Pod)-[r5:RUNNING_ON_TER]->(n2:Node)-[r6:RUNNING_IN]->(v1:VM_Host)-[r7:CONNECTED_TO_TER]->(c) WHERE p2.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p3:Pod)-[r8:RUNNING_ON_TER]->(n3:Node)-[r9:CONNECTED_TO_TER]->(d) WHERE p3.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p4:Pod)-[r10]->(n4:Node)-[r11*1..2]->(e) WHERE p4.ns =~ '${selectedNamespace}' AND (NOT TYPE(r10) IN ['RUNNING_ON_SEC', 'RUNNING_ON_TER']) AND NONE(rel IN r11 WHERE TYPE(rel) IN ['CONNECTED_TO_SEC', 'CONNECTED_TO_TER'])`
    q += addLabelQuery();
    q += `RETURN *`
    draw(q)
    //draw("MATCH (p:Pod)-[r]->(m:Node)-[r2*1..2]->(a) where p.ns =~ '" + selectedNamespace + "' return *")
}

function draw_without_pods() {
    selectedView = View.WithoutPods
    let q = `OPTIONAL MATCH (p:Pod)-[r:RUNNING_ON_SEC]->(n:Node)-[r1:RUNNING_IN]->(v:VM_Host)-  [r2:CONNECTED_TO_SEC]->(a) WHERE p.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p1:Pod)-[r3:RUNNING_ON_SEC]->(n1:Node)-[r4:CONNECTED_TO_SEC]->(b) WHERE p1.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p2:Pod)-[r5:RUNNING_ON_TER]->(n2:Node)-[r6:RUNNING_IN]->(v1:VM_Host)-[r7:CONNECTED_TO_TER]->(c) WHERE p2.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p3:Pod)-[r8:RUNNING_ON_TER]->(n3:Node)-[r9:CONNECTED_TO_TER]->(d) WHERE p3.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p4:Pod)-[r10]->(n4:Node)-[r11*1..2]->(e) WHERE p4.ns =~ '${selectedNamespace}' AND (NOT TYPE(r10) IN ['RUNNING_ON_SEC', 'RUNNING_ON_TER']) AND NONE(rel IN r11 WHERE TYPE(rel) IN ['CONNECTED_TO_SEC', 'CONNECTED_TO_TER'])`
    q += addLabelQuery();
    q += `RETURN n, r1, v, r2, a, n1, r4, b, n2, r6, v1, r7, c, n3, r9, d, n4, r11, e`
    draw(q)
    //draw("MATCH (p:Pod)-[r]->(m:Node)-[r2*1..2]->(a) where p.ns =~ '" + selectedNamespace + "' return m,r2,a")
}

function draw_without_bgp_peers() {
    selectedView = View.WithoutBgpPeers
    let q = ` MATCH (p:Pod)-[r]->(m:Node)-[u:RUNNING_IN]-(v:VM_Host)-[r1:CONNECTED_TO]-(s:Switch) WHERE p.ns =~ '${selectedNamespace}' `
    q += addLabelQuery();
    q += `RETURN u, r1, m, v,s`
    draw(q)
    // draw("MATCH (p:Pod)-->(n:Node)-[r:RUNNING_IN]-(v:VM_Host)-[r1:CONNECTED_TO]-(l:Switch) WHERE p.ns =~ '" + selectedNamespace + "' RETURN r, r1, n, v, l")
}

function draw_pods_and_nodes() {
    selectedView = View.PodsAndNodes
    let q = ` MATCH (p:Pod)-[r1]->(n:Node) WHERE p.ns =~ '${selectedNamespace}' `
    q += addLabelQuery();
    q += `RETURN p,r1,n`
    draw(q, true)
    //draw("MATCH (p:Pod)-[r]->(n2) WHERE p.ns =~ '" + selectedNamespace + "' RETURN *", true)
}

function draw_only_bgp_peers() {
    selectedView = View.OnlyBgpPeers
    let q = ` MATCH (p:Pod)-->(n:Node)-[r:PEERED_INTO]->(s:Switch) WHERE p.ns =~ '${selectedNamespace}' `
    q += addLabelQuery();
    q += `RETURN r, n,s`
    draw(q)
    
    //draw("MATCH (p:Pod)-->(n:Node)-[r:PEERED_INTO]->(s:Switch) WHERE p.ns =~ '" + selectedNamespace + "' RETURN r, n,s")
}

function draw_only_primary_links() {
    selectedView = View.OnlyPrimarylinks
    let q = `OPTIONAL MATCH (p:Pod)-[r:RUNNING_ON]->(n:Node)-[r1:CONNECTED_TO]->(a) WHERE p.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p1:Pod)-[r2:RUNNING_ON]->(n1:Node)-[r3:RUNNING_IN]->(v:VM_Host)-[r4:CONNECTED_TO]-(b) WHERE p1.ns =~ '${selectedNamespace}'`
    q += addLabelQuery();
    q += `RETURN p, p1, n, n1, r, r2, r1, r3, r4, v, a, b`
    draw(q, true)
}

function draw_only_sriov_links() {
    selectedView = View.OnlySriovlinks
    let q = `OPTIONAl MATCH (p:Pod)-[r:RUNNING_ON_SEC]->(n:Node)-[r1:CONNECTED_TO_SEC]->(a) WHERE p.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p1:Pod)-[r2:RUNNING_ON_SEC]->(n1:Node)-[r3:RUNNING_IN]->(v:VM_Host)-[r4:CONNECTED_TO_SEC]->(b) WHERE p1.ns =~ '${selectedNamespace}'`
    q += addLabelQuery();
    q += `RETURN p, p1, n, n1, r, r2, r1, r3, r4, v, a, b`
    draw(q, true)
}

function draw_only_macvlan_links() {
    selectedView = View.OnlyMacvlanlinks
    let q = `OPTIONAL MATCH (p:Pod)-[r:RUNNING_ON_TER]->(n:Node)-[r1:CONNECTED_TO_TER]->(a) WHERE p.ns =~ '${selectedNamespace}'
            OPTIONAL MATCH (p1:Pod)-[r2:RUNNING_ON_TER]->(n1:Node)-[r3:RUNNING_IN]->(v:VM_Host)-[r4:CONNECTED_TO_TER]->(b) WHERE p1.ns =~ '${selectedNamespace}'`
    q += addLabelQuery();
    q += `RETURN p, p1, n, n1, r, r2, r1, r3, r4, v, a, b`
    draw(q, true)
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

    $("#selected_pod_namespace").find("a").each(function () {
        var a = $(this)
        if (a.attr("id") == selectedPodNamespace) {
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
    var viz = new NeoVis.default(config);
    viz.render();
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
    if (asnPresent) {
        var q = `MATCH (p:Pod)-[r]->(n:Node)-[r2]->(s:Switch)
            MATCH (n)-[r3:PEERED_INTO]->(s1)
            WHERE n.name = "${str}"
            RETURN *
        `;
    } else {
        var q = `OPTIONAL MATCH (p:Pod)-[r:RUNNING_ON_SEC]->(n:Node)-[r1:RUNNING_IN]->(v:VM_Host)-      [r2:CONNECTED_TO_SEC]->(a) WHERE n.name = "${str}"
            OPTIONAL MATCH (p1:Pod)-[r3:RUNNING_ON_SEC]->(n1:Node)-[r4:CONNECTED_TO_SEC]->(b) WHERE n1.name = "${str}"
            OPTIONAL MATCH (p2:Pod)-[r5:RUNNING_ON_TER]->(n2:Node)-[r6:RUNNING_IN]->(v1:VM_Host)-[r7:CONNECTED_TO_TER]->(c) WHERE n2.name = "${str}"
            OPTIONAL MATCH (p3:Pod)-[r8:RUNNING_ON_TER]->(n3:Node)-[r9:CONNECTED_TO_TER]->(d) WHERE n3.name = "${str}"
            OPTIONAL MATCH (p4:Pod)-[r10]->(n4:Node)-[r11*1..2]->(e) WHERE n4.name = "${str}" AND (NOT TYPE(r10) IN ['RUNNING_ON_SEC', 'RUNNING_ON_TER']) AND NONE(rel IN r11 WHERE TYPE(rel) IN ['CONNECTED_TO_SEC', 'CONNECTED_TO_TER'])
            RETURN *
        `;
    }
    var config_node = neo_viz_config(true, "viz_node", q, seed)
    var viz_node = new NeoVis.default(config_node);
    viz_node.render();
    // Get seed method: This number is printed when you use getSeed in order for the objects within a certain view to not overlap each ther everytime you click show 1645580358235
    //viz_node.registerOnEvent("completed", function (){
    //console.log(viz_node._network.getSeed())
    //})
}

var viz_pod = null
function draw_pod() {
    var str = $("#podname").val();
    if (!str.trim()) return;
    var seed = "0.8660747593468698:1645662423690"
    var t = "name"
    if (checkIfValidIP(str)) {
        t = "ip"
    }
    if (asnPresent) {
        var p = `MATCH (p:Pod)-[r]->(n:Node)-[r2]->(s:Switch)
            MATCH (n)-[r3:PEERED_INTO]->(s1)
            WHERE p.${t} = "${str}"
            RETURN *
        `;
    } else {
        var p = `OPTIONAL MATCH (p:Pod)-[r:RUNNING_ON_SEC]->(n:Node)-[r1:RUNNING_IN]->(v:VM_Host)-      [r2:CONNECTED_TO_SEC]->(a) WHERE p.${t} = "${str}"
            OPTIONAL MATCH (p1:Pod)-[r3:RUNNING_ON_SEC]->(n1:Node)-[r4:CONNECTED_TO_SEC]->(b) WHERE p1.${t} = "${str}"
            OPTIONAL MATCH (p2:Pod)-[r5:RUNNING_ON_TER]->(n2:Node)-[r6:RUNNING_IN]->(v1:VM_Host)-[r7:CONNECTED_TO_TER]->(c) WHERE p2.${t} = "${str}"
            OPTIONAL MATCH (p3:Pod)-[r8:RUNNING_ON_TER]->(n3:Node)-[r9:CONNECTED_TO_TER]->(d) WHERE p3.${t} = "${str}"
            OPTIONAL MATCH (p4:Pod)-[r10]->(n4:Node)-[r11*1..2]->(e) WHERE p4.${t} = "${str}" AND (NOT TYPE(r10) IN ['RUNNING_ON_SEC', 'RUNNING_ON_TER']) AND NONE(rel IN r11 WHERE TYPE(rel) IN ['CONNECTED_TO_SEC', 'CONNECTED_TO_TER'])
            RETURN *
        `;
    }
    var config_pod = neo_viz_config(true, "viz_pod", p , seed)
    viz_pod = new NeoVis.default(config_pod);
    viz_pod.render();
    // Get seed method: This number is printed when you use getSeed in order for the objects within a certain view to not overlap each ther everytime you click show 1645578356529
    //viz_pod.registerOnEvent("completed", function (){
    //console.log(viz_pod._network.getSeed())
    //})
}

function pod_namespace(namespace) {
    selectedPodNamespace = namespace
    selectView()
    
    // Clear search bar
    $("#podname").val("");
    
    // Clear graph 
    if (viz_pod !== null){
        viz_pod.clearNetwork()
    }
    
    // Update data list
    $.ajax({url: "/pod_names?ns="+namespace, success: function(result){
        // $("#datalist").html(result);
        console.log(result)
        // clearing the Pod Names
        $("#PodList").empty();
        // adding the list of Pod Names
        result.pods.forEach(pod => {
            $('#PodList').append(`<option>${pod}</option>`);
        })
      }});
}

/* Check if string is IP */
function checkIfValidIP(str) {
    // Regular expression to check if string is a IP address
    const regexExp = /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/gi;

    return regexExp.test(str);
}

function removeLabelFilter(id){
    $("#"+$.escapeSelector(id)).remove();
    selectedLabelFilters.delete(id)
    selectedView.drawFunc()
}

function addLabelFilter(){
    let label = $("#input-label-filter").val().trim();
    let labelValue = $("#input-label-value-filter").val().trim();
    let filter = DOMPurify.sanitize(`${label}:${labelValue}`)
    let id = filter.replace(':','-').replace('/','_').replace('.','_')
    if (id !== '-' && !selectedLabelFilters.has(id)){
        let html = 
            `<span id="${id}" class="label label--dark label--round half-margin-left qtr-margin-top">
                <span>${filter}</span>
                <span class="icon-close" onclick="removeLabelFilter('${id}')"></span>
            </span>`
        $('#filtered-container').append(html);
        selectedLabelFilters.set(id, filter)
    }
    closeModal('modal-small-label')
    selectedView.drawFunc()
}

function label_values() {
    
    // Clear value filter
    $("#input-label-value-filter").val("");
    
    // getting the label
    let label = $("#input-label-filter").val();

    // Update data list
    $.ajax({url: "/label_values?label="+label, success: function(result){
        console.log(result)
        // clearing the label values
        $("#LabelValueList").empty();
        // adding the list of label Values
        result.values.forEach(value => {
            $('#LabelValueList').append(`<option>${value}</option>`);
        })
      }});
}
