# Copyright (C) 2021 'Andrew Stevenson' & 'BD3D DIGITAL DESIGN, SLU'
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy

bl_info = {
    "name": "'Sound Falloff' for Geometry-Node",
    "author": "HXY",
    "description": "This plugin adds an extra node for Geometry-Node that will Get sound falloff",
    "blender": (3, 0, 0),
    "version": (1, 0, 0),
    "location": "Node Editor > Geometry Node > Add Menu > Extra",
    "warning": "",
    "tracker_url": "https://devtalk.blender.org/t/extra-nodes-for-geometrynodes/20942",
    "category": "Node"
}
# """

# About creating GeometryNodeCustomGroup:

# >Here are the possibilities:
#     - you can either create a custom interface that interact with a nodegroup
#     - or create simple input node, this plugin is only creating input values. all boiler plate below is dedicated to output sockets.

# > if you want to process data, forget about it:
#    - currently there's no way to get the value out of a socket, not sure how they could translate field to python.
#    - writing simple output value is possible, forget about fields tho.

# > update management is not ideal
#    - socket_value_update() function should send us signal when a socket value is being updated, the api is dead for now
#    - to update, rely on handlers or msgbus ( https://docs.blender.org/api/blender2.8/bpy.app.handlers.html?highlight=handler# module-bpy.app.handlers )

# > socket.type is read only, everything is hardcoded in operators
#    - to change socket type, we forced to use operator `bpy.ops.node.tree_socket_change_type(in_out='IN', socket_type='')` + context 'override'. this is far from ideal.
#      this means that changing socket type outside the node editor context is not possible.

# > in order to change the default value of an output, nodegroup.outputs[n].default value won't work use, api is confusing, it is done via the nodegroup.nodes instead:
#     - nodegroup.nodes["Group Output"].inputs[n].default_value  ->see boiler plate functions i wrote below

# > Warning `node_groups[x].outputs.new("NodeSocketBool","test")` is tricky, type need to be exact, no warning upon error, will just return none

# About this script:

# >You will note that there is an extra attention to detail in order to not register handlers twice

# >You will note that there is an extra attention in the extension of the Add menu with this new 'Extra' category.
#    In, my opinion all plugin nodes should be in this "Extra" menu.
#    Feel free to reuse the menu registration snippets so all custom node makers can share the 'Extra' menu without confilcts.

# """


#######################################################
# BOILER PLATE
#######################################################


def get_socket_value(ng, idx):
    return ng.nodes["Group Output"].inputs[idx].default_value


def set_socket_value(ng, idx, value=None):
    ng.nodes["Group Output"].inputs[idx].default_value = value
    return ng.nodes["Group Output"].inputs[idx].default_value


def set_socket_label(ng, idx, label=None):
    ng.outputs[idx].name = str(label)
    return None


def get_socket_type(ng, idx):
    return ng.outputs[idx].type


def set_socket_type(ng, idx, socket_type="NodeSocketFloat"):
    """set socket type via bpy.ops.node.tree_socket_change_type() with manual override, context MUST be the geometry node editor"""

    snode = bpy.context.space_data
    if snode is None:
        return None

    # forced to do a ugly override like this... eww
    restore_override = {"node_tree": snode.node_tree, "pin": snode.pin}
    snode.pin = True
    snode.node_tree = ng
    ng.active_output = idx
    bpy.ops.node.tree_socket_change_type(
        in_out='OUT', socket_type=socket_type
    )  # operator override is best, but which element do we need to override, not sure what the cpp operator need..

    # then restore... all this will may some signal to depsgraph
    for api, obj in restore_override.items():
        setattr(snode, api, obj)

    return None


# output socket
def create_socket(ng, socket_type="NodeSocketFloat", socket_name="Value"):
    socket = ng.outputs.new(socket_type, socket_name)
    return socket


# remove output socket
def remove_socket(ng, idx):
    todel = ng.outputs[idx]
    ng.outputs.remove(todel)
    return None


