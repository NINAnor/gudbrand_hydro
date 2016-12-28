from grass.pygrass.vector.table import *
#from grass.pygrass.vector.geometry import *
import sqlite3
import grass.script as gscript
import os
import sys
from datetime import datetime

catchment = '002_34'
type = sys.argv[1] # main / contribut
DEM = 'HYDRODEM'
draindir = 'HYDRODEM_draindir@p_Gudbrand_Hydro_stefan.blumentrath'
output = 'streams_002_34_main_seg1000_net_catchments'
e_mapset = 'p_Gudbrand_Hydro_Egenskapsgrid'
o_mapset = 'p_Gudbrand_Hydro_lars.erikstad'
s_mapset = 'p_Gudbrand_Hydro_stefan.blumentrath'
maps = filter(None, gscript.read_command('g.list', type='raster', pattern='eg_*', mapset=e_mapset).split('\n'))
dem_stats = ['HYDRODEM', 'HYDRODEM_slope', 'HYDRODEM_aspect']
suffix = sys.argv[2] if len(sys.argv) >= 3 else None # 1 # SUFFIX
input = 'streams_{}_{}_seg1000_net'.format(catchment, type)

if suffix:
	outfile = '/home/stefan.blumentrath/gudbrand_hydro/SQLite/{}_{}.sqlite'.format(input, suffix)
else:
	outfile = '/home/stefan.blumentrath/gudbrand_hydro/SQLite/{}.sqlite'.format(input)

if os.path.isfile(outfile):
    os.remove(outfile)
else:
    print outfile
# Add required mapsets to searchpath
gscript.run_command('g.mapsets', operation='add', mapset=','.join([e_mapset, o_mapset, s_mapset, 'p_Gudbrand_Hydro']))

# Create sequence
#gscript.read_command('v.db.select', columns=','join(['neighborhood', 'cluster']), where='neighborhood={}'.format(suffix))
if suffix:
    nbhs = map(int, filter(None, gscript.read_command('v.db.select', flags='c', map=input, layer=2, columns='neighborhood', where="CAST(neighborhood AS TEXT) LIKE '%{}'".format(suffix)).split('\n')))
else:
    nbhs = map(int, filter(None, gscript.read_command('v.db.select', flags='c', map=input, layer=2, columns='neighborhood').split('\n')))
nbhs = set(nbhs)
nbhs = list(nbhs)
nbhs.sort()

