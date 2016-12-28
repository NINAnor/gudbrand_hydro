#!/usr/bin/env python

############################################################################
#
# MODULE:       v.igraph.order
# AUTHOR(S):    Stefan Blumentrath
# PURPOSE:      Order nodes in a stream network
# COPYRIGHT:    (C) 2016 by the GRASS Development Team
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################


#%Module
#% description: Orders nodes in a stream network.
#% keyword: vector
#% keyword: network
#% keyword: order
#%End

#%option G_OPT_V_INPUT
#%end
#%option G_OPT_V_FIELD
#%end
#%option G_OPT_V_OUTPUT
#%end

#%option
#% key: node_layer
#% type: integer 
#% answer: 2
#% required: no
#%end


import igraph
import grass.script as gscript

from igraph import *
# import StringIO
#from grass.pygrass.vector import VectorTopo
from grass.pygrass.vector.table import *
#from grass.pygrass.vector.geometry import *
import sqlite3
import tempfile

#print igraph.__version__


def main():
    # gscript.run_command('g.region', flags='p')
    input = options['input']
    # input = '{}_net'.format(oinput)
    layer = options['layer']
    output = options['output']
    node_layer = options['node_layer']

    table = '{}_{}'.format(output, 1)

    # # a tempfile would be needed if graph could be read from an edgelist
    # tmpFile = grass.tempfile()

    gscript.verbose(_("Reading network data..."))

    ## Read Network data from vector map
    gscript.run_command('v.net', flags='c', input=input,
                        output=output, operation='nodes',
                        node_layer=node_layer, quiet=True)

    #gscript.run_command('v.db.addtable', map=output, layer=2, key='cat')
    #gscript.run_command('v.to.db', map=output, layer=node_layer, option='cat', columns='cat', quiet=True)

    # Data has to be parsed or written to file as StringIO objects are not supported by igraph
    # https://github.com/igraph/python-igraph/issues/8
    net = gscript.read_command('v.net', input=output, points=output, node_layer=node_layer,
                             operation='report', quiet=True).split('\n')

    # Parse network data and extract vertices, edges and edge names
    edges = []
    vertices = []
    edge_cat = []
    for l in net:
        if l != '':
            # Names for edges and vertices have to be of type string
            # Names (cat) for edges
            edge_cat.append(l.split(' ')[0])

            # From- and to-vertices for edges
            edges.append((l.split(' ')[1], l.split(' ')[2]))

            # Names (cat) for from-vertices
            vertices.append(l.split(' ')[1])

            # Names (cat) for to-vertices
            vertices.append(l.split(' ')[2])

    # Create Graph object
    g = Graph().as_directed()

    # Add vertices with names
    vertices.sort()
    vertices = set(vertices)
    g.add_vertices(list(vertices))

    # Add vertices with names
    g.add_edges(edges)

    gscript.verbose(_("Computing neighborhood..."))

    # Compute number of vertices that can be reached from each vertex
    # Indicates upstream or downstream position of a node
    g.vs['nbh'] = g.neighborhood_size(mode='out', order=g.diameter())
    g.vs['cl'] = g.as_undirected().clusters().membership

    # Compute incoming degree centrality
    # sources have incoming degree centrality of 0
    g.vs['indegree'] = g.degree(type="in")

    # Compute outgoing degree centrality
    # outlets have outgoing degree centrality of 0
    g.vs['outdegree'] = g.degree(type="out")


    gscript.verbose(_("Writing result to table..."))

    # Get Attributes
    attrs = []
    for n in g.vs:
        attrs.append((int(n['name']), int(n['nbh']), int(n['cl']),
                      int(n['indegree']),int(n['outdegree'])))

    # Write results back to attribute table
    # Note: Backend depenent! For a more general solution this has to be handled
    path = '$GISDBASE/$LOCATION_NAME/$MAPSET/sqlite/sqlite.db'
    conn = sqlite3.connect(get_path(path))
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS {}'.format(table))

    # Create temporary table
    c.execute('''CREATE TABLE {}
                 (cat integer, neighborhood integer,
                  cluster integer, indegree integer,
                  outdegree integer)'''.format(table))
    conn.commit()

    # Insert data into temporary table
    c.executemany('INSERT INTO {} VALUES (?,?,?,?,?)'.format(table), attrs)

    # Save (commit) the changes
    conn.commit()

    # Connect table to output node layer
    gscript.run_command('v.db.connect', map=output, table=table, layer=node_layer, flags='o')
    # Join temporary table to output
    #gscript.run_command('v.db.join', map=output, layer=node_layer,
    #                    column='cat', other_table=tmpTable,
    #                    other_column='cat', quiet=True)

    # Remove temporary table
    #c = conn.cursor()
    #c.execute('DROP TABLE IF EXISTS {}'.format(tmpTable))
    #conn.commit()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()

if __name__ == '__main__':
    options, flags = gscript.parser()
    main()
