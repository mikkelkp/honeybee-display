"""honeybee-display commands."""
import click
import sys
import os
import logging
import json
import pickle
import tempfile
import uuid

from honeybee.model import Model
from honeybee.cli import main

from honeybee_display.attr import FaceAttribute, RoomAttribute

_logger = logging.getLogger(__name__)


# command group for all display extension commands.
@click.group(help='honeybee display commands.')
@click.version_option()
def display():
    pass


@display.command('model-to-vis')
@click.argument('model-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option(
    '--color-by', '-c', help='Text for the property that dictates the colors of '
    'the Model geometry. Choose from: type, boundary_condition, none. '
    'If none, only a wireframe of the Model will be generated (assuming the '
    '--exclude-wireframe option is not used). None is useful when the primary '
    'purpose of  the visualization is to display results in relation to the Model '
    'geometry or display some room_attr or face_attr as an AnalysisGeometry '
    'or Text labels.', type=str, default='type', show_default=True)
@click.option(
    '--wireframe/--exclude-wireframe', ' /-xw', help='Flag to note whether a '
    'ContextGeometry dedicated to the Model Wireframe (in DisplayLineSegment3D) should '
    'be included in the output VisualizationSet.', default=True, show_default=True)
@click.option(
    '--mesh/--faces', help='Flag to note whether the colored model geometries should '
    'be represented with DisplayMesh3D objects instead of DisplayFace3D objects. '
    'Meshes can usually be rendered  faster and they scale well for large models '
    'but all geometry is triangulated (meaning that their wireframe in certain '
    'platforms might not appear ideal).', default=True, show_default=True)
@click.option(
    '--show-color-by/--hide-color-by', ' /-hcb', help='Flag to note whether the '
    'color-by geometry should be hidden or shown by default. Hiding the color-by '
    'geometry is useful when the primary purpose of the visualization is to display '
    'grid-data or room/face attributes but it is still desirable to have the option '
    'to turn on the geometry.', default=True, show_default=True)
@click.option(
    '--room-attr', '-r', help='An optional text string of an attribute that the Model '
    'Rooms have, which will be used to construct a visualization of this attribute '
    'in the resulting VisualizationSet. Multiple instances of this option can be passed '
    'and a separate VisualizationData will be added to the AnalysisGeometry that '
    'represents the attribute in the resulting VisualizationSet (or a separate '
    'ContextGeometry layer if room_text_labels is True). Room attributes '
    'input here can have . that separates the nested attributes from '
    'one another. For example, properties.energy.program_type.',
    type=click.STRING, multiple=True, default=None, show_default=True)
@click.option(
    '--face-attr', '-f', help='An optional text string of an attribute that the Model '
    'Faces have, which will be used to construct a visualization of this attribute in '
    'the resulting VisualizationSet. Multiple instances of this option can be passed and'
    ' a separate VisualizationData will be added to the AnalysisGeometry that '
    'represents the attribute in the resulting VisualizationSet (or a separate '
    'ContextGeometry layer if face_text_labels is True). Face attributes '
    'input here can have . that separates the nested attributes from '
    'one another. For example, properties.energy.construction.',
    type=click.STRING, multiple=True, default=None, show_default=True)
@click.option(
    '--color-attr/--text-attr', help='Flag to note whether to note whether the '
    'input room-attr and face-attr should be expressed as a colored AnalysisGeometry '
    'or a ContextGeometry as text labels.', default=True, show_default=True)
@click.option(
    '--grid-display-mode', '-m', help='Text that dictates how the ContextGeometry '
    'for Model SensorGrids should display in the resulting visualization. The Default '
    'option will draw sensor points whenever there is no grid_data_path and will not '
    'draw them at all when grid data is provided, assuming the AnalysisGeometry of '
    'the grids is sufficient. Choose from: Default, Points, Wireframe, Surface, '
    'SurfaceWithEdges, None.',
    type=str, default='Default', show_default=True)
@click.option(
    '--hide-grid/--show-grid', ' /-sg', help='Flag to note whether the SensorGrid '
    'ContextGeometry should be hidden or shown by default.',
    default=True, show_default=True)