#nbhs = set(v.db.select -c map=streams_002_34_main_seg1000_net@p_Gudbrand_Hydro_stefan.blumentrath layer=2 columns=neighborhood,cluster where="CAST(neighborhood AS TEXT) LIKE '%{}'".format(suffix))
gscript.run_command('g.region', flags='p', raster=draindir, align=draindir)
i = 0
for n in nbhs:
    i = i + 1
    start = datetime.now()
    print 'Computing step {} of {}'.format(i, len(nbhs))
    gscript.run_command('v.extract', overwrite=True, quiet=True, input=input, layer=2, where="neighborhood = {}".format(n), output='{}_nbh{}'.format(input, n))
    #gscript.run_command('g.region', vector='{}_nbh{}'.format(input, n), align=draindir)
    gscript.run_command('v.to.rast', overwrite=True, quiet=True, input='{}_nbh{}'.format(input, n), layer=2, type='point', where="neighborhood = {}".format(n), output='{}_nbh{}'.format(input, n), use='cat', memory=30000)

    # Generate watershed
    gscript.run_command('r.stream.basins', overwrite=True, quiet=True, direction=draindir, stream_rast='{}_nbh{}'.format(input, n), memory=30000, basins='{}_nbh{}_basins'.format(input, n))

    #gscript.run_command('g.region', vector='{}_nbh{}'.format(input, n), align=draindir)
    gscript.run_command('r.to.vect', overwrite=True, quiet=True, flags='v', input='{}_nbh{}_basins'.format(input, n), output='{}_nbh{}_basins'.format(input, n), type='area')

    # Get cats
    #cats = set(map(int, filter(None, gscript.read_command('v.db.select', flags='c', map='{}_nbh{}'.format(input, n), columns='cat', layer=2).split('\n'))))
    #SQL_dict = dict.fromkeys(cats,[])

    path = '$GISDBASE/$LOCATION_NAME/$MAPSET/sqlite/sqlite.db'
    conn = sqlite3.connect(get_path(path))

    for m in maps:
        attrs = []
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS {0}_stat'.format(m))
        SQL_create = """CREATE TABLE {0}_stat (cat integer, {0} integer);""".format(m)
        c.execute(SQL_create)
        conn.commit()
        # Adjust computational region to Egenskapsgrid
        gscript.run_command('g.region', vector='{}_nbh{}_basins'.format(input, n), align=m)

        stat = filter(None, gscript.read_command('r.univar', quiet=True, flags='t', map=m, zones='{}_nbh{}_basins'.format(input, n)).split('\n')[1:])
        for s in stat:
            attrs.append((int(s.split('|')[0]), int(s.split('|')[2])))
        c.executemany('INSERT INTO {0}_stat VALUES (?,?)'.format(m), attrs)
        conn.commit()
        gscript.run_command('v.db.join', map='{}_nbh{}_basins'.format(input, n), layer=1,
                            column='cat', other_table='{0}_stat'.format(m),
                            other_column='cat', quiet=True)
        c.execute('DROP TABLE IF EXISTS {0}_stat'.format(m))

    for d in dem_stats:
        attrs = []
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS {0}_stat'.format(d))
        SQL_create = """CREATE TABLE {0}_stat (cat integer, {0}_min double precision, {0}_max double precision, {0}_avg double precision, {0}_stddev double precision);""".format(d)
        c.execute(SQL_create)
        conn.commit()
        # Adjust computational region to DEM
        gscript.run_command('g.region', vector='{}_nbh{}_basins'.format(input, n), align=d)
	
        stat = filter(None, gscript.read_command('r.univar', quiet=True, flags='t', map=d, zones='{}_nbh{}_basins'.format(input, n)).split('\n')[1:])
        for s in stat:
            attrs.append((float(s.split('|')[0]), float(s.split('|')[4]), float(s.split('|')[5]), float(s.split('|')[7]), float(s.split('|')[9])))
        c.executemany('INSERT INTO {0}_stat VALUES (?,?,?,?,?)'.format(d), attrs)
        conn.commit()
        gscript.run_command('v.db.join', map='{}_nbh{}_basins'.format(input, n), layer=1,
                            column='cat', other_table='{0}_stat'.format(d),
                            other_column='cat', quiet=True)
        c.execute('DROP TABLE IF EXISTS {0}_stat'.format(d))

			
    gscript.run_command('g.region', raster=draindir, align=draindir)
    gscript.run_command('g.remove', quiet=True, flags='f', type='vector', pattern='{}_nbh{}'.format(input, n))
    # Check if SQLite output exists or not
    # v.out.ogr -m --overwrite input=streams_002_34_contribut_seg1000_net_nbh31_basins@p_Gudbrand_Hydro_stefan.blumentrath type=area output=/data/test format=SQLite output_layer=catchments
    #Export result to SQLite
    if not os.path.isfile(outfile):
    	gscript.run_command("v.out.ogr", flags="m", input='{}_nbh{}_basins'.format(input, n), output=outfile, format="SQLite", olayer=input, lco="OVERWRITE=YES,GEOMETRY_NAME=geom,FID=fid,LAUNDER=YES", overwrite=True, quiet=True)
    else:
    	gscript.run_command("v.out.ogr", flags="mua", input='{}_nbh{}_basins'.format(input, n), output=outfile, format="SQLite", olayer=input, lco="OVERWRITE=YES,GEOMETRY_NAME=geom,FID=fid,LAUNDER=YES", quiet=True)

    print 'Took {}'.format(datetime.now() - start)