def create_new_nodegroup(name, sockets={}):
    """create new nodegroup with outputs from given dict {"name":"type",}, make sure given type are correct"""

    ng = bpy.data.node_groups.new(name=name, type="GeometryNodeTree")
    in_node = ng.nodes.new("NodeGroupInput")
    in_node.location.x -= 200
    out_node = ng.nodes.new("NodeGroupOutput")
    out_node.location.x += 200

    for socket_name, socket_type in sockets.items():
        create_socket(ng, socket_type=socket_type, socket_name=socket_name)

    # TODO now only support extra_node_sequencer_volume.py
    ng.inputs.new('NodeSocketFloat', 'volume')

    return ng


# def import_nodegroup(groupname, source_blend="extra_node_sound_falloff.blend",):
#     """import an existing nodegroup"""

#     import os

#     python_path = os.path.dirname(os.path.realpath(__file__))
#     lib_file = os.path.join(python_path,source_blend)

#     with bpy.data.libraries.load(lib_file,link=False) as (data_from,data_to):
#        data_to.node_groups.append(groupname)
#     group = bpy.data.node_groups[groupname]
#     group.use_fake_user = True

#     return group

#######################################################
# CUSTOM NODE
#######################################################


class EXTRANODESOUNDFALLOFF_NG_sound_falloff(bpy.types.GeometryNodeCustomGroup):

    bl_idname = "GeometryNodeSoundFalloff"
    bl_label = "Sound Falloff"

    debug_update_counter: bpy.props.IntProperty()  # visual aid debug

    current_obj: bpy.props.PointerProperty(type=bpy.types.Object)

    volume_fac: bpy.props.FloatProperty(default=1, min=0.1, max=100)
    enable_gravity: bpy.props.BoolProperty()
    gravity_fac: bpy.props.FloatProperty(default=1, min=0.1, max=100)
    enable_bounce: bpy.props.BoolProperty()
    max_bounce_height: bpy.props.FloatProperty(default=0.1,min=0, max=10)

    # inner params for calculating gravity and bounce
    last_frame: bpy.props.IntProperty(default=0,min=0)
    last_speed: bpy.props.FloatProperty(default=0, min=0)  # height per frame
    last_z: bpy.props.FloatProperty(default=0, min=0)

    # sound: bpy.props.PointerProperty(type=bpy.types.Sound) #,poll=sound_poll)

    @classmethod
    def poll(cls, context):  # mandatory with geonode
        return True

    def init(self, context):
        """this fct run when appending the node for the first time"""

        name = f".{self.bl_idname}"
        if name not in bpy.data.node_groups.keys():
            ng = create_new_nodegroup(name, sockets={
                "Falloff" : "NodeSocketFloat",
                "Gravity FallOff" : "NodeSocketFloat",
            })
        else:
            ng = bpy.data.node_groups[name].copy()

        self.node_tree = ng
        self.label = self.bl_label

        # get obj of this node
        self.current_obj = self.get_current_obj()

        # mark an update signal so handler fct do not need to loop every single nodegroups
        bpy.context.space_data.node_tree["extra_node_sound_falloff_update_needed"] = True

        return None

    def copy(self, node):
        """fct run when dupplicating the node"""
        self.node_tree = node.node_tree.copy()
        return None

    def update(self):
        """generic update function"""
        frame = bpy.context.scene.frame_current  # + self.frame_delay

        value = 0
        # TODO maybe current_node can be moved to init(), but don't know how to register the param
        current_node = self.get_current_node()
        if current_node is not None:
            if current_node.inputs[0].is_linked:
                # TODO now only support extra_node_sequencer_volume.py
                value = current_node.inputs[0].links[0].from_socket.node.node_tree.nodes["Group Output"].inputs[0].default_value
            else:
                value = current_node.inputs[0].default_value

        current_z = value * self.volume_fac
        if not self.enable_gravity:
            set_socket_value(self.node_tree, 0, current_z)
            set_socket_value(self.node_tree, 1, current_z)
            self.last_z = current_z
            self.last_frame = frame
            self.last_speed = 0
        else:
            set_socket_value(self.node_tree, 0, current_z)
            # if not bpy.context.screen.is_animation_playing:
            if frame < self.last_frame:
                set_socket_value(self.node_tree, 1, current_z)
                self.last_z = current_z
                self.last_frame = frame
                self.last_speed = 0
            else:
                diff_frame = frame - self.last_frame
                # if diff_frame < 0:
                #     diff_frame = 0
                gravity_z = self.last_z - 9.8 * self.gravity_fac * diff_frame * diff_frame / 1800

                if self.enable_bounce:
                    gravity_z = gravity_z + self.last_speed * diff_frame

                if gravity_z >= current_z:
                    set_socket_value(self.node_tree, 1, gravity_z)
                else:
                    set_socket_value(self.node_tree, 1, current_z)
                    self.last_z = current_z
                    self.last_frame = frame
                    self.last_speed = min(current_z - gravity_z, self.max_bounce_height)

        self.debug_update_counter += 1
        return None

    def get_current_obj(self):
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group.type == 'GEOMETRY':
                    for node in mod.node_group.nodes:
                        if hasattr(node, 'node_tree') and node.node_tree.name == self.node_tree.name:
                            return obj
        return None

    def get_current_node(self):
        if self.current_obj is None:
            return None

        for mod in self.current_obj.modifiers:
            if mod.type == 'NODES' and mod.node_group.type == 'GEOMETRY':
                for node in mod.node_group.nodes:
                    if hasattr(node, 'node_tree') and node.node_tree.name == self.node_tree.name:
                        return node

        return None


    # def socket_value_update(self,context):
    #    """dead api, revive me please?"""
    #    return None

    def draw_label(self,):
        """node label"""
        return "Sound Falloff"

    def draw_buttons(self, context, layout):
        """node interface drawing"""

        row = layout.row(align=True)
        row.prop(self, "volume_fac", text="Volume Fac")

        box = layout.box()
        box.active = self.enable_gravity
        sub = box.row(align=True)
        sub.prop(self, "enable_gravity", text="Gravity", icon="WORLD")
        sub.prop(self, "gravity_fac", text="Fac")
        sub = box.row(align=True)
        sub.prop(self, "enable_bounce", text="Bounce", icon="MOD_PHYSICS")
        sub.prop(self, "max_bounce_height", text="Max")

        if bpy.context.preferences.addons["extra_node_sound_falloff"].preferences.debug:
            box = layout.column()
            box.active = False
            box.prop(self, "node_tree", text="")
            box.prop(self, "debug_update_counter", text="update count")

        return None



