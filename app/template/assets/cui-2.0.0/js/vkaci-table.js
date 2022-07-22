// Tables enums can be grouped as static members of a class
class Table {
  // Create new instances of the same class as static attributes
  static All = new Table("All", "Complete Topology")
  static LeafsAndPods = new Table("LeafsAndPods", "Leafs & Pods")
  static LeafsAndNodes = new Table("LeafsAndNodes", "Leafs & Nodes")
  static BgpPeers = new Table("BgpPeers", "BGP Peering")

  constructor(name, displayName) {
    this.name = name
    this.displayName = displayName
  }
}

var gridd = null
selectedTable = Table.All

function table_all() {
  selectedTable = Table.All
  selectTable()
  renderAllTable()
}

function table_leafs_pods() {
  selectedTable = Table.LeafsAndPods
  selectTable()
  renderLeafPodTable()
}

function table_leafs_nodes() {
  selectedTable = Table.LeafsAndNodes
  selectTable()
  renderLeafNodeTable()
}

function table_bgp_peers() {
  selectedTable = Table.BgpPeers
  selectTable()
  renderBgpPeerTable()
}

function renderAllTable() {
  gridd = {
    view: "treetable",
    css: "webix_dark",
    container: "table",
    id: "gridd",
    resizeColumn: true, resizeRow: true,
    columns: [
      {
        id: "value", header: ["Name", { content: "textFilter" }], width: 300,
        template: "{common.icon()} <img src=./assets/cui-2.0.0/img/#image# width=16 height=16 style='margin:3px 4px 0px 1px;'><span>#value#</span>",
      },
      { id: "ns", header: ["Namespace", { content: "selectFilter" }], width: 150 },
      { id: "ip", header: ["IP", { content: "textFilter" }], width: 200 },
      { id: "interface", header: ["Interface", { content: "selectFilter" }], width: 200 },
    ],

    autoheight: true,
    scroll: false,
    url: "/table_data", datatype: "json"
  };
  $("#table").empty()
  webix.ui(gridd);
}

function renderLeafPodTable() {
  gridd = {
    view: "treetable",
    css: "webix_dark",
    container: "table",
    id: "gridd",
    resizeColumn: true, resizeRow: true,
    columns: [
      {
        id: "value", header: ["Name", { content: "textFilter" }], width: 300,
        template: "{common.icon()} <img src=./assets/cui-2.0.0/img/#image# width=16 height=16 style='margin:3px 4px 0px 1px;'><span>#value#</span>",
      },
      { id: "label_value", header: ["Label Value", { content: "textFilter" }], width: 200 },
      { id: "ns", header: ["Namespace", { content: "selectFilter" }], width: 150 },
      { id: "ip", header: ["IP", { content: "textFilter" }], width: 200 },
    ],

    autoheight: true,
    scroll: false,
    url: "/table_data_pod", datatype: "json"
  };
  $("#table").empty()
  webix.ui(gridd);
}

function renderLeafNodeTable() {
  gridd = {
    view: "treetable",
    css: "webix_dark",
    container: "table",
    id: "gridd",
    resizeColumn: true, resizeRow: true,
    columns: [
      {
        id: "value", header: ["Name", { content: "textFilter" }], width: 300,
        template: "{common.icon()} <img src=./assets/cui-2.0.0/img/#image# width=16 height=16 style='margin:3px 4px 0px 1px;'><span>#value#</span>",
      },
      { id: "label_value", header: ["Label Value", { content: "textFilter" }], width: 200 },
      { id: "ip", header: ["IP", { content: "textFilter" }], width: 200 },
      { id: "interface", header: ["Interface", { content: "selectFilter" }], width: 200 },
    ],

    autoheight: true,
    scroll: false,
    url: "/table_data_node", datatype: "json"
  };
  $("#table").empty()
  webix.ui(gridd);
}

function renderBgpPeerTable() {
  gridd = {
    view: "treetable",
    css: "webix_dark",
    container: "table",
    id: "gridd",
    resizeColumn: true, resizeRow: true,
    columns: [
      {
        id: "value", header: ["Name / Route", { content: "textFilter" }], width: 300,
        template: "{common.icon()} <img src=./assets/cui-2.0.0/img/#image# width=16 height=16 style='margin:3px 4px 0px 1px;'><span>#value#</span>",
      },
      { id: "ip", header: ["IP / NextHop", { content: "textFilter" }], width: 200 },
      { id: "k8s_route", header: ["K8s Route", { content: "selectFilter" }], width: 100 },
      { id: "ns", header: ["Namespace", { content: "selectFilter" }], width: 200 },
      { id: "svc", header: ["Service", { content: "selectFilter" }], width: 200 }
    ],
    on:{
      "onAfterFilter": function () {
        var grid = $$("gridd")
        var ns = grid.getFilter("ns").value
        var columns = grid.config.columns;
        // Update data list
        $.ajax({
          url: "/service_names?ns=" + ns, success: function (result) {
            // adding the list of Service Names
            columns[4].options = result.svc
            grid.refreshColumns(columns);
          }
        });
      }
    },
    autoheight: true,
    scroll: false,
    url: "/table_data_bgp", datatype: "json"
  };
  $("#table").empty()
  webix.ui(gridd);
}

function renderTable() {
  if (gridd === null) {
    table_all()
  }
}

function selectTable() {
  $("#selected_table").find("a").each(function () {
    var a = $(this)
    if (a.attr("id") == selectedTable.name) {
      a.addClass("selected")
    }
    else {
      a.removeClass("selected")
    }
  });
  $("#table_title").text(selectedTable.displayName)
}

function openAll(){
  $$("gridd").openAll()
}

function closeAll(){
  $$("gridd").closeAll()
}