@click.option(
    '--grid-data', '-g', help='An optional path to a folder containing data that '
    'aligns with the SensorGrids in the model. Any sub folder within this path '
    'that contains a grids_into.json (and associated CSV files) will be '
    'converted to an AnalysisGeometry in the resulting VisualizationSet. '
    'If a vis_metadata.json file is found within this sub-folder, the '
    'information contained within it will be used to customize the '
    'AnalysisGeometry. Note that it is acceptable if data and '
    'grids_info.json exist in the root of this grid_data_path. Also '
    'note that this argument has no impact if honeybee-radiance is not '
    'installed and SensorGrids cannot be decoded.',
    default=None, show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option(
    '--grid-data-display-mode', '-dm', help='Text to set the display_mode of the '
    'AnalysisGeometry that is generated from the grid_data_path above. Note '
    'that this has no effect if there are no meshes associated with the model '
    'SensorGrids. Choose from: Surface, SurfaceWithEdges, Wireframe, Points',
    type=str, default='Surface', show_default=True)
@click.option(
    '--active-grid-data', '-ad', help='Text to specify the active data in the '
    'AnalysisGeometry. This should match the name of the sub-folder '
    'within the grid_data_path that should be active. If unspecified, the '
    'first data set in the grid-data with be active.',
    type=str, default=None, show_default=True)
@click.option(
    '--output-format', '-of', help='Text for the output format of the resulting '
    'VisualizationSet File (.vsf). Choose from: vsf, json, pkl, vtkjs, html. Note '
    'that both vsf and json refer to the the JSON version of the VisualizationSet '
    'file and the distinction between the two is only for help in coordinating file '
    'extensions (since both .vsf and .json can be acceptable). Also note that '
    'ladybug-vtk must be installed in order for the vtkjs or html options to be usable '
    'and the html format refers to a web page with the vtkjs file embedded within it.',
    type=str, default='vsf', show_default=True)
@click.option(
    '--output-file', help='Optional file to output the JSON string of '
    'the config object. By default, it will be printed out to stdout',
    type=click.File('w'), default='-', show_default=True)
def model_to_vis_set(
        model_file, color_by, wireframe, mesh, show_color_by,
        room_attr, face_attr, color_attr, grid_display_mode, hide_grid,
        grid_data, grid_data_display_mode, active_grid_data, output_format, output_file):
    """Translate a Honeybee Model file (.hbjson) to a VisualizationSet file (.vsf).

    This command can also optionally translate the Honeybee Model to a .vtkjs file,
    which can be visualized in the open source Visual ToolKit (VTK) platform.

    \b
    Args:
        model_file: Full path to a Honeybee Model (HBJSON or HBpkl) file.
    """
    try:
        model_obj = Model.from_file(model_file)
        room_attrs = [] if len(room_attr) == 0 or room_attr[0] == '' else room_attr
        face_attrs = [] if len(face_attr) == 0 or face_attr[0] == '' else face_attr
        text_labels = not color_attr
        hide_color_by = not show_color_by

        face_attributes = []
        for fa in face_attrs:
            faa = FaceAttribute(name=fa, attrs=[fa], color=color_attr, text=text_labels)
            face_attributes.append(faa)

        room_attributes = []
        for ra in room_attrs:
            raa = RoomAttribute(name=ra, attrs=[ra], color=color_attr, text=text_labels)
            room_attributes.append(raa)

        vis_set = model_obj.to_vis_set(
            color_by=color_by, include_wireframe=wireframe, use_mesh=mesh,
            hide_color_by=hide_color_by, room_attrs=room_attributes,
            face_attrs=face_attributes, grid_display_mode=grid_display_mode,
            hide_grid=hide_grid, grid_data_path=grid_data,
            grid_data_display_mode=grid_data_display_mode,
            active_grid_data=active_grid_data)
        output_format = output_format.lower()
        if output_format in ('vsf', 'json'):
            output_file.write(json.dumps(vis_set.to_dict()))
        elif output_format == 'pkl':
            if output_file.name != '<stdout>':
                out_folder, out_file = os.path.split(output_file.name)
                vis_set.to_pkl(out_file, out_folder)
            else:
                output_file.write(pickle.dumps(vis_set.to_dict()))
        elif output_format in ('vtkjs', 'html'):
            if output_file.name == '<stdout>':  # get a temporary file
                out_file = str(uuid.uuid4())[:6]
                out_folder = tempfile.gettempdir()
            else:
                out_folder, out_file = os.path.split(output_file.name)
                if out_file.endswith('.vtkjs'):
                    out_file = out_file[:-6]
                elif out_file.endswith('.html'):
                    out_file = out_file[:-5]
            try:
                if output_format == 'vtkjs':
                    vis_set.to_vtkjs(output_folder=out_folder, file_name=out_file)
                if output_format == 'html':
                    vis_set.to_html(output_folder=out_folder, file_name=out_file)
            except AttributeError as ae:
                raise AttributeError(
                    'Ladybug-vtk must be installed in order to use --output-format '
                    'vtkjs.\n{}'.format(ae))
            if output_file.name == '<stdout>':  # load file contents to stdout
                out_file_ext = out_file + '.' + output_format
                out_file_path = os.path.join(out_folder, out_file_ext)
                if output_format == 'html':
                    with open(out_file_path, encoding='utf-8') as of:
                        f_contents = of.read()
                else:  # vtkjs can only be read as binary
                    with open(out_file_path, 'rb') as of:
                        f_contents = of.read()
                output_file.write(f_contents)
        else:
            raise ValueError('Unrecognized output-format "{}".'.format(output_format))
    except Exception as e:
        _logger.exception('Failed to translate Model to VisualizationSet.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


# add display sub-group to honeybee CLI
main.add_command(display)
