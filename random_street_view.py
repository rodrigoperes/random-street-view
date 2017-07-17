import pandas as pd
import numpy as np
import argparse
import os
import random
import shapefile
import sys
import requests
import time
import json

# Read CSV country file

paises = pd.read_csv("UNSD Methodology.csv")

paises = paises[paises['Region Name'].isin(['Europe', 'Oceania']) | 
       paises['Country or Area'].isin(['South Africa','Botswana','Ghana','Senegal',
                                       'Sri Lanka','Bangladesh','Japan', 'South Korea','Mexico']) |
       paises['Intermediate Region Name'].isin(['South America']) | 
       paises['Sub-region Name'].isin(['Northern America','South-eastern Asia'])]

shape_file = "TM_WORLD_BORDERS-0.3.shp"
if not os.path.exists(shape_file):
    print("Cannot find " + shape_file + ". Please download it from "
    "http://thematicmapping.org/downloads/world_borders.php "
    "and try again.")
    sys.exit()

sf = shapefile.Reader(shape_file)

records = pd.DataFrame([record for record in sf.records()])
shapes = pd.DataFrame([record for record in sf.shapes()])
shapes = shapes[records[2].isin(list(paises["ISO-alpha3 Code"]))]
records = records[records[2].isin(list(paises["ISO-alpha3 Code"]))]

# Determine if a point is inside a given polygon or not
# Polygon is a list of (x,y) pairs.
# http://www.ariel.com.au/a/python-point-int-poly.html
def point_inside_polygon(x, y, poly):
	n = len(poly)
	inside = False
	p1x, p1y = poly[0]
	for i in range(n+1):
		p2x, p2y = poly[i % n]
		if y > min(p1y, p2y):
			if y <= max(p1y, p2y):
				if x <= max(p1x, p2x):
					if p1y != p2y:
						xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
					if p1x == p2x or x <= xinters:
						inside = not inside
		p1x, p1y = p2x, p2y
	return inside
    
def get_street_view_images_2(images_wanted, paises, formas):
	# Google Street View Image API
	# 25,000 image requests per 24 hours
	# See https://developers.google.com/maps/documentation/streetview/
	API_KEY = "AIzaSyC4tTaiv-T9hjjyt2nQ-eb8cm0fHeDt2os"
	GOOGLE_URL = ("http://maps.googleapis.com/maps/api/streetview?sensor=false&"
			"size=640x640&key=" + API_KEY)
	META_URL = ("https://maps.googleapis.com/maps/api/streetview/metadata?"
			"key=" + API_KEY)

	IMG_PREFIX = "img_"
	IMG_SUFFIX = ".jpg"

	attempts, imagery_hits= 0, 0

	if not os.path.exists("Images 2"):
		os.makedirs("Images 2")

	images = os.listdir("Images 2")
	images = [i.replace(IMG_PREFIX,'').replace(IMG_SUFFIX,'') for i in images]

	coord_set = set(images)
	local_hit = 0
	local_start_time = 0

	start_time = time.time()
	try:
		elapsed_time = 0
		while(1):
			elapsed_time = time.time() - start_time 
			attempts += 1
			if (local_hit == 0):
				i = int(np.random.choice(range(0,len(paises)),1))
				#print(i)
				record = paises.iloc[i]
				heading = str(random.random()*360)
				#print("Finding country")
				#print(record[2], record[4])
				#print(shapes.iloc[i][0].bbox)
				min_lon = formas.iloc[i][0].bbox[0]
				min_lat = formas.iloc[i][0].bbox[1]
				max_lon = formas.iloc[i][0].bbox[2]
				max_lat = formas.iloc[i][0].bbox[3]
				borders = formas.iloc[i][0].points
				rand_lat = round(random.uniform(min_lat, max_lat),2)
				rand_lon = round(random.uniform(min_lon, max_lon),2)
				#print(attempts, rand_lat, rand_lon)
			else:
				if (time.time() - local_start_time >= 10):
					local_hit = 0
					attempts -= 1
					continue
				rand_lat = round(random.uniform(rand_lat - rand_lat/60, rand_lat + rand_lat/60),2)
				rand_lon = round(random.uniform(rand_lon - rand_lon/60, rand_lon + rand_lon/60),2)
			lat_lon = str(rand_lat) + "," + str(rand_lon)
			if lat_lon in coord_set:
				continue
			# Is (lat,lon) inside borders?
			if point_inside_polygon(rand_lon, rand_lat, borders):
				#print("  In country")
				#country_hits += 1
				#print(lat_lon)
				outfile = os.path.join("Images 2", IMG_PREFIX + lat_lon + IMG_SUFFIX)
				meta_url = META_URL + "&location=" + lat_lon
				print(meta_url)
				url = GOOGLE_URL + "&location=" + lat_lon
				url += "&heading=" + heading
				try:
					#r = requests.get(url, stream=True)
					#with open(outfile, 'wb') as f:
					#	for chunk in r:
					#		f.write(chunk)
					r = requests.get(meta_url, stream=True)
					metadata = json.loads(r.text)
					print(metadata["status"])
				except KeyboardInterrupt:
					elapsed_time = time.time() - start_time
					#print("Keyboard interrupt")
				except:
					pass
				# if os.path.isfile(outfile):
					#print(lat_lon)
					# if os.path.getsize(outfile) < 9000:
						#print("    No imagery")
						#imagery_misses += 1
						# os.remove(outfile)
					# else:
						#print("    ========== Got one! ==========")
						# coord_set.add(lat_lon)
						# imagery_hits += 1
						# local_hit = 1
						# local_start_time = time.time()
						# if imagery_hits == images_wanted:
							# elapsed_time = time.time() - start_time
							# break
	except KeyboardInterrupt:
		elapsed_time = time.time() - start_time
		#print("Keyboard interrupt")

	print("Elapsed time:\t", elapsed_time)
	print("Number of hits:\t", imagery_hits)
	print("Imagery hit rate per second:\t", imagery_hits/elapsed_time)

	return imagery_hits

get_street_view_images_2(1000, records, shapes) 