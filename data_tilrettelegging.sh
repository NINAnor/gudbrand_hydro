
#############################################################################################################################################
### Egenskapsgrid

for m in BrattO10 Midlere4_10 Rolig2_4 bre elver flattu2uvann gab innsjo konfast magasin myr storelv
do
g.region -p raster=$m align=$m
r.mapcalc --o --v expression="eg_${m}=if(${m}==0,null(),${m})"
done


### Clean "egenskapsgrid"
# N50_adekke     2 (Dyrket), 6 (Skog), 8 (Aapent) 	
echo '2 = 1
* = NULL' | r.reclass input=n50_adekke output=eg_n50_dyrketMark rules=- --o --v


# treslagAR5 		31 (Barskog), 32 (Lauvskog), 33 (Blandingsskog)
echo '31 = 1
* = NULL' | r.reclass input=treslagAR5 output=eg_ar5_barskog rules=- --o --v
echo '32 = 1
* = NULL' | r.reclass input=treslagAR5 output=eg_ar5_lauvskog rules=- --o --v
echo '33 = 1
* = NULL' | r.reclass input=treslagAR5 output=eg_ar5_blandingsskog rules=- --o --v

# RikhetBG  		1 (fattig), 2 (middels), 3 (rik)
echo '1 = 1
* = NULL' | r.reclass input=rikhetBG output=eg_bg_fattig rules=- --o --v
echo '2 = 1
* = NULL' | r.reclass input=rikhetBG output=eg_bg_middels rules=- --o --v
echo '3 = 1
* = NULL' | r.reclass input=rikhetBG output=eg_bg_rik rules=- --o --v

# Snauar  		51 (impediment), 52 (Flekkvis_skrinn), 53 (lavmark),  54 (middels), 55 (frisk)
echo '51 = 1
* = NULL' | r.reclass input=snauarveg output=eg_ar50_snauarveg_impediment rules=- --o --v
echo '52 = 1
* = NULL' | r.reclass input=snauarveg output=eg_ar50_snauarveg_flekkvisSkrinn rules=- --o --v
echo '53 = 1
* = NULL' | r.reclass input=snauarveg output=eg_ar50_snauarveg_lavmark rules=- --o --v
echo '54 = 1
* = NULL' | r.reclass input=snauarveg output=eg_ar50_snauarveg_middels rules=- --o --v
echo '55 = 1
* = NULL' | r.reclass input=snauarveg output=eg_ar50_snauarveg_frisk rules=- --o --v

#############################################################################################################################################
### Terrain model
elvenett=Elv_Elvenett
DEM=HYDRODEM@p_Gudbrand_Hydro
DEM_stream=DEM_elvenett
g.region -p raster=$DEM align=$DEM
v.to.rast --o --v -d input=$elvenett output=$elvenett use=val val=1
r.mapcalc --o expression="${DEM_stream}=10.0+if(isnull(${elvenett}),${DEM},${DEM}-10.0)"
# r.carve -n --overwrite --verbose raster=HYDRODEM@p_Gudbrand_Hydro vector=Elv_Elvenett@p_Gudbrand_Hydro_Egenskapsgrid output=HYDRODEM_carved points=HYDRODEM_stream_points_adjusted
r.watershed --overwrite --verbose elevation=$DEM_stream accumulation=HYDRODEM_accum tci=HYDRODEM_tci spi=HYDRODEM_spi drainage=HYDRODEM_draindir memory=30000
r.stream.extract --overwrite --verbose elevation=$DEM_stream accumulation=HYDRODEM_accum threshold=400 stream_length=5 memory=30000 stream_raster=HYDRODEM_streams stream_vector=HYDRODEM_streams
r.stream.basins -l --overwrite --verbose direction=HYDRODEM_draindir coordinates=257687,6580087 memory=30000 basins=HYDRODEM_basin
r.to.vect --overwrite --verbose input=HYDRODEM_basin output=HYDRODEM_basin type=area

r.slope.aspect elevation=$DEM slope=HYDRODEM_slope aspect=HYDRODEM_aspect
## v.overlay --overwrite --verbose ainput=Elv_Elvenett@p_Gudbrand_Hydro_Egenskapsgrid atype=line binput=HYDRODEM_basin@p_Gudbrand_Hydro_stefan.blumentrath operator=and output=Elvenett_HYDRODEM_basin olayer=0,1,0
## v.to.points -i --overwrite --verbose input=Elvenett_HYDRODEM_basin@p_Gudbrand_Hydro_stefan.blumentrath type=line output=Elvenett_HYDRODEM_basin_points use=vertex dmax=500
## v.build.polylines --overwrite --verbose input=Elvenett_HYDRODEM_basin@p_Gudbrand_Hydro_stefan.blumentrath output=Elvenett_HYDRODEM_basin_polylines cats=first type=line

