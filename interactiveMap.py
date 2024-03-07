import geopandas as gpd
import matplotlib as plt

from bokeh.plotting import figure, output_file, save

# Initialize the plot (p) and give it a Title
p = figure(title = "My first Interactive plot !")

# X and Y Coordinates
x_coords = [0,1,2,3,4]
y_coords = [5,4,1,2,0]

#plot the points
p.circle(x=x_coords, y=y_coords, size = 10, color="red")

outfp = r"C:/Users/Joe Chang/Desktop/CS/Python/InteractiveMap/points.html"
save(obj=p, filename=outfp)