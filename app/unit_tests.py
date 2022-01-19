from graph import vkaci_draw
import unittest
import json

"""New Fake data for unit testing"""

# Opening JSON file
f = open('test_topology.json')
 
# returns JSON object as
# a dictionary
data = json.load(f)
 
# Closing file
f.close()




class testvkacigraph(unittest.TestCase):

    def test_vkaci_graph(self):
        draw = vkaci_draw(data)
        draw.add_pod("goldpinger-znt4g")
        g = draw.get_gRoot()
        nodes = g.number_of_nodes()
        edges = g.number_of_edges()
        #draw.svg("goldpinger-znt4g")
        self.assertEqual(nodes,7)
        self.assertEqual(edges,6)
        

    def test_no_topology(self):
        """Test that no topology throws an error"""
        draw = vkaci_draw(None)
        with self.assertRaises(AttributeError):
            draw.add_pod("goldpinger-znt4g")

    def test_empty_topology(self):
        """Test that an empty topology file loads"""
        draw = vkaci_draw({})
        draw.add_pod("goldpinger-znt4g")
        g = draw.get_gRoot()
        nodes = g.number_of_nodes()
        edges = g.number_of_edges()
        self.assertEqual(nodes,1)
        self.assertEqual(edges,0)
        

    def test_pod_not_in_topology(self):
        """Test any pod midsing from the topology"""
        draw = vkaci_draw(None)
# In progress

    def test_shapes_of_nodes(self):
        """Test the shapes of the nodes in the topology"""
        draw = vkaci_draw(None)
# In progress

        

       


  

unittest.main()

