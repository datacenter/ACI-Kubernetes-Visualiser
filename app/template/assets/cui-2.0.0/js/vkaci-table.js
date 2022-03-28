
var photo = function (obj) {
  if (obj.image)
    return "{common.icon()} <img src=./assets/cui-2.0.0/img/#image# width=16 height=16 style='margin:3px 4px 0px 1px;'><span>#value#</span>";
  return "";
};

var gridd = {
  view: "treetable",
  css: "webix_dark",
  container: "table",
  resizeColumn: true, resizeRow: true,
  columns: [
    // { id: "id", header: "", css: { "text-align": "right" }, width: 50 },
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

webix.ui(gridd);



