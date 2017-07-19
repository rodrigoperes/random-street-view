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
records.columns = ['0a','1','ISO-alpha3 Code','3','4','5','6','7','8','9','10']
shapes = pd.DataFrame([record for record in sf.shapes()])

records = pd.concat([records, shapes], axis = 1)
records = pd.merge(records, paises[[10,14]], on=['ISO-alpha3 Code'])


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
    
def get_street_view_images(images_wanted, development, paises):
	# Google Street View Image API
	# 25,000 image requests per 24 hours
	# See https://developers.google.com/maps/documentation/streetview/
	API_KEY = "AIzaSyC4tTaiv-T9hjjyt2nQ-eb8cm0fHeDt2os"
	GOOGLE_URL = ("http://maps.googleapis.com/maps/api/streetview?sensor=false&"
			"size=227x227&fov=120&key=" + API_KEY)
	META_URL = ("https://maps.googleapis.com/maps/api/streetview/metadata?"
			"key=" + API_KEY)

	IMG_PREFIX = "img_"
	IMG_SUFFIX = ".jpg"

	attempts, imagery_hits= 0, 0

	if not os.path.exists(development):
		os.makedirs(development)

	images = os.listdir(development)
	images = [i.replace(IMG_PREFIX,'').replace(IMG_SUFFIX,'') for i in images]
    
	coord_set = set(images)
	paises = paises[paises['Developed / Developing Countries'] == development]
    
	start_time = time.time()
	try:
		elapsed_time = 0
		while(1):
			elapsed_time = time.time() - start_time 
			attempts += 1
			i = int(np.random.choice(range(0,len(paises)),1))
			#print(paises.iloc[i][4])
			min_lon = paises.iloc[i][0].bbox[0]
			min_lat = paises.iloc[i][0].bbox[1]
			max_lon = paises.iloc[i][0].bbox[2]
			max_lat = paises.iloc[i][0].bbox[3]
			borders = paises.iloc[i][0].points
			rand_lat = round(random.uniform(min_lat, max_lat),2)
			rand_lon = round(random.uniform(min_lon, max_lon),2)
			lat_lon = str(rand_lat) + "," + str(rand_lon)
			if lat_lon in coord_set:
				continue
			# Is (lat,lon) inside borders?
			if point_inside_polygon(rand_lon, rand_lat, borders):
				meta_url = META_URL + "&location=" + lat_lon
				try:
					r = requests.get(meta_url, stream=True)
					metadata = json.loads(r.text)
				except KeyboardInterrupt:
					elapsed_time = time.time() - start_time
				except:
					pass
				if metadata["status"] == "OK":
					#print("    ========== Got one! ==========")
					heading = str(random.random()*360)
					outfile = os.path.join(development, IMG_PREFIX + lat_lon + IMG_SUFFIX)
					url = GOOGLE_URL + "&location=" + lat_lon
					url += "&heading=" + heading
					r = requests.get(url, stream=True)
					with open(outfile, 'wb') as f:
						for chunk in r:
							f.write(chunk)
					coord_set.add(lat_lon)
					imagery_hits += 1
					if imagery_hits == images_wanted:
						elapsed_time = time.time() - start_time
						break
	except KeyboardInterrupt:
		elapsed_time = time.time() - start_time

	print("Elapsed time:\t", elapsed_time)
	print("Number of hits:\t", imagery_hits)
	print("Imagery hit rate per second:\t", imagery_hits/elapsed_time)

	return imagery_hits

get_street_view_images(5000, 'Developing', records) 