#######################################################
# HANDLER UPDATE
#######################################################


def update_node():
    # search for nodes all over data and update
    for n in [
            n for ng in bpy.data.node_groups if ("extra_node_sound_falloff_update_needed" in ng) for n in ng.nodes
            if (n.bl_idname == "GeometryNodeSoundFalloff")
    ]:
        n.update()
    return None 


@bpy.app.handlers.persistent
def extra_node_sound_falloff_depsgraph(scene, desp):  # used for Api node, if allowed!
    """update on depsgraph change"""
    if bpy.context.preferences.addons["extra_node_sound_falloff"].preferences.debug:
        print("extra_node_sound_falloff: depsgraph signal")
    update_node()
    return None


@bpy.app.handlers.persistent
def extra_node_sound_falloff_frame_pre(scene, desp):  # used for Volume and Api Node!
    """update on frame change"""
    if bpy.context.preferences.addons["extra_node_sound_falloff"].preferences.debug:
        print("extra_node_sound_falloff: frame_pre signal")
    update_node()
    return None


def all_handlers():
    """return a list of handler stored in .blend"""

    return_list = []
    for oh in bpy.app.handlers:
        try:
            for h in oh:
                return_list.append(h)
        except:
            pass
    return return_list


def register_handlers(status):
    """register dispatch for handlers"""

    if (status == "register"):

        all_handler_names = [h.__name__ for h in all_handlers()]

        # depsgraph
        if "extra_node_sound_falloff_depsgraph" not in all_handler_names:
            bpy.app.handlers.depsgraph_update_post.append(extra_node_sound_falloff_depsgraph)

        # frame_change
        if "extra_node_sound_falloff_frame_pre" not in all_handler_names:
            bpy.app.handlers.frame_change_pre.append(extra_node_sound_falloff_frame_pre)

        return None

    elif (status == "unregister"):

        for h in all_handlers():

            # depsgraph
            if (h.__name__ == "extra_node_sound_falloff_depsgraph"):
                bpy.app.handlers.depsgraph_update_post.remove(h)

            # frame_change
            if (h.__name__ == "extra_node_sound_falloff_frame_pre"):
                bpy.app.handlers.frame_change_pre.remove(h)

    return None


