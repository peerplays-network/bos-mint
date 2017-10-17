'''
Created on 13.10.2017

@author: schiessl
'''
import unittest
from multiprocessing.pool import Pool
from app.node import Node
from peerplays.peerplays import PeerPlays


class Test(unittest.TestCase):


    def setUp(self):
        wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"

        Node.node = PeerPlays(
            nobroadcast=True,
            wif=[wif]
        )

    def tearDown(self):
        pass

#     def getMockSportNewForm(self):
#         sportForm = SportNewForm()
#         
#         # empty the fieldlist
#         while len(sportForm.names) > 0:
#             sportForm.names.pop_entry()
#                 
#         lng1 = InternationalizedString( "de", "Tischtennis" )
#         lng2 = InternationalizedString( "en", "Table tennis" )
#         
#         # append entry to a FieldList creates forms from dictionary!                            
#         sportForm.names.append_entry( lng1.getForm() )
#         sportForm.names.append_entry( lng2.getForm() )

    def testSportCreateNode(self):
#         sportForm = self.getMockSportNewForm()
        proposal = Node().createSport( [("de", "Tischtennis" ), ( "en", "Table tennis" )] )
        
        tx = proposal.json()
        ops = tx["operations"]
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0][0], 22)
        prop = ops[0][1]
        self.assertEqual(len(prop["proposed_ops"]), 1)
        
        prop_op = prop["proposed_ops"][0]['op']
        self.assertEqual(prop_op[0], 47) # create sport id 
        self.assertEqual(prop_op[1]['name'], [['de', 'Tischtennis'], ['en', 'Table tennis']]) # correct names reflected
