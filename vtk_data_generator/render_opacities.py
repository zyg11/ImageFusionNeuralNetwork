import sys
import os
import colorsys
import numpy as np
import math
import pickle
import vtk
from tqdm import tqdm

if len(sys.argv) < 5:
    print('usage: python render_opacities.py volume_dataset view_params opacity_maps color_maps (scalar_field_name) (offset_scale)')
    sys.exit(1)

volume_filename = sys.argv[1]
view_params = np.load(sys.argv[2])
opacity_maps = np.load(sys.argv[3])
color_maps = np.load(sys.argv[4])
base_dir = os.path.dirname(sys.argv[2])
if base_dir[-1] != '/':
    base_dir+='/'

sf_name = 'ImageFile'
if len(sys.argv) >= 6:
    sf_name = sys.argv[5]

offset_scale = 2.0
if len(sys.argv) == 7:
    offset_scale = float(sys.argv[6])

to_render = True

reader = vtk.vtkNIFTIImageReader()
reader.SetFileName(volume_filename)

castFilter = vtk.vtkImageCast()
castFilter.SetInputConnection(reader.GetOutputPort())
castFilter.SetOutputScalarTypeToUnsignedShort()
castFilter.Update()

volume_data = castFilter.GetOutput()

# compute volume center
volume_spacing = np.array(volume_data.GetSpacing())
volume_origin = np.array(volume_data.GetOrigin())
volume_dimensions = np.array(volume_data.GetDimensions())
volume_max = volume_origin+volume_spacing*volume_dimensions
volume_center = 0.5*(volume_origin+volume_max)
volume_diag = volume_max-volume_origin

# setup renderer
renderer = vtk.vtkRenderer()
renderer.SetBackground(0.0,0.0,0.0)
render_window = vtk.vtkRenderWindow()
render_window.SetOffScreenRendering(1)
render_window.AddRenderer(renderer)

# setup camera - default to offset Z-axis
camera = renderer.MakeCamera()
camera.SetPosition(volume_center[0],volume_center[1],volume_center[2]+offset_scale*np.linalg.norm(volume_diag))
camera.SetFocalPoint(volume_center[0],volume_center[1],volume_center[2])
#camera.SetParallelScale(135.24329927948372)
camera.Elevation(-85)
renderer.SetActiveCamera(camera)

# volume properties
prop_volume = vtk.vtkVolumeProperty()
prop_volume.ShadeOff()
prop_volume.SetInterpolationTypeToLinear()

# vtk volume renderer
mapperVolume = vtk.vtkSmartVolumeMapper()
mapperVolume.SetRequestedRenderModeToGPU()
#mapperVolume.SetRequestedRenderModeToRayCast()
mapperVolume.SetBlendModeToComposite()
mapperVolume.SetInputData(volume_data)
actorVolume = vtk.vtkVolume()
actorVolume.SetMapper(mapperVolume)
actorVolume.SetProperty(prop_volume)
renderer.AddActor(actorVolume)

if not os.path.exists(base_dir+'imgs'):
    os.makedirs(base_dir+'imgs')
if not os.path.exists(base_dir+'inputs'):
    os.makedirs(base_dir+'inputs')

output_img_dir = base_dir+'imgs/'
ind = 0
for view_param,opacity_map,color_map in tqdm(zip(view_params,opacity_maps,color_maps)):
    rel_filename = 'opacity'+str(ind)+'.png'
    elev,azimuth,roll,zoom = view_param

    if to_render:
        vtk_opacity_map = vtk.vtkPiecewiseFunction()
        for op_val in opacity_map:
            vtk_opacity_map.AddPoint(op_val[0],op_val[1])
        vtk_color_map = vtk.vtkColorTransferFunction()
        for color_val in color_map:
            vtk_color_map.AddRGBPoint(color_val[0],1.0,1.0,1.0)

        prop_volume.SetScalarOpacity(vtk_opacity_map)
        prop_volume.SetColor(vtk_color_map)

        # camera
        camera.Elevation(elev)
        camera.Azimuth(azimuth)
        camera.Roll(roll)
        camera.Zoom(zoom)

        # render to image
        render_window.Render()
        window_to_image = vtk.vtkWindowToImageFilter()
        window_to_image.SetInputBufferTypeToRGBA()
        window_to_image.SetInput(render_window)
        window_to_image.Update()

        image_writer = vtk.vtkPNGWriter()
        image_writer.SetFileName(output_img_dir+rel_filename)
        image_writer.SetInputConnection(window_to_image.GetOutputPort())
        image_writer.Write()

        # undo camera
        camera.Zoom(1.0/zoom)
        camera.Roll(-roll)
        camera.Azimuth(-azimuth)
        camera.Elevation(-elev)
    #

    ind+=1
#