# v.split -f --overwrite input=hovedelv output=hovedelv_segments_1000 length=1000
#############################################################################################################################################
### Stream network

stream_network=Elv_Elvenett
catchment='002-34'
catchmentMapSuffix=$(echo '002-34' | tr '-' '_')
segLength=1000

mkdir gudbrand_hydro
mkdir gudbrand_hydro/SQLite

v.in.ogr input="PG:dbname=gisdata" layer="Topography.Norway_N50_ArealdekkeFlate" where="\"OBJTYPE\"='Innsjø'" snap=0.01 output=N50_innsjoe --o

# Extract streams in catchment
v.extract --overwrite --verbose input=$stream_network layer="1" type="line" where="elvID LIKE '${catchment}-%'" output=streams_${catchmentMapSuffix} new=-1

# Extract main stream
v.extract --overwrite --verbose input=streams_${catchmentMapSuffix} layer="1" type="line" where="elvID = '${catchment}-1'" output=streams_${catchmentMapSuffix}_main_pre new=-1
v.to.rast --o --v -d input=streams_${catchmentMapSuffix}_main_pre output=streams_${catchmentMapSuffix}_main_pre use=val val=1
r.buffer --o --v input=streams_${catchmentMapSuffix}_main_pre output=streams_${catchmentMapSuffix}_main_pre_buffer distances=35.4
r.mapcalc --o --v expression="streams_${catchmentMapSuffix}_main_buffer=if(streams_${catchmentMapSuffix}_main_pre_buffer,1,null())"
r.to.vect --overwrite --verbose -s input=streams_${catchmentMapSuffix}_main_buffer output=streams_${catchmentMapSuffix}_main_buffer_full type=area

# Buffer main streams by one pixel
#v.buffer --overwrite --verbose input=streams_${catchmentMapSuffix}_main_pre type=line output=streams_${catchmentMapSuffix}_main_buffer distance=50
v.buffer --overwrite --verbose input=streams_${catchmentMapSuffix}_main_buffer_full output=streams_${catchmentMapSuffix}_main_buffer distance=-12.5

###
# Contributories
###
# Extract contributories
v.overlay --overwrite --verbose ainput=streams_${catchmentMapSuffix} atype=line binput=streams_${catchmentMapSuffix}_main_buffer operator=not output=streams_${catchmentMapSuffix}_contribut_pre olayer=0,1,0

# Remove lake areas
v.overlay --overwrite --verbose ainput=streams_${catchmentMapSuffix}_contribut_pre atype=line binput=N50_innsjoe operator=not output=streams_${catchmentMapSuffix}_contribut olayer=0,1,0

# Split contributories into segments of max 1 km
v.split -f --overwrite input=streams_${catchmentMapSuffix}_contribut output=streams_${catchmentMapSuffix}_contribut_seg$segLength length=$segLength

~/Avd15GIS/Prosjekter/Gudbrand_Hydro/v.igraph.order.py --overwrite --verbose input=streams_${catchmentMapSuffix}_contribut_seg$segLength output=streams_${catchmentMapSuffix}_contribut_seg${segLength}_net # node_layer=1 # with nodes on layer 1 output can be used in r.stream.basins

python ~/Avd15GIS/Prosjekter/Gudbrand_Hydro/stream_watershed.py contribut

###
# Main stream
###

# Remove lake areas
v.overlay --overwrite --verbose ainput=streams_${catchmentMapSuffix}_main_pre atype=line binput=N50_innsjoe operator=not output=streams_${catchmentMapSuffix}_main olayer=0,1,0

# Split main stream into segments of max 1 km
v.split -f --overwrite input=streams_${catchmentMapSuffix}_main output=streams_${catchmentMapSuffix}_main_seg$segLength length=$segLength

~/Avd15GIS/Prosjekter/Gudbrand_Hydro/v.igraph.order.py --overwrite --verbose input=streams_${catchmentMapSuffix}_main_seg$segLength output=streams_${catchmentMapSuffix}_main_seg${segLength}_net # node_layer=1 # with nodes on layer 1 output can be used in r.stream.basins

python ~/Avd15GIS/Prosjekter/Gudbrand_Hydro/stream_watershed.py main
