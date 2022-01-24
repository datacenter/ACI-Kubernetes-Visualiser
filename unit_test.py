from app.graph import vkaci_draw, vkaci_build_topology, vkaci_env_variables
import unittest
import json

class testvkacigraph(unittest.TestCase):

    """New Fake data for unit testing"""

    # Opening JSON file
    f = open('app/test_topology.json')
 
    # returns JSON object as a dictionary
    data = json.load(f)
    
    # Closing file
    f.close()

    def test_vkaci_graph(self):
        draw = vkaci_draw(self.data)
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
# visualisation to replace 

    def test_shapes_of_nodes(self):
        """Test the shapes of the nodes in the topology"""
        draw = vkaci_draw(None)
# visualisation to replace 

    def test_no_env_variables(self):
        """Test that no environment variables are handled"""
        # Arange
        build = vkaci_build_topology(vkaci_env_variables({}))
        
        # Act
        build.update()

        # Assert
        self.assertEqual(build.env.mode, 'None')
        self.assertIsNone(build.aci_vrf)
        self.assertEqual(len(build.env.apic_ip), 0)
        

if __name__ == '__main__':
    unittest.main()