#######################################################
# EXTEND MENU
#######################################################

# extra menu


def extra_geonode_menu(self, context):
    """extend NODE_MT_add with new extra menu"""
    self.layout.menu("NODE_MT_category_GEO_EXTRA", text="Extra")
    return None


class NODE_MT_category_GEO_EXTRA(bpy.types.Menu):

    bl_idname = "NODE_MT_category_GEO_EXTRA"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return (bpy.context.space_data.tree_type == "GeometryNodeTree")

    def draw(self, context):
        return None


# extra menu extension


def extra_node_sound_falloff(self, context):
    """extend extra menu with new node"""
    op = self.layout.operator("node.add_node", text="Sound Falloff")
    op.type = "GeometryNodeSoundFalloff"
    op.use_transform = True


# register


def register_menus(status):
    """register extra menu, if not already, append item, if not already"""

    if (status == "register"):

        # register new extra menu class if not exists already, perhaps another plugin already implemented it
        if "NODE_MT_category_GEO_EXTRA" not in bpy.types.__dir__():
            bpy.utils.register_class(NODE_MT_category_GEO_EXTRA)

        # extend add menu with extra menu if not already, _dyn_ui_initialize() will get appended drawing functions of a menu
        add_menu = bpy.types.NODE_MT_add
        if "extra_geonode_menu" not in [f.__name__ for f in add_menu._dyn_ui_initialize()]:
            add_menu.append(extra_geonode_menu)

        # extend extra menu with our custom nodes if not already
        extra_menu = bpy.types.NODE_MT_category_GEO_EXTRA
        if "extra_node_sound_falloff" not in [f.__name__ for f in extra_menu._dyn_ui_initialize()]:
            extra_menu.append(extra_node_sound_falloff)

        return None

    elif (status == "unregister"):

        add_menu = bpy.types.NODE_MT_add
        extra_menu = bpy.types.NODE_MT_category_GEO_EXTRA

        # remove our custom function to extra menu
        for f in extra_menu._dyn_ui_initialize().copy():
            if (f.__name__ == "extra_node_sound_falloff"):
                extra_menu.remove(f)

        # if extra menu is empty
        if len(extra_menu._dyn_ui_initialize()) == 1:

            # remove our extra menu item draw fct add menu
            for f in add_menu._dyn_ui_initialize().copy():
                if (f.__name__ == "extra_geonode_menu"):
                    add_menu.remove(f)

            # unregister extra menu
            bpy.utils.unregister_class(extra_menu)

    return None


#######################################################
# PROPERTIES & PREFS
#######################################################


class EXTRANODESOUNDFALLOFF_AddonPref(bpy.types.AddonPreferences):
    """addon_prefs = bpy.context.preferences.addons["extra_node_sound_falloff"].preferences"""

    bl_idname = "extra_node_sound_falloff"

    debug: bpy.props.BoolProperty(default=False)

    # drawing part in ui module
    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.prop(self, "debug", text="Debug Mode")

        return None


#######################################################
# INIT REGISTRATION
#######################################################

classes = [
    EXTRANODESOUNDFALLOFF_AddonPref,
    EXTRANODESOUNDFALLOFF_NG_sound_falloff,
]


def register():

    # classes
    for cls in classes:
        bpy.utils.register_class(cls)

    # extend add menu
    register_menus("register")

    # handlers
    register_handlers("register")

    return None


def unregister():

    # handlers
    register_handlers("unregister")

    # extend add menu
    register_menus("unregister")

    # classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    return None


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
