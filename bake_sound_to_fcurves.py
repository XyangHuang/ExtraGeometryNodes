import bpy
import os

from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

bl_info = {
        "name": "Back Sound To Fcurves",
        "author": "HXY",
        "version": (0,6,2),
        "blender": (2,90,0),
        "location": "Properties > Object",
        "category": "Animation",
        "description": "A tool to bake sound to f curves.",
        }


class CustomProperties(bpy.types.PropertyGroup):

    @staticmethod
    def initialize():
        bpy.types.Scene.sound_file_path = bpy.props.StringProperty(
            default='*.mp3;*.m4a;*.wav;',
            options={'HIDDEN'}
        )
        bpy.types.Scene.sound_bake_part = bpy.props.IntProperty(
            default=1,
            min=1,
            max=20
        )
        bpy.types.Scene.sound_bake_scale = bpy.props.FloatProperty(
            default=1,
            min=0.1,
            max=100
        )
        bpy.types.Scene.sound_gravity_fac = bpy.props.FloatProperty(
            default=1,
            min=0.01,
            max=100
        )

    @staticmethod
    def cleanup():
        del bpy.types.Scene.sound_file_path
        del bpy.types.Scene.sound_bake_part
        del bpy.types.Scene.sound_bake_scale
        del bpy.types.Scene.sound_gravity_fac
        
        
class SelectSoundFileBrowser(Operator, ImportHelper):

    bl_idname = "bake_sound.select_sound_file_browser"
    bl_label = "Select"
    
    filter_glob: StringProperty(
        default='*.mp3;*.m4a;*.wav;',
        options={'HIDDEN'}
    )
    
    some_boolean: BoolProperty(
        name='Do a thing',
        description='Do a thing with the file you\'ve selected',
        default=True,
    )

    def execute(self, context):
        """Do something with the selected file(s)."""

        filename, extension = os.path.splitext(self.filepath)
        
        bpy.context.scene.sound_file_path = self.filepath
        
        print('Selected file:', self.filepath)
        print('File name:', filename)
        print('File extension:', extension)
        print('Some Boolean:', self.some_boolean)
        
        return {'FINISHED'}


def remove_all_fcurves(obj):
    if obj.animation_data.action is not None:
        for fcurve in obj.animation_data.action.fcurves:
            obj.animation_data.action.fcurves.remove(fcurve)


def unselect_all_fcurves(obj):
    if obj.animation_data.action is not None:
        for fcurve in obj.animation_data.action.fcurves:
            fcurve.select = False


def change_fcurve_scale(obj, scale=1):
    for fcu in obj.animation_data.action.fcurves:
        if fcu.data_path == 'music' or fcu.data_path == 'music_g':
            for keyframe in fcu.sampled_points:
                keyframe.co[1] = keyframe.co[1] * scale
                

def change_fcurve_gravity(obj, gravity=1):
    i = 0
    last_i = i
    last_z = 0
    
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    a = 9.8 * gravity / fps / fps / 2
    
    for fcu in obj.animation_data.action.fcurves:
        if fcu.data_path == 'music_g':
            for keyframe in fcu.sampled_points:
                down_z = pow(i - last_i, 2) * a
                
                if keyframe.co[1] >= last_z - down_z:
                    last_z = keyframe.co[1]
                    last_i = i
                else:
                    keyframe.co[1] = last_z - down_z
                    last_z = last_z - down_z
                    
                i = i + 1


def bake_sound(n=1, scale=1):
    file = bpy.context.scene.sound_file_path
    if os.path.exists(file):
        pass
    else:
        return

    bpy.context.scene.frame_current = 1
    
    obj = bpy.context.active_object
    
    area_type = bpy.context.area.type
    bpy.context.area.type = 'GRAPH_EDITOR'
    step = 10000 / n

    remove_all_fcurves(obj)

    for i in range(n):
        unselect_all_fcurves(obj)
        obj.animation_data.action.fcurves.new(data_path='music', index=i, action_group='music')
        obj.animation_data.action.fcurves.new(data_path='music_g', index=i, action_group='music')
                
        l = i * step
        h = i * step + step
        bpy.ops.graph.sound_bake(filepath=file,low=l,high=h)

    change_fcurve_scale(obj, scale)
    change_fcurve_gravity(obj, bpy.context.scene.sound_gravity_fac)
    bpy.context.area.type = area_type
    

class BakeSoundToFcurves(Operator):

    bl_idname = "bake_sound.bake_sound_to_fcurves"
    bl_label = "Bake"

    def execute(self, context):
        """Do something with the selected file(s)."""

        bake_sound(context.scene.sound_bake_part, context.scene.sound_bake_scale)
        
        return {'FINISHED'}
        

class BakeSoundPanel(bpy.types.Panel):
    """Creates a Panel for baking sound"""
    bl_label = "Bake Sound To Fcurves"
    bl_idname = "bake_sound_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):  # mandatory with geonode
        if len(bpy.context.selected_objects) == 1:
            return True
        return False
    
    def draw(self, context):
        layout = self.layout

        scene = context.scene

        row = layout.row()
        row.prop(scene, "sound_file_path", text='Sound File')
        row.enabled = False
        row = layout.row()
        row.operator(SelectSoundFileBrowser.bl_idname)
        
        row = layout.row()
        row.prop(scene, "sound_bake_part", text='Parts')
        row = layout.row()
        row.prop(scene, "sound_bake_scale", text='Z Scale')
        row = layout.row()
        row.prop(scene, "sound_gravity_fac", text='Gravity Fac')
        
        row = layout.row()
        row.operator(BakeSoundToFcurves.bl_idname)


def register():
    bpy.utils.register_class(CustomProperties)
    bpy.utils.register_class(BakeSoundPanel)
    bpy.utils.register_class(SelectSoundFileBrowser)
    bpy.utils.register_class(BakeSoundToFcurves)
    
    CustomProperties.initialize()


def unregister():
    bpy.utils.unregister_class(BakeSoundPanel)
    bpy.utils.unregister_class(SelectSoundFileBrowser)
    bpy.utils.unregister_class(BakeSoundToFcurves)
    CustomProperties.cleanup()
    bpy.utils.unregister_class(CustomProperties)
    
if __name__ == "__main__":
    register()
